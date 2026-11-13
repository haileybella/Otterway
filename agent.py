import os
import re
import smtplib
import threading
import time
from datetime import datetime
from email.message import EmailMessage
from urllib.parse import urlencode

from flask import Flask, request
from openai import OpenAI
from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse, Gather

import server  # Otterway's route server: flood data, place lookup and flood-avoiding routes

app = Flask(__name__)

client = OpenAI(base_url="http://10.184.237.138:8000/v1", api_key="NONE", timeout=4)

QWEN_MODEL = "Qwen/Qwen3-VL-8B-Instruct"
LOCATION = "UT San Antonio"  # test value for now
LOCATION_COORDS = (29.5831, -98.6199)  # latitude, longitude of that test location
BASE_URL = "https://harvest-trickster-upscale.ngrok-free.dev"

GMAIL_SENDER = os.environ.get("GMAIL_SENDER")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD")
TRANSCRIPT_TO = os.environ.get("TRANSCRIPT_TO")

GOODBYE = re.compile(r"\b(bye|goodbye)\b", re.IGNORECASE)
# Qwen asks for a route lookup by replying with a line such as "LOOKUP: Blanco, Texas".
LOOKUP = re.compile(r"^\s*LOOKUP:\s*(.+?)\s*$", re.IGNORECASE | re.MULTILINE)

SYSTEM = (
    f"You are a flood safety assistant talking with someone on a phone call. The caller is at {LOCATION}. "
    "They may be stressed or on the move, and they hear your words read aloud. Reply in one to "
    "three short, plain sentences, with no lists and no special characters. If you are not sure "
    "what they said, ask them to repeat it. "

    "Route lookups: you cannot see maps or flood data yourself. Otterway's map system does the "
    "lookup for you. When the caller tells you where they want to go, reply with exactly one line "
    "in this form and nothing else: LOOKUP: followed by the destination as a place name or "
    "address, for example LOOKUP: Blanco, Texas. Include the city or state if the caller said it. "
    "If you could not make out the destination, ask them to repeat it instead. The map system "
    "then tells the caller which place it matched and what it found. "

    "After a lookup you will see a message that begins with ROUTE RESULT. It comes from the map "
    "system, not from the caller, and it is your only source of facts about routes, roads and "
    "flooding. Answer follow-up questions, such as what the next directions are, using only what "
    "it says. Never say that a place or road is flooded, closed, safe or clear, and never give "
    "directions, unless a ROUTE RESULT says so. If the caller names a different destination, send "
    "a new LOOKUP line. The routes are driving routes. You can also give the general flood safety "
    "guidance below. "

    "How the call should go: when the caller names a destination, send the LOOKUP line straight "
    "away. After the result, if they have not said how they plan to travel, ask. "

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
lookups = {}      # the route lookup in progress for a call, if any
last_call_started = None  # when the app last asked for a call, to ignore double taps

STAY_PUT = (
    "If you are somewhere dry and on high ground, the safest choice is to stay where you are "
    "until the water goes down."
)


def log(speaker, text):
    print(f"{speaker}: {text}", flush=True)
    transcripts.setdefault(request.values["CallSid"], []).append(f"{speaker}: {text}")


def route_facts(*lines):
    """A note for Qwen about what the map system found, so it can answer follow-up questions."""
    return "ROUTE RESULT from Otterway's map system (the caller did not say this). " + " ".join(lines)


def trip_length(summary):
    miles = round(summary.get("distance", 0) / 1609.344)
    minutes = max(1, round(summary.get("duration", 0) / 60))
    distance = "less than a mile" if miles < 1 else f"about {miles} mile{'' if miles == 1 else 's'}"
    return f"{distance} and about {minutes} minute{'' if minutes == 1 else 's'}"


def plan_route(destination):
    """Look the destination up and plan a drive that avoids mapped flood areas.

    Returns (spoken, facts): the words for the caller, and a note of what was found
    for Qwen to use if the caller asks more. Every statement about flooding and
    routes is built here from the route server's data, never written by Qwen.
    """
    lat, lon = LOCATION_COORDS
    origin = [lon, lat]  # the route server works in longitude, latitude order
    try:
        try:
            found = server.heigit("/pelias/v1/search?" + urlencode({
                "text": destination, "size": 1,
                "focus.point.lat": lat, "focus.point.lon": lon,  # prefer places near the caller
            }))
        except server.ApiError as error:
            if error.status != 404:
                raise
            found = {}
        matches = found.get("features") or []
        if not matches:
            return (
                f"I couldn't find {destination} on the map. Could you say the destination again, "
                "with the city or a nearby street?",
                route_facts(f"No place matching {destination} was found, so there is no route."),
            )
        label = matches[0]["properties"]["label"]
        target = matches[0]["geometry"]["coordinates"][:2]

        # The same areas the route server steers around: verified closures and mapped flood observations.
        closures = server.load_closures()
        flood_areas = [feature["geometry"]["coordinates"] for feature in closures["features"]]
        flood_areas += server.flood_avoidance_polygons(server.load_flood_layer()["features"])

        def in_flood_area(point):
            return any(server.route_crosses_polygon([point, point], area) for area in flood_areas)

        if in_flood_area(target):
            return (
                f"I found {label}. That destination is inside a mapped flood area, so I advise you "
                f"not to go there right now. {STAY_PUT} Is there somewhere else you need to get to?",
                route_facts(f"Destination matched: {label}. It is inside a mapped flood area.",
                            "The caller was advised not to go there. No route was given."),
            )
        if in_flood_area(origin):
            return (
                f"I found {label}, but your own location is inside a mapped flood area, so I can't "
                "give you a safe driving route from there. Move to higher ground if you can, and "
                "hang up and call 911 if you are in danger.",
                route_facts(f"Destination matched: {label}.",
                            "The caller's location is inside a mapped flood area. No route was given."),
            )

        try:
            route = server.route_avoiding_floods([origin, target], closures)
        except server.ApiError as error:
            if error.status == 422:
                return (
                    f"I found {label}, but I could not find a driving route there that avoids the "
                    f"mapped flood areas, so I advise you not to make this trip right now. {STAY_PUT}",
                    route_facts(f"Destination matched: {label}.",
                                "No driving route avoids the mapped flood areas. The caller was "
                                "advised not to make the trip. No route was given."),
                )
            if error.status == 404:
                return (
                    f"I found {label}, but I could not find a driving route there from your location.",
                    route_facts(f"Destination matched: {label}. No driving route was found."),
                )
            raise

        properties = route["features"][0]["properties"]
        steps = [step["instruction"].rstrip(".") + "."
                 for segment in properties.get("segments", []) for step in segment.get("steps", [])]
        length = trip_length(properties.get("summary", {}))
        detour = bool(route.get("otterway_detour"))
        spoken = f"I found {label}. The drive is {length}, " + (
            "and the route detours around mapped flood areas. " if detour
            else "and the route does not cross any mapped flood area. "
        )
        if steps:
            spoken += "To start: " + " ".join(steps[:2]) + " "
        spoken += "If you meet water on the road, turn around."
        if len(steps) > 2:
            spoken += " Would you like the next directions?"
        return spoken, route_facts(
            f"Destination matched: {label}. Driving route found: {length}.",
            "It detours around mapped flood areas." if detour else "It crosses no mapped flood area.",
            "The caller has heard directions 1 and 2. All driving directions in order:",
            " ".join(f"{number}. {step}" for number, step in enumerate(steps[:30], 1)),
        )
    except Exception as error:
        # Fail closed: with no map data, say so instead of guessing whether the trip is safe.
        print("Route lookup error:", error, flush=True)
        return (
            "Sorry, I can't check routes or flood areas right now, so I can't tell you whether "
            "that trip is safe. If you meet water on the road, turn around.",
            route_facts("The lookup failed. Nothing is known about this route or about flooding on it."),
        )


def start_lookup(call_sid, destination):
    """Run the lookup in the background, because Twilio only waits 5 seconds for each reply."""
    lookup = {"result": None, "waits": 0}

    def work():
        lookup["result"] = plan_route(destination)

    lookup["thread"] = threading.Thread(target=work, daemon=True)
    lookups[call_sid] = lookup
    lookup["thread"].start()


def send_transcript(call_sid):
    lines = transcripts.pop(call_sid, None)  # popping means it can only be sent once
    history.pop(call_sid, None)
    lookups.pop(call_sid, None)
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


def speak_then_fetch_route(text):
    """Say a holding line, then have Twilio ask /route for the lookup's answer."""
    log("AGENT", text)
    resp = VoiceResponse()
    resp.say(text)
    resp.redirect(f"{BASE_URL}/route")
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

    wanted = LOOKUP.search(reply or "")
    if wanted:
        destination = wanted.group(1).strip(" .\"'")[:120]
        if not destination:
            messages.pop()
            return speak_then_listen("Sorry, where are you trying to get to?")
        messages.append({"role": "assistant", "content": f"LOOKUP: {destination}"})
        start_lookup(call_sid, destination)
        return speak_then_fetch_route(f"Let me check the way to {destination}. One moment.")

    messages.append({"role": "assistant", "content": reply})
    return speak_then_listen(reply)


@app.route("/route", methods=["GET", "POST"])
def route_result():
    """Twilio comes here after the holding line to collect the lookup's answer."""
    call_sid = request.values["CallSid"]
    lookup = lookups.get(call_sid)
    if lookup is None:
        return speak_then_listen("Where are you trying to get to?")

    lookup["thread"].join(timeout=3)  # stay inside Twilio's 5 second limit
    if lookup["thread"].is_alive() and lookup["waits"] < 4:
        lookup["waits"] += 1
        resp = VoiceResponse()
        resp.pause(length=1)
        resp.redirect(f"{BASE_URL}/route")  # not ready yet, so ask again
        return str(resp), 200, {"Content-Type": "text/xml"}

    lookups.pop(call_sid, None)
    spoken, facts = lookup["result"] or (
        "Sorry, the route check is taking too long, so I can't tell you whether that trip is "
        "safe right now. If you meet water on the road, turn around.",
        route_facts("The lookup timed out. Nothing is known about this route or about flooding on it."),
    )
    messages = history.setdefault(call_sid, [{"role": "system", "content": SYSTEM}])
    messages.append({"role": "user", "content": facts})
    messages.append({"role": "assistant", "content": spoken})
    return speak_then_listen(spoken)


@app.route("/status", methods=["GET", "POST"])
def status():
    # Twilio calls this when the call ends, including when the caller just hangs up.
    send_transcript(request.values["CallSid"])
    return "", 204


@app.route("/agent/call", methods=["POST"])
def start_call():
    """The app's Talk to Ollie button lands here. It rings the phone, as call.py does by hand."""
    global last_call_started
    # The public tunnel exists only so Twilio can reach /voice, /turn and /status.
    # ngrok adds X-Forwarded-For to what it forwards, and the app's own requests
    # (through the Vite proxy on this machine) do not, so this stops anyone who
    # finds the tunnel address from making the phone ring.
    if request.headers.get("X-Forwarded-For"):
        return {"error": "Calls can only be started from the Otterway app."}, 403
    if last_call_started is not None and time.monotonic() - last_call_started < 20:
        return {"error": "Ollie is already calling you."}, 429

    try:
        call = Client().calls.create(  # reads TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN
            to=os.environ["MY_PHONE"],           # your verified mobile
            from_=os.environ["TWILIO_NUMBER"],   # your Twilio trial number
            url=f"{BASE_URL}/voice",
            status_callback=f"{BASE_URL}/status",
        )
    except KeyError as missing:
        print(f"Call not started: {missing.args[0]} is not set", flush=True)
        return {"error": f"{missing.args[0]} is not set where agent.py runs."}, 503
    except Exception as err:
        print("Call error:", err, flush=True)
        return {"error": "Twilio could not start the call."}, 502

    last_call_started = time.monotonic()
    print("Call requested from the app:", call.sid, flush=True)
    return {"call_sid": call.sid}, 202


if __name__ == "__main__":
    # Route lookups use the same key file and flood data as server.py.
    server.load_local_key("HEIGIT_API_KEY", "otterway.env")
    if not os.getenv("HEIGIT_API_KEY", "").strip():
        print("Route lookups are off: set HEIGIT_API_KEY before starting agent.py.", flush=True)
    try:
        areas = len(server.load_flood_layer()["features"])
        print(f"Flood data loaded: {areas} mapped flood points and footprints.", flush=True)
    except server.ApiError as error:
        print(f"Route lookups are off: {error}", flush=True)
    app.run(port=5000)