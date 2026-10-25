import logging
from datetime import datetime, timezone, timedelta
from werkzeug.security import generate_password_hash
from extensions import get_db
from models import utc_now_iso
from models.user import UserModel
from models.donor import DonorProfileModel
from models.hospital import HospitalModel, DEFAULT_TIME_SLOTS
from models.stock import BLOOD_GROUPS, BloodStockModel, get_stock_status
from models.appointment import AppointmentModel
from models.blood_request import BloodRequestModel
from models.audit import AuditLogModel
from models.notification import NotificationModel
from models.donation import DonationModel

logger = logging.getLogger(__name__)

def ensure_smart_blood_entities(db):
    """
    Guarantees ABC Hospital (H001), XYZ Hospital (H002),
    Donor 01 (D001), Donor 02 (D002), blood stock for all 9 groups,
    pending donation requests, and donation history are present.
    """
    now = utc_now_iso()

    # 1. ABC Hospital (H001) - Chennai
    abc_email = "abc.hospital@chennai.gov.in"
    abc_user = db.users.find_one({"email": abc_email})
    if not abc_user:
        abc_uid = db.users.insert_one({
            "email": abc_email,
            "password_hash": generate_password_hash("Hospital@2026"),
            "role": "hospital",
            "name": "ABC Hospital (Management)",
            "phone": "+91 44 2829 0200",
            "is_active": True,
            "created_at": now,
            "updated_at": now
        }).inserted_id
    else:
        abc_uid = abc_user["_id"]

    abc_hosp = db.hospitals.find_one({"hospital_id": "H001"})
    if not abc_hosp:
        abc_hosp_doc = {
            "hospital_id": "H001",
            "user_id": str(abc_uid),
            "name": "ABC Hospital",
            "hospital_name": "ABC Hospital",
            "license_number": "TN-BB-2022-H001",
            "facility_type": "Government",
            "state": "Tamil Nadu",
            "district": "Chennai",
            "city": "Chennai",
            "location": "Chennai",
            "address": "100 Anna Salai, Guindy, Chennai, Tamil Nadu - 600032",
            "contact": "+91 44 2829 0200",
            "contact_person": "Medical Superintendent",
            "phone": "+91 44 2829 0200",
            "emergency_phone": "+91 44 2829 0999",
            "email": abc_email,
            "status": "verified",
            "verification_notes": "Primary tertiary blood bank facility.",
            "verified_at": now,
            "verified_by": "admin@raktkosh.gov.in",
            "operating_hours": "24/7 (Emergency & Routine)",
            "daily_slot_capacity": 5,
            "available_slots": DEFAULT_TIME_SLOTS,
            "latitude": 13.0067,
            "longitude": 80.2038,
            "created_at": now,
            "updated_at": now
        }
        abc_hid = db.hospitals.insert_one(abc_hosp_doc).inserted_id
        abc_hosp = abc_hosp_doc
    else:
        abc_hid = abc_hosp["_id"]

    # ABC Hospital Stock: All 9 blood groups
    # O+: 25 units, min 10 -> Normal 🟢
    # A-: 4 units, min 10 -> Critical 🔴
    # Bombay Blood Group (hh): 2 units, min 5 -> Critical 🔴
    abc_stock_levels = {
        "O+": (25, 10),
        "A-": (4, 10),
        "Bombay Blood Group (hh)": (2, 5),
        "A+": (15, 10),
        "B+": (18, 10),
        "B-": (3, 8),
        "AB+": (8, 10),
        "AB-": (2, 6),
        "O-": (5, 10)
    }
    for bg, (units, min_req) in abc_stock_levels.items():
        if not db.blood_stock.find_one({"hospital_id": {"$in": ["H001", str(abc_hid)]}, "blood_group": bg}):
            db.blood_stock.insert_one(BloodStockModel.create_stock_doc(
                hospital_id="H001",
                hospital_name="ABC Hospital",
                blood_group=bg,
                units=units,
                updated_by_user=abc_email,
                minimum_required=min_req,
                location="Chennai"
            ))

    # 2. XYZ Hospital (H002) - Chennai
    xyz_email = "xyz.hospital@chennai.gov.in"
    xyz_user = db.users.find_one({"email": xyz_email})
    if not xyz_user:
        xyz_uid = db.users.insert_one({
            "email": xyz_email,
            "password_hash": generate_password_hash("Hospital@2026"),
            "role": "hospital",
            "name": "XYZ Hospital (Management)",
            "phone": "+91 44 2626 5000",
            "is_active": True,
            "created_at": now,
            "updated_at": now
        }).inserted_id
    else:
        xyz_uid = xyz_user["_id"]

    xyz_hosp = db.hospitals.find_one({"hospital_id": "H002"})
    if not xyz_hosp:
        xyz_hosp_doc = {
            "hospital_id": "H002",
            "user_id": str(xyz_uid),
            "name": "XYZ Hospital",
            "hospital_name": "XYZ Hospital",
            "license_number": "TN-BB-2023-H002",
            "facility_type": "Government",
            "state": "Tamil Nadu",
            "district": "Chennai",
            "city": "Chennai",
            "location": "Chennai",
            "address": "45 Poonamallee High Road, Kilpauk, Chennai, Tamil Nadu - 600010",
            "contact": "+91 44 2626 5000",
            "contact_person": "Chief Medical Officer",
            "phone": "+91 44 2626 5000",
            "emergency_phone": "+91 44 2626 5111",
            "email": xyz_email,
            "status": "verified",
            "verification_notes": "Regional healthcare center.",
            "verified_at": now,
            "verified_by": "admin@raktkosh.gov.in",
            "operating_hours": "24/7",
            "daily_slot_capacity": 5,
            "available_slots": DEFAULT_TIME_SLOTS,
            "latitude": 13.0784,
            "longitude": 80.2412,
            "created_at": now,
            "updated_at": now
        }
        xyz_hid = db.hospitals.insert_one(xyz_hosp_doc).inserted_id
        xyz_hosp = xyz_hosp_doc
    else:
        xyz_hid = xyz_hosp["_id"]

    xyz_stock_levels = {
        "O+": (16, 10),
        "A-": (6, 10),
        "Bombay Blood Group (hh)": (1, 5),
        "A+": (12, 10),
        "B+": (14, 10),
        "B-": (4, 8),
        "AB+": (7, 10),
        "AB-": (2, 6),
        "O-": (6, 10)
    }
    for bg, (units, min_req) in xyz_stock_levels.items():
        if not db.blood_stock.find_one({"hospital_id": {"$in": ["H002", str(xyz_hid)]}, "blood_group": bg}):
            db.blood_stock.insert_one(BloodStockModel.create_stock_doc(
                hospital_id="H002",
                hospital_name="XYZ Hospital",
                blood_group=bg,
                units=units,
                updated_by_user=xyz_email,
                minimum_required=min_req,
                location="Chennai"
            ))

    # 3. Donor 001 (D001) - Rahul Sharma
    d001_email = "donor01@example.com"
    d001_user = db.users.find_one({"email": d001_email})
    if not d001_user:
        d001_uid = db.users.insert_one({
            "email": d001_email,
            "password_hash": generate_password_hash("Donor@2026"),
            "role": "donor",
            "name": "Donor 01 (Rahul Sharma)",
            "phone": "+91 98765 43210",
            "is_active": True,
            "created_at": now,
            "updated_at": now
        }).inserted_id
    else:
        d001_uid = d001_user["_id"]

    if not db.donor_profiles.find_one({"donor_id": "D001"}):
        db.donor_profiles.insert_one({
            "donor_id": "D001",
            "user_id": str(d001_uid),
            "name": "Donor 01 (Rahul Sharma)",
            "blood_group": "O+",
            "contact": "+91 98765 43210",
            "phone": "+91 98765 43210",
            "email": d001_email,
            "location": "Chennai, Tamil Nadu",
            "state": "Tamil Nadu",
            "district": "Chennai",
            "date_of_birth": "1997-04-15",
            "gender": "Male",
            "address": "42 TTK Road, Alwarpet, Chennai, Tamil Nadu - 600018",
            "last_donation_date": "2026-08-15",
            "preference_regular": True,
            "preference_emergency": True,
            "total_donations": 2,
            "eligibility_review_status": "Eligible for Review",
            "notification_preferences": {"in_app": True, "email": True, "sms": True, "whatsapp": True},
            "created_at": now,
            "updated_at": now
        })

    # 4. Donor 002 (D002) - Priya Patel
    d002_email = "donor02@example.com"
    d002_user = db.users.find_one({"email": d002_email})
    if not d002_user:
        d002_uid = db.users.insert_one({
            "email": d002_email,
            "password_hash": generate_password_hash("Donor@2026"),
            "role": "donor",
            "name": "Donor 02 (Priya Patel)",
            "phone": "+91 98220 12345",
            "is_active": True,
            "created_at": now,
            "updated_at": now
        }).inserted_id
    else:
        d002_uid = d002_user["_id"]

    if not db.donor_profiles.find_one({"donor_id": "D002"}):
        db.donor_profiles.insert_one({
            "donor_id": "D002",
            "user_id": str(d002_uid),
            "name": "Donor 02 (Priya Patel)",
            "blood_group": "A+",
            "contact": "+91 98220 12345",
            "phone": "+91 98220 12345",
            "email": d002_email,
            "location": "Chennai, Tamil Nadu",
            "state": "Tamil Nadu",
            "district": "Chennai",
            "date_of_birth": "2000-01-20",
            "gender": "Female",
            "address": "15 Cathedral Road, Gopalapuram, Chennai, Tamil Nadu - 600086",
            "last_donation_date": None,
            "preference_regular": False,
            "preference_emergency": True,
            "total_donations": 0,
            "eligibility_review_status": "First-Time Donor",
            "notification_preferences": {"in_app": True, "email": True, "sms": False, "whatsapp": False},
            "created_at": now,
            "updated_at": now
        })

    # 5. Pre-seeded Appointments specifically for ABC Hospital (H001):
    # Donor 01 (D001) -> ABC Hospital (H001), O+, 25 Oct 2026, 10:30 AM, Status: Pending
    if not db.appointments.find_one({"request_id": "REQ-001"}):
        db.appointments.insert_one({
            "request_id": "REQ-001",
            "booking_reference": "REQ-001",
            "donor_id": "D001",
            "donor_user_id": str(d001_uid),
            "donor_name": "Donor 01 (Rahul Sharma)",
            "donor_email": d001_email,
            "donor_phone": "+91 98765 43210",
            "blood_group": "O+",
            "donor_blood_group": "O+",
            "hospital_id": "H001",
            "hospital_obj_id": str(abc_hid),
            "hospital_name": "ABC Hospital",
            "hospital_district": "Chennai",
            "hospital_state": "Tamil Nadu",
            "appointment_date": "25 Oct 2026",
            "slot_date": "2026-10-25",
            "appointment_time": "10:30 AM",
            "slot_time": "10:00 AM - 11:00 AM",
            "status": "Pending",
            "additional_details": "Voluntary donation for emergency reserve.",
            "notes": "Voluntary donation for emergency reserve.",
            "is_regular_pledge": True,
            "cancellation_reason": None,
            "rescheduled_from": None,
            "status_history": [
                {
                    "status": "Pending",
                    "timestamp": now,
                    "note": "Donation request sent to ABC Hospital."
                }
            ],
            "created_at": now,
            "updated_at": now
        })

    # Donor 02 (D002) -> ABC Hospital (H001), A+, 26 Oct 2026, 11:00 AM, Status: Pending
    if not db.appointments.find_one({"request_id": "REQ-002"}):
        db.appointments.insert_one({
            "request_id": "REQ-002",
            "booking_reference": "REQ-002",
            "donor_id": "D002",
            "donor_user_id": str(d002_uid),
            "donor_name": "Donor 02 (Priya Patel)",
            "donor_email": d002_email,
            "donor_phone": "+91 98220 12345",
            "blood_group": "A+",
            "donor_blood_group": "A+",
            "hospital_id": "H001",
            "hospital_obj_id": str(abc_hid),
            "hospital_name": "ABC Hospital",
            "hospital_district": "Chennai",
            "hospital_state": "Tamil Nadu",
            "appointment_date": "26 Oct 2026",
            "slot_date": "2026-10-26",
            "appointment_time": "11:00 AM",
            "slot_time": "11:00 AM - 12:00 PM",
            "status": "Pending",
            "additional_details": "First-time blood donation pledge.",
            "notes": "First-time blood donation pledge.",
            "is_regular_pledge": False,
            "cancellation_reason": None,
            "rescheduled_from": None,
            "status_history": [
                {
                    "status": "Pending",
                    "timestamp": now,
                    "note": "Donation request sent to ABC Hospital."
                }
            ],
            "created_at": now,
            "updated_at": now
        })

    # 6. Completed Donation Record for ABC Hospital & D001
    if not db.donations.find_one({"donation_id": "DON-001"}):
        db.donations.insert_one({
            "donation_id": "DON-001",
            "donor_id": "D001",
            "donor_name": "Donor 01 (Rahul Sharma)",
            "hospital_id": "H001",
            "hospital_name": "ABC Hospital",
            "blood_group": "O+",
            "donation_date": "2026-08-15",
            "units_collected": 1,
            "details": "Routine voluntary donation camp collection (Bag #TN-ABC-402)",
            "recorded_by": abc_email,
            "created_at": now
        })

    # 7. Incoming Blood Request for ABC Hospital (REQ-BLD-001)
    if not db.blood_requests.find_one({"blood_request_id": "REQ-BLD-001"}):
        db.blood_requests.insert_one({
            "blood_request_id": "REQ-BLD-001",
            "tracking_code": "REQ-BLD-001",
            "hospital_id": "H001",
            "hospital_name": "ABC Hospital",
            "hospital_district": "Chennai",
            "hospital_state": "Tamil Nadu",
            "patient_name": "Emergency Cardiac Patient (OT-4)",
            "blood_group": "O+",
            "required_units": 3,
            "units_needed": 3,
            "priority": "High",
            "urgency": "High",
            "status": "Pending",
            "requester_name": "Dr. E. Parthasarathy",
            "requester_phone": "+91 44 2829 0255",
            "medical_notes": "Urgent aortic replacement surgery. Immediate cross-match required.",
            "created_at": now,
            "updated_at": now
        })

def ensure_tamil_nadu_and_regional_hospitals(db):
    """
    Guarantees verified Tamil Nadu hospitals and live blood stocks exist in database.
    Seeds realistic values: A Positive — 12 units, O Positive — 8 units, B Positive — 5 units.
    """
    ensure_smart_blood_entities(db)
    rgggh_existing = db.hospitals.find_one({"state": "Tamil Nadu", "status": "verified", "name": {"$regex": "Rajiv Gandhi", "$options": "i"}})
    if rgggh_existing and db.blood_stock.count_documents({"hospital_id": str(rgggh_existing["_id"])}) >= 8:
        return

    logger.info("Seeding verified Tamil Nadu hospitals and blood stock...")
    now = utc_now_iso()

    # 1. RGGGH Chennai (A+ 12 units, O+ 8 units, B+ 5 units)
    rgggh_email = "rgggh.bloodbank@tn.gov.in"
    rgggh_user = db.users.find_one({"email": rgggh_email})
    if not rgggh_user:
        rgggh_user_doc = {
            "email": rgggh_email,
            "password_hash": generate_password_hash("Hospital@2026"),
            "role": "hospital",
            "name": "Dr. S. Kanthimathy",
            "phone": "+91 44 2530 5000",
            "is_active": True,
            "created_at": now,
            "updated_at": now
        }
        rgggh_uid = db.users.insert_one(rgggh_user_doc).inserted_id
    else:
        rgggh_uid = rgggh_user["_id"]

    rgggh_hospital = {
        "user_id": str(rgggh_uid),
        "name": "Rajiv Gandhi Government General Hospital (RGGGH) Central Blood Bank",
        "license_number": "TN-BB-2018-0045",
        "facility_type": "Government",
        "state": "Tamil Nadu",
        "district": "Chennai",
        "city": "Chennai",
        "address": "EVR Periyar Salai, Park Town, Chennai, Tamil Nadu - 600003",
        "contact_person": "Dr. S. Kanthimathy",
        "phone": "+91 44 2530 5000",
        "emergency_phone": "+91 44 2530 5111",
        "email": rgggh_email,
        "status": "verified",
        "verification_notes": "Apex government tertiary hospital blood transfusion center in Tamil Nadu.",
        "verified_at": now,
        "verified_by": "admin@raktkosh.gov.in",
        "operating_hours": "24/7 (Emergency & Routine)",
        "daily_slot_capacity": 5,
        "available_slots": DEFAULT_TIME_SLOTS,
        "latitude": 13.0827,
        "longitude": 80.2707,
        "created_at": now,
        "updated_at": now
    }
    rgggh_hid = db.hospitals.insert_one(rgggh_hospital).inserted_id

    # Live database stock (sample values: A Positive - 12 units, O Positive - 8 units, B Positive - 5 units)
    rgggh_units = {
        "A+": 12, "A-": 4, "B+": 5, "B-": 2,
        "AB+": 6, "AB-": 1, "O+": 8, "O-": 3
    }
    for bg, units in rgggh_units.items():
        db.blood_stock.insert_one(BloodStockModel.create_stock_doc(
            hospital_id=str(rgggh_hid),
            hospital_name=rgggh_hospital["name"],
            blood_group=bg,
            units=units,
            updated_by_user=rgggh_email
        ))

    # 2. Coimbatore Medical College Hospital
    cmch_email = "cmch.bloodbank@tn.gov.in"
    cmch_user = db.users.find_one({"email": cmch_email})
    if not cmch_user:
        cmch_user_doc = {
            "email": cmch_email,
            "password_hash": generate_password_hash("Hospital@2026"),
            "role": "hospital",
            "name": "Dr. K. Nirmala",
            "phone": "+91 422 230 1393",
            "is_active": True,
            "created_at": now,
            "updated_at": now
        }
        cmch_uid = db.users.insert_one(cmch_user_doc).inserted_id
    else:
        cmch_uid = cmch_user["_id"]

    cmch_hospital = {
        "user_id": str(cmch_uid),
        "name": "Coimbatore Medical College Hospital Blood Center",
        "license_number": "TN-BB-2020-0112",
        "facility_type": "Government",
        "state": "Tamil Nadu",
        "district": "Coimbatore",
        "city": "Coimbatore",
        "address": "Trichy Road, Town Hall, Coimbatore, Tamil Nadu - 641018",
        "contact_person": "Dr. K. Nirmala",
        "phone": "+91 422 230 1393",
        "emergency_phone": "+91 422 230 1394",
        "email": cmch_email,
        "status": "verified",
        "verification_notes": "Government district apex blood center.",
        "verified_at": now,
        "verified_by": "admin@raktkosh.gov.in",
        "operating_hours": "24/7",
        "daily_slot_capacity": 4,
        "available_slots": DEFAULT_TIME_SLOTS,
        "latitude": 11.0018,
        "longitude": 76.9629,
        "created_at": now,
        "updated_at": now
    }
    cmch_hid = db.hospitals.insert_one(cmch_hospital).inserted_id

    cmch_units = {
        "A+": 14, "A-": 3, "B+": 16, "B-": 3,
        "AB+": 7, "AB-": 2, "O+": 22, "O-": 5
    }
    for bg, units in cmch_units.items():
        db.blood_stock.insert_one(BloodStockModel.create_stock_doc(
            hospital_id=str(cmch_hid),
            hospital_name=cmch_hospital["name"],
            blood_group=bg,
            units=units,
            updated_by_user=cmch_email
        ))

    # 3. Government Rajaji Hospital Madurai
    grh_email = "grh.bloodbank@tn.gov.in"
    grh_user = db.users.find_one({"email": grh_email})
    if not grh_user:
        grh_user_doc = {
            "email": grh_email,
            "password_hash": generate_password_hash("Hospital@2026"),
            "role": "hospital",
            "name": "Dr. A. Rathinavel",
            "phone": "+91 452 253 2535",
            "is_active": True,
            "created_at": now,
            "updated_at": now
        }
        grh_uid = db.users.insert_one(grh_user_doc).inserted_id
    else:
        grh_uid = grh_user["_id"]

    grh_hospital = {
        "user_id": str(grh_uid),
        "name": "Government Rajaji Hospital Regional Blood Transfusion Center",
        "license_number": "TN-BB-2019-0089",
        "facility_type": "Government",
        "state": "Tamil Nadu",
        "district": "Madurai",
        "city": "Madurai",
        "address": "Panagal Road, Shenoy Nagar, Madurai, Tamil Nadu - 625020",
        "contact_person": "Dr. A. Rathinavel",
        "phone": "+91 452 253 2535",
        "emergency_phone": "+91 452 253 2536",
        "email": grh_email,
        "status": "verified",
        "verification_notes": "Southern regional blood transfusion center.",
        "verified_at": now,
        "verified_by": "admin@raktkosh.gov.in",
        "operating_hours": "08:00 AM - 08:00 PM",
        "daily_slot_capacity": 4,
        "available_slots": DEFAULT_TIME_SLOTS,
        "latitude": 9.9252,
        "longitude": 78.1198,
        "created_at": now,
        "updated_at": now
    }
    grh_hid = db.hospitals.insert_one(grh_hospital).inserted_id

    grh_units = {
        "A+": 9, "A-": 2, "B+": 12, "B-": 2,
        "AB+": 4, "AB-": 1, "O+": 15, "O-": 3
    }
    for bg, units in grh_units.items():
        db.blood_stock.insert_one(BloodStockModel.create_stock_doc(
            hospital_id=str(grh_hid),
            hospital_name=grh_hospital["name"],
            blood_group=bg,
            units=units,
            updated_by_user=grh_email
        ))

def seed_database(force=False):
    db = get_db()
    
    # If users already exist and not forcing, ensure supplemental records are present and return
    if not force and db.users.count_documents({}) > 0:
        ensure_tamil_nadu_and_regional_hospitals(db)
        logger.info("Database already seeded with initial data.")
        return

    logger.info("Seeding database with realistic Indian healthcare entities...")

    # Clear if force
    if force:
        db.users.delete_many({})
        db.donor_profiles.delete_many({})
        db.hospitals.delete_many({})
        db.blood_stock.delete_many({})
        db.appointments.delete_many({})
        db.donations.delete_many({})
        db.blood_requests.delete_many({})
        db.notifications.delete_many({})
        db.audit_logs.delete_many({})
        db.stock_assistance.delete_many({})

    # 1. Administrator Account
    admin_user = {
        "email": "admin@raktkosh.gov.in",
        "password_hash": generate_password_hash("Admin@2026"),
        "role": "admin",
        "name": "Dr. Vinod Paul (Director General, Blood Transfusion Authority)",
        "phone": "+91 11 2306 1423",
        "is_active": True,
        "created_at": utc_now_iso(),
        "updated_at": utc_now_iso()
    }
    admin_id = db.users.insert_one(admin_user).inserted_id

    # 2. Hospital 1: AIIMS New Delhi (Verified)
    aiims_user = {
        "email": "aiims.bloodbank@delhi.gov.in",
        "password_hash": generate_password_hash("Hospital@2026"),
        "role": "hospital",
        "name": "Dr. Sunil Grover (Head of Transfusion Medicine)",
        "phone": "+91 11 2658 8500",
        "is_active": True,
        "created_at": utc_now_iso(),
        "updated_at": utc_now_iso()
    }
    aiims_uid = db.users.insert_one(aiims_user).inserted_id

    aiims_hospital = {
        "user_id": str(aiims_uid),
        "name": "All India Institute of Medical Sciences (AIIMS) Central Blood Bank",
        "license_number": "DL-BB-2021-0012",
        "facility_type": "Government",
        "state": "Delhi (NCR)",
        "district": "New Delhi",
        "city": "New Delhi",
        "address": "Sri Aurobindo Marg, Ansari Nagar, New Delhi, Delhi - 110029",
        "contact_person": "Dr. Sunil Grover",
        "phone": "+91 11 2658 8500",
        "emergency_phone": "+91 11 2659 4405",
        "email": "aiims.bloodbank@delhi.gov.in",
        "status": "verified",
        "verification_notes": "Central government apex medical institute. Validated by Directorate General of Health Services (DGHS).",
        "verified_at": utc_now_iso(),
        "verified_by": "admin@raktkosh.gov.in",
        "operating_hours": "24/7 (Emergency & Routine)",
        "daily_slot_capacity": 5,
        "available_slots": DEFAULT_TIME_SLOTS,
        "latitude": 28.5672,
        "longitude": 77.2100,
        "created_at": utc_now_iso(),
        "updated_at": utc_now_iso()
    }
    aiims_hid = db.hospitals.insert_one(aiims_hospital).inserted_id

    # AIIMS Blood Stock
    aiims_units = {
        "A+": 16, "A-": 4, "B+": 25, "B-": 3,
        "AB+": 9, "AB-": 2, "O+": 32, "O-": 6
    }
    for bg, units in aiims_units.items():
        db.blood_stock.insert_one(BloodStockModel.create_stock_doc(
            hospital_id=str(aiims_hid),
            hospital_name=aiims_hospital["name"],
            blood_group=bg,
            units=units,
            updated_by_user="aiims.bloodbank@delhi.gov.in"
        ))

    # 3. Hospital 2: KEM Hospital Mumbai (Verified)
    kem_user = {
        "email": "kem.bloodbank@mumbai.gov.in",
        "password_hash": generate_password_hash("Hospital@2026"),
        "role": "hospital",
        "name": "Dr. Snehal Patil",
        "phone": "+91 22 2410 7000",
        "is_active": True,
        "created_at": utc_now_iso(),
        "updated_at": utc_now_iso()
    }
    kem_uid = db.users.insert_one(kem_user).inserted_id

    kem_hospital = {
        "user_id": str(kem_uid),
        "name": "King Edward Memorial (KEM) Hospital Blood Center",
        "license_number": "MH-BB-2019-4401",
        "facility_type": "Government",
        "state": "Maharashtra",
        "district": "Mumbai City",
        "city": "Mumbai",
        "address": "Acharya Donde Marg, Parel, Mumbai, Maharashtra - 400012",
        "contact_person": "Dr. Snehal Patil",
        "phone": "+91 22 2410 7000",
        "emergency_phone": "+91 22 2410 7555",
        "email": "kem.bloodbank@mumbai.gov.in",
        "status": "verified",
        "verification_notes": "Municipal corporation tertiary care blood bank.",
        "verified_at": utc_now_iso(),
        "verified_by": "admin@raktkosh.gov.in",
        "operating_hours": "24/7",
        "daily_slot_capacity": 6,
        "available_slots": DEFAULT_TIME_SLOTS,
        "latitude": 18.9986,
        "longitude": 72.8427,
        "created_at": utc_now_iso(),
        "updated_at": utc_now_iso()
    }
    kem_hid = db.hospitals.insert_one(kem_hospital).inserted_id

    # KEM Stock
    kem_units = {
        "A+": 12, "A-": 2, "B+": 18, "B-": 4,
        "AB+": 6, "AB-": 1, "O+": 24, "O-": 4
    }
    for bg, units in kem_units.items():
        db.blood_stock.insert_one(BloodStockModel.create_stock_doc(
            hospital_id=str(kem_hid),
            hospital_name=kem_hospital["name"],
            blood_group=bg,
            units=units,
            updated_by_user="kem.bloodbank@mumbai.gov.in"
        ))

    # 4. Hospital 3: Victoria Hospital Bengaluru (Verified)
    vic_user = {
        "email": "victoria.bloodbank@karnataka.gov.in",
        "password_hash": generate_password_hash("Hospital@2026"),
        "role": "hospital",
        "name": "Dr. Ramesh Murthy",
        "phone": "+91 80 2670 1150",
        "is_active": True,
        "created_at": utc_now_iso(),
        "updated_at": utc_now_iso()
    }
    vic_uid = db.users.insert_one(vic_user).inserted_id

    vic_hospital = {
        "user_id": str(vic_uid),
        "name": "Victoria Hospital & Bowring Blood Center",
        "license_number": "KA-BB-2020-1192",
        "facility_type": "Government",
        "state": "Karnataka",
        "district": "Bengaluru Urban",
        "city": "Bengaluru",
        "address": "Fort Road, near City Market, Kalasipalya, Bengaluru, Karnataka - 560002",
        "contact_person": "Dr. Ramesh Murthy",
        "phone": "+91 80 2670 1150",
        "emergency_phone": "+91 80 2670 1155",
        "email": "victoria.bloodbank@karnataka.gov.in",
        "status": "verified",
        "verification_notes": "State government teaching hospital blood bank.",
        "verified_at": utc_now_iso(),
        "verified_by": "admin@raktkosh.gov.in",
        "operating_hours": "08:00 AM - 08:00 PM",
        "daily_slot_capacity": 4,
        "available_slots": DEFAULT_TIME_SLOTS,
        "latitude": 12.9634,
        "longitude": 77.5755,
        "created_at": utc_now_iso(),
        "updated_at": utc_now_iso()
    }
    vic_hid = db.hospitals.insert_one(vic_hospital).inserted_id

    # Victoria Stock
    vic_units = {
        "A+": 8, "A-": 1, "B+": 14, "B-": 2,
        "AB+": 5, "AB-": 0, "O+": 19, "O-": 2
    }
    for bg, units in vic_units.items():
        db.blood_stock.insert_one(BloodStockModel.create_stock_doc(
            hospital_id=str(vic_hid),
            hospital_name=vic_hospital["name"],
            blood_group=bg,
            units=units,
            updated_by_user="victoria.bloodbank@karnataka.gov.in"
        ))

    # 5. Hospital 4: Sanjeevani Blood Bank (Pending Verification for Admin demo)
    sanj_user = {
        "email": "sanjeevani@punecharity.org",
        "password_hash": generate_password_hash("Hospital@2026"),
        "role": "hospital",
        "name": "Dr. Anita Joshi",
        "phone": "+91 20 2565 4321",
        "is_active": True,
        "created_at": utc_now_iso(),
        "updated_at": utc_now_iso()
    }
    sanj_uid = db.users.insert_one(sanj_user).inserted_id

    sanj_hospital = {
        "user_id": str(sanj_uid),
        "name": "Sanjeevani Charitable Blood Bank & Research Institute",
        "license_number": "MH-BB-2026-9041",
        "facility_type": "Charitable",
        "state": "Maharashtra",
        "district": "Pune",
        "city": "Pune",
        "address": "45/2, FC Road, Shivajinagar, Pune, Maharashtra - 411005",
        "contact_person": "Dr. Anita Joshi",
        "phone": "+91 20 2565 4321",
        "emergency_phone": "+91 20 2565 9999",
        "email": "sanjeevani@punecharity.org",
        "status": "pending_verification",
        "verification_notes": "Application submitted with Maharashtra FDA Form 28C. Awaiting inspection report.",
        "verified_at": None,
        "verified_by": None,
        "operating_hours": "09:00 AM - 07:00 PM",
        "daily_slot_capacity": 3,
        "available_slots": DEFAULT_TIME_SLOTS,
        "latitude": 18.5204,
        "longitude": 73.8567,
        "created_at": utc_now_iso(),
        "updated_at": utc_now_iso()
    }
    db.hospitals.insert_one(sanj_hospital)

    # 6. Sample Donors
    # Donor 1: Rahul Sharma
    rahul_user = {
        "email": "rahul.sharma@gmail.com",
        "password_hash": generate_password_hash("Donor@2026"),
        "role": "donor",
        "name": "Rahul Sharma",
        "phone": "+91 98765 43210",
        "is_active": True,
        "created_at": utc_now_iso(),
        "updated_at": utc_now_iso()
    }
    rahul_uid = db.users.insert_one(rahul_user).inserted_id

    last_donation_date = (datetime.now(timezone.utc).date() - timedelta(days=96)).strftime("%Y-%m-%d")
    rahul_profile = {
        "user_id": str(rahul_uid),
        "blood_group": "O+",
        "state": "Delhi (NCR)",
        "district": "New Delhi",
        "date_of_birth": "1997-04-15",
        "gender": "Male",
        "address": "B-42, Lajpat Nagar II, New Delhi - 110024",
        "last_donation_date": last_donation_date,
        "preference_regular": True,
        "preference_emergency": True,
        "total_donations": 3,
        "eligibility_review_status": "Eligible for Review (Recovery Gap Met)",
        "eligibility_notes": "Last donated >90 days ago. Medical vitals and Hemoglobin check to be performed at center.",
        "notification_preferences": {
            "in_app": True,
            "email": True,
            "sms": True,
            "whatsapp": True
        },
        "created_at": utc_now_iso(),
        "updated_at": utc_now_iso()
    }
    db.donor_profiles.insert_one(rahul_profile)

    # Donor 2: Priya Deshmukh
    priya_user = {
        "email": "priya.deshmukh@gmail.com",
        "password_hash": generate_password_hash("Donor@2026"),
        "role": "donor",
        "name": "Priya Deshmukh",
        "phone": "+91 98220 12345",
        "is_active": True,
        "created_at": utc_now_iso(),
        "updated_at": utc_now_iso()
    }
    priya_uid = db.users.insert_one(priya_user).inserted_id

    priya_profile = {
        "user_id": str(priya_uid),
        "blood_group": "B+",
        "state": "Maharashtra",
        "district": "Mumbai City",
        "date_of_birth": "1999-09-22",
        "gender": "Female",
        "address": "12, Shivaji Park, Dadar West, Mumbai - 400028",
        "last_donation_date": None,
        "preference_regular": False,
        "preference_emergency": True,
        "total_donations": 0,
        "eligibility_review_status": "First-Time Donor (On-Site Review Required)",
        "eligibility_notes": "First donation. Mandatory physical examination and hemoglobin test required.",
        "notification_preferences": {
            "in_app": True,
            "email": True,
            "sms": False,
            "whatsapp": False
        },
        "created_at": utc_now_iso(),
        "updated_at": utc_now_iso()
    }
    db.donor_profiles.insert_one(priya_profile)

    # 7. Sample Appointments
    tomorrow_str = (datetime.now(timezone.utc).date() + timedelta(days=2)).strftime("%Y-%m-%d")
    appt1 = {
        "booking_reference": "BD-2026-DEL101",
        "donor_id": str(rahul_uid),
        "donor_name": "Rahul Sharma",
        "donor_email": "rahul.sharma@gmail.com",
        "donor_phone": "+91 98765 43210",
        "donor_blood_group": "O+",
        "hospital_id": str(aiims_hid),
        "hospital_name": aiims_hospital["name"],
        "hospital_district": "New Delhi",
        "hospital_state": "Delhi (NCR)",
        "slot_date": tomorrow_str,
        "slot_time": "10:00 AM - 11:00 AM",
        "status": "confirmed",
        "is_regular_pledge": True,
        "notes": "Regular quarterly voluntary donation pledge.",
        "cancellation_reason": None,
        "rescheduled_from": None,
        "status_history": [
            {"status": "pending", "timestamp": utc_now_iso(), "note": "Appointment requested by donor."},
            {"status": "confirmed", "timestamp": utc_now_iso(), "note": "Confirmed by AIIMS Blood Center staff."}
        ],
        "donation_bag_id": None,
        "volume_ml": None,
        "attendance_verified_by": None,
        "completed_at": None,
        "created_at": utc_now_iso(),
        "updated_at": utc_now_iso()
    }
    db.appointments.insert_one(appt1)

    past_date_str = (datetime.now(timezone.utc).date() - timedelta(days=96)).strftime("%Y-%m-%d")
    appt_past = {
        "booking_reference": "BD-2026-DEL008",
        "donor_id": str(rahul_uid),
        "donor_name": "Rahul Sharma",
        "donor_email": "rahul.sharma@gmail.com",
        "donor_phone": "+91 98765 43210",
        "donor_blood_group": "O+",
        "hospital_id": str(aiims_hid),
        "hospital_name": aiims_hospital["name"],
        "hospital_district": "New Delhi",
        "hospital_state": "Delhi (NCR)",
        "slot_date": past_date_str,
        "slot_time": "11:00 AM - 12:00 PM",
        "status": "completed",
        "is_regular_pledge": True,
        "notes": "Voluntary blood donation.",
        "cancellation_reason": None,
        "rescheduled_from": None,
        "status_history": [
            {"status": "pending", "timestamp": utc_now_iso(), "note": "Appointment requested."},
            {"status": "confirmed", "timestamp": utc_now_iso(), "note": "Confirmed."},
            {"status": "completed", "timestamp": utc_now_iso(), "note": "Donation completed. Bag ID: DL-AIIMS-9810, Volume: 450ml."}
        ],
        "donation_bag_id": "DL-AIIMS-9810",
        "volume_ml": 450,
        "attendance_verified_by": "aiims.bloodbank@delhi.gov.in",
        "completed_at": utc_now_iso(),
        "created_at": utc_now_iso(),
        "updated_at": utc_now_iso()
    }
    db.appointments.insert_one(appt_past)

    # 8. Sample Blood Requests
    req1 = {
        "tracking_code": "REQ-2026-DL8921",
        "patient_name": "Amitav Sengupta",
        "blood_group": "AB-",
        "units_needed": 2,
        "hospital_name": "Safdarjung Hospital",
        "hospital_district": "New Delhi",
        "hospital_state": "Delhi (NCR)",
        "doctor_case_ref": "SJ-CARDIO-4491",
        "urgency": "Emergency",
        "requester_name": "Meera Sengupta",
        "requester_phone": "+91 98112 34567",
        "requester_email": "meera.s@gmail.com",
        "medical_notes": "Emergency coronary bypass surgery scheduled. Rare blood group required immediately.",
        "status": "verified",
        "assigned_hospital_id": str(aiims_hid),
        "assigned_hospital_name": aiims_hospital["name"],
        "verification_notes": "Prescription and operative requirement verified with Safdarjung duty surgeon Dr. Mathur.",
        "verified_by": "admin@raktkosh.gov.in",
        "status_history": [
            {"status": "pending_verification", "timestamp": utc_now_iso(), "note": "Public request logged."},
            {"status": "verified", "timestamp": utc_now_iso(), "note": "Verified by central authority; cross-matched with AIIMS blood stock."}
        ],
        "created_at": utc_now_iso(),
        "updated_at": utc_now_iso()
    }
    db.blood_requests.insert_one(req1)

    req2 = {
        "tracking_code": "REQ-2026-MH3014",
        "patient_name": "Siddharth Shinde",
        "blood_group": "O-",
        "units_needed": 3,
        "hospital_name": "Sion Hospital",
        "hospital_district": "Mumbai City",
        "hospital_state": "Maharashtra",
        "doctor_case_ref": "LTMMC-TRAUMA-102",
        "urgency": "Urgent",
        "requester_name": "Kavita Shinde",
        "requester_phone": "+91 98201 98765",
        "requester_email": "kavita.shinde@yahoo.in",
        "medical_notes": "Trauma surgery follow-up. Universal donor units needed.",
        "status": "pending_verification",
        "assigned_hospital_id": None,
        "assigned_hospital_name": None,
        "verification_notes": "Awaiting prescription verification with attending trauma surgeon.",
        "verified_by": None,
        "status_history": [
            {"status": "pending_verification", "timestamp": utc_now_iso(), "note": "Public request submitted."}
        ],
        "created_at": utc_now_iso(),
        "updated_at": utc_now_iso()
    }
    db.blood_requests.insert_one(req2)

    # 9. Inter-Hospital Stock Assistance Request
    assist1 = {
        "requesting_hospital_id": str(vic_hid),
        "requesting_hospital_name": vic_hospital["name"],
        "blood_group": "AB-",
        "units_needed": 2,
        "urgency": "High",
        "reason": "Critical stock depletion (0 units available) for pediatric thalassemia patient.",
        "status": "Open",
        "accepted_by_hospital_id": None,
        "accepted_by_hospital_name": None,
        "created_at": utc_now_iso(),
        "updated_at": utc_now_iso()
    }
    db.stock_assistance.insert_one(assist1)

    # 10. Audit Logs
    AuditLogModel.create_log_doc("SYSTEM_INIT", "system", "system", "Smart Blood Donation System seeded with national reference data.")
    db.audit_logs.insert_one({
        "action": "SYSTEM_INITIALIZED",
        "performed_by": "system",
        "role": "system",
        "details": "Platform baseline entities (AIIMS, KEM, Victoria Hospital, Administrator) initialized.",
        "ip_address": "127.0.0.1",
        "timestamp": utc_now_iso()
    })
    db.audit_logs.insert_one({
        "action": "HOSPITAL_VERIFIED",
        "performed_by": "admin@raktkosh.gov.in",
        "role": "admin",
        "details": f"AIIMS Central Blood Bank verified by Directorate General of Health Services.",
        "ip_address": "127.0.0.1",
        "timestamp": utc_now_iso()
    })

    # 11. Initial In-App Notifications for Rahul Sharma
    db.notifications.insert_one(NotificationModel.create_notification_doc(
        user_id=str(rahul_uid),
        email="rahul.sharma@gmail.com",
        title="Donation Appointment Reminder",
        message=f"Reminder: You have an upcoming blood donation scheduled at AIIMS Central Blood Bank on {tomorrow_str} at 10:00 AM. Thank you for your commitment!",
        notif_type="appointment"
    ))

    ensure_tamil_nadu_and_regional_hospitals(db)

    logger.info("Database seeding completed successfully.")

if __name__ == "__main__":
    from app import create_app
    app = create_app()
    with app.app_context():
        seed_database(force=True)
        print("Database seeded successfully with realistic demonstration data.")
