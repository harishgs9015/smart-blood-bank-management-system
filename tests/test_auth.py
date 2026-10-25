from services.auth_service import AuthService
from extensions import get_db

def test_donor_registration_and_login(client):
    # 1. Register new voluntary donor
    res = client.post("/register/donor", data={
        "name": "Amit Kumar",
        "email": "amit.kumar@test.com",
        "phone": "+91 99887 76655",
        "blood_group": "A+",
        "state": "Maharashtra",
        "district": "Pune",
        "password": "Password@123",
        "confirm_password": "Password@123",
        "consent": "on"
    }, follow_redirects=False)
    assert res.status_code == 302
    assert "registered=1" in res.headers["Location"]
    assert "amit.kumar%40test.com" in res.headers["Location"] or "amit.kumar@test.com" in res.headers["Location"]

    # Follow redirect to login page
    res_login_page = client.get(res.headers["Location"])
    assert res_login_page.status_code == 200
    assert b"Registration Successful" in res_login_page.data

    # 2. Verify role in DB cannot be escalated
    db = get_db()
    user = db.users.find_one({"email": "amit.kumar@test.com"})
    assert user is not None
    assert user["role"] == "donor"

    # 3. Duplicate email prevention on retry
    res_dup = client.post("/register/donor", data={
        "name": "Amit Duplicate",
        "email": "amit.kumar@test.com",
        "phone": "+91 99887 76655",
        "blood_group": "A+",
        "state": "Maharashtra",
        "district": "Pune",
        "password": "Password@123",
        "confirm_password": "Password@123",
        "consent": "on"
    }, follow_redirects=True)
    assert res_dup.status_code == 200
    assert b"already exists" in res_dup.data

    # 4. Field-specific validation failures
    res_invalid = client.post("/register/donor", data={
        "name": "",
        "email": "bad-email",
        "phone": "123",
        "blood_group": "",
        "state": "",
        "district": "",
        "password": "pass",
        "confirm_password": "other",
    }, follow_redirects=True)
    assert res_invalid.status_code == 200
    assert b"Full name is required" in res_invalid.data or b"full legal name" in res_invalid.data
    assert b"valid 10-digit Indian mobile number" in res_invalid.data
    assert b"valid email address" in res_invalid.data
    assert b"select your blood group" in res_invalid.data
    assert b"Passwords do not match" in res_invalid.data
    assert b"voluntary donor declaration" in res_invalid.data

    # 5. Login with registered donor credentials and verify dashboard access
    res_login = client.post("/login", data={
        "email": "amit.kumar@test.com",
        "password": "Password@123"
    }, follow_redirects=True)
    assert res_login.status_code == 200
    assert b"Welcome back, Amit Kumar" in res_login.data
    assert b"Donor Dashboard" in res_login.data or b"Voluntary Donor" in res_login.data

def test_hospital_registration_pending_verification(client):
    # Register a new hospital
    res = client.post("/register/hospital", data={
        "hospital_name": "Ruby Hall Clinic Blood Bank",
        "license_number": "MH-BB-2026-RUBY",
        "facility_type": "Private",
        "state": "Maharashtra",
        "district": "Pune",
        "address": "Sassoon Road, Pune - 411001",
        "contact_person": "Dr. Pradeep Sharma",
        "email": "ruby.bloodbank@pune.org",
        "phone": "+91 20 6645 5100",
        "emergency_phone": "+91 20 6645 5999",
        "password": "Hospital@123",
        "confirm_password": "Hospital@123"
    }, follow_redirects=True)
    assert res.status_code == 200
    assert b"submitted successfully" in res.data

    # Verify hospital record in database has status pending_verification
    db = get_db()
    hosp = db.hospitals.find_one({"license_number": "MH-BB-2026-RUBY"})
    assert hosp is not None
    assert hosp["status"] == "pending_verification"

def test_role_based_route_protections(client):
    # Anonymous accessing donor dashboard should be redirected to login
    res_anon = client.get("/donor/dashboard")
    assert res_anon.status_code == 302
    assert "/login" in res_anon.headers["Location"]

    # Login as donor (Rahul Sharma)
    client.post("/login", data={
        "email": "rahul.sharma@gmail.com",
        "password": "Donor@2026"
    }, follow_redirects=True)

    # Donor attempting to access Admin dashboard should be forbidden/redirected
    res_forbidden = client.get("/admin/dashboard", follow_redirects=True)
    assert b"Access denied" in res_forbidden.data
