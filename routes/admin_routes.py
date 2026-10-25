from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from routes import role_required
from extensions import get_db
from services.hospital_service import HospitalService
from services.request_service import RequestService
from services.audit_service import AuditService

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

@admin_bp.route("/dashboard")
@role_required(["admin"])
def dashboard():
    db = get_db()
    # High-level metrics
    total_users = db.users.count_documents({})
    total_donors = db.users.count_documents({"role": "donor"})
    total_hospitals = db.hospitals.count_documents({})
    verified_hospitals = db.hospitals.count_documents({"status": "verified"})
    pending_hospitals = db.hospitals.count_documents({"status": "pending_verification"})
    total_appointments = db.appointments.count_documents({})
    total_requests = db.blood_requests.count_documents({})

    stocks = list(db.blood_stock.find())
    total_units = sum(s.get("units", 0) for s in stocks)

    # Pending hospitals queue
    pending_hospital_list = HospitalService.get_all_hospitals(status_filter="pending_verification")

    # All registered hospitals list
    all_hospitals = HospitalService.get_all_hospitals()

    # Public blood requests
    recent_requests = RequestService.get_all_requests()[:10]

    # Audit logs
    audit_logs = AuditService.get_recent_logs(limit=25)

    return render_template(
        "admin/dashboard.html",
        metrics={
            "total_users": total_users,
            "total_donors": total_donors,
            "total_hospitals": total_hospitals,
            "verified_hospitals": verified_hospitals,
            "pending_hospitals": pending_hospitals,
            "total_appointments": total_appointments,
            "total_requests": total_requests,
            "total_units": total_units
        },
        pending_hospitals=pending_hospital_list,
        all_hospitals=all_hospitals,
        recent_requests=recent_requests,
        audit_logs=audit_logs
    )

@admin_bp.route("/hospitals/verify/<hospital_id>", methods=["POST"])
@role_required(["admin"])
def verify_hospital(hospital_id):
    admin_email = session.get("email")
    notes = request.form.get("notes", "Hospital verified by government health administration authority.").strip()
    ip_addr = request.remote_addr or "127.0.0.1"

    success, msg = HospitalService.verify_hospital(
        hospital_id=hospital_id,
        admin_email=admin_email,
        approve=True,
        notes=notes,
        ip_address=ip_addr
    )

    if success:
        flash(msg, "success")
    else:
        flash(msg, "danger")

    return redirect(url_for("admin.dashboard"))

@admin_bp.route("/hospitals/reject/<hospital_id>", methods=["POST"])
@role_required(["admin"])
def reject_hospital(hospital_id):
    admin_email = session.get("email")
    notes = request.form.get("notes", "Registration rejected due to invalid clinical establishment credentials.").strip()
    ip_addr = request.remote_addr or "127.0.0.1"

    success, msg = HospitalService.verify_hospital(
        hospital_id=hospital_id,
        admin_email=admin_email,
        approve=False,
        notes=notes,
        ip_address=ip_addr
    )

    if success:
        flash(msg, "warning")
    else:
        flash(msg, "danger")

    return redirect(url_for("admin.dashboard"))

@admin_bp.route("/requests/verify/<request_id>", methods=["POST"])
@role_required(["admin"])
def verify_blood_request(request_id):
    admin_email = session.get("email")
    status = request.form.get("status", "verified")
    notes = request.form.get("notes", "").strip()
    ip_addr = request.remote_addr or "127.0.0.1"

    success, msg = RequestService.update_request_status(
        request_id=request_id,
        new_status=status,
        staff_email=admin_email,
        role="admin",
        notes=notes,
        ip_address=ip_addr
    )

    if success:
        flash(msg, "success")
    else:
        flash(msg, "danger")

    return redirect(url_for("admin.dashboard"))
