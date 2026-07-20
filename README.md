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

### MAIN MENU
<img width="603" height="1311" alt="main menu" src="https://github.com/user-attachments/assets/eddac0eb-128e-4b03-a687-d6cbe8cf8fe4" />

### BOOKING
<img width="603" height="1311" alt="appointment booking" src="https://github.com/user-attachments/assets/c31bf5ea-943a-4e33-b358-355b313505c5" />

### REQUEST FORWARDING
<img width="603" height="1311" alt="sending request" src="https://github.com/user-attachments/assets/f26ca15d-6593-4638-95e5-a991961654e1" />

### REQUEST ON DOCTORS PHONE
<img width="717" height="1600" alt="new appointment request" src="https://github.com/user-attachments/assets/fe61484a-d2e6-43fd-af33-d590edc94768" />

### CONFLICT DETECTION
<img width="717" height="1600" alt="conflict detection" src="https://github.com/user-attachments/assets/54d9ba09-ec7b-41df-9d91-98aa3c0fdba4" />


### APPOINTMENTS SHEETS
<img width="1470" height="831" alt="appointments sheets" src="https://github.com/user-attachments/assets/e5f3ed29-a019-446f-8355-5ec03d0aed89" />

### LEADS ENTRY
<img width="1470" height="831" alt="leads entry sheets" src="https://github.com/user-attachments/assets/903dbd73-06cd-4d7f-99a7-4c7b27a53380" />

### CONFIRMATION
<img width="603" height="1311" alt="confirmation" src="https://github.com/user-attachments/assets/6f6a7c41-9599-4781-ae2c-3012373553a5" />


## Future Improvements

- Email notifications
- SMS reminders
- Cloud deployment
- Patient rescheduling
- Multiple doctor support
- Database integration
- Admin dashboard
