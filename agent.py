import requests
from flask import Flask, request
from twilio.twiml.voice_response import VoiceResponse, Gather

app = Flask(__name__)

QWEN_URL = "http://localhost:11434/v1/chat/completions"  # change to match how Qwen is served
QWEN_MODEL = "your-qwen-model-name"
LOCATION = "Main Street and 5th Avenue"                  # test value for now

SYSTEM = (
    f"You are a flood safety assistant on a phone call. The caller is at {LOCATION}. "
    "Reply in one or two short sentences. If the caller is in danger, tell them to hang up "
    "and call emergency services. You have no live flood or road data yet, so never invent routes."
)
GREETING = (
    f"Hi, this is the flood safety line calling you back. "
    f"I have your location as {LOCATION}. Where are you trying to get to?"
)

history = {}  # one conversation per call, kept in memory only


def speak_then_listen(text):
    resp = VoiceResponse()
    gather = Gather(input="speech", action="/turn", speech_timeout="auto")
    gather.say(text)
    resp.append(gather)
    resp.redirect("/turn")  # reached only if the caller says nothing
    return str(resp), 200, {"Content-Type": "text/xml"}


@app.post("/voice")
def voice():
    history[request.form["CallSid"]] = [
        {"role": "system", "content": SYSTEM},
        {"role": "assistant", "content": GREETING},
    ]
    return speak_then_listen(GREETING)


@app.post("/turn")
def turn():
    messages = history.setdefault(
        request.form["CallSid"], [{"role": "system", "content": SYSTEM}]
    )
    said = request.form.get("SpeechResult")
    if not said:
        return speak_then_listen("Sorry, I didn't catch that. Where are you trying to get to?")

    messages.append({"role": "user", "content": said})
    r = requests.post(
        QWEN_URL,
        json={"model": QWEN_MODEL, "messages": messages, "max_tokens": 80},
        timeout=4,  # Twilio gives up after 5 seconds
    )
    reply = r.json()["choices"][0]["message"]["content"]
    messages.append({"role": "assistant", "content": reply})
    return speak_then_listen(reply)


if __name__ == "__main__":
    app.run(port=5000)