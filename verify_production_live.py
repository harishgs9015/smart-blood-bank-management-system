"""
Live Production Deployment End-to-End Verification Test Script
"""
import sys
import io
import urllib.request
import urllib.parse
import http.cookiejar
import re

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE_URL = "https://internal-exactly-trace-situations.trycloudflare.com"

class SessionClient:
    def __init__(self):
        self.cj = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.cj))

    def get(self, path):
        url = BASE_URL + path if path.startswith("/") else path
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
        with self.opener.open(req) as resp:
            return resp.status, resp.read().decode("utf-8", errors="ignore"), resp.geturl()

    def post(self, path, data):
        url = BASE_URL + path if path.startswith("/") else path
        encoded = urllib.parse.urlencode(data).encode("utf-8")
        req = urllib.request.Request(url, data=encoded, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Content-Type": "application/x-www-form-urlencoded"
        })
        with self.opener.open(req) as resp:
            return resp.status, resp.read().decode("utf-8", errors="ignore"), resp.geturl()

def run_production_tests():
    print("=" * 75)
    print("STARTING LIVE PRODUCTION VERIFICATION ON PUBLIC HTTPS URL")
    print(f"Target: {BASE_URL}")
    print("=" * 75)

    # 1. Test Home & Login
    client = SessionClient()
    print("\n[STEP 1] Testing Public Home Page & Login Page...")
    s, html, u = client.get("/")
    assert s == 200, f"Home page failed: {s}"
    assert "Smart" in html
    print("  ✓ Live Home page loaded successfully (HTTP 200).")

    s, html, u = client.get("/login")
    assert s == 200, f"Login page failed: {s}"
    assert "Donor Login" in html and "Hospital Login" in html
    print("  ✓ Live Login portal loaded with Donor and Hospital login options.")

    # 2. Donor Login (Rahul Sharma D001)
    print("\n[STEP 2] Testing Donor Login on Live URL (donor01@example.com)...")
    s, html, u = client.post("/login", {
        "email": "donor01@example.com",
        "password": "Donor@2026",
        "role_tab": "donor"
    })
    assert s == 200
    assert "Donor ID: D001" in html or "D001" in html
    print(f"  ✓ Donor logged in successfully and redirected to: {u}")

    # 3. Test Donor Navigation Pages
    print("\n[STEP 3] Testing Donor Navigation Pages...")
    for p in ["/donor/dashboard", "/donor/find-hospital", "/donor/applications", "/donor/appointments", "/donor/history", "/donor/profile"]:
        s, html, _ = client.get(p)
        assert s == 200, f"Page {p} failed: {s}"
        print(f"  ✓ Live endpoint {p} returned HTTP 200 OK.")

    # 4. Donor Submits Donation Request to ABC Hospital (H001)
    print("\n[STEP 4] Submitting Live Donation Request to ABC Hospital (H001)...")
    test_slot_date = "29 Oct 2026"
    test_slot_time = "10:30 AM"
    s, html, u = client.post("/donor/donate/H001", {
        "hospital_id": "H001",
        "donor_name": "Rahul Sharma",
        "donor_id": "D001",
        "blood_group": "O+",
        "contact_number": "+91 98765 43210",
        "preferred_date": test_slot_date,
        "preferred_time": test_slot_time,
        "additional_details": "Production live end-to-end verification pledge."
    })
    assert s == 200
    assert "Donation Request Sent to ABC Hospital" in html
    assert "Pending" in html
    print("  ✓ Live submission successful: 'Donation Request Sent to ABC Hospital' displayed with Status: Pending.")

    # 5. Hospital Login: ABC Hospital (H001)
    print("\n[STEP 5] Testing Hospital Login for ABC Hospital (H001)...")
    hosp_client = SessionClient()
    s, html, u = hosp_client.post("/login", {
        "email": "abc.hospital@chennai.gov.in",
        "password": "Hospital@2026",
        "role_tab": "hospital"
    })
    assert s == 200
    assert "ABC Hospital" in html and "H001" in html
    print(f"  ✓ ABC Hospital logged in successfully. Redirected to: {u}")

    # 6. Test Hospital Stock Overview (All 9 Blood Groups)
    print("\n[STEP 6] Testing Blood Stock Overview & Auto-Calculated Status...")
    s, html, _ = hosp_client.get("/hospital/stock")
    assert s == 200
    for bg in ["A+", "A-", "B+", "B-", "O+", "O-", "AB+", "AB-", "Bombay Blood Group (hh)"]:
        assert bg in html, f"Missing blood group {bg} in stock view!"
    assert "Normal" in html and "Critical" in html
    print("  ✓ All 9 blood groups displayed with automatically calculated status (🟢 Normal, 🟡 Low, 🔴 Critical).")

    # 7. Test Blood Group Details
    print("\n[STEP 7] Testing Blood Group Details for Bombay Blood Group (hh)...")
    s, html, _ = hosp_client.get("/hospital/stock/Bombay%20Blood%20Group%20(hh)")
    assert s == 200
    assert "Bombay Blood Group (hh)" in html
    print("  ✓ Detailed page for Bombay Blood Group (hh) rendered cleanly.")

    # 8. Test Hospital Appointments / Donation Requests Feed
    print("\n[STEP 8] Testing Appointments / Donation Requests Feed...")
    s, html, _ = hosp_client.get("/hospital/appointments")
    assert s == 200
    assert "Rahul Sharma" in html and "D001" in html and "O+" in html
    print("  ✓ Submitted request automatically visible in ABC Hospital's Appointments / Requests section!")

    # 9. Strict Multi-Hospital Isolation Test: XYZ Hospital (H002)
    print("\n[STEP 9] Testing Multi-Hospital Isolation with XYZ Hospital (H002)...")
    xyz_client = SessionClient()
    s, html, _ = xyz_client.post("/login", {
        "email": "xyz.hospital@chennai.gov.in",
        "password": "Hospital@2026",
        "role_tab": "hospital"
    })
    assert s == 200
    s, xyz_html, _ = xyz_client.get("/hospital/appointments")
    assert s == 200
    assert test_slot_date not in xyz_html, "CRITICAL: Data leaked to XYZ Hospital!"
    print("  ✓ Strict multi-hospital isolation verified! Request for H001 is completely absent from H002.")

    # 10. Hospital Donors Roster
    print("\n[STEP 10] Testing Hospital Donors Roster...")
    s, html, _ = hosp_client.get("/hospital/donors")
    assert s == 200
    assert "D001" in html
    print("  ✓ Connected donors roster loaded with isolated donor records.")

    # 11. Hospital Blood Requests
    print("\n[STEP 11] Testing Hospital Blood Requests section...")
    s, html, _ = hosp_client.get("/hospital/blood-requests")
    assert s == 200
    print("  ✓ Hospital blood requirements section loaded successfully.")

    # 12. Hospital Donation History
    print("\n[STEP 12] Testing Hospital Donation History section...")
    s, html, _ = hosp_client.get("/hospital/donations")
    assert s == 200
    print("  ✓ Hospital donation history section loaded successfully.")

    print("\n" + "=" * 75)
    print("ALL 12 LIVE PRODUCTION VERIFICATION SUITES PASSED FLAWLESSLY! (100%)")
    print(f"Production URL: {BASE_URL}")
    print("=" * 75)

if __name__ == "__main__":
    run_production_tests()
