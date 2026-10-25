# Smart Blood Donation and Blood Bank Management System (India)

[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-crimson.svg)](https://www.python.org/)
[![Flask 3.1](https://img.shields.io/badge/Flask-3.1-black.svg)](https://flask.palletsprojects.com/)
[![MongoDB Atlas](https://img.shields.io/badge/MongoDB-Atlas%20%7C%20PyMongo-green.svg)](https://www.mongodb.com/atlas)
[![Bootstrap 5.3](https://img.shields.io/badge/Bootstrap-5.3-purple.svg)](https://getbootstrap.com/)
[![Tests Passed](https://img.shields.io/badge/pytest-10%2F10%20passing-brightgreen.svg)]()

A complete, modern, responsive web application designed for the Indian healthcare ecosystem, connecting voluntary blood donors, accredited hospital blood banks, and critical patients across Indian states and districts with real-time stock monitoring and appointment scheduling safeguards.

> **Academic Prototype & Medical Disclaimer**  
> *This application is a student software engineering prototype and capstone project demonstration. It is NOT a certified clinical diagnostic system and is not connected to live 108/104 national emergency dispatchers. Under National Blood Transfusion Council (NBTC) norms, donor medical clearance (Hb &ge; 12.5 g/dL, weight &ge; 45kg, BP, vitals) and cross-matching decisions belong strictly to certified medical professionals at the blood center.*

---

## 1. Technology Stack

- **Backend:** Python 3.11+ with Flask 3.1
- **Database:** MongoDB Atlas (Persistent Cloud Storage) connected via **PyMongo 4.18+** with **dnspython**
- **Fallback / Demo Engine:** Built-in isolated in-memory persistence (`mongomock`) that activates automatically if `MONGO_URI` is not provided or unreachable, enabling instant 1-click evaluation without prior cloud setup
- **Frontend:** HTML5, CSS3 with healthcare-tailored crimson design system (`#B71C1C`), and Vanilla JavaScript
- **CSS Framework:** Bootstrap 5.3 for responsive layouts, modals, tables, and stepper workflows
- **Typography & Icons:** Google Fonts (*Outfit* and *Inter*) and Font Awesome 6 Icons
- **Security:** Werkzeug password hashing (PBKDF2-HMAC-SHA256), session management, role-based decorators, CSRF/injection prevention
- **Testing:** Automated test suite using `pytest` (10 passing tests)

---

## 2. System Architecture & Folder Structure

```
d:\antigravity\
├── app.py                     # Application factory, routes registration & context providers
├── config.py                  # Location matrix (Indian States & Districts), blood groups, settings
├── extensions.py              # MongoDB manager, Atlas connection & graceful demo fallback
├── seed_data.py               # Pre-populates AIIMS, KEM, Victoria Hospital, stock & demo users
├── requirements.txt           # Python dependencies (Flask, PyMongo, dnspython, etc.)
├── .env.example               # Template environment variables
├── .env                       # Local environment variables
│
├── models/                    # Data models and document schemas
│   ├── __init__.py            # ISO timestamp utilities and date filters
│   ├── user.py                # User account model and password hashing
│   ├── donor.py               # Donor profile, reminder cooldown & NBTC criteria
│   ├── hospital.py            # Hospital entity, licensing & time slot definitions
│   ├── stock.py               # 8-blood group stock model & assistance requests
│   ├── appointment.py         # Appointment booking model & reference generator
│   ├── blood_request.py       # Patient blood request & tracking code generator
│   ├── notification.py        # In-app notifications schema
│   └── audit.py               # Platform audit logging schema
│
├── services/                  # Business logic services
│   ├── auth_service.py        # Registration, validation, credential verification
│   ├── hospital_service.py    # Hospital directory, admin verification, slot configuration
│   ├── stock_service.py       # 8-group stock operations, shortages, inter-hospital exchange
│   ├── appointment_service.py # Booking, atomic capacity check, rescheduling, completion
│   ├── request_service.py     # Public emergency blood requests & status updates
│   ├── notification_service.py# In-app alerts, consent toggles & external gateway stubs
│   └── audit_service.py       # Audit trail logger
│
├── routes/                    # Modular Flask Blueprints
│   ├── __init__.py            # Auth decorators (@login_required, @role_required)
│   ├── auth_routes.py         # /login, /register/donor, /register/hospital, /logout
│   ├── public_routes.py       # /, /find-blood, /request-blood, /track-request, /about, /faq
│   ├── donor_routes.py        # /donor/dashboard, /donor/book, /donor/appointments, /donor/profile
│   ├── hospital_routes.py     # /hospital/dashboard, /hospital/stock, /hospital/appointments
│   ├── admin_routes.py        # /admin/dashboard, verification queue, request moderation
│   └── api_routes.py          # /api/locations, /api/hospitals, /api/hospitals/<id>/slots
│
├── static/
│   ├── css/
│   │   └── style.css          # Healthcare crimson design system, badges, card styles
│   └── js/
│       ├── main.js            # Cascading district dropdowns, notification dismiss, demo fill
│       └── booking.js         # Interactive slot picker & real-time capacity calculator
│
├── templates/                 # Jinja2 HTML5 Templates
│   ├── base.html              # Layout master with navbar, footer, demo credentials modal
│   ├── index.html             # Homepage with hero, live metrics, and quick search widget
│   ├── about.html             # How it works & ABO/Rh blood compatibility matrix
│   ├── faq.html               # NBTC eligibility criteria, physical parameters & FAQs
│   ├── contact.html           # Feedback form & college project demonstration details
│   ├── 404.html, 500.html, 403.html # Custom error pages
│   ├── auth/
│   │   ├── login.html         # Login with 1-click evaluation credentials
│   │   ├── register_donor.html# Voluntary donor registration with consent
│   │   └── register_hospital.html # Hospital facility registration
│   ├── donor/
│   │   ├── dashboard.html     # Donor dashboard with recovery cooldown banner
│   │   ├── book_appointment.html # Complete appointment booking stepper
│   │   └── my_appointments.html  # Appointment management, slips, reschedule & cancel
│   ├── hospital/
│   │   ├── dashboard.html     # Hospital inventory KPIs & slot capacity settings
│   │   ├── stock_management.html # 8-group stock adjuster & inter-hospital assistance
│   │   └── appointments.html  # Appointment confirmation & attendance completion
│   ├── admin/
│   │   └── dashboard.html     # Hospital verification queue, audit trail & moderation
│   ├── public/
│   │   ├── find_blood.html    # State/district verified blood bank directory
│   │   ├── request_blood.html # Emergency & scheduled surgery request form
│   │   └── track_request.html # Tracking stepper with case progress history
│   └── user/
│       └── profile.html       # Profile settings & notification channel consent
│
└── tests/                     # Automated Test Suite (pytest)
    ├── conftest.py            # App test fixtures & in-memory test runner
    ├── test_auth.py           # Registration, login, duplicate check & permissions
    ├── test_appointments.py   # Booking, capacity safeguards, rescheduling & completion
    ├── test_stock.py          # 8-group stock updates, audit logs & assistance requests
    ├── test_requests.py       # Blood requests, tracking codes & moderation
    └── test_mongo_fallback.py # MongoDB connection failure & recovery test
```

---

## 3. Major Features & Technical Workflows

### A. User Roles & Security
1. **Voluntary Donors:** Can register, configure Indian state & district, declare blood group, manage last donation date, schedule appointments, view printable booking slips, and set emergency notification consent.
2. **Hospitals & Blood Banks:** Can register with official drug controller license numbers. Accounts start with `pending_verification` status. Once verified, staff can manage inventory for all 8 blood groups, configure daily slot capacity, confirm appointments, record attendance with collection bag numbers, and request inter-hospital assistance.
3. **Administrators:** Central health authority dashboard to approve/reject pending blood bank registrations, inspect audit logs, and verify public emergency blood requests.
4. **Public Visitors:** Can freely search verified blood availability by blood group and district, and submit emergency patient requests with tracking codes without exposing donor phone numbers.

### B. Core Feature: Blood Donation Appointment Booking
- **Step 1:** Select Indian State and District.
- **Step 2:** Choose a verified participating blood bank.
- **Step 3:** Choose an appointment date (up to 60 days in advance).
- **Step 4:** Real-time time slot selector checks remaining capacity (e.g. `4/5 left`) and disables full slots.
- **Safeguards:** Server-side atomic validation prevents double-booking of the same slot or multiple active appointments on the same date for a single donor.
- **Management:** Donors can view printable booking slips (`window.print()`), reschedule to a new slot, or cancel with a reason.
- **Completion & Attendance:** Hospital staff records physical collection bag ID and volume (350ml/450ml). Completing the donation:
  1. Marks the appointment `completed`.
  2. Updates donor profile `last_donation_date` and increments `total_donations`.
  3. Automatically adds 1 unit to that blood group in hospital stock with an audit log.
  4. Dispatches a celebration in-app notification to the donor.

### C. Blood Stock Inventory & Inter-Hospital Exchange
- Tracks all 8 standard ABO & Rh blood groups: **A+, A-, B+, B-, AB+, AB-, O+, O-**.
- Inventory levels: **Adequate** (&ge; 8 units), **Low** (3-7 units), **Critical** (&le; 2 units).
- Audit trail logs previous units, new units, reason (Donation Camp, Dispensed, Expired, Hospital Transfer), and authorized user email.
- **Inter-Hospital Assistance:** When a blood center experiences a critical deficit (e.g. 0 units of AB-), staff can broadcast an assistance request. Neighboring blood banks can view and accept the request to coordinate unit transfers.

### D. Public Blood Search & Request Tracking
- **Search:** Filter by blood group, state, and district to find nearby accredited blood banks with verified units.
- **Emergency Requests:** Patients/attendants can submit requests specifying urgency (Emergency &lt; 2h, Urgent &lt; 24h, Standard). Produces a unique tracking code (e.g., `REQ-2026-DL8921`).
- **Tracking:** Public timeline tracker displays verification status, assigned blood bank, and case progress history.

### E. Ethical Medical Cooldown Logic
- Adheres to the **National Blood Transfusion Council (NBTC)** 90-day recovery interval for males and 120-day interval for females.
- Calculations are used *only* to manage reminder cooldowns and prevent inappropriate appointment notifications. Medical clearance is explicitly confirmed on-site by physicians.

---

## 4. Pre-Seeded Demonstration Accounts

For instant testing and evaluation, pre-seeded accounts are provided with 1-click login buttons on the login page:

| Role | Email | Password | Details |
|---|---|---|---|
| **Administrator** | `admin@raktkosh.gov.in` | `Admin@2026` | Dr. Vinod Paul (Central Health Authority) |
| **Hospital Staff (Delhi)** | `aiims.bloodbank@delhi.gov.in` | `Hospital@2026` | AIIMS Central Blood Bank, New Delhi |
| **Hospital Staff (Tamil Nadu)** | `rgggh.bloodbank@tn.gov.in` | `Hospital@2026` | Rajiv Gandhi Govt General Hospital, Chennai (Live Stock Demo) |
| **Voluntary Donor** | `rahul.sharma@gmail.com` | `Donor@2026` | Rahul Sharma (O+ Donor, New Delhi) |
| **Pending Hospital** | `sanjeevani@punecharity.org` | `Hospital@2026` | Sanjeevani Blood Bank, Pune (For Admin Verification Demo) |

---

## 5. MongoDB Setup Guide

### Option A: Interactive In-Memory Demo Mode (Zero Setup)
Leave `MONGO_URI` empty in `.env`. The application automatically boots into in-memory persistence (`mongomock`), seeds all reference hospitals, blood stocks, appointments, and user accounts, and operates with 100% functionality out of the box.

### Option B: Connecting MongoDB Atlas (Production Cloud)
1. Go to [MongoDB Atlas](https://www.mongodb.com/atlas) and sign up for a free shared cluster (M0).
2. Under **Security &rarr; Database Access**, create a database user (e.g., `smart_admin`) with password.
3. Under **Security &rarr; Network Access**, add an IP Access List entry allowing `0.0.0.0/0` (or your IP).
4. Click **Connect &rarr; Connect your application &rarr; Driver: Python**.
5. Copy the connection string:
   ```env
   MONGO_URI=mongodb+srv://smart_admin:<password>@cluster0.abcde.mongodb.net/?retryWrites=true&w=majority
   DB_NAME=smart_blood_bank
   ```
6. Paste your URI into `.env`.
7. Re-seed your cloud cluster:
   ```powershell
   .\.venv\Scripts\python.exe seed_data.py
   ```

### Option C: Connecting Local MongoDB
If you have MongoDB Community Server installed locally on Windows:
```env
MONGO_URI=mongodb://localhost:27017/smart_blood_bank
DB_NAME=smart_blood_bank
```

---

## 6. Local Installation & Run Instructions (Windows)

### Prerequisites
- Windows 10/11
- PowerShell 5.1+

### Step-by-Step Setup
1. **Open PowerShell** in the project directory:
   ```powershell
   cd d:\antigravity
   ```

2. **Activate the Virtual Environment:**
   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```
   *(If not already created, run `uv venv .venv --python 3.11` followed by `uv pip install -r requirements.txt`)*

3. **Verify Configuration:**
   Ensure `.env` exists (copied from `.env.example`).

4. **Seed Database (Optional / Automatic):**
   ```powershell
   .\.venv\Scripts\python.exe seed_data.py
   ```

5. **Start the Flask Web Server:**
   ```powershell
   .\.venv\Scripts\python.exe app.py
   ```

6. **Open in Web Browser:**
   Navigate to **`http://127.0.0.1:5000`** in Chrome, Edge, or Firefox.

---

## 7. Running Automated Tests

Run the test suite to verify authentication, appointment booking, slot double-booking safeguards, stock audit logs, inter-hospital exchange, and MongoDB failover:

```powershell
.\.venv\Scripts\pytest -v tests -p no:cacheprovider --rootdir=.
```

**Test Suite Coverage (10/10 Passing):**
- `test_donor_registration_and_login`: Validates password hashing, input constraints, and duplicate email prevention.
- `test_hospital_registration_pending_verification`: Ensures new hospital registrations require administrative approval.
- `test_role_based_route_protections`: Verifies route protection for donor, hospital, and admin URLs.
- `test_appointment_booking_and_duplicate_prevention`: Tests slot reservation and prevents multi-booking on the same day.
- `test_slot_capacity_limit_enforcement`: Tests atomic slot capacity enforcement when slots are full.
- `test_reschedule_cancel_and_completion_lifecycle`: Verifies rescheduling, confirmation, collection bag logging, and automatic stock increment.
- `test_stock_retrieval_and_audit_update`: Tests inventory tracking for all 8 blood groups and immutable audit logging.
- `test_inter_hospital_stock_assistance`: Tests assistance request broadcast and acceptance between centers.
- `test_public_blood_request_submission_and_tracking`: Tests patient request tracking codes and administrative moderation.
- `test_mongodb_connection_failure_and_graceful_recovery`: Verifies graceful fallback to in-memory mode if Atlas is unreachable.

---

## 8. Feature Status Matrix

| Feature | Status | Notes |
|---|---|---|
| **Donor Registration & Login** | Working | Role forced to `donor`; secure password hashing. |
| **Hospital Registration & Verification** | Working | Starts as `pending_verification`; admin approval required. |
| **Administrator Console** | Working | Hospital verification queue, audit logs, request moderation. |
| **Donor Dashboard & Recovery Cooldown** | Working | Displays NBTC 90/120-day guidance; medical review notice. |
| **Appointment Booking Stepper** | Working | Real-time capacity counter; atomic double-booking safeguard. |
| **Printable Appointment Slip** | Working | Formatted modal pass with `window.print()` functionality. |
| **Reschedule & Cancel Appointment** | Working | Updates appointment status history with reasons. |
| **Donation Attendance & Bag ID** | Working | Auto-increments hospital stock by 1 unit with audit log. |
| **8 Blood Groups Inventory Management** | Working | Tracks A+, A-, B+, B-, AB+, AB-, O+, O- with audit trail. |
| **Inter-Hospital Stock Assistance** | Working | Centers can request and accept emergency unit transfers. |
| **Public Blood Search Directory** | Working | Filter by blood group, state, and district with live stock. |
| **Public Emergency Blood Requests** | Working | Generates unique tracking code (`REQ-2026-XXXX`). |
| **Public Request Tracking Stepper** | Working | Timeline showing verification, assignment, and fulfillment. |
| **In-App Notification Center** | Working | Stored in database; badge counter and mark-as-read. |
| **Google Maps Integration** | Configured | Google Maps ready via `GOOGLE_MAPS_API_KEY`; fallback district directory active. |
| **SMS / WhatsApp Business Gateway** | Stubs Active | Ready for Twilio / Meta API via `SMS_GATEWAY_API_KEY` / `WHATSAPP_BUSINESS_API_KEY`. |
| **MongoDB Atlas Persistence** | Supported | Connects via `MONGO_URI`; auto-recovers to demo mode if unset. |

---

## 9. Academic Prototype Notice

This web application was developed as a college project prototype demonstrating modern full-stack web architecture, reactive healthcare interfaces, and clinical database integrity. It is not intended for unsupervised commercial use or emergency dispatch.
