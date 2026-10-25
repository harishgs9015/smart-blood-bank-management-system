from models import utc_now_iso

DEFAULT_TIME_SLOTS = [
    "09:00 AM - 10:00 AM",
    "10:00 AM - 11:00 AM",
    "11:00 AM - 12:00 PM",
    "12:00 PM - 01:00 PM",
    "02:00 PM - 03:00 PM",
    "03:00 PM - 04:00 PM",
    "04:00 PM - 05:00 PM"
]

class HospitalModel:
    @staticmethod
    def create_hospital_doc(user_id, name, license_number, facility_type, 
                            state, district, address, contact_person, 
                            phone, emergency_phone, email, 
                            operating_hours="24/7", daily_slot_capacity=4,
                            lat=None, lng=None, hospital_id=None):
        return {
            "hospital_id": hospital_id or f"H{abs(hash(str(user_id))) % 900 + 100}",
            "user_id": str(user_id),
            "name": name.strip(),
            "hospital_name": name.strip(),
            "license_number": license_number.strip().upper(),
            "facility_type": facility_type,  # Government, Private, Red Cross, Charitable, Autonomous
            "state": state.strip(),
            "district": district.strip(),
            "city": district.strip(),
            "address": address.strip(),
            "contact_person": contact_person.strip(),
            "phone": phone.strip(),
            "emergency_phone": emergency_phone.strip(),
            "email": email.strip().lower(),
            "status": "pending_verification",  # 'pending_verification', 'verified', 'rejected'
            "verification_notes": "Application submitted. Awaiting administrative review and credential verification.",
            "verified_at": None,
            "verified_by": None,
            "operating_hours": operating_hours,
            "daily_slot_capacity": int(daily_slot_capacity),
            "available_slots": DEFAULT_TIME_SLOTS,
            "latitude": lat,
            "longitude": lng,
            "created_at": utc_now_iso(),
            "updated_at": utc_now_iso()
        }
