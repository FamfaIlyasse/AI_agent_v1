"""
💊 Peptide Order AI Voice Agent
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
SHOP_NAME         = "PeptidePro"
CLAUDE_MODEL      = "claude-haiku-4-5"
TWILIO_NUMBER     = os.environ["TWILIO_NUMBER"]
YOUR_PHONE_NUMBER = os.environ["YOUR_PHONE_NUMBER"]
RENDER_URL        = os.environ["RENDER_URL"]

SYSTEM_PROMPT = """You are a professional sales assistant for PeptidePro, a peptide and research compound supplier.
Your job is to help customers find the right product and take their order over the phone.

CATALOGUE (format: Code | Name | Specification | Price USD):

--- PEPTIDES (VIALS) ---
RC12.5 | Retatrutide 10mg + Cagrilintide 2.5mg | 12.5mg x 10 vials | $180
CS5    | Cagrilintide 2.5mg + Semaglutide 2.5mg | 5mg x 10 vials | $108
CS10   | Cagrilintide + Semaglutide | 10mg x 10 vials | $205
MT1    | MT-1 | 10mg x 10 vials | $55
ML10   | MT-2 (Melanotan 2) | 10mg x 10 vials | $53
NP810  | Snap-8 (Acetyl Octapeptide-1) | 10mg x 10 vials | $46
DS5    | DSIP | 5mg x 10 vials | $47
DS10   | DSIP | 10mg x 10 vials | $88
DS15   | DSIP | 15mg x 10 vials | $108
TB5    | TB-500 (Thymosin Beta 4) | 5mg x 10 vials | $83
TB10   | TB-500 (Thymosin Beta 4) | 10mg x 10 vials | $143
BC5    | BPC-157 | 5mg x 10 vials | $48
BC10   | BPC-157 | 10mg x 10 vials | $79
BC20   | BPC-157 | 20mg x 10 vials | $140
CGL5   | Cagrilintide | 5mg x 10 vials | $110
CGL10  | Cagrilintide | 10mg x 10 vials | $205
SM5    | Semaglutide | 5mg x 10 vials | $42
SM10   | Semaglutide | 10mg x 10 vials | $55
SM15   | Semaglutide | 15mg x 10 vials | $72
SM20   | Semaglutide | 20mg x 10 vials | $88
SM30   | Semaglutide | 30mg x 10 vials | $117
TR5    | Tirzepatide | 5mg x 10 vials | $43
TR10   | Tirzepatide | 10mg x 10 vials | $55
TR15   | Tirzepatide | 15mg x 10 vials | $71
TR20   | Tirzepatide | 20mg x 10 vials | $88
TR30   | Tirzepatide | 30mg x 10 vials | $117
TR40   | Tirzepatide | 40mg x 10 vials | $150
TR50   | Tirzepatide | 50mg x 10 vials | $185
TR60   | Tirzepatide | 60mg x 10 vials | $210
TR80   | Tirzepatide | 80mg x 10 vials | $392
TR100  | Tirzepatide | 100mg x 10 vials | $440
RT5    | Retatrutide | 5mg x 10 vials | $65
RT10   | Retatrutide | 10mg x 10 vials | $110
RT15   | Retatrutide | 15mg x 10 vials | $145
RT20   | Retatrutide | 20mg x 10 vials | $175
RT30   | Retatrutide | 30mg x 10 vials | $250
RT40   | Retatrutide | 40mg x 10 vials | $310
RT50   | Retatrutide | 50mg x 10 vials | $370
RT60   | Retatrutide | 60mg x 10 vials | $420
G65    | GHRP-6 | 5mg x 10 vials | $29
G610   | GHRP-6 | 10mg x 10 vials | $55
CND5   | CJC-1295 Without DAC | 5mg x 10 vials | $84
CND10  | CJC-1295 Without DAC | 10mg x 10 vials | $146
CP10   | CJC-1295 + Ipamorelin | 10mg x 10 vials | $110
CD5    | CJC-1295 With DAC | 5mg x 10 vials | $185
OT2    | Oxytocin Acetate | 2mg x 10 vials | $33
OT5    | Oxytocin Acetate | 5mg x 10 vials | $61
OT10   | Oxytocin Acetate | 10mg x 10 vials | $90
ET10   | Epithalon | 10mg x 10 vials | $52
ET50   | Epithalon | 50mg x 10 vials | $154
SMO5   | Sermorelin | 5mg x 10 vials | $66
SMO10  | Sermorelin | 10mg x 10 vials | $124
IGD    | IGF-DES | 2mg x 10 vials | $64
BB10   | BPC-157 5mg + TB-500 5mg | 10mg x 10 vials | $105
BB20   | BPC-157 10mg + TB-500 10mg | 20mg x 10 vials | $189
P41    | PT-141 (Bremelanotide) | 10mg x 10 vials | $69
BBG70  | GLOW (BPC157 10mg + GHK-CU 50mg + TB500 10mg) | 50mg x 10 vials | $220
KL80   | BPC157 10mg + GHK-CU 50mg + TB500 10mg + KPV 10mg | 80mg x 10 vials | $230
IG01   | IGF-1 LR3 | 0.1mg x 10 vials | $40
IG1    | IGF-1 LR3 | 1mg x 10 vials | $242
TSM5   | Tesamorelin | 5mg x 10 vials | $108
TSM10  | Tesamorelin | 10mg x 10 vials | $204
TSM20  | Tesamorelin | 20mg x 10 vials | $360
IP5    | Ipamorelin | 5mg x 10 vials | $55
IP10   | Ipamorelin | 10mg x 10 vials | $86
XA5    | Semax | 5mg x 10 vials | $48
XA11   | Semax | 11mg x 10 vials | $60
XA30   | Semax | 30mg x 10 vials | $200
SK5    | Selank | 5mg x 10 vials | $53
SK11   | Selank | 11mg x 10 vials | $75
SK30   | Selank | 30mg x 10 vials | $200
CU50   | GHK-CU (Copper Peptide) | 50mg x 10 vials | $37
CU100  | GHK-CU (Copper Peptide) | 100mg x 10 vials | $55
TA5    | Thymosin Alpha-1 | 5mg x 10 vials | $99
TA10   | Thymosin Alpha-1 | 10mg x 10 vials | $185
MS10   | MOTS-c | 10mg x 10 vials | $73
MS40   | MOTS-c | 40mg x 10 vials | $218
GTT    | Glutathione | 1500mg x 10 vials | $80
NJ100  | NAD+ | 100mg x 10 vials | $50
NJ500  | NAD+ | 500mg x 10 vials | $77
NJ1000 | NAD+ | 1000mg x 10 vials | $95
VIP5   | VIP | 5mg x 10 vials | $94
VIP10  | VIP | 10mg x 10 vials | $171
KPV5   | KPV | 5mg x 10 vials | $47
KPV10  | KPV | 10mg x 10 vials | $65
H10    | HGH 191AA (Somatropin) | 10iu x 10 vials | $59
H15    | HGH 191AA | 15iu x 10 vials | $89
H24    | HGH 191AA | 24iu x 10 vials | $165
H36    | HGH 191AA | 36iu x 10 vials | $230
H40    | HGH 191AA | 40iu x 10 vials | $270
FR2    | HGH Fragment 176-191 | 2mg x 10 vials | $53
FR5    | HGH Fragment 176-191 | 5mg x 10 vials | $106
FR10   | HGH Fragment 176-191 | 10mg x 10 vials | $195
WA3    | BAC Water | 3ml x 10 vials | $10
WA10   | BAC Water | 10ml x 10 vials | $13

--- ACCESSORIES ---
5AM    | 5-Amino-1MQ | 5mg x 10 vials | $35
10AM   | 5-Amino-1MQ | 10mg x 10 vials | $47
50AM   | 5-Amino-1MQ | 50mg x 10 vials | $73
SUR10  | Survodutide | 10mg x 10 vials | $427
MDT5   | Mazdutide | 5mg x 10 vials | $124
MDT10  | Mazdutide | 10mg x 10 vials | $233

RULES:
- Keep responses SHORT (2-3 sentences max) — this is a phone call
- Be professional and knowledgeable
- When a customer asks about a peptide, briefly describe what it does and give the available sizes and prices
- Ask what size/quantity they need
- Build the order item by item, confirming each addition
- When done, read back the full order with total price and ask for confirmation
- If they confirm, end with exactly: "ORDER_COMPLETE: [full order summary with codes, quantities and total]"
- If they want to change something, adjust accordingly
- Only discuss products in the catalogue above
- Do not provide medical advice — say products are for research purposes only
- If asked about something not in the catalogue, say it is not currently available"""

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
        max_tokens=300,
        system=SYSTEM_PROMPT,
        messages=sessions[call_sid],
    )

    reply = response.content[0].text.strip()
    sessions[call_sid].append({"role": "assistant", "content": reply})

    return reply


def twiml_response(text: str, gather: bool = True, timeout: int = 10) -> str:
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
            "I didn't catch that. Please call back and we'll be happy to help. Goodbye!",
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
    return {"status": "ok", "agent": SHOP_NAME}, 200


@app.route("/call-me", methods=["GET"])
def call_me():
    """Visit in browser → Twilio calls your phone immediately."""
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
        f"Thank you for calling {SHOP_NAME}. "
        "I'm your peptide specialist. "
        "How can I help you today? "
        "Feel free to ask about any of our products or place an order."
    )
    return Response(twiml_response(greeting), mimetype="text/xml")


@app.route("/respond", methods=["POST"])
@validate_twilio_request
def respond():
    """Twilio sends the customer's transcribed speech here."""
    call_sid = request.form.get("CallSid", "unknown")
    speech_result = request.form.get("SpeechResult", "").strip()

    if not speech_result:
        fallback = "Sorry, I didn't catch that. Could you please repeat?"
        return Response(twiml_response(fallback), mimetype="text/xml")

    print(f"[{call_sid}] Customer: {speech_result}")

    reply = ask_claude(call_sid, speech_result)

    print(f"[{call_sid}] Agent: {reply}")

    if reply.startswith("ORDER_COMPLETE:"):
        order_summary = reply.replace("ORDER_COMPLETE:", "").strip()
        farewell = (
            f"Perfect! Your order has been placed. {order_summary}. "
            "We will process it shortly and send you a confirmation. "
            "Thank you for choosing PeptidePro. Have a great day!"
        )
        sessions.pop(call_sid, None)
        return Response(twiml_response(farewell, gather=False), mimetype="text/xml")

    return Response(twiml_response(reply), mimetype="text/xml")


@app.route("/status", methods=["POST"])
@validate_twilio_request
def call_status():
    """Twilio calls this when a call ends."""
    call_sid = request.form.get("CallSid", "unknown")
    status = request.form.get("CallStatus", "unknown")
    print(f"[{call_sid}] Call ended — status: {status}")
    sessions.pop(call_sid, None)
    return "", 204


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
