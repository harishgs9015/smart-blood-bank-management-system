import re
from datetime import datetime, timezone
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from services.auth_service import AuthService
from extensions import get_db, db_manager
from config import Config

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        role = session.get("role")
        if role == "donor":
            return redirect(url_for("donor.dashboard"))
        elif role == "hospital":
            return redirect(url_for("hospital.dashboard"))
        elif role == "admin":
            return redirect(url_for("admin.dashboard"))
        return redirect(url_for("public.index"))

    is_registered = request.args.get("registered") == "1"
    initial_email = request.args.get("email", "").strip() if is_registered else ""
    initial_pass = ""
    active_tab = request.args.get("tab") or request.args.get("role") or "donor"

    demo_user = request.args.get("demo_user")
    if demo_user in ["hospital", "abc", "h001"]:
        initial_email = "abc.hospital@chennai.gov.in"
        initial_pass = "Hospital@2026"
        active_tab = "hospital"
    elif demo_user in ["xyz", "h002"]:
        initial_email = "xyz.hospital@chennai.gov.in"
        initial_pass = "Hospital@2026"
        active_tab = "hospital"
    elif demo_user in ["donor", "d001", "donor01"]:
        initial_email = "donor01@example.com"
        initial_pass = "Donor@2026"
        active_tab = "donor"
    elif demo_user in ["donor02", "d002"]:
        initial_email = "donor02@example.com"
        initial_pass = "Donor@2026"
        active_tab = "donor"
    elif demo_user == "admin":
        initial_email = "admin@raktkosh.gov.in"
        initial_pass = "Admin@2026"
        active_tab = "donor"

    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()
        selected_role = request.form.get("role_tab") or active_tab
        next_url = request.form.get("next") or request.args.get("next")

        if not email or not password:
            flash("Please enter both email and password.", "danger")
            return render_template("auth/login.html", email=email, initial_email=initial_email, initial_pass=initial_pass, registered=is_registered, active_tab=selected_role)

        user_info, msg = AuthService.authenticate_user(email, password)
        if not user_info:
            flash(msg, "danger")
            return render_template("auth/login.html", email=email, initial_email=initial_email, initial_pass=initial_pass, registered=is_registered, active_tab=selected_role)

        # Store session
        session.clear()
        session["user_id"] = user_info["user_id"]
        session["email"] = user_info["email"]
        session["name"] = user_info["name"]
        session["role"] = user_info["role"]

        if user_info["role"] == "donor":
            session["donor_id"] = user_info.get("donor_id", "D001")
            session["blood_group"] = user_info.get("blood_group", "")
            session["district"] = user_info.get("district", "")
            session["state"] = user_info.get("state", "")
            session["location"] = user_info.get("location", "Chennai, Tamil Nadu")
            flash(f"Welcome back, {user_info['name']} (Donor ID: {session['donor_id']})!", "success")
            return redirect(next_url or url_for("donor.dashboard"))

        elif user_info["role"] == "hospital":
            session["hospital_id"] = user_info.get("hospital_id", "")
            session["hospital_name"] = user_info.get("hospital_name", "")
            session["hospital_status"] = user_info.get("hospital_status", "verified")
            session["district"] = user_info.get("district", "")
            session["state"] = user_info.get("state", "")
            session["location"] = user_info.get("location", "Chennai")
            flash(f"Signed in as {user_info.get('hospital_name')} (Hospital ID: {session['hospital_id']}).", "success")
            return redirect(next_url or url_for("hospital.dashboard"))

        elif user_info["role"] == "admin":
            flash("Welcome to the Administration Console.", "success")
            return redirect(next_url or url_for("admin.dashboard"))

        return redirect(url_for("public.index"))

    return render_template("auth/login.html", initial_email=initial_email, initial_pass=initial_pass, registered=is_registered, active_tab=active_tab)

@auth_bp.route("/register/donor", methods=["GET", "POST"])
def register_donor():
    if session.get("user_id"):
        return redirect(url_for("public.index"))

    locations = Config.INDIAN_LOCATIONS
    blood_groups = Config.BLOOD_GROUPS
    field_errors = {}

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "").strip()
        confirm_password = request.form.get("confirm_password", "").strip()
        name = request.form.get("name", "").strip()
        phone = request.form.get("phone", "").strip()
        blood_group = request.form.get("blood_group", "").strip()
        state = request.form.get("state", "").strip()
        district = request.form.get("district", "").strip()
        date_of_birth = request.form.get("dob", "").strip()
        gender = request.form.get("gender", "").strip()
        address = request.form.get("address", "").strip()
        last_donation_date = request.form.get("last_donation_date", "").strip() or None
        preference_regular = "pref_regular" in request.form
        preference_emergency = "pref_emergency" in request.form
        consent = "consent" in request.form

        # 1. Full name validation
        if not name or len(name) < 2:
            field_errors["name"] = "Please enter your full legal name (at least 2 characters)."

        # 2. Indian mobile number validation (10 digits starting with 6, 7, 8, or 9)
        clean_phone = re.sub(r"[\s\-\+]", "", phone)
        if clean_phone.startswith("91") and len(clean_phone) == 12:
            clean_phone = clean_phone[2:]
        if not re.match(r"^[6-9]\d{9}$", clean_phone):
            field_errors["phone"] = "Please enter a valid 10-digit Indian mobile number (e.g. 9876543210)."

        # 3. Email validation & duplicate check
        if not email or not AuthService.validate_email(email):
            field_errors["email"] = "Please enter a valid email address (e.g. name@domain.com)."
        else:
            db = get_db()
            if db.users.find_one({"email": email}):
                field_errors["email"] = "An account with this email address already exists. Please sign in instead."

        # 4. Blood group validation
        if not blood_group or blood_group not in blood_groups:
            field_errors["blood_group"] = "Please select your blood group."

        # 5. State / Location validation
        if not state or state not in locations:
            field_errors["state"] = "Please select your State or Union Territory."
        if not district:
            field_errors["district"] = "Please select your District or City."

        # 6. Date of birth validation (18 to 65 years old)
        if date_of_birth:
            try:
                dob_val = datetime.strptime(date_of_birth, "%Y-%m-%d").date()
                today = datetime.now(timezone.utc).date()
                age = (today - dob_val).days // 365
                if age < 18 or age > 65:
                    field_errors["dob"] = f"Voluntary blood donors must be 18 to 65 years old (calculated age: {age} yrs)."
            except ValueError:
                field_errors["dob"] = "Invalid date format."

        # 7. Password validations
        if not password or len(password) < 6:
            field_errors["password"] = "Password must be at least 6 characters long."
        if password != confirm_password:
            field_errors["confirm_password"] = "Passwords do not match."

        # 8. Consent verification
        if not consent:
            field_errors["consent"] = "Please accept the voluntary donor declaration and medical terms."

        if field_errors:
            flash("Please correct the invalid fields highlighted below.", "danger")
            return render_template(
                "auth/register_donor.html",
                locations=locations,
                blood_groups=blood_groups,
                field_errors=field_errors,
                form_data=request.form
            )

        # 9. Register in Database
        ip_addr = request.remote_addr or "127.0.0.1"
        success, result = AuthService.register_donor(
            email=email,
            password=password,
            name=name,
            phone=clean_phone,
            blood_group=blood_group,
            state=state,
            district=district,
            date_of_birth=date_of_birth,
            gender=gender or "Other",
            address=address,
            last_donation_date=last_donation_date,
            preference_regular=preference_regular,
            preference_emergency=preference_emergency,
            ip_address=ip_addr
        )

        if not success:
            flash(result, "danger")
            if "already exists" in result:
                field_errors["email"] = result
            return render_template(
                "auth/register_donor.html",
                locations=locations,
                blood_groups=blood_groups,
                field_errors=field_errors,
                form_data=request.form
            )

        # 10. Success: Show confirmation message and redirect to sign-in with email prepared
        flash("Registration successful! Your voluntary donor profile is active. Please sign in below to access your donor dashboard.", "success")
        return redirect(url_for("auth.login", registered="1", email=email))

    return render_template("auth/register_donor.html", locations=locations, blood_groups=blood_groups, field_errors={}, form_data={})

@auth_bp.route("/register/hospital", methods=["GET", "POST"])
def register_hospital():
    if session.get("user_id"):
        return redirect(url_for("public.index"))

    locations = Config.INDIAN_LOCATIONS

    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()
        confirm_password = request.form.get("confirm_password", "").strip()
        hospital_name = request.form.get("hospital_name", "").strip()
        license_number = request.form.get("license_number", "").strip()
        facility_type = request.form.get("facility_type", "Government")
        state = request.form.get("state", "")
        district = request.form.get("district", "")
        address = request.form.get("address", "")
        contact_person = request.form.get("contact_person", "").strip()
        phone = request.form.get("phone", "").strip()
        emergency_phone = request.form.get("emergency_phone", "").strip()
        daily_capacity = request.form.get("daily_capacity", 4)
        operating_hours = request.form.get("operating_hours", "24/7")

        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return render_template("auth/register_hospital.html", locations=locations, form_data=request.form)

        ip_addr = request.remote_addr or "127.0.0.1"
        success, result = AuthService.register_hospital(
            email=email,
            password=password,
            hospital_name=hospital_name,
            license_number=license_number,
            facility_type=facility_type,
            state=state,
            district=district,
            address=address,
            contact_person=contact_person,
            phone=phone,
            emergency_phone=emergency_phone,
            daily_capacity=daily_capacity,
            operating_hours=operating_hours,
            ip_address=ip_addr
        )

        if not success:
            flash(result, "danger")
            return render_template("auth/register_hospital.html", locations=locations, form_data=request.form)

        # Automatically sign in the registered hospital so staff can immediately manage blood stock
        session.clear()
        session["user_id"] = result["user_id"]
        session["email"] = email
        session["name"] = contact_person
        session["role"] = "hospital"
        session["hospital_id"] = result["hospital_id"]
        session["hospital_name"] = hospital_name
        session["hospital_status"] = "pending_verification"
        session["district"] = district
        session["state"] = state

        flash(f"Hospital registration submitted successfully! Welcome to your Hospital Dashboard, {hospital_name}. You can now add and manage your blood stock below.", "success")
        return redirect(url_for("hospital.dashboard"))

    return render_template("auth/register_hospital.html", locations=locations, form_data={})

@auth_bp.route("/logout")
def logout():
    session.clear()
    flash("You have been signed out safely.", "info")
    return redirect(url_for("public.index"))
