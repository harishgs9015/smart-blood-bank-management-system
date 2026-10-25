import re
import logging
from bson import ObjectId
from extensions import get_db
from models.user import UserModel
from models.donor import DonorProfileModel
from models.hospital import HospitalModel
from models.stock import BLOOD_GROUPS, BloodStockModel
from services.audit_service import AuditService

logger = logging.getLogger(__name__)

EMAIL_REGEX = re.compile(r"^[\w\.-]+@[\w\.-]+\.\w+$")

class AuthService:
    @staticmethod
    def validate_email(email):
        return bool(email and EMAIL_REGEX.match(email.strip()))

    @staticmethod
    def register_donor(email, password, name, phone, blood_group, state, district,
                       date_of_birth="", gender="Other", address="",
                       last_donation_date=None, preference_regular=False,
                       preference_emergency=True, ip_address="127.0.0.1"):
        db = get_db()
        email = email.strip().lower()

        if not AuthService.validate_email(email):
            return False, "Invalid email address format."
        if len(password) < 6:
            return False, "Password must be at least 6 characters long."
        if not name.strip():
            return False, "Full name is required."
        if not blood_group:
            return False, "Blood group selection is required."

        # Check existing user
        if db.users.find_one({"email": email}):
            return False, "An account with this email already exists."

        # Create user document - always forced to 'donor' role
        user_doc = UserModel.create_user_doc(
            email=email,
            password=password,
            role="donor",
            name=name,
            phone=phone
        )
        res = db.users.insert_one(user_doc)
        user_id = str(res.inserted_id)

        # Create donor profile
        donor_doc = DonorProfileModel.create_profile_doc(
            user_id=user_id,
            blood_group=blood_group,
            state=state,
            district=district,
            date_of_birth=date_of_birth,
            gender=gender,
            address=address,
            last_donation_date=last_donation_date if last_donation_date else None,
            preference_regular=preference_regular,
            preference_emergency=preference_emergency
        )
        db.donor_profiles.insert_one(donor_doc)

        AuditService.log_action("DONOR_REGISTERED", email, "donor", f"New donor registered: {name} ({blood_group})", ip_address)
        return True, {"user_id": user_id, "email": email, "role": "donor", "name": name}

    @staticmethod
    def register_hospital(email, password, hospital_name, license_number, facility_type,
                          state, district, address, contact_person, phone, emergency_phone,
                          daily_capacity=4, operating_hours="24/7", ip_address="127.0.0.1"):
        db = get_db()
        email = email.strip().lower()
        license_number = license_number.strip().upper()

        if not AuthService.validate_email(email):
            return False, "Invalid email address format."
        if len(password) < 6:
            return False, "Password must be at least 6 characters long."
        if not hospital_name.strip() or not license_number:
            return False, "Hospital name and license number are required."

        if db.users.find_one({"email": email}):
            return False, "An account with this email already exists."

        if db.hospitals.find_one({"license_number": license_number}):
            return False, "A hospital with this license number is already registered."

        # Create hospital staff user account
        user_doc = UserModel.create_user_doc(
            email=email,
            password=password,
            role="hospital",
            name=contact_person,
            phone=phone
        )
        res = db.users.insert_one(user_doc)
        user_id = str(res.inserted_id)

        # Create hospital entity with pending_verification status
        hospital_doc = HospitalModel.create_hospital_doc(
            user_id=user_id,
            name=hospital_name,
            license_number=license_number,
            facility_type=facility_type,
            state=state,
            district=district,
            address=address,
            contact_person=contact_person,
            phone=phone,
            emergency_phone=emergency_phone,
            email=email,
            operating_hours=operating_hours,
            daily_slot_capacity=daily_capacity
        )
        h_res = db.hospitals.insert_one(hospital_doc)
        hospital_id = str(h_res.inserted_id)

        # Initialize stock records in database linked to this hospital
        location_str = f"{district}, {state}" if district and state else address
        for bg in BLOOD_GROUPS:
            db.blood_stock.insert_one(BloodStockModel.create_stock_doc(
                hospital_id=hospital_id,
                hospital_name=hospital_name,
                blood_group=bg,
                units=0,
                updated_by_user=email,
                location=location_str,
                details="Initial Registration Stock"
            ))

        AuditService.log_action("HOSPITAL_APPLICATION_SUBMITTED", email, "hospital", 
                                f"Hospital {hospital_name} submitted registration (License: {license_number})", ip_address)
        return True, {"user_id": user_id, "hospital_id": hospital_id, "email": email, "role": "hospital", "hospital_name": hospital_name}

    @staticmethod
    def authenticate_user(email, password):
        db = get_db()
        email = email.strip().lower()
        user = db.users.find_one({"email": email})

        if not user or not user.get("is_active", True):
            return None, "Invalid email or account is inactive."

        if not UserModel.verify_password(user["password_hash"], password):
            return None, "Invalid password credentials."

        # Attach role-specific metadata
        user_info = {
            "user_id": str(user["_id"]),
            "email": user["email"],
            "role": user["role"],
            "name": user.get("name", ""),
            "phone": user.get("phone", "")
        }

        if user["role"] == "donor":
            profile = db.donor_profiles.find_one({"user_id": str(user["_id"])}) or db.donor_profiles.find_one({"email": user["email"]})
            if profile:
                user_info["donor_id"] = profile.get("donor_id") or f"D{str(user['_id'])[:4]}"
                user_info["blood_group"] = profile.get("blood_group")
                user_info["district"] = profile.get("district")
                user_info["state"] = profile.get("state")
                user_info["location"] = f"{profile.get('district', '')}, {profile.get('state', '')}".strip(", ")
            else:
                user_info["donor_id"] = f"D{str(user['_id'])[:4]}"
                user_info["location"] = "Chennai, Tamil Nadu"
        elif user["role"] == "hospital":
            hospital = db.hospitals.find_one({"user_id": str(user["_id"])}) or db.hospitals.find_one({"email": user["email"]})
            if hospital:
                user_info["hospital_id"] = hospital.get("hospital_id") or str(hospital["_id"])
                user_info["hospital_name"] = hospital.get("name")
                user_info["hospital_status"] = hospital.get("status", "verified")
                user_info["district"] = hospital.get("district")
                user_info["state"] = hospital.get("state")
                user_info["location"] = hospital.get("location") or f"{hospital.get('district', '')}, {hospital.get('state', '')}".strip(", ") or "Chennai"
            else:
                user_info["hospital_id"] = f"H{str(user['_id'])[:4]}"
                user_info["hospital_name"] = "Blood Center"
                user_info["location"] = "Chennai"

        return user_info, "Authentication successful."

    @staticmethod
    def get_user_by_id(user_id):
        db = get_db()
        try:
            return db.users.find_one({"_id": ObjectId(user_id)})
        except Exception:
            return db.users.find_one({"_id": user_id})
