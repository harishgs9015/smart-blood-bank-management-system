import logging
from bson import ObjectId
from extensions import get_db
from models import utc_now_iso
from models.stock import BLOOD_GROUPS, BloodStockModel
from services.audit_service import AuditService
from services.notification_service import NotificationService

logger = logging.getLogger(__name__)

class HospitalService:
    @staticmethod
    def get_verified_hospitals(state=None, district=None):
        db = get_db()
        query = {"status": "verified"}
        if state:
            query["state"] = state
        if district:
            query["district"] = district
        return list(db.hospitals.find(query).sort("name", 1))

    @staticmethod
    def get_all_hospitals(status_filter=None):
        db = get_db()
        query = {}
        if status_filter:
            query["status"] = status_filter
        return list(db.hospitals.find(query).sort("created_at", -1))

    @staticmethod
    def get_hospital_by_id(hospital_id):
        if not hospital_id:
            return None
        db = get_db()
        hid_str = str(hospital_id).strip()
        # 1. Search by custom hospital_id (e.g., 'H001')
        h = db.hospitals.find_one({"hospital_id": hid_str})
        if h:
            if "hospital_id" not in h:
                h["hospital_id"] = hid_str
            return h
        # 2. Search by ObjectId or raw _id
        try:
            h = db.hospitals.find_one({"_id": ObjectId(hid_str)})
            if h:
                if "hospital_id" not in h:
                    h["hospital_id"] = str(h["_id"])
                return h
        except Exception:
            pass
        h = db.hospitals.find_one({"_id": hid_str})
        if h and "hospital_id" not in h:
            h["hospital_id"] = str(h["_id"])
        return h

    @staticmethod
    def get_hospital_by_user_id(user_id):
        db = get_db()
        h = db.hospitals.find_one({"user_id": str(user_id)})
        if h and "hospital_id" not in h:
            h["hospital_id"] = str(h.get("_id"))
        return h

    @staticmethod
    def get_hospital_donors(hospital_id):
        """
        Returns donors connected specifically to this hospital through
        donation requests, appointments, or completed donations.
        Guarantees strict hospital data isolation.
        """
        db = get_db()
        hospital = HospitalService.get_hospital_by_id(hospital_id)
        if not hospital:
            return []

        h_keys = [str(hospital.get("hospital_id")), str(hospital.get("_id"))]
        h_keys = list(set([k for k in h_keys if k]))

        # Find donor_ids from appointments
        appts = list(db.appointments.find({"hospital_id": {"$in": h_keys}}))
        # Find donor_ids from donations
        dons = list(db.donations.find({"hospital_id": {"$in": h_keys}}))

        donor_ids = set()
        for a in appts:
            if a.get("donor_id"):
                donor_ids.add(str(a.get("donor_id")))
        for d in dons:
            if d.get("donor_id"):
                donor_ids.add(str(d.get("donor_id")))

        donors_list = []
        for did in donor_ids:
            # Match donor profile or user
            prof = db.donor_profiles.find_one({"$or": [{"donor_id": did}, {"user_id": did}]}) or {}
            usr = None
            if prof.get("user_id"):
                try:
                    usr = db.users.find_one({"_id": ObjectId(prof["user_id"])})
                except Exception:
                    usr = db.users.find_one({"_id": prof["user_id"]})
            if not usr:
                usr = db.users.find_one({"email": did}) or {}

            # Count donations at THIS hospital
            hospital_donations = [d for d in dons if str(d.get("donor_id")) == did]
            donor_appts = [a for a in appts if str(a.get("donor_id")) == did]

            # Last donation date
            last_date = None
            if hospital_donations:
                sorted_d = sorted(hospital_donations, key=lambda x: x.get("donation_date", ""), reverse=True)
                last_date = sorted_d[0].get("donation_date")
            elif prof.get("last_donation_date"):
                last_date = prof.get("last_donation_date")

            # Resolve name, phone, blood group
            name = usr.get("name") if usr else prof.get("name")
            if not name and donor_appts:
                name = donor_appts[0].get("donor_name")
            if not name:
                name = f"Donor {did}"

            contact = (usr.get("phone") if usr else "") or prof.get("phone")
            if not contact and donor_appts:
                contact = donor_appts[0].get("donor_phone")
            email = usr.get("email") if usr else prof.get("email", "")

            blood_group = prof.get("blood_group")
            if not blood_group and donor_appts:
                blood_group = donor_appts[0].get("blood_group") or donor_appts[0].get("donor_blood_group")

            donors_list.append({
                "donor_id": prof.get("donor_id", did),
                "name": name,
                "blood_group": blood_group or "Unknown",
                "contact": contact or email or "N/A",
                "phone": contact,
                "email": email,
                "location": f"{prof.get('district', '')}, {prof.get('state', '')}".strip(", ") or prof.get("address", "N/A"),
                "donation_history_count": len(hospital_donations),
                "total_donations": len(hospital_donations),
                "last_donation_date": last_date or "Never",
                "status": "Active"
            })

        return donors_list

    @staticmethod
    def verify_hospital(hospital_id, admin_email, approve=True, notes="", ip_address="127.0.0.1"):
        db = get_db()
        hospital = HospitalService.get_hospital_by_id(hospital_id)
        if not hospital:
            return False, "Hospital record not found."

        new_status = "verified" if approve else "rejected"
        update_data = {
            "status": new_status,
            "verification_notes": notes.strip() if notes else f"Hospital account {new_status} by administrator.",
            "verified_at": utc_now_iso(),
            "verified_by": admin_email,
            "updated_at": utc_now_iso()
        }

        try:
            query = {"_id": ObjectId(hospital_id)}
        except Exception:
            query = {"_id": hospital_id}

        db.hospitals.update_one(query, {"$set": update_data})

        # If verified, ensure blood stock records exist for all 8 groups
        if approve:
            for bg in BLOOD_GROUPS:
                existing = db.blood_stock.find_one({
                    "hospital_id": str(hospital["_id"]),
                    "blood_group": bg
                })
                if not existing:
                    stock_doc = BloodStockModel.create_stock_doc(
                        hospital_id=str(hospital["_id"]),
                        hospital_name=hospital["name"],
                        blood_group=bg,
                        units=5,  # initial stock units
                        updated_by_user=admin_email
                    )
                    db.blood_stock.insert_one(stock_doc)

        action = "HOSPITAL_VERIFIED" if approve else "HOSPITAL_REJECTED"
        AuditService.log_action(action, admin_email, "admin", 
                                f"Hospital {hospital['name']} ({hospital.get('license_number')}) {new_status}.", ip_address)

        # Notify hospital staff user
        NotificationService.send_notification(
            user_id=hospital.get("user_id"),
            email=hospital.get("email"),
            title=f"Hospital Verification {new_status.capitalize()}",
            message=f"Your hospital account has been {new_status}. {update_data['verification_notes']}",
            notif_type="system"
        )

        return True, f"Hospital successfully marked as {new_status}."

    @staticmethod
    def update_hospital_settings(hospital_id, capacity, operating_hours, phone, emergency_phone):
        db = get_db()
        try:
            query = {"_id": ObjectId(hospital_id)}
        except Exception:
            query = {"_id": hospital_id}

        db.hospitals.update_one(query, {
            "$set": {
                "daily_slot_capacity": max(1, int(capacity)),
                "operating_hours": operating_hours.strip(),
                "phone": phone.strip(),
                "emergency_phone": emergency_phone.strip(),
                "updated_at": utc_now_iso()
            }
        })
        return True, "Hospital settings updated successfully."
