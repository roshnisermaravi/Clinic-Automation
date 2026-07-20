# Sunshine Clinic WhatsApp Bot

This version has three upgrades:

1. Secrets moved out of `bot.py` into `.env`
2. Only the registered doctor WhatsApp number can approve or reject appointments
3. Patients can cancel appointments

## Setup

Install the Python packages:

```bash
pip install -r requirements.txt
```

Open `.env` and replace the placeholder values:

```bash
TWILIO_ACCOUNT_SID=your_twilio_account_sid_here
TWILIO_AUTH_TOKEN=your_twilio_auth_token_here
TWILIO_WHATSAPP_NUM=whatsapp:+14155238886
DOCTOR_WHATSAPP=whatsapp:+91XXXXXXXXXX
GOOGLE_CREDENTIALS_FILE=credentials.json
GOOGLE_SHEET_NAME=Clinic Leads
```

Keep `credentials.json` in the same folder as `bot.py`.

## Run

```bash
python3 bot.py
```

Your Twilio webhook should point to:

```text
https://your-ngrok-url.ngrok-free.app/bot
```

## Test Messages

Patient booking:

```text
1
Ravi Kumar, 5 July, Fever and cold
1
```

Doctor approval, sent from the doctor WhatsApp number in `.env`:

```text
approve Ravi Kumar 10am
```

Doctor rejection:

```text
reject Ravi Kumar
```

Patient cancellation:

```text
5
Ravi Kumar, 5 July
```

Or in one message:

```text
cancel Ravi Kumar, 5 July
```
