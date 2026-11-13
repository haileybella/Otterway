from flask import Flask, request
from openai import OpenAI
from twilio.twiml.voice_response import VoiceResponse, Gather

app = Flask(__name__)

client = OpenAI(base_url="http://10.184.237.138:8000/v1", api_key="NONE", timeout=4)

QWEN_MODEL = "Qwen/Qwen3-VL-8B-Instruct"
LOCATION = "UT San Antonio"  # test value for now

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
    if not said:
        return speak_then_listen("Sorry, I didn't catch that. Where are you trying to get to?")

    messages.append({"role": "user", "content": said})
    try:
        completion = client.chat.completions.create(
            model=QWEN_MODEL, messages=messages, max_tokens=80
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