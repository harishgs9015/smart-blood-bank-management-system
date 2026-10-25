from flask import Blueprint, render_template, request, flash, redirect, url_for
from config import Config
from extensions import get_db
from services.stock_service import StockService
from services.hospital_service import HospitalService
from services.request_service import RequestService

public_bp = Blueprint("public", __name__)

@public_bp.route("/")
def index():
    db = get_db()
    # Compute live high-level statistics for homepage
    total_donors = db.users.count_documents({"role": "donor"})
    total_hospitals = db.hospitals.count_documents({"status": "verified"})
    total_appointments = db.appointments.count_documents({})
    
    # Calculate total blood units
    stocks = list(db.blood_stock.find())
    total_units = sum(s.get("units", 0) for s in stocks)

    # Urgent emergency requests count
    emergency_requests = list(db.blood_requests.find({
        "status": {"$in": ["pending_verification", "verified"]},
        "urgency": "Emergency"
    }).limit(3))

    locations = Config.INDIAN_LOCATIONS
    blood_groups = Config.BLOOD_GROUPS

    return render_template(
        "index.html",
        stats={
            "donors": total_donors,
            "hospitals": total_hospitals,
            "appointments": total_appointments,
            "units": total_units
        },
        emergency_requests=emergency_requests,
        locations=locations,
        blood_groups=blood_groups
    )

@public_bp.route("/about")
def about():
    return render_template("about.html", blood_groups=Config.BLOOD_GROUPS)

@public_bp.route("/faq")
def faq():
    return render_template("faq.html")

@public_bp.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        flash("Thank you for your feedback! As this is an academic prototype demonstration, your message has been recorded.", "success")
        return redirect(url_for("public.contact"))
    return render_template("contact.html")

@public_bp.route("/find-blood")
def find_blood():
    from models.stock import normalize_blood_group
    raw_blood_group = request.args.get("blood_group", "").strip()
    norm_blood_group = normalize_blood_group(raw_blood_group) if raw_blood_group else ""
    state = request.args.get("state", "").strip()
    district = request.args.get("district", "").strip()

    locations = Config.INDIAN_LOCATIONS
    blood_groups = Config.BLOOD_GROUPS

    has_searched = bool(raw_blood_group or state or district)

    # Perform search if query entered, or show all verified centers by default
    results = StockService.search_blood_availability(
        blood_group=norm_blood_group if norm_blood_group else None,
        state=state if state else None,
        district=district if district else None
    )

    return render_template(
        "public/find_blood.html",
        results=results,
        locations=locations,
        blood_groups=blood_groups,
        selected_blood_group=norm_blood_group or raw_blood_group,
        selected_state=state,
        selected_district=district,
        has_searched=has_searched
    )

@public_bp.route("/request-blood", methods=["GET", "POST"])
def request_blood():
    locations = Config.INDIAN_LOCATIONS
    blood_groups = Config.BLOOD_GROUPS

    if request.method == "POST":
        patient_name = request.form.get("patient_name", "").strip()
        blood_group = request.form.get("blood_group", "")
        units_needed = request.form.get("units_needed", 1)
        hospital_name = request.form.get("hospital_name", "").strip()
        hospital_district = request.form.get("hospital_district", "").strip()
        hospital_state = request.form.get("hospital_state", "").strip()
        doctor_case_ref = request.form.get("doctor_case_ref", "").strip()
        urgency = request.form.get("urgency", "Urgent")
        requester_name = request.form.get("requester_name", "").strip()
        requester_phone = request.form.get("requester_phone", "").strip()
        requester_email = request.form.get("requester_email", "").strip()
        medical_notes = request.form.get("medical_notes", "").strip()

        if not patient_name or not blood_group or not hospital_name or not requester_phone:
            flash("Please complete all required patient and hospital contact fields.", "danger")
            return render_template("public/request_blood.html", locations=locations, blood_groups=blood_groups, form_data=request.form)

        ip_addr = request.remote_addr or "127.0.0.1"
        success, req_doc = RequestService.submit_request(
            patient_name=patient_name,
            blood_group=blood_group,
            units_needed=units_needed,
            hospital_name=hospital_name,
            hospital_district=hospital_district,
            hospital_state=hospital_state,
            doctor_case_ref=doctor_case_ref,
            urgency=urgency,
            requester_name=requester_name,
            requester_phone=requester_phone,
            requester_email=requester_email,
            medical_notes=medical_notes,
            ip_address=ip_addr
        )

        tracking_code = req_doc["tracking_code"]
        flash(f"Blood request submitted successfully! Your tracking reference code is {tracking_code}. Keep this code to check the verification and allotment status.", "success")
        return redirect(url_for("public.track_request", code=tracking_code))

    return render_template("public/request_blood.html", locations=locations, blood_groups=blood_groups, form_data={})

@public_bp.route("/track-request")
def track_request():
    code = request.args.get("code", "").strip()
    request_data = None
    searched = False

    if code:
        searched = True
        request_data = RequestService.get_request_by_tracking_code(code)
        if not request_data:
            flash(f"No blood request found matching tracking code '{code}'. Please verify the reference number.", "warning")

    return render_template("public/track_request.html", request_data=request_data, code=code, searched=searched)
