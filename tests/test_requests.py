from services.request_service import RequestService
from extensions import get_db

def test_public_blood_request_submission_and_tracking(client):
    # 1. Submit public emergency blood request
    res = client.post("/request-blood", data={
        "patient_name": "Rohan Mehra",
        "blood_group": "AB-",
        "units_needed": 2,
        "hospital_name": "Apollo Indraprastha",
        "hospital_state": "Delhi (NCR)",
        "hospital_district": "South Delhi",
        "doctor_case_ref": "AI-ICU-8821",
        "urgency": "Emergency",
        "requester_name": "Sunita Mehra",
        "requester_phone": "+91 98111 22334",
        "medical_notes": "Platelet and PRBC support needed for emergency surgical care"
    }, follow_redirects=True)
    assert res.status_code == 200
    assert b"Tracking" in res.data

    # 2. Verify in DB
    db = get_db()
    req = db.blood_requests.find_one({"doctor_case_ref": "AI-ICU-8821"})
    assert req is not None
    assert req["tracking_code"].startswith("REQ-2026-")
    assert req["status"] == "pending_verification"

    # 3. Track request via tracking page
    res_track = client.get(f"/track-request?code={req['tracking_code']}")
    assert res_track.status_code == 200
    assert b"Rohan Mehra" in res_track.data
    assert b"Under Verification" in res_track.data

    # 4. Admin verifies the request
    ok, _ = RequestService.update_request_status(
        request_id=str(req["_id"]),
        new_status="verified",
        staff_email="admin@raktkosh.gov.in",
        role="admin",
        notes="Verified prescription with Apollo ICU duty doctor."
    )
    assert ok is True

    # 5. Track again and verify status changed
    res_track_updated = client.get(f"/track-request?code={req['tracking_code']}")
    assert b"Prescription Verified" in res_track_updated.data

def test_request_minimal_fields_and_flexible_tracking(client):
    # Submit with minimal required fields (optional fields omitted)
    res = client.post("/request-blood", data={
        "patient_name": "Pooja Verma",
        "blood_group": "B+",
        "units_needed": 1,
        "hospital_name": "Civil Hospital",
        "hospital_state": "Gujarat",
        "hospital_district": "Ahmedabad",
        "urgency": "Urgent",
        "requester_phone": "9898989898"
    }, follow_redirects=True)
    assert res.status_code == 200
    assert b"Tracking" in res.data

    # Query with raw phone number in tracking search
    res_phone = client.get("/track-request?code=9898989898")
    assert res_phone.status_code == 200
    assert b"Pooja Verma" in res_phone.data

    # Query without 'REQ-' prefix
    db = get_db()
    req = db.blood_requests.find_one({"patient_name": "Pooja Verma"})
    assert req is not None
    code_suffix = req["tracking_code"].replace("REQ-", "")
    res_suffix = client.get(f"/track-request?code={code_suffix}")
    assert res_suffix.status_code == 200
    assert b"Pooja Verma" in res_suffix.data

