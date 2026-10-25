"""
Web Routes and Template Integration Test Script
"""
import sys
import io
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from app import create_app
from extensions import get_db
from seed_data import ensure_smart_blood_entities

def test_web_routes():
    print("=" * 70)
    print("TESTING HTTP ROUTES, SESSIONS, AND JINJA TEMPLATES")
    print("=" * 70)

    app = create_app()
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False

    with app.app_context():
        db = get_db()
        ensure_smart_blood_entities(db)

    client = app.test_client()

    # 1. Login Page
    print("\n[ROUTE 1] Testing /login...")
    res = client.get("/login")
    print(f"Status: {res.status_code}, Location: {res.location}")
    if res.status_code == 302:
        res = client.get(res.location)
    assert res.status_code == 200
    html = res.get_data(as_text=True)
    assert "Donor Login" in html
    assert "Hospital Login" in html
    assert "D001" in html
    assert "H001" in html
    print("  ✓ Login page renders with Donor and Hospital login options & test credentials.")

    # 2. Donor 01 Login & Flow
    print("\n[ROUTE 2] Testing Donor Login (donor01@example.com)...")
    login_res = client.post("/login", data={
        "email": "donor01@example.com",
        "password": "Donor@2026",
        "role_tab": "donor"
    }, follow_redirects=True)
    assert login_res.status_code == 200
    donor_html = login_res.get_data(as_text=True)
    assert "Donor ID: D001" in donor_html or "D001" in donor_html
    assert "Rahul Sharma" in donor_html
    print("  ✓ Donor login succeeded. Automatically redirected to Donor Dashboard.")

    # Donor Navigation views
    for path, title_needle in [
        ("/donor/dashboard", "Donor Dashboard"),
        ("/donor/find-hospital", "Find Hospital"),
        ("/donor/donate/H001", "Donation Request"),
        ("/donor/applications", "My Applications"),
        ("/donor/appointments", "My Appointments"),
        ("/donor/history", "Donation History"),
        ("/donor/profile", "Profile")
    ]:
        res = client.get(path)
        assert res.status_code == 200, f"Failed GET {path}: {res.status_code}"
        print(f"  ✓ {path} rendered cleanly (Status 200).")

    # Donor Submits Request to ABC Hospital (H001)
    print("\n[ROUTE 3] Testing Donor Request Submission to ABC Hospital (H001)...")
    submit_res = client.post("/donor/donate/H001", data={
        "hospital_id": "H001",
        "donor_name": "Rahul Sharma",
        "donor_id": "D001",
        "blood_group": "O+",
        "contact_number": "+91 98765 43210",
        "preferred_date": "28 Oct 2026",
        "preferred_time": "10:30 AM",
        "additional_details": "Voluntary blood donation slot booking test."
    }, follow_redirects=True)
    assert submit_res.status_code == 200
    sub_html = submit_res.get_data(as_text=True)
    assert "Donation Request Sent to ABC Hospital" in sub_html
    assert "Pending" in sub_html
    print("  ✓ Successfully submitted request: 'Donation Request Sent to ABC Hospital' shown with Status: Pending.")

    # 3. Hospital Login (ABC Hospital H001)
    print("\n[ROUTE 4] Testing Hospital Login for ABC Hospital (H001)...")
    # First logout
    client.get("/logout")
    hosp_login_res = client.post("/login", data={
        "email": "abc.hospital@chennai.gov.in",
        "password": "Hospital@2026",
        "role_tab": "hospital"
    }, follow_redirects=True)
    assert hosp_login_res.status_code == 200
    h_html = hosp_login_res.get_data(as_text=True)
    assert "ABC Hospital" in h_html
    assert "H001" in h_html
    print("  ✓ Hospital login succeeded. Automatically redirected to Hospital Dashboard.")

    # Hospital Navigation views
    for path in [
        "/hospital/dashboard",
        "/hospital/stock",
        "/hospital/stock/O+",
        "/hospital/stock/Bombay%20Blood%20Group%20(hh)",
        "/hospital/donors",
        "/hospital/appointments",
        "/hospital/donations",
        "/hospital/blood-requests"
    ]:
        res = client.get(path)
        assert res.status_code == 200, f"Failed GET {path}: {res.status_code}"
        print(f"  ✓ {path} rendered cleanly (Status 200).")

    # Verify submitted request appears in ABC Hospital's appointments
    appts_res = client.get("/hospital/appointments")
    appts_html = appts_res.get_data(as_text=True)
    assert "Rahul Sharma" in appts_html
    assert "D001" in appts_html
    assert "O+" in appts_html
    print("  ✓ Submitted request automatically visible in ABC Hospital's Appointments / Donation Requests!")

    # 4. Strict Isolation Test: XYZ Hospital (H002) Login
    print("\n[ROUTE 5] Testing Hospital Isolation with XYZ Hospital (H002)...")
    client.get("/logout")
    xyz_login_res = client.post("/login", data={
        "email": "xyz.hospital@chennai.gov.in",
        "password": "Hospital@2026",
        "role_tab": "hospital"
    }, follow_redirects=True)
    assert xyz_login_res.status_code == 200
    xyz_appts_res = client.get("/hospital/appointments")
    xyz_appts_html = xyz_appts_res.get_data(as_text=True)
    # The request created for H001 for 28 Oct 2026 must NOT appear in H002
    assert "28 Oct 2026" not in xyz_appts_html
    print("  ✓ Isolation verified! Request sent to H001 is completely absent from H002.")

    print("\n" + "=" * 70)
    print("ALL WEB ROUTE AND TEMPLATE INTEGRATION TESTS PASSED! (100% SUCCESS)")
    print("=" * 70)

if __name__ == "__main__":
    test_web_routes()
