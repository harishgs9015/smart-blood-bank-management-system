from datetime import datetime, timezone, timedelta
from models import utc_now_iso

class DonorProfileModel:
    @staticmethod
    def create_profile_doc(user_id, blood_group, state, district, date_of_birth="", 
                           gender="Other", address="", last_donation_date=None, 
                           preference_regular=False, preference_emergency=True,
                           donor_id=None):
        return {
            "donor_id": donor_id or f"D{abs(hash(str(user_id))) % 900 + 100}",
            "user_id": str(user_id),
            "blood_group": blood_group,
            "state": state,
            "district": district,
            "date_of_birth": date_of_birth,
            "gender": gender,
            "address": address,
            "last_donation_date": last_donation_date,  # Format: YYYY-MM-DD or None
            "preference_regular": bool(preference_regular),
            "preference_emergency": bool(preference_emergency),
            "total_donations": 0,
            "eligibility_review_status": "Review Required by Medical Staff",
            "eligibility_notes": "Eligibility must be medically verified at the blood center on the day of donation (Hb >= 12.5 g/dl, Weight >= 45kg, BP normal).",
            "notification_preferences": {
                "in_app": True,
                "email": True,
                "sms": False,
                "whatsapp": False
            },
            "created_at": utc_now_iso(),
            "updated_at": utc_now_iso()
        }

    @staticmethod
    def calculate_cooldown(last_donation_date_str, gap_days=90):
        """
        Calculates cooldown for safe reminder scheduling.
        NOTE: This is NOT a medical clearance; clearance is strictly performed
        in-person by blood bank medical staff.
        """
        if not last_donation_date_str:
            return {
                "can_schedule_review": True,
                "days_since": None,
                "next_recommended_date": None,
                "cooldown_remaining_days": 0,
                "message": "No recorded donation. Full on-site health screening required."
            }

        try:
            last_date = datetime.strptime(last_donation_date_str, "%Y-%m-%d").date()
            today = datetime.now(timezone.utc).date()
            days_since = (today - last_date).days
            next_date = last_date + timedelta(days=gap_days)
            remaining = max(0, gap_days - days_since)

            if days_since < gap_days:
                return {
                    "can_schedule_review": False,
                    "days_since": days_since,
                    "next_recommended_date": next_date.strftime("%Y-%m-%d"),
                    "cooldown_remaining_days": remaining,
                    "message": f"Standard recovery gap active ({remaining} days remaining before next safe review)."
                }
            else:
                return {
                    "can_schedule_review": True,
                    "days_since": days_since,
                    "next_recommended_date": None,
                    "cooldown_remaining_days": 0,
                    "message": "Past standard recovery gap. Eligible for appointment and on-site screening."
                }
        except Exception:
            return {
                "can_schedule_review": True,
                "days_since": None,
                "next_recommended_date": None,
                "cooldown_remaining_days": 0,
                "message": "Eligibility review required by medical team."
            }
