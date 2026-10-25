import uuid
from models import utc_now_iso

def generate_request_tracking_code():
    # E.g. REQ-2026-X9Y8Z7
    short_code = uuid.uuid4().hex[:6].upper()
    return f"REQ-2026-{short_code}"

class BloodRequestModel:
    @staticmethod
    def create_request_doc(patient_name, blood_group, units_needed, hospital_name,
                           hospital_district, hospital_state, doctor_case_ref,
                           urgency, requester_name, requester_phone, requester_email="",
                           medical_notes=""):
        return {
            "tracking_code": generate_request_tracking_code(),
            "patient_name": patient_name.strip(),
            "blood_group": blood_group,
            "units_needed": int(units_needed),
            "hospital_name": hospital_name.strip(),
            "hospital_district": hospital_district.strip(),
            "hospital_state": hospital_state.strip(),
            "doctor_case_ref": doctor_case_ref.strip(),
            "urgency": urgency,  # 'Emergency', 'Urgent', 'Standard'
            "requester_name": requester_name.strip(),
            "requester_phone": requester_phone.strip(),
            "requester_email": requester_email.strip().lower() if requester_email else "",
            "medical_notes": medical_notes.strip(),
            "status": "pending_verification",  # 'pending_verification', 'verified', 'hospital_assigned', 'fulfilled', 'cancelled'
            "assigned_hospital_id": None,
            "assigned_hospital_name": None,
            "verification_notes": "Submitted by public user. Medical prescription must be verified by attending blood bank staff.",
            "verified_by": None,
            "status_history": [
                {
                    "status": "pending_verification",
                    "timestamp": utc_now_iso(),
                    "note": "Request registered in system."
                }
            ],
            "created_at": utc_now_iso(),
            "updated_at": utc_now_iso()
        }
