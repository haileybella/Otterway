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
    "their car or home, or someone being hurt. "
    "If their mode of transport is dangerous, such as walking during a flood or driving "
    "during heavy rain, notify the caller and provide a safer alternative, such as traveling "
    "with other people, waiting for the storm to pass, or finding a safe shelter."
)
GREETING = (
    f"Hi, this is Ollie. I can help you look up directions. If you’re in immediate danger or need "
    f"emergency help, slide the button to call nine-one-one. "
    f" For non-emergency city services in San Antonio, call three-one-one, or two-one-zero,"
    f" two-zero-seven, six-zero-zero-zero."
    f"I have your location as {LOCATION}. Where are you trying to get to?"
)

history = {}  # one conversation per call, kept in memory only




The City of San Antonio’s 311 page confirms both city service numbers, and San Antonio Police lists 911 for emergencies.

Once the map returns a route
I found a route to [destination]. Your first step is [map instruction]. You can say “repeat that” to hear it again, or “find another route” if your location changed or the way is blocked.

When the caller asks for help again
“Repeat that.” Read back the last instruction. If the caller has moved or missed a turn, confirm where they are before giving a new step.
“Find another route” or “The road is blocked.” Say, “I can check for another route. Where are you now?” Use the updated location and avoid the reported blockage if the map supports it. If no suitable route comes back, say, “I couldn’t find another route from here.”
“I need help.” If the caller describes immediate danger, direct them to 911 right away. If it’s unclear, ask, “Are you in immediate danger, or do you need help with directions?”
For the demo, “I can check for another route” is the promise to make once rerouting is wired up. A map result can provide directions, but Ollie should never call a route safe or send someone through a reported blockage.

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