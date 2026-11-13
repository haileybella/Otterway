import os
from twilio.rest import Client

client = Client()  # reads TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN
call = client.calls.create(
    to=os.environ["MY_PHONE"],           # your verified mobile
    from_=os.environ["TWILIO_NUMBER"],   # your Twilio trial number
    url="https://harvest-trickster-upscale.ngrok-free.dev/voice",
)
print(call.sid)