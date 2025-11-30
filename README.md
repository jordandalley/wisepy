# No longer maintained

Moved this function to Cloudflare workers so I don't have to run any infra: https://github.com/jordandalley/autowise

# WisePy

WisePy creates a webhook listener using Flask that listens for incoming connections from Wise (formally Transferwise).

When parameters (set in variables at the top of the script) are met, a transfer is initiated using the Wise API.

# Dependencies

WisePy requires Python3 and the following modules:

- uuid
- requests
- threading
- flask
- gevent

# Implementation

*** I highly recommend testing this with the Wise sandbox first, to test all is good: https://sandbox.transferwise.tech/ ***

Step 1 - Creating an API token:

1. Login to Wise, go to your profile, click 'Settings' then 'API Tokens'
2. Click 'Add Token'

Step 2 - Create a target account:

1. Login to Wise, and go to 'Recipients'
2. Click 'Add Recipient'
3. Add the target bank account and currency

Step 3 - Modify the wise.py script:

1. Edit the 'wise_api_token' variable with the API token that you configured in step 1
2. Edit the 'wise_source_currency' variable to the source currency you're being paid in
3. Edit the 'wise_target_currency' variable to the target currency you wish to send your deposit to (created in step 2)
4. Edit the 'wise_minimum_deposit' variable to the amount (in source currency) being paid that will trigger an automated transfer. Eg, you may wish to not automate a transfer
5. Edit the 'wise_target_account_number' variable to the account number that was put into the target account in step 2

Step 4 - Front-Ending the webhook:

The Webhook listens for http POSTS on http://127.0.0.1:8888/balance-update

This webhook will need to be front-ended according to Wise's requirements for it to work.

For more information on Wise's requirements, please visit: https://docs.wise.com/api-docs/features/webhooks-notifications

Front ending could be achieved using a web server such as Apache or Nginx with an SSL certificate from Letsencrypt, or it could be frontended by a service such as Cloudflare.

Step 5 - Creating the Webhook:

1. Login to Wise, go to your profile, click 'Settings' then 'Webhooks'
2. Create a webhook and test

<img width="458" alt="image" src="https://github.com/jordandalley/wisepy/assets/7189075/04018538-6715-4f2d-a4ec-61f9ee73eb94">

3. If all good, then it should show tests as successful.

Step 6 - Daemonising the script:

You may wish to set this script up in systemd as a service. A sample wisepy.service file is included in this repository to get you started.
