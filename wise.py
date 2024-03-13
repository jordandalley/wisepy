import sys
import uuid
import requests
import threading
from flask import Flask, request
from gevent.pywsgi import WSGIServer

# Check if Python version is less than 3
if sys.version_info < (3, 0):
    print("This script requires Python 3 or later to run.")
    sys.exit(1)

# Production
#wise_api_url = "https://api.transferwise.com"
#wise_api_token = "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"

# Test Sandbox
wise_api_url = "https://api.sandbox.transferwise.tech"
wise_api_token = "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"

# Source and Target currencies
wise_source_currency = "AUD"
wise_target_currency = "NZD"

# Minimum amount is whole dollars that will trigger an automatic transfer
wise_minimum_deposit = 1000

# Target account number of the recipient receiving the funds
wise_target_account_number = "060901078703100"

# Port to run the flask webhook on
webhook_port = 8888

app = Flask(__name__)

@app.route('/balance-update', methods=['POST'])
def webhook():
    try:
        # Get the data from the webhook
        webhook_data = request.json

        webhook_currency = webhook_data['data']['currency']
        #webhook_currency = "AUD"
        webhook_transaction_type = webhook_data['data']['transaction_type']
        webhook_amount = webhook_data['data']['amount']
        #webhook_amount = 5335
        webhook_balance = webhook_data['data']['post_transaction_balance_amount']

        if webhook_transaction_type == "credit" and webhook_currency == wise_source_currency and webhook_amount >= wise_minimum_deposit:
            # If transaction from webhook is a 'credit', the currency matches the wise_source_currency and the deposit amount is more than or equal to the wise_minimum_deposit, initiate a new thread for processing the transfer api calls
            print(f"An amount of ${webhook_amount} was deposited into your {webhook_currency} account. Beginning transfer...")
            transfer_thread = threading.Thread(target=handle_transfer, args=(webhook_amount,))
            transfer_thread.start()
        else:
            # A webhook was received but didn't meet the criteria to initiate a transfer
            print(f"An amount of ${webhook_amount} was deposited into your {webhook_currency} account which doesn't meet the parameters for a transfer. Exiting.")
            return '', 200

    except KeyError as e:
        print("KeyError: Missing key in JSON data:", e)
        return 'Bad Request', 400  # Return 400 Bad Request status if key is missing

    except Exception as e:
        print("An error occurred:", e)
        return 'Internal Server Error', 500  # Return 500 Internal Server Error for other exceptions

    return '', 200  # Return 200 OK if everything is processed successfully

def handle_transfer(webhook_amount):
    # Kicks off a new thread to handle the beginning of the transfer
    try:
        getProfile(webhook_amount)
    except Exception as e:
        print("An error occurred during transfer:", e)

def getProfile(webhook_amount):
    try:
        # Fetch the profile ID related to a personal account (change to business if it's a business account)
        profile_response = requests.get(f"{wise_api_url}/v1/profiles", headers={"Authorization": f"Bearer {wise_api_token}"})

        # Check if the request was successful
        profile_response.raise_for_status()

        profile_json = profile_response.json()
        profile_id = next((profile['id'] for profile in profile_json if profile['type'] == 'personal'), None)

        if profile_id:
            # Profile ID fetched - move onto finding the recipient in the target currency
            getRecipient(webhook_amount, profile_id)
        else:
            print("Error: Personal profile not found.")
    except requests.exceptions.RequestException as e:
        print("Error fetching profile:", e)
    except Exception as e:
        print("An unexpected error occurred while fetching profile:", e)

def getProfile(webhook_amount):
    try:
        # Fetch the profile ID related to a personal account (change to business if it's a business account)
        profile_response = requests.get(f"{wise_api_url}/v1/profiles", headers={"Authorization": f"Bearer {wise_api_token}"})

        # Check if the request was successful
        profile_response.raise_for_status()

        profile_json = profile_response.json()
        profile_id = next((profile['id'] for profile in profile_json if profile['type'] == 'personal'), None)

        if profile_id:
            # Profile ID fetched - move onto finding the recipient in the target currency
            getRecipient(webhook_amount, profile_id)
        else:
            print("Error: Personal profile not found.")
    except requests.exceptions.RequestException as e:
        print("Error fetching profile:", e)
    except KeyError as e:
        print("KeyError while processing profile JSON data:", e)
    except StopIteration:
        print("Error: No personal profile found.")
    except Exception as e:
        print("An unexpected error occurred while fetching profile:", e)

def getRecipient(webhook_amount, profile_id):
    try:
        recipient_response = requests.get(f"{wise_api_url}/v1/accounts?currency={wise_target_currency}", headers={"Authorization": f"Bearer {wise_api_token}"})

        # Check if the request was successful
        recipient_response.raise_for_status()

        recipient_json = recipient_response.json()
        recipient_account = next((account for account in recipient_json if account['details']['accountNumber'] == wise_target_account_number), None)

        if recipient_account is None:
            print(f"ERROR: No recipient matches the account number {wise_target_account_number}")
            return
        else:
            recipient_name = recipient_account['accountHolderName']
            recipient_id = recipient_account['id']
            print(f"Found recipient {recipient_name} by account number \"{wise_target_account_number}\"...")

        getQuote(webhook_amount, profile_id, recipient_id)
    except requests.exceptions.RequestException as e:
        print("Error fetching recipient:", e)
    except KeyError as e:
        print("KeyError while processing recipient JSON data:", e)
    except StopIteration:
        print("Error: No recipient found for the specified account number.")
    except Exception as e:
        print("An unexpected error occurred while fetching recipient:", e)

def getQuote(webhook_amount, profile_id, recipient_id):
    try:
        quote_data = {
            "sourceCurrency": wise_source_currency,
            "targetCurrency": wise_target_currency,
            "sourceAmount": webhook_amount,
            "targetAmount": None,
            "payOut": "BANK_TRANSFER",
            "preferredPayIn": "BALANCE"
        }

        quote_response = requests.post(f"{wise_api_url}/v3/profiles/{profile_id}/quotes", headers={"Authorization": f"Bearer {wise_api_token}", "Content-Type": "application/json"}, json=quote_data)

        # Check if the request was successful
        quote_response.raise_for_status()

        quote_json = quote_response.json()
        quote_id = quote_json['id']
        pair_rate = quote_json['rate']
        source_amount = quote_json['sourceAmount']
        target_amount = next((option['targetAmount'] for option in quote_json['paymentOptions'] if option['payIn'] == 'BALANCE'), None)
        wise_fee = next((option['fee']['total'] for option in quote_json['paymentOptions'] if option['payIn'] == 'BALANCE'), None)

        print("*** Quotation Received ***")
        print(f"Current Rate: {pair_rate}")
        print(f"Source Amount: ${source_amount} {wise_source_currency}")
        print(f"Wise Fee: ${wise_fee} {wise_source_currency}")
        print(f"Target Amount: ${target_amount} {wise_target_currency}")

        startTransfer(profile_id, recipient_id, quote_id)

    except requests.exceptions.RequestException as e:
        print("Error fetching quote:", e)
    except KeyError as e:
        print("KeyError while processing quote JSON data:", e)
    except StopIteration:
        print("Error: No payment option found for BALANCE.")
    except Exception as e:
        print("An unexpected error occurred while fetching quote:", e)

def startTransfer(profile_id, recipient_id, quote_id):
    try:
        print("Beginning Transfer Request...")
        transfer_data = {
            "targetAccount": recipient_id,
            "quoteUuid": quote_id,
            "customerTransactionId": str(uuid.uuid4()),
            "details": {
                "reference": "Salary",
                "transferPurpose": "Salary",
                "transferPurposeSubTransferPurpose": "Salary",
                "sourceOfFunds": "Salary"
            }
        }

        transfer_response = requests.post(f"{wise_api_url}/v1/transfers", headers={"Authorization": f"Bearer {wise_api_token}", "Content-Type": "application/json"}, json=transfer_data)

        # Check if the request was successful
        transfer_response.raise_for_status()

        transfer_json = transfer_response.json()
        transfer_id = transfer_json['id']

        fund_data = {
            "type": "BALANCE"
        }

        fund_response = requests.post(f"{wise_api_url}/v3/profiles/{profile_id}/transfers/{transfer_id}/payments", headers={"Authorization": f"Bearer {wise_api_token}", "Content-Type": "application/json"}, json=fund_data)

        # Check if the request was successful
        fund_response.raise_for_status()

        fund_json = fund_response.json()
        fund_status = fund_json['status']
        print(f"Funding has been completed with status: {fund_status}")

    except requests.exceptions.RequestException as e:
        print("Error starting transfer:", e)
    except KeyError as e:
        print("KeyError while processing transfer JSON data:", e)
    except Exception as e:
        print("An unexpected error occurred while starting transfer:", e)

if __name__ == '__main__':
    # Development
    #app.run(debug=True, host='0.0.0.0', port=webhook_port)
    # Production
    http_server = WSGIServer(('', webhook_port), app)
    http_server.serve_forever()
