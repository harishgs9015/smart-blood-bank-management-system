from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from routes import role_required
from extensions import get_db
from models.stock import BLOOD_GROUPS, normalize_blood_group
from services.hospital_service import HospitalService
from services.stock_service import StockService
from services.appointment_service import AppointmentService
from services.request_service import RequestService

hospital_bp = Blueprint("hospital", __name__, url_prefix="/hospital")

def get_current_hospital():
    user_id = session.get("user_id")
    hospital = HospitalService.get_hospital_by_user_id(user_id)
    if not hospital and session.get("hospital_id"):
        hospital = HospitalService.get_hospital_by_id(session.get("hospital_id"))
    return hospital

@hospital_bp.route("/dashboard")
@role_required(["hospital"])
def dashboard():
    """
    Section 6: HOSPITAL MANAGEMENT DASHBOARD
    Show:
    - Hospital Name
    - Hospital ID
    - Location
    Main sections: Dashboard, Blood Stock, Donors, Blood Requests, Appointments / Donation Requests, Donation History
    """
    hospital = get_current_hospital()
    if not hospital:
        flash("Hospital profile not linked to this account.", "danger")
        return redirect(url_for("public.index"))

    hospital_id = hospital.get("hospital_id") or str(hospital["_id"])
    session["hospital_id"] = hospital_id
    session["hospital_name"] = hospital.get("name")

    # 1. Stock overview for all 9 blood groups
    stocks = StockService.get_hospital_stock(hospital_id)
    total_units = sum(s.get("available_units", 0) for s in stocks)
    critical_stocks = [s for s in stocks if s.get("status") == "Critical"]
    low_stocks = [s for s in stocks if s.get("status") == "Low"]

    # 2. Appointments / Donation Requests for THIS hospital (strict isolation)
    all_appts = AppointmentService.get_hospital_appointments(hospital_id)
    pending_appts = [a for a in all_appts if str(a.get("status", "")).capitalize() == "Pending"]
    confirmed_appts = [a for a in all_appts if str(a.get("status", "")).capitalize() == "Confirmed"]

    # 3. Connected donors for THIS hospital
    donors = HospitalService.get_hospital_donors(hospital_id)

    # 4. Blood Requests for THIS hospital
    blood_requests = RequestService.get_hospital_blood_requests(hospital_id)

    # 5. Donations history count
    db = get_db()
    h_keys = [hospital_id, str(hospital.get("_id"))]
    h_keys = list(set([k for k in h_keys if k]))
    donations_count = db.donations.count_documents({"hospital_id": {"$in": h_keys}})

    location_str = hospital.get("location") or f"{hospital.get('district', '')}, {hospital.get('state', '')}".strip(", ") or hospital.get("city", "Chennai")

    return render_template(
        "hospital/dashboard.html",
        hospital=hospital,
        hospital_id=hospital_id,
        hospital_name=hospital.get("name", "Hospital Management"),
        location=location_str,
        stocks=stocks,
        total_units=total_units,
        critical_count=len(critical_stocks),
        low_count=len(low_stocks),
        pending_count=len(pending_appts),
        confirmed_count=len(confirmed_appts),
        donors_count=len(donors),
        blood_requests_count=len(blood_requests),
        donations_count=donations_count,
        recent_appointments=all_appts[:5],
        recent_requests=blood_requests[:5]
    )

@hospital_bp.route("/stock")
@role_required(["hospital"])
def stock_management():
    """
    Section 7: BLOOD STOCK OVERVIEW
    Displays 9 blood groups:
    A+, A-, B+, B-, O+, O-, AB+, AB-, Bombay Blood Group (hh)
    Shows:
    - Available Units
    - Minimum Required Level
    - Automatically calculated Status (🟢 Normal, 🟡 Low, 🔴 Critical)
    """
    hospital = get_current_hospital()
    if not hospital:
        return redirect(url_for("public.index"))

    hospital_id = hospital.get("hospital_id") or str(hospital["_id"])
    stocks = StockService.get_hospital_stock(hospital_id)
    total_units = sum(s.get("available_units", 0) for s in stocks)

    location_str = hospital.get("location") or f"{hospital.get('district', '')}, {hospital.get('state', '')}".strip(", ") or "Chennai"

    return render_template(
        "hospital/stock_overview.html",
        hospital=hospital,
        hospital_id=hospital_id,
        hospital_name=hospital.get("name"),
        location=location_str,
        stocks=stocks,
        total_units=total_units,
        blood_groups=BLOOD_GROUPS
    )

@hospital_bp.route("/stock/<path:blood_group>", methods=["GET", "POST"])
@role_required(["hospital"])
def blood_group_details(blood_group):
    """
    Section 8: BLOOD GROUP DETAILS
    When hospital management clicks a blood group, opens detailed page:
    - Blood Group
    - Current Stock
    - Minimum Required Level
    - Automatically calculated Status
    - Donors for that blood group
    - Donation History (scrollable table)
    Each donation record: Donor ID, Donor Name, Blood Group, Donation Date, Units Collected, Details
    """
    hospital = get_current_hospital()
    if not hospital:
        return redirect(url_for("public.index"))

    hospital_id = hospital.get("hospital_id") or str(hospital["_id"])
    norm_bg = normalize_blood_group(blood_group)

    if request.method == "POST":
        units_raw = request.form.get("available_units") or request.form.get("units", 0)
        min_req_raw = request.form.get("minimum_required", 10)
        reason = request.form.get("reason", "Stock Level Adjustment").strip()

        try:
            units = max(0, int(units_raw))
        except (ValueError, TypeError):
            units = 0

        try:
            min_req = max(1, int(min_req_raw))
        except (ValueError, TypeError):
            min_req = 10

        user_email = session.get("email")
        ip_addr = request.remote_addr or "127.0.0.1"

        StockService.update_stock(
            hospital_id=hospital_id,
            hospital_name=hospital.get("name"),
            blood_group=norm_bg,
            units=units,
            minimum_required=min_req,
            reason=reason,
            user_email=user_email,
            ip_address=ip_addr
        )

        flash(f"Blood stock for {norm_bg} updated to {units} units (Min Required: {min_req}). Status recalculated automatically.", "success")
        return redirect(url_for("hospital.blood_group_details", blood_group=norm_bg))

    details = StockService.get_blood_group_details(hospital_id, norm_bg)

    return render_template(
        "hospital/blood_group_details.html",
        hospital=hospital,
        hospital_id=hospital_id,
        details=details,
        blood_group=norm_bg
    )

@hospital_bp.route("/donors")
@role_required(["hospital"])
def donors():
    """
    Section 9: DONOR MANAGEMENT
    Show donors connected to that hospital:
    - Donor ID
    - Donor Name
    - Blood Group
    - Contact
    - Donation history
    - Last donation date
    Do not expose another hospital's private donor information.
    """
    hospital = get_current_hospital()
    if not hospital:
        return redirect(url_for("public.index"))

    hospital_id = hospital.get("hospital_id") or str(hospital["_id"])
    donors_list = HospitalService.get_hospital_donors(hospital_id)

    return render_template(
        "hospital/donors.html",
        hospital=hospital,
        hospital_id=hospital_id,
        donors=donors_list
    )

@hospital_bp.route("/appointments")
@hospital_bp.route("/requests")
@role_required(["hospital"])
def appointments():
    """
    Section 10 & 11: APPOINTMENTS / DONATION REQUESTS
    Where hospital management sees donation requests sent by donors.
    Example table:
    Donor | Blood Group | Date | Time | Status
    Actions: Accept (Confirmed), Reject (Rejected), Reschedule (Rescheduled)
    """
    hospital = get_current_hospital()
    if not hospital:
        return redirect(url_for("public.index"))

    hospital_id = hospital.get("hospital_id") or str(hospital["_id"])
    date_filter = request.args.get("date", "").strip()
    status_filter = request.args.get("status", "").strip()

    all_appts = AppointmentService.get_hospital_appointments(
        hospital_id=hospital_id,
        date_filter=date_filter if date_filter else None,
        status_filter=status_filter if status_filter else None
    )

    return render_template(
        "hospital/requests.html",
        hospital=hospital,
        hospital_id=hospital_id,
        appointments=all_appts,
        selected_date=date_filter,
        selected_status=status_filter
    )

@hospital_bp.route("/requests/<req_id>/accept", methods=["POST"])
@role_required(["hospital"])
def accept_request(req_id):
    """
    Section 11: Accept action: Pending -> Confirmed
    """
    hospital = get_current_hospital()
    if not hospital:
        return redirect(url_for("public.index"))

    staff_email = session.get("email")
    ip_addr = request.remote_addr or "127.0.0.1"

    success, msg = AppointmentService.confirm_appointment(
        appointment_id=req_id,
        staff_email=staff_email,
        ip_address=ip_addr
    )

    if success:
        flash("Donation request Accepted! Status updated to Confirmed. Donor notified automatically.", "success")
    else:
        flash(msg, "danger")

    return redirect(url_for("hospital.appointments"))

@hospital_bp.route("/requests/<req_id>/reject", methods=["POST"])
@role_required(["hospital"])
def reject_request(req_id):
    """
    Section 11: Reject action: Pending -> Rejected
    """
    hospital = get_current_hospital()
    if not hospital:
        return redirect(url_for("public.index"))

    staff_email = session.get("email")
    reason = request.form.get("reason", "Donor scheduling criteria or facility capacity").strip()
    ip_addr = request.remote_addr or "127.0.0.1"

    success, msg = AppointmentService.reject_appointment(
        appointment_id=req_id,
        staff_email=staff_email,
        reason=reason,
        ip_address=ip_addr
    )

    if success:
        flash(f"Donation request Rejected. Status updated to Rejected. Reason logged: {reason}", "warning")
    else:
        flash(msg, "danger")

    return redirect(url_for("hospital.appointments"))

@hospital_bp.route("/requests/<req_id>/reschedule", methods=["POST"])
@role_required(["hospital"])
def reschedule_request(req_id):
    """
    Section 11: Reschedule action: Select new Date & Time -> Rescheduled
    """
    hospital = get_current_hospital()
    if not hospital:
        return redirect(url_for("public.index"))

    new_date = request.form.get("new_date", "").strip() or request.form.get("new_slot_date", "").strip()
    new_time = request.form.get("new_time", "").strip() or request.form.get("new_slot_time", "").strip()
    staff_email = session.get("email")
    ip_addr = request.remote_addr or "127.0.0.1"

    if not new_date or not new_time:
        flash("Please specify both the new date and time for rescheduling.", "danger")
        return redirect(url_for("hospital.appointments"))

    success, msg = AppointmentService.reschedule_appointment(
        appointment_id=req_id,
        new_date=new_date,
        new_slot_time=new_time,
        rescheduled_by_email=staff_email,
        role="hospital",
        ip_address=ip_addr
    )

    if success:
        flash(f"Appointment Rescheduled to {new_date} at {new_time}! Status updated to Rescheduled. Donor notified.", "success")
    else:
        flash(msg, "danger")

    return redirect(url_for("hospital.appointments"))

@hospital_bp.route("/donations", methods=["GET", "POST"])
@role_required(["hospital"])
def donation_history():
    """
    Section 14: DONATION HISTORY
    After a successful donation, record:
    - Donor
    - Blood Group
    - Donation Date
    - Units Collected
    - Details
    When saved:
    1. Added to Donation History
    2. Corresponding hospital's blood stock increases
    3. Donor's donation history is updated
    4. Linked to correct donor and hospital
    """
    hospital = get_current_hospital()
    if not hospital:
        return redirect(url_for("public.index"))

    hospital_id = hospital.get("hospital_id") or str(hospital["_id"])
    db = get_db()
    h_keys = [hospital_id, str(hospital.get("_id"))]
    h_keys = list(set([k for k in h_keys if k]))

    if request.method == "POST":
        donor_identifier = request.form.get("donor_id", "").strip()
        blood_group = request.form.get("blood_group", "").strip()
        donation_date = request.form.get("donation_date", "").strip()
        units_raw = request.form.get("units_collected", 1)
        details = request.form.get("details", "").strip() or "Voluntary In-Center Blood Donation"
        appointment_id = request.form.get("appointment_id", "").strip() or None

        try:
            units = max(1, int(units_raw))
        except (ValueError, TypeError):
            units = 1

        if not donor_identifier or not blood_group or not donation_date:
            flash("Please provide Donor ID/Name, Blood Group, and Donation Date.", "danger")
            return redirect(url_for("hospital.donation_history"))

        staff_email = session.get("email")
        ip_addr = request.remote_addr or "127.0.0.1"

        success, res = AppointmentService.record_donation(
            donor_id=donor_identifier,
            hospital_id=hospital_id,
            blood_group=blood_group,
            donation_date=donation_date,
            units_collected=units,
            details=details,
            staff_email=staff_email,
            appointment_id=appointment_id,
            ip_address=ip_addr
        )

        flash(f"Donation recorded successfully! {units} unit(s) of {blood_group} added to {hospital.get('name')} blood stock. Donor history updated.", "success")
        return redirect(url_for("hospital.donation_history"))

    # Fetch donations for this hospital
    donations_list = list(db.donations.find({"hospital_id": {"$in": h_keys}}).sort("donation_date", -1))

    # Connected donors for quick selector
    connected_donors = HospitalService.get_hospital_donors(hospital_id)

    # Confirmed appointments eligible for completion recording
    confirmed_appts = list(db.appointments.find({
        "hospital_id": {"$in": h_keys},
        "status": {"$in": ["Confirmed", "confirmed", "Rescheduled", "rescheduled"]}
    }).sort("slot_date", 1))

    return render_template(
        "hospital/donations.html",
        hospital=hospital,
        hospital_id=hospital_id,
        donations=donations_list,
        connected_donors=connected_donors,
        confirmed_appts=confirmed_appts,
        blood_groups=BLOOD_GROUPS
    )

@hospital_bp.route("/blood-requests", methods=["GET", "POST"])
@role_required(["hospital"])
def blood_requests():
    """
    Section 15: BLOOD REQUEST MANAGEMENT
    Show incoming blood requirements:
    - Request ID
    - Blood Group
    - Required Units
    - Request Date
    - Priority
    - Status
    Hospital management can update request status or create emergency requirements.
    """
    hospital = get_current_hospital()
    if not hospital:
        return redirect(url_for("public.index"))

    hospital_id = hospital.get("hospital_id") or str(hospital["_id"])

    if request.method == "POST":
        action = request.form.get("action")
        if action == "create":
            bg = request.form.get("blood_group")
            units = request.form.get("required_units", 2)
            priority = request.form.get("priority", "High")
            notes = request.form.get("notes", "Clinical Emergency Requirement")
            staff_email = session.get("email")

            RequestService.create_hospital_blood_request(
                hospital_id=hospital_id,
                blood_group=bg,
                required_units=units,
                priority=priority,
                staff_email=staff_email,
                notes=notes
            )
            flash(f"New clinical blood requirement for {units} unit(s) of {bg} created.", "success")
            return redirect(url_for("hospital.blood_requests"))

        elif action == "update_status":
            req_id = request.form.get("request_id")
            new_status = request.form.get("new_status")
            notes = request.form.get("notes", "")
            staff_email = session.get("email")
            role = "hospital"

            RequestService.update_request_status(
                request_id=req_id,
                new_status=new_status,
                staff_email=staff_email,
                role=role,
                notes=notes
            )
            flash(f"Blood requirement status updated to {new_status}.", "success")
            return redirect(url_for("hospital.blood_requests"))

    requests_list = RequestService.get_hospital_blood_requests(hospital_id)

    return render_template(
        "hospital/blood_requests.html",
        hospital=hospital,
        hospital_id=hospital_id,
        requests=requests_list,
        blood_groups=BLOOD_GROUPS
    )
