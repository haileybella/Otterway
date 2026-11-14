# Otterway

**Find your otterway there safely.**

Otterway is a mobile navigation and AI voice-guide prototype built around a familiar question during San Antonio flooding: **How do I get from where I am to where I need to be?**

Find driving directions from your current location on a mobile map, or call **Ollie**, our AI otter guide, for a spoken conversation. The datathon demo explores how maps and phone-based AI can make navigation guidance easier to access when a familiar trip becomes uncertain.

Built for the **Dell Social AI Impact Datathon**.

## The problem

Flooding can turn an everyday trip into an unfamiliar situation. People need to understand where they are, where they need to go, and what to do next.

Otterway explores two ways to make that guidance accessible on a phone:

- **See the trip.** Use a map with your current location, a destination, and driving directions.
- **Talk it through.** Speak with an AI guide over a real phone call.

The prototype demonstrates these interactions. It does not currently verify flood conditions or determine whether a road is safe to travel.

## The solution

Otterway brings together a mobile interface, a live routing map, and a phone-based AI guide:

1. **Start where you are.** Allow location access so the standalone map can use your phone’s GPS.
2. **Choose your destination.** Enter where you need to go and request driving directions.
3. **Hear the next turn.** Start browser voice guidance to hear route instructions aloud.
4. **Talk to Ollie.** Use the separate Twilio phone prototype to speak with an AI guide powered by Qwen running on the ASUS Ascent GX10.

These components demonstrate the experience we want to bring together: visual navigation and conversational guidance in one mobile flow.

## Meet Ollie

Ollie is Otterway’s AI voice guide. Instead of typing into a chat window, you speak over a phone call and hear Ollie respond.

During each conversation:

1. **Twilio captures your speech** and converts it into text.
2. **The Python phone agent sends your message and conversation history to Qwen.**
3. **Qwen generates Ollie’s response on the ASUS Ascent GX10.**
4. **Twilio reads the response aloud** and listens for your next turn.

The current phone prototype uses a fixed test location. Live route lookup during a call is not available on `main`.

## Powered by the ASUS Ascent GX10

We ran **Qwen3-VL-8B-Instruct** on the **ASUS Ascent GX10**, powered by the **NVIDIA GB10 Grace Blackwell Superchip**.

The GX10 handled the model inference behind Ollie’s replies. Our Python agent connected to the Qwen server through an OpenAI-compatible client, sending the caller’s transcribed message and conversation history to the model.

This gave each part of the system a clear role:

| Component | Role |
| --- | --- |
| **ASUS Ascent GX10 / NVIDIA GB10** | Runs Qwen and generates Ollie’s responses |
| **Qwen3-VL-8B-Instruct** | Processes the conversation and produces text replies |
| **Python phone agent** | Coordinates messages, conversation history, and model requests |
| **Twilio Voice** | Handles the phone call, speech transcription, and spoken playback |

Although Qwen3-VL supports vision, this prototype uses **text-based conversation**. Twilio handles the audio; Qwen generates the reply.

[Learn more about the ASUS Ascent GX10](https://www.asus.com/displays-desktops/mini-pcs/ascent-series/asus-ascent-gx10/)

## Design & AI interaction

We designed Otterway’s **mobile screens, components, and user flows in Figma** before building the interface in React.

The design follows three main interactions:

- **Set a destination:** move from a starting location to a trip request.
- **Follow a route:** view directions on a mobile map.
- **Connect with Ollie:** transition into a voice-guidance experience.

The AI interaction extends that experience beyond the screen. The phone agent includes conversation history with each model request so Ollie can respond in the context of the ongoing call.

## Demo features

| Feature | Current implementation |
| --- | --- |
| Mobile interface | React screens with sample destinations and routes |
| Ollie call interface | Simulated call experience in the React app |
| Current-location lookup | Live GPS in the standalone map, with location permission |
| Driving directions | HeiGIT routing through the Python map server |
| Spoken turn instructions | Browser voice guidance in the standalone map |
| Real phone conversation | Twilio Voice connected to the Python agent and Qwen |
| AI inference on the GX10 | Qwen3-VL-8B-Instruct generates Ollie’s replies |

**Current scope:** the React app, standalone map, and phone agent are separate prototype components. The demo does not yet connect live routing to Ollie’s calls or incorporate live flood and road-closure data.

## Tech stack

| Layer | Tools |
| --- | --- |
| UI/UX design | Figma |
| Mobile frontend | React, Vite |
| Map server | Python |
| Driving directions | HeiGIT |
| Map voice guidance | Browser speech synthesis |
| Phone integration | Twilio Voice |
| Phone agent | Python, Flask, OpenAI-compatible client |
| AI model | Qwen3-VL-8B-Instruct |
| AI hardware | ASUS Ascent GX10 with NVIDIA GB10 Grace Blackwell Superchip |
| Local webhook tunnel | ngrok |

## Getting started

Choose the component you want to try below.

### 1. Run the mobile web app

Use **Node.js 20.19+ on the 20.x line**, or **Node.js 22.12 or newer**.

From the repository root:

```bash
cd frontend
npm ci
npm run dev
```

Open the local URL printed by Vite.

To try the interface on a phone:

```bash
npm run dev:phone
```

Open the HTTPS network URL from a phone connected to the same Wi-Fi.

The React app on `main` uses **sample destinations and routes** and **simulates the Ollie call screen**. For live GPS and directions, run the standalone map below.

### 2. Try live GPS and driving directions

Get a Standard API key from the [HeiGIT account portal](https://account.heigit.org/).

With **Python 3.9 or newer**, run these commands from the repository root in **zsh**:

```zsh
read -rs 'HEIGIT_API_KEY?Paste your HeiGIT API key and press Return: '
export HEIGIT_API_KEY
python3 server.py
```

Open [http://127.0.0.1:8000/map.html](http://127.0.0.1:8000/map.html), then:

1. Select **Use my location** and allow location access.
2. Enter a destination.
3. Select **Get directions**.
4. Select **Start voice guidance** to hear turn instructions.

These are standard driving directions. They are not checked against flooding or road closures.

### 3. Try the Ollie phone prototype

You will need:

- A Twilio account and Voice-capable phone number.
- A reachable Qwen server with an OpenAI-compatible endpoint.
- ngrok for exposing the local Flask server to Twilio.
- A verified recipient number if using a Twilio trial.

From the repository root, create a virtual environment and install the dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install flask openai twilio
```

In a separate terminal, start the tunnel:

```bash
ngrok http 5000
```

Configure the prototype:

1. Set the ngrok tunnel URL in `agent.py` and the two callback URLs in `call.py`.
2. Point the OpenAI-compatible client in `agent.py` at your reachable Qwen server.
3. Set the following environment variables in the terminal used to run `call.py`:

| Variable | Purpose |
| --- | --- |
| `TWILIO_ACCOUNT_SID` | Twilio account identifier |
| `TWILIO_AUTH_TOKEN` | Twilio authentication token |
| `TWILIO_NUMBER` | Twilio phone number placing the call |
| `MY_PHONE` | Recipient phone number |

Keep credentials out of committed source files.

Start the phone agent:

```bash
python agent.py
```

In another terminal, activate the virtual environment and place the call:

```bash
source .venv/bin/activate
python call.py
```

On `main`, **`call.py` initiates an outgoing call**. Ollie uses a fixed test location, and live route lookup during the call is unavailable.

## What’s next

- **Flood-aware routing:** incorporate reliable flood and road-closure data into route decisions.
- **Live directions through Ollie:** connect the phone agent to location and routing services.
- **A connected mobile experience:** replace sample routes and simulated calls with the working map and phone integrations.
- **Clearer uncertainty:** communicate when road conditions are unknown or route information may be outdated.

Our goal is to help people in San Antonio understand their options when flooding changes the way home.
