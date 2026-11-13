import os
import re
import smtplib
import threading
from datetime import datetime
from email.message import EmailMessage

from flask import Flask, request
from openai import OpenAI
from twilio.twiml.voice_response import VoiceResponse, Gather

app = Flask(__name__)

client = OpenAI(base_url="http://10.184.237.138:8000/v1", api_key="NONE", timeout=4)

QWEN_MODEL = "Qwen/Qwen3-VL-8B-Instruct"
LOCATION = "UT San Antonio"  # test value for now
BASE_URL = "https://harvest-trickster-upscale.ngrok-free.dev"

GMAIL_SENDER = os.environ.get("GMAIL_SENDER")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD")
TRANSCRIPT_TO = os.environ.get("TRANSCRIPT_TO")

GOODBYE = re.compile(r"\b(bye|goodbye)\b", re.IGNORECASE)

SYSTEM = (
    f"You are a flood safety assistant talking with someone on a phone call. The caller is at {LOCATION}. "
    "They may be stressed or on the move, and they hear your words read aloud. Reply in one to "
    "three short, plain sentences, with no lists and no special characters. If you are not sure "
    "what they said, ask them to repeat it. "

    "What you know: you have no live information about which places or roads are flooded, closed, "
    "safe or clear, so never claim that about any specific place or road. Route lookup is not "
    "connected yet, so if asked for directions, say so. You can give the general flood safety "
    "guidance below. "

    "How the call should go: when the caller names a destination, repeat it back to confirm it. "
    "If they have not said how they plan to travel, ask. "

    "Judging the travel plan: the danger is the flood water itself, and it is the same whether "
    "someone is alone or in a group. Never suggest that travelling with other people makes an "
    "unsafe plan safe. Walking, cycling, or riding a motorcycle or scooter where there may be "
    "flood water is unsafe, because six inches of moving water can knock an adult off their feet, "
    "and water hides open drains, debris and downed power lines. Driving is safer than being on "
    "foot or on a bike, but only on roads with no water on them, because a foot of moving water "
    "can carry away a car and its depth is impossible to judge, especially at night. Drivers "
    "should never enter water covering a road and should avoid low water crossings, underpasses "
    "and roads beside creeks or rivers. "

    "Safer options: if the trip is not urgent and the caller is somewhere dry and on high ground, "
    "the safest choice is usually to stay there until the water goes down. If they have to leave "
    "because where they are is unsafe, they should head for higher ground or the nearest shelter "
    "and turn around if they meet water. "

    "When the caller's plan is unsafe, say so plainly, give the reason in one sentence, and offer "
    "the safer option that fits their situation. Say it once and calmly, without lecturing or "
    "repeating it every turn. If their plan is reasonable, do not invent a warning. "

    "Emergencies: naming a destination or asking a question is not an emergency. Tell the caller "
    "to hang up and call 911 only if they describe immediate danger, such as being trapped, water "
    "entering their car or home, being swept along by water, or someone being hurt."
)
GREETING = (
    "Hi, this is Ollie. I can help you look up directions. If you're in immediate danger or need "
    "emergency help, slide the button to call nine-one-one. "
    "For non-emergency city services in San Antonio, call three-one-one, or two-one-zero, "
    "two-zero-seven, six-zero-zero-zero. "
    f"I have your location as {LOCATION}. Where are you trying to get to?"
)

history = {}      # what Qwen sees, one list per call, kept in memory only
transcripts = {}  # every spoken line, one list per call, for the email


def log(speaker, text):
    print(f"{speaker}: {text}", flush=True)
    transcripts.setdefault(request.values["CallSid"], []).append(f"{speaker}: {text}")


def send_transcript(call_sid):
    lines = transcripts.pop(call_sid, None)  # popping means it can only be sent once
    history.pop(call_sid, None)
    if not lines:
        return
    if not (GMAIL_SENDER and GMAIL_APP_PASSWORD and TRANSCRIPT_TO):
        print("Email not sent: GMAIL_SENDER, GMAIL_APP_PASSWORD or TRANSCRIPT_TO is not set")
        return

    msg = EmailMessage()
    msg["Subject"] = f"Flood line call transcript, {datetime.now():%Y-%m-%d %H:%M}"
    msg["From"] = GMAIL_SENDER
    msg["To"] = TRANSCRIPT_TO
    msg.set_content(
        f"Call ID: {call_sid}\nCaller location: {LOCATION}\n\n" + "\n".join(lines)
    )

    def deliver():
        try:
            with smtplib.SMTP("smtp.gmail.com", 587, timeout=20) as smtp:
                smtp.starttls()
                smtp.login(GMAIL_SENDER, GMAIL_APP_PASSWORD)
                smtp.send_message(msg)
            print("Transcript emailed", flush=True)
        except Exception as err:
            print("Email error:", err, flush=True)

    # Sent in the background so the call never waits on the email.
    threading.Thread(target=deliver, daemon=True).start()


def speak_then_listen(text):
    log("AGENT", text)
    resp = VoiceResponse()
    gather = Gather(input="speech", action=f"{BASE_URL}/turn", speech_timeout="auto")
    gather.say(text)
    resp.append(gather)
    resp.redirect(f"{BASE_URL}/turn")  # reached only if the caller says nothing
    return str(resp), 200, {"Content-Type": "text/xml"}


def speak_then_hang_up(text):
    log("AGENT", text)
    resp = VoiceResponse()
    resp.say(text)
    resp.hangup()
    return str(resp), 200, {"Content-Type": "text/xml"}


@app.route("/voice", methods=["GET", "POST"])
def voice():
    history[request.values["CallSid"]] = [
        {"role": "system", "content": SYSTEM},
        {"role": "assistant", "content": GREETING},
    ]
    return speak_then_listen(GREETING)


@app.route("/turn", methods=["GET", "POST"])
def turn():
    call_sid = request.values["CallSid"]
    messages = history.setdefault(call_sid, [{"role": "system", "content": SYSTEM}])
    said = request.values.get("SpeechResult")
    if not said:
        return speak_then_listen("Sorry, I didn't catch that. Where are you trying to get to?")
    log("CALLER", said)
    print("  confidence:", request.values.get("Confidence"), flush=True)

    if GOODBYE.search(said) and len(said.split()) <= 6:
        response = speak_then_hang_up("Goodbye, and stay safe.")
        send_transcript(call_sid)
        return response

    messages.append({"role": "user", "content": said})
    try:
        completion = client.chat.completions.create(
            model=QWEN_MODEL, messages=messages, max_tokens=120, temperature=0.2
        )
        reply = completion.choices[0].message.content
    except Exception as err:
        print("Qwen error:", err)
        messages.pop()  # forget the turn that failed
        return speak_then_listen("Sorry, I had trouble with that. Could you say it again?")

    messages.append({"role": "assistant", "content": reply})
    return speak_then_listen(reply)


@app.route("/status", methods=["GET", "POST"])
def status():
    # Twilio calls this when the call ends, including when the caller just hangs up.
    send_transcript(request.values["CallSid"])
    return "", 204


if __name__ == "__main__":
    app.run(port=5000)