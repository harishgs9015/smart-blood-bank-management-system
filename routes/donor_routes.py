from datetime import datetime, timezone
from bson import ObjectId
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from routes import role_required
from config import Config
from extensions import get_db
from models.donor import DonorProfileModel
from models.stock import BLOOD_GROUPS, get_stock_status
from services.appointment_service import AppointmentService
from services.hospital_service import HospitalService
from services.stock_service import StockService
from services.notification_service import NotificationService

donor_bp = Blueprint("donor", __name__, url_prefix="/donor")

@donor_bp.route("/dashboard")
@role_required(["donor"])
def dashboard():
    user_id = session.get("user_id")
    db = get_db()

    # User document
    try:
        user = db.users.find_one({"_id": ObjectId(user_id)})
    except Exception:
        user = db.users.find_one({"_id": user_id})
    if not user:
        user = db.users.find_one({"email": session.get("email")}) or {}

    # Donor Profile
    profile = db.donor_profiles.find_one({"$or": [{"user_id": str(user_id)}, {"email": session.get("email")}]})
    if not profile:
        profile = {
            "donor_id": session.get("donor_id", "D001"),
            "blood_group": session.get("blood_group", "O+"),
            "state": "Tamil Nadu",
            "district": "Chennai",
            "address": "Chennai, Tamil Nadu",
            "total_donations": 0
        }

    donor_id = profile.get("donor_id") or session.get("donor_id", "D001")
    session["donor_id"] = donor_id

    # Donation history records from db.donations
    donations = list(db.donations.find({
        "$or": [{"donor_id": donor_id}, {"donor_id": str(user_id)}]
    }).sort("donation_date", -1))

    # All submitted donation requests / appointments
    all_appointments = AppointmentService.get_donor_appointments(user_id)
    
    # Active requests / upcoming
    active_requests = [a for a in all_appointments if str(a.get("status", "")).capitalize() in ["Pending", "Confirmed", "Rescheduled"]]
    recent_status = active_requests[0] if active_requests else (all_appointments[0] if all_appointments else None)

    # Location string
    location_str = f"{profile.get('district', '')}, {profile.get('state', '')}".strip(", ") or profile.get("address", "Chennai, Tamil Nadu")

    # Notifications
    notifications = NotificationService.get_user_notifications(user_id, limit=5)

    return render_template(
        "donor/dashboard.html",
        user=user,
        profile=profile,
        donor_id=donor_id,
        blood_group=profile.get("blood_group", session.get("blood_group", "O+")),
        location=location_str,
        donations=donations,
        donation_count=len(donations) or profile.get("total_donations", 0),
        all_appointments=all_appointments,
        active_requests=active_requests,
        recent_status=recent_status,
        notifications=notifications
    )

@donor_bp.route("/find-hospital")
@donor_bp.route("/hospitals")
@role_required(["donor"])
def find_hospital():
    """
    Section 3: FIND HOSPITAL / DONATE BLOOD
    Show list of registered hospitals with:
    - Hospital Name
    - Hospital ID (e.g. H001, H002)
    - Location (e.g. Chennai)
    - Available blood groups
    - Blood stock status
    """
    db = get_db()
    hospitals = list(db.hospitals.find({"status": "verified"}).sort("hospital_id", 1))

    # Prepare each hospital with its blood stock summary
    hospital_data = []
    for h in hospitals:
        hid = h.get("hospital_id") or str(h.get("_id"))
        stocks = StockService.get_hospital_stock(hid)
        
        # Collect available blood groups and quick summary
        available_bgs = [s["blood_group"] for s in stocks if s.get("available_units", 0) > 0]
        
        hospital_data.append({
            "hospital": h,
            "hospital_id": hid,
            "name": h.get("name", "Blood Bank"),
            "location": h.get("location") or f"{h.get('district', '')}, {h.get('state', '')}".strip(", ") or h.get("city", "Chennai"),
            "phone": h.get("phone") or h.get("contact", "N/A"),
            "operating_hours": h.get("operating_hours", "24/7"),
            "stocks": stocks,
            "available_blood_groups": available_bgs or BLOOD_GROUPS[:4]
        })

    return render_template("donor/find_hospital.html", hospitals=hospital_data)

@donor_bp.route("/donate/<hospital_id>", methods=["GET", "POST"])
@donor_bp.route("/book", methods=["GET", "POST"])
@role_required(["donor"])
def donate_blood(hospital_id=None):
    """
    Section 4: DONATION REQUEST / APPOINTMENT FORM
    Fields:
    - Donor Name
    - Donor ID
    - Blood Group
    - Selected Hospital
    - Hospital ID
    - Preferred Donation Date
    - Preferred Donation Time
    - Contact Number
    - Additional Details
    Submits and shows:
    'Donation Request Sent to [Hospital Name]'
    Status: Pending
    """
    user_id = session.get("user_id")
    db = get_db()
    
    # Profile
    profile = db.donor_profiles.find_one({"$or": [{"user_id": str(user_id)}, {"email": session.get("email")}]}) or {}
    try:
        user = db.users.find_one({"_id": ObjectId(user_id)})
    except Exception:
        user = db.users.find_one({"_id": user_id})
    if not user:
        user = db.users.find_one({"email": session.get("email")}) or {}

    donor_id = profile.get("donor_id") or session.get("donor_id", "D001")
    donor_name = session.get("name") or user.get("name", "Donor")
    donor_blood_group = profile.get("blood_group") or session.get("blood_group", "O+")
    donor_phone = user.get("phone") or profile.get("phone", "+91 98765 43210")
    donor_email = session.get("email")

    # Target Hospital
    target_hid = hospital_id or request.args.get("hospital_id") or request.form.get("hospital_id")
    selected_hospital = None
    if target_hid:
        selected_hospital = HospitalService.get_hospital_by_id(target_hid)
    
    if not selected_hospital:
        # Default to first verified hospital (e.g. ABC Hospital H001)
        selected_hospital = db.hospitals.find_one({"hospital_id": "H001"}) or db.hospitals.find_one({"status": "verified"})

    hospitals = list(db.hospitals.find({"status": "verified"}).sort("hospital_id", 1))

    if request.method == "POST":
        sel_h_id = request.form.get("hospital_id", "").strip() or (selected_hospital.get("hospital_id") if selected_hospital else "")
        req_hospital = HospitalService.get_hospital_by_id(sel_h_id) or selected_hospital

        preferred_date = request.form.get("preferred_date", "").strip() or request.form.get("slot_date", "").strip()
        preferred_time = request.form.get("preferred_time", "").strip() or request.form.get("slot_time", "").strip()
        contact_number = request.form.get("contact_number", "").strip() or donor_phone
        blood_group = request.form.get("blood_group", "").strip() or donor_blood_group
        additional_details = request.form.get("additional_details", "").strip() or request.form.get("notes", "").strip()

        if not preferred_date or not preferred_time:
            flash("Please provide your preferred donation date and time.", "danger")
            return render_template(
                "donor/donation_request.html",
                selected_hospital=req_hospital,
                hospitals=hospitals,
                donor_name=donor_name,
                donor_id=donor_id,
                donor_blood_group=blood_group,
                donor_phone=contact_number,
                blood_groups=BLOOD_GROUPS
            )

        ip_addr = request.remote_addr or "127.0.0.1"
        success, res = AppointmentService.book_appointment(
            donor_id=user_id,
            donor_name=donor_name,
            donor_email=donor_email,
            donor_phone=contact_number,
            donor_blood_group=blood_group,
            hospital_id=req_hospital.get("hospital_id") or str(req_hospital["_id"]),
            slot_date=preferred_date,
            slot_time=preferred_time,
            notes=additional_details,
            ip_address=ip_addr,
            donor_custom_id=donor_id
        )

        if not success:
            flash(res, "danger")
            return redirect(url_for("donor.donate_blood", hospital_id=req_hospital.get("hospital_id")))

        # Prompt specification Section 4:
        # After submission, show:
        # "Donation Request Sent to [Hospital Name]"
        # Status: Pending
        h_display_name = req_hospital.get("name", "Hospital")
        flash(f"Donation Request Sent to {h_display_name}! Status: Pending (Request ID: {res.get('request_id')})", "success")
        return redirect(url_for("donor.my_applications"))

    return render_template(
        "donor/donation_request.html",
        selected_hospital=selected_hospital,
        hospitals=hospitals,
        donor_name=donor_name,
        donor_id=donor_id,
        donor_blood_group=donor_blood_group,
        donor_phone=donor_phone,
        blood_groups=BLOOD_GROUPS
    )

@donor_bp.route("/applications")
@role_required(["donor"])
def my_applications():
    """
    Section 13: MY APPLICATIONS
    Show all donation requests submitted by the donor.
    Columns: Hospital, Blood Group, Requested Date, Requested Time, Status
    """
    user_id = session.get("user_id")
    applications = AppointmentService.get_donor_appointments(user_id)
    return render_template("donor/my_applications.html", applications=applications)

@donor_bp.route("/appointments")
@role_required(["donor"])
def my_appointments():
    """
    Section 13: MY APPOINTMENTS
    Show confirmed, rejected, and rescheduled appointments.
    Example:
    ABC Hospital | O+ | 25 Oct | 10:30 AM | 🟢 Confirmed
    If rejected: 🔴 Rejected
    If rescheduled: 🟡 Rescheduled | New Date: [date] | New Time: [time]
    """
    user_id = session.get("user_id")
    all_appts = AppointmentService.get_donor_appointments(user_id)
    # Filter to active appointments (Confirmed, Rescheduled, Rejected, Pending)
    return render_template("donor/my_appointments.html", appointments=all_appts)

@donor_bp.route("/history")
@role_required(["donor"])
def donation_history():
    """
    Donor Donation History: shows past completed donations.
    """
    user_id = session.get("user_id")
    db = get_db()
    profile = db.donor_profiles.find_one({"$or": [{"user_id": str(user_id)}, {"email": session.get("email")}]})
    donor_id = profile.get("donor_id") if profile else session.get("donor_id", "D001")

    donations = list(db.donations.find({
        "$or": [{"donor_id": donor_id}, {"donor_id": str(user_id)}]
    }).sort("donation_date", -1))

    return render_template("donor/donation_history.html", donations=donations, donor_id=donor_id)

@donor_bp.route("/appointments/cancel/<appointment_id>", methods=["POST"])
@role_required(["donor"])
def cancel_appointment(appointment_id):
    user_id = session.get("user_id")
    appt = AppointmentService.get_appointment_by_id(appointment_id)
    profile = get_db().donor_profiles.find_one({"user_id": str(user_id)}) or {}
    donor_id = profile.get("donor_id", str(user_id))

    if not appt or (str(appt.get("donor_id")) != str(user_id) and str(appt.get("donor_id")) != donor_id and str(appt.get("donor_user_id")) != str(user_id)):
        flash("You are not authorized to cancel another donor's request.", "danger")
        return redirect(url_for("donor.my_appointments"))

    reason = request.form.get("reason", "Donor scheduling conflict").strip()
    user_email = session.get("email")
    ip_addr = request.remote_addr or "127.0.0.1"

    success, msg = AppointmentService.cancel_appointment(
        appointment_id=appointment_id,
        cancelled_by_email=user_email,
        role="donor",
        reason=reason,
        ip_address=ip_addr
    )

    if success:
        flash(msg, "warning")
    else:
        flash(msg, "danger")

    return redirect(url_for("donor.my_appointments"))

@donor_bp.route("/profile", methods=["GET", "POST"])
@role_required(["donor"])
def profile():
    user_id = session.get("user_id")
    db = get_db()
    user = db.users.find_one({"email": session.get("email")}) or {}
    donor_prof = db.donor_profiles.find_one({"$or": [{"user_id": str(user_id)}, {"email": session.get("email")}]}) or {}

    locations = Config.INDIAN_LOCATIONS
    blood_groups = Config.BLOOD_GROUPS

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        phone = request.form.get("phone", "").strip()
        blood_group = request.form.get("blood_group", donor_prof.get("blood_group", "O+"))
        state = request.form.get("state", donor_prof.get("state", "Tamil Nadu"))
        district = request.form.get("district", donor_prof.get("district", "Chennai"))
        address = request.form.get("address", "").strip()

        db.users.update_one({"_id": user["_id"]}, {
            "$set": {"name": name, "phone": phone}
        })
        session["name"] = name

        db.donor_profiles.update_one({"$or": [{"user_id": str(user_id)}, {"email": session.get("email")}]}, {
            "$set": {
                "blood_group": blood_group,
                "state": state,
                "district": district,
                "address": address,
                "phone": phone,
                "name": name,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
        })

        session["blood_group"] = blood_group
        session["state"] = state
        session["district"] = district
        session["location"] = f"{district}, {state}"

        flash("Profile updated successfully.", "success")
        return redirect(url_for("donor.profile"))

    return render_template(
        "user/profile.html",
        user=user,
        profile=donor_prof,
        donor_id=donor_prof.get("donor_id", session.get("donor_id", "D001")),
        locations=locations,
        blood_groups=blood_groups
    )
