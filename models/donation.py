import uuid
from models import utc_now_iso

def generate_donation_id():
    return f"DON-{uuid.uuid4().hex[:6].upper()}"

class DonationModel:
    @staticmethod
    def create_donation_doc(donor_id, donor_name, hospital_id, hospital_name,
                            blood_group, donation_date, units_collected=1,
                            details="", recorded_by=""):
        try:
            units = max(1, int(units_collected))
        except (ValueError, TypeError):
            units = 1

        return {
            "donation_id": generate_donation_id(),
            "donor_id": str(donor_id),
            "donor_name": donor_name.strip() if donor_name else "Anonymous Donor",
            "hospital_id": str(hospital_id),
            "hospital_name": hospital_name.strip() if hospital_name else "Blood Center",
            "blood_group": blood_group.strip(),
            "donation_date": donation_date.strip(),
            "units_collected": units,
            "details": details.strip() if details else "Voluntary Blood Donation",
            "recorded_by": recorded_by.strip() if recorded_by else "Hospital Staff",
            "created_at": utc_now_iso()
        }
