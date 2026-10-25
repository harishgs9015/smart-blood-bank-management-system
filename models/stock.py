import uuid
from models import utc_now_iso

BLOOD_GROUPS = ["A+", "A-", "B+", "B-", "O+", "O-", "AB+", "AB-", "Bombay Blood Group (hh)"]

BLOOD_GROUP_SYNONYMS = {
    "A+": "A+", "A POSITIVE": "A+", "A POS": "A+", "A+VE": "A+", "A +": "A+", "A-POSITIVE": "A+", "A": "A+",
    "A-": "A-", "A NEGATIVE": "A-", "A NEG": "A-", "A-VE": "A-", "A -": "A-", "A-NEGATIVE": "A-",
    "B+": "B+", "B POSITIVE": "B+", "B POS": "B+", "B+VE": "B+", "B +": "B+", "B-POSITIVE": "B+", "B": "B+",
    "B-": "B-", "B NEGATIVE": "B-", "B NEG": "B-", "B-VE": "B-", "B -": "B-", "B-NEGATIVE": "B-",
    "AB+": "AB+", "AB POSITIVE": "AB+", "AB POS": "AB+", "AB+VE": "AB+", "AB +": "AB+", "AB-POSITIVE": "AB+", "AB": "AB+",
    "AB-": "AB-", "AB NEGATIVE": "AB-", "AB NEG": "AB-", "AB-VE": "AB-", "AB -": "AB-", "AB-NEGATIVE": "AB-",
    "O+": "O+", "O POSITIVE": "O+", "O POS": "O+", "O+VE": "O+", "O +": "O+", "O-POSITIVE": "O+", "O": "O+",
    "O-": "O-", "O NEGATIVE": "O-", "O NEG": "O-", "O-VE": "O-", "O -": "O-", "O-NEGATIVE": "O-",
    "BOMBAY BLOOD GROUP (HH)": "Bombay Blood Group (hh)",
    "BOMBAY": "Bombay Blood Group (hh)",
    "HH": "Bombay Blood Group (hh)",
    "BOMBAY (HH)": "Bombay Blood Group (hh)"
}

BLOOD_GROUP_FULL_NAMES = {
    "A+": "A Positive",
    "A-": "A Negative",
    "B+": "B Positive",
    "B-": "B Negative",
    "O+": "O Positive",
    "O-": "O Negative",
    "AB+": "AB Positive",
    "AB-": "AB Negative",
    "Bombay Blood Group (hh)": "Bombay Blood Group (hh)"
}

def normalize_blood_group(bg):
    if not bg:
        return ""
    clean = bg.strip().upper().replace("_", " ")
    if bg.endswith(" ") and bg.strip().upper() in ["A", "B", "AB", "O"]:
        return bg.strip().upper() + "+"
    return BLOOD_GROUP_SYNONYMS.get(clean, bg.strip())

def get_blood_group_full_name(bg):
    norm = normalize_blood_group(bg)
    return BLOOD_GROUP_FULL_NAMES.get(norm, norm or bg)

def get_stock_status(units, minimum_required=10):
    try:
        u = int(units)
    except (ValueError, TypeError):
        u = 0
    try:
        min_req = int(minimum_required) if minimum_required else 10
    except (ValueError, TypeError):
        min_req = 10

    if u >= min_req:
        return "Normal"
    elif u > (min_req * 0.4):
        return "Low"
    else:
        return "Critical"

class BloodStockModel:
    @staticmethod
    def create_stock_doc(hospital_id, hospital_name, blood_group, units, updated_by_user, minimum_required=10, location="", details=""):
        try:
            units = int(units)
        except (ValueError, TypeError):
            units = 0
        try:
            minimum_required = int(minimum_required) if minimum_required else 10
        except (ValueError, TypeError):
            minimum_required = 10

        status = get_stock_status(units, minimum_required)
        return {
            "stock_id": f"STK-{uuid.uuid4().hex[:6].upper()}",
            "hospital_id": str(hospital_id),
            "hospital_name": hospital_name,
            "blood_group": blood_group,
            "available_units": max(0, units),
            "units": max(0, units),  # backward compatibility alias
            "minimum_required": minimum_required,
            "status": status,
            "location": location.strip() if location else "",
            "details": details.strip() if details else "Routine Inventory",
            "last_updated": utc_now_iso(),
            "updated_by": updated_by_user,
            "created_at": utc_now_iso()
        }

    @staticmethod
    def create_assistance_request_doc(requesting_hospital_id, requesting_hospital_name,
                                      blood_group, units_needed, urgency="High",
                                      reason="Emergency Shortage"):
        return {
            "requesting_hospital_id": str(requesting_hospital_id),
            "requesting_hospital_name": requesting_hospital_name,
            "blood_group": blood_group,
            "units_needed": int(units_needed),
            "urgency": urgency,
            "reason": reason,
            "status": "Open",  # Open, Accepted, Fulfilled, Closed
            "accepted_by_hospital_id": None,
            "accepted_by_hospital_name": None,
            "created_at": utc_now_iso(),
            "updated_at": utc_now_iso()
        }
