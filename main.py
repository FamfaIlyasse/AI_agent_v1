"""
☕ Coffee Order AI Voice Agent
--------------------------------
Stack: Twilio (calls) + Claude AI (brain) + Flask (server)
Deploy: Railway.app (free tier)
"""

import os
import json
from flask import Flask, request, Response
from twilio.twiml.voice_response import VoiceResponse, Gather
import anthropic

app = Flask(__name__)

# ── Clients ──────────────────────────────────────────────────────────────────
claude = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

# ── Config ────────────────────────────────────────────────────────────────────
COFFEE_SHOP_NAME = "Brew & Co."

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
- End your confirmation message with: "Is there anything else I can help you with?"
- If they say no or goodbye, end with exactly: "CALL_COMPLETE: [order summary]"
- Never make up menu items or prices
- If asked something off-topic, politely redirect to coffee ordering"""

# In-memory session store  { call_sid: [messages] }
# For production → use Redis or a DB
sessions: dict[str, list[dict]] = {}


def ask_claude(call_sid: str, user_message: str) -> str:
    """Send user message to Claude, maintain conversation history."""
    if call_sid not in sessions:
        sessions[call_sid] = []

    sessions[call_sid].append({"role": "user", "content": user_message})

    response = claude.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=200,  # Keep responses short for voice
        system=SYSTEM_PROMPT,
        messages=sessions[call_sid],
    )

    assistant_reply = response.content[0].text
    sessions[call_sid].append({"role": "assistant", "content": assistant_reply})

    return assistant_reply


def twiml_response(text: str, gather: bool = True, timeout: int = 5) -> str:
    """Build a TwiML response that speaks text and optionally listens."""
    response = VoiceResponse()

    if gather:
        # Gather = speak + listen for speech input
        g = Gather(
            input="speech",
            action="/respond",
            method="POST",
            speech_timeout="auto",
            timeout=timeout,
            language="en-US",
        )
        g.say(text, voice="Polly.Joanna")  # AWS Polly via Twilio — sounds natural
        response.append(g)

        # Fallback if no speech detected
        response.say("I didn't catch that. Let me transfer you to our team. Goodbye!", voice="Polly.Joanna")
        response.hangup()
    else:
        # Just speak and hang up
        response.say(text, voice="Polly.Joanna")
        response.pause(length=1)
        response.hangup()

    return str(response)


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/health", methods=["GET"])
def health():
    """Health check for Railway."""
    return {"status": "ok", "agent": COFFEE_SHOP_NAME}, 200


@app.route("/incoming-call", methods=["POST"])
def incoming_call():
    """Twilio hits this when someone calls your number."""
    call_sid = request.form.get("CallSid", "unknown")

    # Clear any old session for this call
    sessions.pop(call_sid, None)

    greeting = (
        f"Hi, welcome to {COFFEE_SHOP_NAME}! "
        "I'm your virtual barista. What can I get started for you today?"
    )

    return Response(twiml_response(greeting), mimetype="text/xml")


@app.route("/respond", methods=["POST"])
def respond():
    """Twilio sends the customer's speech transcript here."""
    call_sid = request.form.get("CallSid", "unknown")
    speech_result = request.form.get("SpeechResult", "").strip()

    if not speech_result:
        fallback = "Sorry, I didn't catch that. Could you repeat your order?"
        return Response(twiml_response(fallback), mimetype="text/xml")

    print(f"[{call_sid}] Customer said: {speech_result}")

    # Get Claude's reply
    reply = ask_claude(call_sid, speech_result)

    print(f"[{call_sid}] Agent replied: {reply}")

    # Check if the order is complete
    if reply.startswith("CALL_COMPLETE:"):
        order_summary = reply.replace("CALL_COMPLETE:", "").strip()
        farewell = (
            f"Perfect! So your order is: {order_summary}. "
            "Your order has been placed. Thank you for calling Brew & Co. "
            "See you soon!"
        )
        # Clean up session
        sessions.pop(call_sid, None)
        return Response(twiml_response(farewell, gather=False), mimetype="text/xml")

    return Response(twiml_response(reply), mimetype="text/xml")


@app.route("/status", methods=["POST"])
def call_status():
    """Twilio calls this when a call ends — clean up session."""
    call_sid = request.form.get("CallSid", "unknown")
    call_status = request.form.get("CallStatus", "unknown")

    print(f"[{call_sid}] Call ended with status: {call_status}")
    sessions.pop(call_sid, None)

    return "", 204


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
