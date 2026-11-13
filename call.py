from twilio.rest import Client

client = Client()  # reads TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN
call = client.calls.create(
    to="+1XXXXXXXXXX",     # your verified mobile
    from_="+1XXXXXXXXXX",  # your Twilio trial number
    url="https://YOUR-TUNNEL-ADDRESS/voice",
)
print(call.sid)