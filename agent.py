from flask import Flask, request
from openai import OpenAI
from twilio.twiml.voice_response import VoiceResponse, Gather

app = Flask(__name__)

client = OpenAI(base_url="http://10.184.237.138:8000/v1", api_key="NONE", timeout=4)

QWEN_MODEL = "Qwen/Qwen3-VL-8B-Instruct"
LOCATION = "UT San Antonio"  # test value for now
BASE_URL = "https://harvest-trickster-upscale.ngrok-free.dev"

SYSTEM = (
    f"You are a flood safety assistant on a phone call. The caller is at {LOCATION}. "
    "Reply in one or two short sentences. "
    "You have NO information about which places or roads are flooded. "
    "Never say that any place or road is flooded, closed, safe or clear. "
    "When the caller names a destination, repeat it back to confirm it, then say that "
    "route lookup is not connected yet. "
    "Naming a destination is not an emergency. Only tell the caller to hang up and call 911 "
    "if they themselves describe immediate danger, such as being trapped, water entering "
    "their car or home, or someone being hurt."
)
GREETING = (
    f"Hi, this is the flood safety line calling you back. "
    f"I have your location as {LOCATION}. Where are you trying to get to?"
)

history = {}  # one conversation per call, kept in memory only


def speak_then_listen(text):
    print("AGENT: ", text, flush=True)
    resp = VoiceResponse()
    gather = Gather(input="speech", action=f"{BASE_URL}/turn", speech_timeout="auto")
    gather.say(text)
    resp.append(gather)
    resp.redirect(f"{BASE_URL}/turn")  # reached only if the caller says nothing
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
    messages = history.setdefault(
        request.values["CallSid"], [{"role": "system", "content": SYSTEM}]
    )
    said = request.values.get("SpeechResult")
    print("CALLER:", said, "| confidence:", request.values.get("Confidence"), flush=True)
    if not said:
        return speak_then_listen("Sorry, I didn't catch that. Where are you trying to get to?")

    messages.append({"role": "user", "content": said})
    try:
        completion = client.chat.completions.create(
            model=QWEN_MODEL, messages=messages, max_tokens=80, temperature=0.2
        )
        reply = completion.choices[0].message.content
    except Exception as err:
        print("Qwen error:", err)
        messages.pop()  # forget the turn that failed
        return speak_then_listen("Sorry, I had trouble with that. Could you say it again?")

    messages.append({"role": "assistant", "content": reply})
    return speak_then_listen(reply)


if __name__ == "__main__":
    app.run(port=5000)