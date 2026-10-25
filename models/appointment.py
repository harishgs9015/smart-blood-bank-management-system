import uuid
from models import utc_now_iso

def generate_booking_reference():
    short_code = uuid.uuid4().hex[:6].upper()
    return f"REQ-2026-{short_code}"

class AppointmentModel:
    @staticmethod
    def create_appointment_doc(donor_id, donor_name, donor_email, donor_phone,
                               donor_blood_group, hospital_id, hospital_name,
                               hospital_district, hospital_state,
                               slot_date, slot_time, is_regular_pledge=False, notes="",
                               request_id=None):
        req_id = request_id or generate_booking_reference()
        return {
            "request_id": req_id,
            "booking_reference": req_id,
            "donor_id": str(donor_id),
            "donor_name": donor_name,
            "donor_email": donor_email,
            "donor_phone": donor_phone,
            "blood_group": donor_blood_group,
            "donor_blood_group": donor_blood_group,
            "hospital_id": str(hospital_id),
            "hospital_name": hospital_name,
            "hospital_district": hospital_district,
            "hospital_state": hospital_state,
            "appointment_date": slot_date,
            "slot_date": slot_date,
            "appointment_time": slot_time,
            "slot_time": slot_time,
            "status": "Pending",  # Pending, Confirmed, Rejected, Rescheduled, Completed
            "additional_details": notes.strip(),
            "notes": notes.strip(),
            "is_regular_pledge": bool(is_regular_pledge),
            "cancellation_reason": None,
            "rescheduled_from": None,
            "status_history": [
                {
                    "status": "Pending",
                    "timestamp": utc_now_iso(),
                    "note": f"Donation request sent to {hospital_name}."
                }
            ],
            # Filled upon attendance / completion:
            "donation_bag_id": None,
            "volume_ml": None,
            "attendance_verified_by": None,
            "completed_at": None,
            "created_at": utc_now_iso(),
            "updated_at": utc_now_iso()
        }
