# AI_agent_v1 ☕

A conversational AI phone agent that takes coffee orders using:
- **Twilio** — phone calls & speech recognition
- **Claude AI** — conversation brain
- **Flask** — web server
- **Railway** — free cloud hosting

---

## How It Works

```
Customer calls your number
        ↓
Twilio receives call → hits /incoming-call
        ↓
Flask greets the customer (TTS via Polly.Joanna)
        ↓
Customer speaks → Twilio transcribes → hits /respond
        ↓
Flask sends transcript → Claude AI → gets reply
        ↓
Flask speaks reply back → listens again
        ↓
Loop until order is complete → hang up
```

---

## 🚀 Deployment Guide (Step by Step)

### Step 1 — Get Your Free Accounts

| Service | URL | What you need |
|---|---|---|
| Twilio | twilio.com | Free trial (~$15 credit) → phone number |
| Anthropic | console.anthropic.com | API key (free credits) |
| Railway | railway.app | Free hosting |
| GitHub | github.com | To connect to Railway |

---

### Step 2 — Push to GitHub

```bash
# In the coffee-agent folder:
git init
git add .
git commit -m "Initial coffee agent"

# Create a new repo on github.com, then:
git remote add origin https://github.com/YOUR_USERNAME/coffee-agent.git
git push -u origin main
```

---

### Step 3 — Deploy to Railway

1. Go to [railway.app](https://railway.app) → **New Project**
2. Click **Deploy from GitHub repo** → select `coffee-agent`
3. Railway auto-detects Python + Procfile ✅
4. Go to **Variables** tab → add:
   ```
   ANTHROPIC_API_KEY = sk-ant-your-actual-key
   ```
5. Click **Deploy** — wait ~2 min
6. Go to **Settings → Networking → Generate Domain**
7. Copy your URL (e.g. `https://coffee-agent-production.up.railway.app`)

---

### Step 4 — Configure Twilio

1. Log in to [twilio.com/console](https://twilio.com/console)
2. Go to **Phone Numbers → Manage → Active Numbers**
3. Click your number
4. Under **Voice Configuration**:
   - **A call comes in** → Webhook
   - URL: `https://YOUR-RAILWAY-URL/incoming-call`
   - Method: `POST`
5. Under **Call Status Changes**:
   - URL: `https://YOUR-RAILWAY-URL/status`
   - Method: `POST`
6. Click **Save**

---

### Step 5 — Test It!

Call your Twilio number. The agent will:
1. Greet you as Brew & Co.
2. Take your coffee order conversationally
3. Ask clarifying questions (size, milk, extras)
4. Confirm your order with the total
5. Say goodbye and hang up

---

## 🗂️ Project Structure

```
coffee-agent/
├── app/
│   └── main.py          # Flask app (all the logic)
├── requirements.txt     # Python dependencies
├── Procfile             # Tells Railway how to run the app
├── .env.example         # Environment variable template
├── .gitignore
└── README.md
```

---

## 🔧 Customization

### Change the coffee shop name
In `app/main.py`, edit:
```python
COFFEE_SHOP_NAME = "Your Shop Name"
```

### Update the menu
Edit the `SYSTEM_PROMPT` in `app/main.py` — the `MENU:` section.

### Change the voice
Replace `Polly.Joanna` with any Twilio-supported voice:
- `Polly.Matthew` (US male)
- `Polly.Amy` (UK female)
- `Polly.Brian` (UK male)
- `alice` (Twilio default)

### Add a different language
Change `language="en-US"` in the `Gather` call to:
- `fr-FR` (French)
- `es-ES` (Spanish)
- `ar-SA` (Arabic)

---

## 🔒 Production Upgrades (when ready)

| What | Why |
|---|---|
| Replace `sessions` dict with **Redis** | So sessions survive server restarts |
| Add **Twilio signature validation** | Verify requests actually come from Twilio |
| Log orders to **PostgreSQL / Supabase** | Persist order history |
| Add **ElevenLabs TTS** | More natural voice quality |
| Use **Twilio Media Streams** | Real-time streaming (lower latency) |

---

## 💰 Cost Estimate (Free Tier)

| Service | Free Amount |
|---|---|
| Twilio | ~$15 trial credit (~300 min of calls) |
| Anthropic | $5 free credits (thousands of calls) |
| Railway | 500 hours/month free |

**Total to get started: $0**
