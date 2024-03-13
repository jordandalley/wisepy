# WisePy

Creates a webhook on port 8888 that listens for incoming connections from Wise (formally Transferwise). I frontend my implementation of this using Cloudflare.

Match the variables in the python file to your choosing. On a "Balance Deposit" event, Wise will trigger an http POST. If it matches the specified amount and currency, it'll use Wise API's to kick off an automated transfer to an account and destination currency of your choice.
