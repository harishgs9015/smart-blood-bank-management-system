import logging
import re
import uuid
from bson import ObjectId
from extensions import get_db
from models import utc_now_iso
from models.blood_request import BloodRequestModel
from services.audit_service import AuditService
from services.notification_service import NotificationService

logger = logging.getLogger(__name__)

class RequestService:
    @staticmethod
    def submit_request(patient_name, blood_group, units_needed, hospital_name,
                       hospital_district, hospital_state, doctor_case_ref="",
                       urgency="Urgent", requester_name="", requester_phone="", requester_email="",
                       medical_notes="", ip_address="127.0.0.1"):
        db = get_db()
        clean_case_ref = doctor_case_ref.strip() if doctor_case_ref else "N/A - Direct Emergency Request"
        clean_requester_name = requester_name.strip() if requester_name else f"Attendant of {patient_name.strip()}"

        req_doc = BloodRequestModel.create_request_doc(
            patient_name=patient_name,
            blood_group=blood_group,
            units_needed=units_needed,
            hospital_name=hospital_name,
            hospital_district=hospital_district,
            hospital_state=hospital_state,
            doctor_case_ref=clean_case_ref,
            urgency=urgency,
            requester_name=clean_requester_name,
            requester_phone=requester_phone,
            requester_email=requester_email,
            medical_notes=medical_notes
        )

        res = db.blood_requests.insert_one(req_doc)
        code = req_doc["tracking_code"]

        AuditService.log_action("BLOOD_REQUEST_SUBMITTED", requester_phone, "public",
                                f"Blood request submitted for {patient_name} ({units_needed} units of {blood_group}). Tracking: {code}",
                                ip_address)

        return True, req_doc

    @staticmethod
    def get_request_by_tracking_code(tracking_code):
        db = get_db()
        raw_query = str(tracking_code).strip()
        code = raw_query.upper()
        # Search by exact tracking code, formatted code with REQ- prefix, phone number, or case ref
        query = {
            "$or": [
                {"tracking_code": code},
                {"tracking_code": f"REQ-{code}" if not code.startswith("REQ-") else code},
                {"tracking_code": f"REQ-2026-{code}" if not code.startswith("REQ-") else code},
                {"requester_phone": raw_query},
                {"doctor_case_ref": {"$regex": f"^{raw_query}$", "$options": "i"}}
            ]
        }
        return db.blood_requests.find_one(query)

    @staticmethod
    def get_all_requests(status_filter=None, urgency_filter=None):
        db = get_db()
        query = {}
        if status_filter:
            query["status"] = status_filter
        if urgency_filter:
            query["urgency"] = urgency_filter
        return list(db.blood_requests.find(query).sort("created_at", -1))

    @staticmethod
    def get_hospital_incoming_requests(hospital_name=None, district=None):
        db = get_db()
        query = {"status": {"$in": ["pending_verification", "verified", "hospital_assigned", "Pending", "In Progress", "Approved"]}}
        if hospital_name:
            query["$or"] = [
                {"hospital_name": {"$regex": hospital_name, "$options": "i"}},
                {"hospital_district": district}
            ]
        elif district:
            query["hospital_district"] = district
        return list(db.blood_requests.find(query).sort("created_at", -1))

    @staticmethod
    def get_hospital_blood_requests(hospital_id):
        """
        Retrieves incoming blood requirements for Section 15.
        Shows: Request ID, Blood Group, Required Units, Request Date, Priority, Status
        Guarantees hospital isolation.
        """
        db = get_db()
        from services.hospital_service import HospitalService
        hospital = HospitalService.get_hospital_by_id(hospital_id)
        h_keys = [str(hospital_id)]
        h_name = ""
        if hospital:
            h_keys.extend([str(hospital.get("hospital_id")), str(hospital.get("_id"))])
            h_name = hospital.get("name", "")
        h_keys = list(set([k for k in h_keys if k]))

        query = {
            "$or": [
                {"hospital_id": {"$in": h_keys}},
                {"assigned_hospital_id": {"$in": h_keys}}
            ]
        }
        if h_name:
            query["$or"].append({"hospital_name": {"$regex": f"^{re.escape(h_name)}$", "$options": "i"}})

        reqs = list(db.blood_requests.find(query).sort("created_at", -1))

        formatted = []
        for r in reqs:
            formatted.append({
                "blood_request_id": r.get("blood_request_id") or r.get("tracking_code", f"REQ-{r.get('_id')}"),
                "request_id": r.get("blood_request_id") or r.get("tracking_code", f"REQ-{r.get('_id')}"),
                "hospital_id": r.get("hospital_id", hospital_id),
                "blood_group": r.get("blood_group", "Unknown"),
                "required_units": r.get("required_units", r.get("units_needed", 1)),
                "units_needed": r.get("required_units", r.get("units_needed", 1)),
                "request_date": r.get("created_at", "")[:10] if r.get("created_at") else "Today",
                "created_at": r.get("created_at", utc_now_iso()),
                "priority": r.get("priority", r.get("urgency", "Standard")),
                "status": r.get("status", "Pending"),
                "patient_name": r.get("patient_name", "Clinical Patient Requirement"),
                "notes": r.get("medical_notes", r.get("verification_notes", ""))
            })
        return formatted

    @staticmethod
    def create_hospital_blood_request(hospital_id, blood_group, required_units, priority="High", staff_email="staff", notes=""):
        db = get_db()
        import uuid
        from services.hospital_service import HospitalService
        hospital = HospitalService.get_hospital_by_id(hospital_id)
        h_id_to_store = str(hospital.get("hospital_id", hospital_id)) if hospital else str(hospital_id)
        h_name = hospital.get("name", "Blood Bank") if hospital else "Blood Bank"

        code = f"REQ-BLD-{uuid.uuid4().hex[:6].upper()}"
        now = utc_now_iso()
        doc = {
            "blood_request_id": code,
            "tracking_code": code,
            "hospital_id": h_id_to_store,
            "hospital_name": h_name,
            "hospital_district": hospital.get("district", "") if hospital else "",
            "hospital_state": hospital.get("state", "") if hospital else "",
            "patient_name": f"Clinical Requirement ({h_name})",
            "blood_group": blood_group,
            "required_units": int(required_units),
            "units_needed": int(required_units),
            "priority": priority,
            "urgency": priority,
            "status": "Pending",
            "requester_name": f"Hospital Staff ({staff_email})",
            "medical_notes": notes.strip() if notes else "Routine clinical requirement posted by hospital staff.",
            "created_at": now,
            "updated_at": now
        }
        db.blood_requests.insert_one(doc)
        return True, doc

    @staticmethod
    def update_request_status(request_id, new_status, staff_email, role, notes="", 
                              assigned_hospital_id=None, assigned_hospital_name=None, ip_address="127.0.0.1"):
        db = get_db()
        req = db.blood_requests.find_one({
            "$or": [
                {"blood_request_id": str(request_id)},
                {"tracking_code": str(request_id)},
                {"_id": str(request_id)}
            ]
        })
        if not req:
            try:
                req = db.blood_requests.find_one({"_id": ObjectId(request_id)})
            except Exception:
                pass
        if not req:
            return False, "Blood request not found."

        query = {"_id": req["_id"]}

        now = utc_now_iso()
        status_entry = {
            "status": new_status,
            "timestamp": now,
            "note": notes or f"Status updated to {new_status} by {staff_email} ({role})."
        }

        update_fields = {
            "status": new_status,
            "updated_at": now
        }

        if new_status == "verified":
            update_fields["verified_by"] = staff_email
            update_fields["verification_notes"] = notes or "Prescription and case verified with treating hospital."

        if assigned_hospital_id and assigned_hospital_name:
            update_fields["assigned_hospital_id"] = str(assigned_hospital_id)
            update_fields["assigned_hospital_name"] = assigned_hospital_name

        db.blood_requests.update_one(query, {
            "$set": update_fields,
            "$push": {"status_history": status_entry}
        })

        AuditService.log_action("REQUEST_STATUS_UPDATED", staff_email, role,
                                f"Request {req.get('tracking_code')} updated to {new_status}. {notes}",
                                ip_address)

        return True, "Blood request status updated successfully."
