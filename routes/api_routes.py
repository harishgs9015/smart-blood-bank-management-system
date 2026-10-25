from flask import Blueprint, jsonify, request, session
from config import Config
from services.hospital_service import HospitalService
from services.appointment_service import AppointmentService
from services.notification_service import NotificationService

api_bp = Blueprint("api", __name__, url_prefix="/api")

@api_bp.route("/locations/districts")
def get_districts():
    state = request.args.get("state", "").strip()
    districts = Config.INDIAN_LOCATIONS.get(state, [])
    return jsonify({"success": True, "state": state, "districts": districts})

@api_bp.route("/hospitals")
def get_hospitals():
    state = request.args.get("state", "").strip()
    district = request.args.get("district", "").strip()
    hospitals = HospitalService.get_verified_hospitals(
        state=state if state else None,
        district=district if district else None
    )

    clean_list = []
    for h in hospitals:
        clean_list.append({
            "id": str(h["_id"]),
            "name": h["name"],
            "facility_type": h.get("facility_type", "Government"),
            "district": h.get("district", ""),
            "state": h.get("state", ""),
            "address": h.get("address", ""),
            "phone": h.get("phone", ""),
            "operating_hours": h.get("operating_hours", "24/7"),
            "latitude": h.get("latitude"),
            "longitude": h.get("longitude")
        })

    return jsonify({"success": True, "hospitals": clean_list})

@api_bp.route("/hospitals/<hospital_id>/slots")
def get_slots(hospital_id):
    date_str = request.args.get("date", "").strip()
    if not date_str:
        return jsonify({"success": False, "message": "Date parameter (YYYY-MM-DD) is required."}), 400

    slots, msg = AppointmentService.get_hospital_slot_availability(hospital_id, date_str)
    if slots is None:
        return jsonify({"success": False, "message": msg}), 404

    return jsonify({"success": True, "date": date_str, "slots": slots})

@api_bp.route("/notifications/mark-read/<notif_id>", methods=["POST"])
def mark_notification_read(notif_id):
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"success": False, "message": "Unauthorized"}), 401

    ok = NotificationService.mark_as_read(notif_id, user_id)
    return jsonify({"success": ok})
