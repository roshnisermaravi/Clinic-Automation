# Clinic Appointment Automation

A WhatsApp-based clinic appointment automation system that streamlines appointment booking through an automated conversational workflow. The system manages appointment requests, detects scheduling conflicts, supports doctor approval, handles cancellations, and stores records using Google Sheets.

## Features

- WhatsApp appointment booking
- Doctor approval and rejection workflow
- Intelligent conflict detection
- Doctor can assign an alternate appointment time
- Appointment cancellation
- Google Sheets integration
- Conversation state management
- Automatic status updates
- Doctor verification before approval
- Cancelled appointments automatically free reserved slots

## Tech Stack

### Programming Language

- Python

### Framework

- Flask

### APIs & Services

- Twilio WhatsApp API
- Google Sheets API

### Libraries

- gspread
- python-dotenv

### Data Storage

- Google Sheets

### Development Tools

- VS Code
- Ngrok

## Workflow
### Workflow Diagram

```text
Patient
    │
    ▼
WhatsApp
    │
    ▼
Interactive Menu
    │
    ├── Book Appointment
    ├── Consultation Fee
    ├── Doctor Timings
    ├── Clinic Location
    └── Cancel Appointment
            │
            ▼
      Appointment Booking
            │
            ▼
    Collect Patient Details
            │
            ▼
      Validate User Input
            │
            ▼
    Check Slot Availability
            │
      ┌─────┴─────┐
      │           │
Available     Slot Occupied
      │           │
      │     Suggest Available Slots
      │           │
      └─────┬─────┘
            ▼
 Store Appointment in Google Sheets
            │
            ▼
 Send Approval Request to Doctor
            │
      ┌─────┴─────────────────────┐
      │                           │
Approve                      Modify Time
      │                           │
      │                   Check Availability
      │                           │
      │                  ┌────────┴────────┐
      │                  │                 │
      │            Time Available    Time Unavailable
      │                  │                 │
      │                  ▼                 ▼
      │          Confirm Appointment   Return Available Slots
      │                                  │
      └──────────────────────┬───────────┘
                             ▼
                Update Appointment Status
                             │
                             ▼
          Notify Patient via WhatsApp
                             │
                             ▼
         Patient Cancels Appointment?
                      │
               ┌──────┴──────┐
               │             │
              No            Yes
               │             │
               │      Release Reserved Slot
               │             │
               │      Update Google Sheets
               │             │
               └──────┬──────┘
                      ▼
                 Workflow Complete
```

### Workflow Highlights

- Patients can book appointments, view consultation fees, doctor timings, clinic location, or cancel appointments directly through WhatsApp.
- The system validates every user input and maintains conversation state throughout the booking process.
- Intelligent scheduling prevents duplicate bookings by checking appointment availability before confirmation.
- When scheduling conflicts occur, the system automatically suggests available alternative time slots.
- Appointment requests are stored in Google Sheets and forwarded to the doctor for review.
- Doctors can approve, reject, or assign a different appointment time.
- If the doctor selects an unavailable time, the system automatically returns the currently available slots and requests re-approval.
- Appointment records are updated immediately after every approval, rejection, modification, or cancellation.
- Cancelled appointments automatically release the reserved slot, making it immediately available for future bookings.
- Appointment data and conversation states remain synchronized throughout the workflow to ensure data consistency.

## Setup

Install the required packages:

```bash
pip install -r requirements.txt
```

Create a `.env` file with the following values:

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

Configure the Twilio webhook:

```text
https://your-ngrok-url.ngrok-free.app/bot
```

## Sample Messages

### Patient Booking

```text
1
Ravi Kumar, 5 July, Fever and cold
1
```

### Doctor Approval

```text
approve Ravi Kumar 10am
```

### Doctor Rejection

```text
reject Ravi Kumar
```

### Patient Cancellation

```text
5
Ravi Kumar, 5 July
```

or

```text
cancel Ravi Kumar, 5 July
```

## Screenshots

### Main Menu

### Appointment Booking

### Doctor Approval

### Conflict Detection

### Appointments Google Sheet

### Conversation State Google Sheet

## Future Improvements

- Email notifications
- SMS reminders
- Cloud deployment
- Patient rescheduling
- Multiple doctor support
- Database integration
- Admin dashboard
