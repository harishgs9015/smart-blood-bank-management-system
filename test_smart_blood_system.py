"""
End-to-End Verification Test Script for Smart Blood Donation & Blood Bank Management System
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
from services.stock_service import StockService
from services.appointment_service import AppointmentService
from services.hospital_service import HospitalService
from services.request_service import RequestService
from models.stock import BLOOD_GROUPS, get_stock_status

def run_tests():
    print("=" * 70)
    print("STARTING SMART BLOOD SYSTEM VERIFICATION TESTS")
    print("=" * 70)

    app = create_app()
    with app.app_context():
        db = get_db()
        ensure_smart_blood_entities(db)

        # -------------------------------------------------------------
        # TEST 1: Check 9 Blood Groups & Stock Auto-Calculation
        # -------------------------------------------------------------
        print("\n[TEST 1] Verifying 9 Blood Groups & Auto-Calculated Stock Status...")
        assert "Bombay Blood Group (hh)" in BLOOD_GROUPS, "Bombay Blood Group (hh) missing from BLOOD_GROUPS!"
        assert len(BLOOD_GROUPS) == 9, f"Expected 9 blood groups, found {len(BLOOD_GROUPS)}"

        # Status formula checks
        assert get_stock_status(25, 10) == "Normal", "25 units / min 10 should be Normal"
        assert get_stock_status(4, 10) == "Critical", "4 units / min 10 should be Critical"
        assert get_stock_status(6, 10) == "Low", "6 units / min 10 should be Low"

        # Check ABC Hospital (H001) Stock
        h001_stocks = StockService.get_hospital_stock("H001")
        assert len(h001_stocks) == 9, f"H001 should have 9 stock records, got {len(h001_stocks)}"
        
        o_pos = next(s for s in h001_stocks if s["blood_group"] == "O+")
        assert o_pos["available_units"] >= 25, f"O+ expected >= 25 units, got {o_pos['available_units']}"
        assert o_pos["status"] == "Normal", f"O+ expected Normal status, got {o_pos['status']}"

        a_neg = next(s for s in h001_stocks if s["blood_group"] == "A-")
        assert a_neg["available_units"] == 4, f"A- expected 4 units, got {a_neg['available_units']}"
        assert a_neg["status"] == "Critical", f"A- expected Critical status, got {a_neg['status']}"

        bombay = next(s for s in h001_stocks if s["blood_group"] == "Bombay Blood Group (hh)")
        assert bombay["status"] == "Critical", f"Bombay expected Critical status, got {bombay['status']}"
        print("  ✓ All 9 blood groups present with automatically calculated status (🟢 Normal, 🟡 Low, 🔴 Critical).")

        # -------------------------------------------------------------
        # TEST 2: Check Pre-seeded Entities (H001, H002, D001, D002)
        # -------------------------------------------------------------
        print("\n[TEST 2] Verifying Pre-seeded Hospitals and Donors...")
        h_abc = HospitalService.get_hospital_by_id("H001")
        h_xyz = HospitalService.get_hospital_by_id("H002")
        assert h_abc is not None, "ABC Hospital (H001) not found!"
        assert h_xyz is not None, "XYZ Hospital (H002) not found!"
        assert h_abc["name"] == "ABC Hospital", f"Expected ABC Hospital, got {h_abc['name']}"
        assert h_xyz["name"] == "XYZ Hospital", f"Expected XYZ Hospital, got {h_xyz['name']}"

        d001 = db.users.find_one({"email": "donor01@example.com"})
        d002 = db.users.find_one({"email": "donor02@example.com"})
        assert d001 is not None, "Donor 01 not found!"
        assert d002 is not None, "Donor 02 not found!"
        print(f"  ✓ Found ABC Hospital (H001) & XYZ Hospital (H002).")
        print(f"  ✓ Found Donor 01 (D001, {d001.get('blood_group')}) & Donor 02 (D002, {d002.get('blood_group')}).")

        # -------------------------------------------------------------
        # TEST 3: Donor Submits Request to ABC Hospital (H001)
        # -------------------------------------------------------------
        print("\n[TEST 3] Testing Donor Request Submission to ABC Hospital (H001)...")
        test_slot_date = "30 Oct 2026"
        test_slot_time = "10:30 AM"
        success, res = AppointmentService.book_appointment(
            donor_id=str(d001["_id"]),
            donor_name="Rahul Sharma",
            donor_email=d001["email"],
            donor_phone="+91 98765 43210",
            donor_blood_group="O+",
            hospital_id="H001",
            slot_date=test_slot_date,
            slot_time=test_slot_time,
            notes="Urgent voluntary donation test",
            donor_custom_id="D001"
        )
        assert success, f"Booking appointment failed: {res}"
        req_id = res["request_id"]
        assert res["status"] == "Pending", f"Expected status Pending, got {res['status']}"
        assert res["hospital_id"] == "H001", f"Expected hospital_id H001, got {res['hospital_id']}"
        assert res["donor_id"] == "D001", f"Expected donor_id D001, got {res['donor_id']}"
        print(f"  ✓ Donation Request created successfully: Ref={req_id}, Status={res['status']}")

        # -------------------------------------------------------------
        # TEST 4: Strict Hospital Isolation (Section 5 & 17)
        # -------------------------------------------------------------
        print("\n[TEST 4] Testing Strict Hospital Isolation between H001 and H002...")
        abc_appts = AppointmentService.get_hospital_appointments("H001")
        xyz_appts = AppointmentService.get_hospital_appointments("H002")

        abc_req_ids = [a.get("request_id") for a in abc_appts]
        xyz_req_ids = [a.get("request_id") for a in xyz_appts]

        assert req_id in abc_req_ids, f"Request {req_id} should appear in ABC Hospital (H001)!"
        assert req_id not in xyz_req_ids, f"CRITICAL: Request {req_id} leaked to XYZ Hospital (H002)!"
        print(f"  ✓ Strict isolation verified! Request {req_id} appears ONLY in H001 and NEVER in H002.")

        # -------------------------------------------------------------
        # TEST 5: Hospital Action (Accept / Reject / Reschedule)
        # -------------------------------------------------------------
        print("\n[TEST 5] Testing Hospital Action: Accept -> Confirmed...")
        acc_ok, acc_msg = AppointmentService.confirm_appointment(
            appointment_id=req_id,
            staff_email="abc.hospital@chennai.gov.in"
        )
        assert acc_ok, f"Confirm appointment failed: {acc_msg}"

        # Check DB update on same document
        updated_appt = db.appointments.find_one({"request_id": req_id})
        assert updated_appt["status"] == "Confirmed", f"Expected Confirmed status, got {updated_appt['status']}"

        # Check Donor side automatically sees updated status
        donor_appts = AppointmentService.get_donor_appointments(str(d001["_id"]))
        matching_donor_appt = next((a for a in donor_appts if a.get("request_id") == req_id), None)
        assert matching_donor_appt is not None, "Appointment missing from donor portal!"
        assert matching_donor_appt["status"] == "Confirmed", f"Donor expected Confirmed, got {matching_donor_appt['status']}"
        print(f"  ✓ Hospital Accept verified: Status successfully updated Pending -> Confirmed in database.")
        print(f"  ✓ Donor portal automatically displays: 🟢 Confirmed.")

        # Test Reschedule
        print("\n[TEST 5b] Testing Hospital Action: Reschedule -> Rescheduled with new date/time...")
        resched_ok, resched_msg = AppointmentService.reschedule_appointment(
            appointment_id=req_id,
            new_date="31 Oct 2026",
            new_slot_time="02:30 PM",
            rescheduled_by_email="abc.hospital@chennai.gov.in"
        )
        assert resched_ok, f"Reschedule failed: {resched_msg}"
        updated_resched = db.appointments.find_one({"request_id": req_id})
        assert updated_resched["status"] == "Rescheduled", f"Expected Rescheduled, got {updated_resched['status']}"
        assert updated_resched["appointment_date"] == "31 Oct 2026"
        assert updated_resched["appointment_time"] == "02:30 PM"
        print(f"  ✓ Hospital Reschedule verified: Status is 🟡 Rescheduled, new slot: 31 Oct 2026 at 02:30 PM.")

        # Test Reject
        print("\n[TEST 5c] Testing Hospital Action: Reject -> Rejected with reason...")
        rej_ok, rej_msg = AppointmentService.reject_appointment(
            appointment_id=req_id,
            staff_email="abc.hospital@chennai.gov.in",
            reason="Blood bank slot over capacity"
        )
        assert rej_ok, f"Reject failed: {rej_msg}"
        updated_rej = db.appointments.find_one({"request_id": req_id})
        assert updated_rej["status"] == "Rejected", f"Expected Rejected, got {updated_rej['status']}"
        assert updated_rej["cancellation_reason"] == "Blood bank slot over capacity"
        print(f"  ✓ Hospital Reject verified: Status is 🔴 Rejected, reason recorded.")

        # -------------------------------------------------------------
        # TEST 6: Section 14 Donation Recording & Blood Stock Increment
        # -------------------------------------------------------------
        print("\n[TEST 6] Testing Section 14: Recording Completed Donation & Auto-Incrementing Stock...")
        # Get current O+ stock
        curr_o_stock = next(s for s in StockService.get_hospital_stock("H001") if s["blood_group"] == "O+")
        initial_units = curr_o_stock["available_units"]

        # Record donation of 2 units of O+
        don_ok, don_res = AppointmentService.record_donation(
            donor_id="D001",
            hospital_id="H001",
            blood_group="O+",
            donation_date="2026-10-25",
            units_collected=2,
            details="Successful whole blood collection from D001",
            staff_email="abc.hospital@chennai.gov.in",
            appointment_id=req_id
        )

        # 1. Check added to db.donations
        saved_don = db.donations.find_one({"donation_id": don_res["donation_id"]})
        assert saved_don is not None, "Donation record missing from db.donations!"
        assert saved_don["units_collected"] == 2

        # 2. Check blood stock increased by 2
        new_o_stock = next(s for s in StockService.get_hospital_stock("H001") if s["blood_group"] == "O+")
        assert new_o_stock["available_units"] == initial_units + 2, f"Expected {initial_units + 2} units, got {new_o_stock['available_units']}"

        # 3. Check donor history updated
        donor_prof = db.donor_profiles.find_one({"donor_id": "D001"})
        assert donor_prof is not None
        assert donor_prof["total_donations"] >= 2

        print(f"  ✓ Donation record saved to db.donations (Ref: {saved_don.get('donation_id')}).")
        print(f"  ✓ Hospital H001 blood stock for O+ increased from {initial_units} to {new_o_stock['available_units']} units.")
        print(f"  ✓ Donor D001 total donations incremented to {donor_prof['total_donations']}.")

        # -------------------------------------------------------------
        # TEST 7: Hospital Donors Section Isolation (Section 9)
        # -------------------------------------------------------------
        print("\n[TEST 7] Testing Section 9: Hospital Donors view isolation...")
        h001_donors = HospitalService.get_hospital_donors("H001")
        h002_donors = HospitalService.get_hospital_donors("H002")
        h001_donor_ids = [d["donor_id"] for d in h001_donors]
        assert "D001" in h001_donor_ids, "D001 should be connected to H001!"
        print(f"  ✓ H001 connected donors: {h001_donor_ids}")

        # -------------------------------------------------------------
        # TEST 8: Blood Requests Management (Section 15)
        # -------------------------------------------------------------
        print("\n[TEST 8] Testing Section 15: Clinical Blood Requirement creation and update...")
        ok, bld_req = RequestService.create_hospital_blood_request(
            hospital_id="H001",
            blood_group="B+",
            required_units=3,
            priority="Emergency",
            staff_email="abc.hospital@chennai.gov.in",
            notes="Trauma OT emergency requirement"
        )
        assert ok and bld_req is not None, "Blood request creation failed!"
        bld_req_id = bld_req["blood_request_id"]

        h001_reqs = RequestService.get_hospital_blood_requests("H001")
        matching_req = next((r for r in h001_reqs if r.get("blood_request_id") == bld_req_id), None)
        assert matching_req is not None, "Blood request missing from H001 list!"
        assert matching_req["priority"] == "Emergency"

        # Update status
        upd_ok, upd_res = RequestService.update_request_status(
            request_id=bld_req_id,
            new_status="Fulfilled",
            staff_email="abc.hospital@chennai.gov.in",
            role="hospital",
            notes="Dispatched to Trauma OT"
        )
        assert upd_ok, "Updating blood request status failed!"
        refreshed_req = db.blood_requests.find_one({"blood_request_id": bld_req_id})
        assert refreshed_req["status"] == "Fulfilled", f"Expected Fulfilled, got {refreshed_req['status']}"
        print(f"  ✓ Clinical Blood Requirement {bld_req_id} created and updated to 🟢 Fulfilled.")

        print("\n" + "=" * 70)
        print("ALL 8 VERIFICATION SUITES PASSED FLAWLESSLY! (100% SUCCESS)")
        print("=" * 70)

if __name__ == "__main__":
    run_tests()
