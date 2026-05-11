"""
☕ Coffee Order AI Voice Agent
--------------------------------
Stack: Twilio (calls) + Claude AI (brain) + Flask (server)
Deploy: Render.com (free tier)
"""

import os
from functools import wraps
from flask import Flask, request, Response, abort, jsonify
from twilio.twiml.voice_response import VoiceResponse, Gather
from twilio.request_validator import RequestValidator
from twilio.rest import Client
import anthropic

app = Flask(__name__)

# ── Clients ──────────────────────────────────────────────────────────────────
claude = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
twilio_client = Client(os.environ["TWILIO_ACCOUNT_SID"], os.environ["TWILIO_AUTH_TOKEN"])
twilio_validator = RequestValidator(os.environ["TWILIO_AUTH_TOKEN"])

# ── Config ────────────────────────────────────────────────────────────────────
COFFEE_SHOP_NAME  = "Brew & Co."
CLAUDE_MODEL      = "claude-sonnet-4-20250514"
TWILIO_NUMBER     = os.environ["TWILIO_NUMBER"]
YOUR_PHONE_NUMBER = os.environ["YOUR_PHONE_NUMBER"]
RENDER_URL        = os.environ["RENDER_URL"]

SYSTEM_PROMPT = """You are a friendly voice assistant for a coffee shop called Brew & Co.
Your job is to take customer coffee orders over the phone.

MENU:
- Espresso ($3), Double Espresso ($4)
- Americano ($4), Latte ($5), Cappuccino ($5), Flat White ($5)
- Mocha ($5.50), Macchiato ($4.50)
- Cold Brew ($5), Iced Latte ($5.50)
- Sizes: Small, Medium, Large (+$0.50 each size up)
- Milk options: Whole, Oat (+$0.75), Almond (+$0.75), Soy (+$0.50)
- Extras: Extra shot (+$1), Vanilla/Caramel/Hazelnut syrup (+$0.75)

RULES:
- Keep responses SHORT (1-3 sentences max) — this is a phone call
- Be warm and conversational
- Ask clarifying questions one at a time (size, milk, extras)
- When the order is complete, confirm it with the total price
- Ask the customer to confirm the order vocally (say yes or no)
- If they confirm with yes, end with exactly: "CALL_COMPLETE: [order summary with total]"
- If they say no, ask what they would like to change
- Never make up menu items or prices
- If asked something off-topic, politely redirect to coffee ordering"""

# In-memory session store { call_sid: [messages] }
sessions: dict[str, list] = {}


# ── Twilio signature validation ───────────────────────────────────────────────
def validate_twilio_request(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        url = request.url
        signature = request.headers.get("X-Twilio-Signature", "")
        params = request.form.to_dict()
        if not twilio_validator.validate(url, params, signature):
            abort(403)
        return f(*args, **kwargs)
    return decorated


# ── Helpers ───────────────────────────────────────────────────────────────────
def ask_claude(call_sid: str, user_message: str) -> str:
    """Send user message to Claude, maintain conversation history per call."""
    if call_sid not in sessions:
        sessions[call_sid] = []

    sessions[call_sid].append({"role": "user", "content": user_message})

    response = claude.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=200,
        system=SYSTEM_PROMPT,
        messages=sessions[call_sid],
    )

    reply = response.content[0].text.strip()

    sessions[call_sid].append({"role": "assistant", "content": reply})

    return reply


def twiml_response(text: str, gather: bool = True, timeout: int = 8) -> str:
    """Build a TwiML response that speaks text and optionally listens."""
    response = VoiceResponse()

    if gather:
        g = Gather(
            input="speech",
            action="/respond",
            method="POST",
            speech_timeout="auto",
            timeout=timeout,
            language="en-US",
        )
        g.say(text, voice="Polly.Joanna")
        response.append(g)
        response.say(
            "I didn't catch that. Let me transfer you to our team. Goodbye!",
            voice="Polly.Joanna",
        )
        response.hangup()
    else:
        response.say(text, voice="Polly.Joanna")
        response.pause(length=1)
        response.hangup()

    return str(response)


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/health", methods=["GET"])
def health():
    """Health check — also warms up the server."""
    return {"status": "ok", "agent": COFFEE_SHOP_NAME}, 200


@app.route("/call-me", methods=["GET"])
def call_me():
    """Visit this URL in your browser → Twilio calls your phone immediately."""
    call = twilio_client.calls.create(
        to=YOUR_PHONE_NUMBER,
        from_=TWILIO_NUMBER,
        url=f"{RENDER_URL}/incoming-call",
    )
    return jsonify({
        "status": "calling",
        "message": f"📞 Calling {YOUR_PHONE_NUMBER} now — pick up!",
        "call_sid": call.sid,
    })


@app.route("/incoming-call", methods=["POST"])
@validate_twilio_request
def incoming_call():
    """Twilio hits this when the call connects."""
    call_sid = request.form.get("CallSid", "unknown")
    sessions.pop(call_sid, None)

    greeting = (
        f"Hi! Welcome to {COFFEE_SHOP_NAME}. "
        "I'm your virtual barista. "
        "What can I get started for you today?"
    )
    return Response(twiml_response(greeting), mimetype="text/xml")


@app.route("/respond", methods=["POST"])
@validate_twilio_request
def respond():
    """Twilio sends the customer's transcribed speech here after each turn."""
    call_sid = request.form.get("CallSid", "unknown")
    speech_result = request.form.get("SpeechResult", "").strip()

    if not speech_result:
        fallback = "Sorry, I didn't catch that. Could you repeat that please?"
        return Response(twiml_response(fallback), mimetype="text/xml")

    print(f"[{call_sid}] Customer: {speech_result}")

    reply = ask_claude(call_sid, speech_result)

    print(f"[{call_sid}] Agent: {reply}")

    if reply.startswith("CALL_COMPLETE:"):
        order_summary = reply.replace("CALL_COMPLETE:", "").strip()
        farewell = (
            f"Perfect! {order_summary}. "
            "Your order has been placed. "
            "Thank you for calling Brew & Co. See you soon!"
        )
        sessions.pop(call_sid, None)
        return Response(twiml_response(farewell, gather=False), mimetype="text/xml")

    return Response(twiml_response(reply), mimetype="text/xml")


@app.route("/status", methods=["POST"])
@validate_twilio_request
def call_status():
    """Twilio calls this when a call ends — clean up session."""
    call_sid = request.form.get("CallSid", "unknown")
    status = request.form.get("CallStatus", "unknown")
    print(f"[{call_sid}] Call ended — status: {status}")
    sessions.pop(call_sid, None)
    return "", 204


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
