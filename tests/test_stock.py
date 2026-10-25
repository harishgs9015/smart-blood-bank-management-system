from extensions import get_db
from services.stock_service import StockService
from models.stock import BLOOD_GROUPS

def test_stock_retrieval_and_audit_update(client):
    db = get_db()
    hosp = db.hospitals.find_one({"license_number": "DL-BB-2021-0012"})
    hosp_id = str(hosp["_id"])

    # 1. Verify all 8 blood groups are returned
    stocks = StockService.get_hospital_stock(hosp_id)
    assert len(stocks) == 8
    returned_groups = {s["blood_group"] for s in stocks}
    assert returned_groups == set(BLOOD_GROUPS)

    # 2. Update stock units
    ok, msg = StockService.update_stock(
        hospital_id=hosp_id,
        hospital_name=hosp["name"],
        blood_group="AB+",
        units=25,
        reason="Large voluntary camp collection at university campus",
        user_email="aiims.bloodbank@delhi.gov.in"
    )
    assert ok is True

    # 3. Verify stock in DB
    updated = db.blood_stock.find_one({"hospital_id": hosp_id, "blood_group": "AB+"})
    assert updated["units"] == 25
    assert updated["status"] == "Available"

    # 4. Verify audit log was recorded
    audit = db.audit_logs.find_one({"action": "STOCK_UPDATE", "performed_by": "aiims.bloodbank@delhi.gov.in"})
    assert audit is not None
    assert "AB+" in audit["details"]

def test_inter_hospital_stock_assistance(client):
    db = get_db()
    hosp_1 = db.hospitals.find_one({"license_number": "DL-BB-2021-0012"})
    hosp_2 = db.hospitals.find_one({"license_number": "MH-BB-2019-4401"})

    # 1. Hospital 1 creates assistance request
    ok, req_id = StockService.create_assistance_request(
        requesting_hospital_id=str(hosp_1["_id"]),
        requesting_hospital_name=hosp_1["name"],
        blood_group="O-",
        units_needed=3,
        urgency="Critical",
        reason="Trauma multiple casualty protocol",
        user_email="aiims.bloodbank@delhi.gov.in"
    )
    assert ok is True

    # 2. Hospital 2 views open requests
    open_reqs = StockService.get_assistance_requests(exclude_hospital_id=str(hosp_2["_id"]))
    matching = [r for r in open_reqs if str(r["_id"]) == req_id]
    assert len(matching) == 1

    # 3. Hospital 2 responds & accepts
    resp_ok, _ = StockService.respond_to_assistance_request(
        request_id=req_id,
        responding_hospital_id=str(hosp_2["_id"]),
        responding_hospital_name=hosp_2["name"],
        user_email="kem.bloodbank@mumbai.gov.in"
    )
    assert resp_ok is True

    # 4. Request status is now Accepted
    updated_req = db.stock_assistance.find_one({"_id": matching[0]["_id"]})
    assert updated_req["status"] == "Accepted"

def test_tamil_nadu_blood_search_and_stock_matching(client):
    """
    Validates:
    1. Searching Tamil Nadu + O Positive returns matching verified hospitals.
    2. Does not show 'No verified centers found'.
    3. Reads live sample values from database: A+ (12 units), O+ (8 units), B+ (5 units).
    """
    db = get_db()
    # Ensure RGGGH hospital exists in DB
    rgggh = db.hospitals.find_one({"name": {"$regex": "Rajiv Gandhi", "$options": "i"}})
    assert rgggh is not None
    assert rgggh["state"] == "Tamil Nadu"
    assert rgggh["status"] == "verified"

    # Search with state=Tamil Nadu and blood_group=O Positive
    results = StockService.search_blood_availability(blood_group="O Positive", state="Tamil Nadu")
    assert len(results) > 0
    h_names = [r["hospital"]["name"] for r in results]
    assert any("Rajiv Gandhi" in name for name in h_names)

    # Check that O+ stock for RGGGH is returned as 8 units
    rgggh_result = next(r for r in results if "Rajiv Gandhi" in r["hospital"]["name"])
    assert rgggh_result["target_stock"] is not None
    assert rgggh_result["target_stock"]["units"] == 8
    assert rgggh_result["stocks"]["A+"]["units"] == 12
    assert rgggh_result["stocks"]["B+"]["units"] == 5

def test_search_reflects_updated_stock_from_database(client):
    """
    Validates:
    When hospital staff updates stock, search results read the new stock from DB
    without any hardcoding.
    """
    db = get_db()
    rgggh = db.hospitals.find_one({"name": {"$regex": "Rajiv Gandhi", "$options": "i"}})
    hid = str(rgggh["_id"])

    # Update O+ units to 35
    ok, msg = StockService.update_stock(
        hospital_id=hid,
        hospital_name=rgggh["name"],
        blood_group="O+",
        units=35,
        reason="Emergency regional camp collection",
        user_email="rgggh.bloodbank@tn.gov.in"
    )
    assert ok is True

    # Search again and verify target_stock has 35 units
    results = StockService.search_blood_availability(blood_group="O+", state="Tamil Nadu")
    rgggh_result = next(r for r in results if str(r["hospital"]["_id"]) == hid)
    assert rgggh_result["target_stock"]["units"] == 35

def test_find_blood_view_endpoint_and_clear_filters(client):
    """
    Validates:
    1. HTTP GET /find-blood?state=Tamil+Nadu&blood_group=O+ returns matching centers.
    2. HTTP GET /find-blood returns all centers without filters.
    3. HTTP GET /find-blood?state=NonExistentState displays 'No Verified Centers Found'.
    """
    # 1. Matching search
    resp = client.get("/find-blood?state=Tamil+Nadu&blood_group=O%2B")
    assert resp.status_code == 200
    html = resp.data.decode("utf-8")
    assert "Rajiv Gandhi" in html
    assert "Available Blood Banks" in html
    assert "Clear" in html

    # 2. Reset / Clear (empty query)
    resp_clear = client.get("/find-blood")
    assert resp_clear.status_code == 200
    html_clear = resp_clear.data.decode("utf-8")
    assert "Rajiv Gandhi" in html_clear
    assert "AIIMS" in html_clear

    # 3. Non-existent location shows No Verified Centers Found
    resp_empty = client.get("/find-blood?state=NonExistentState123")
    assert resp_empty.status_code == 200
    html_empty = resp_empty.data.decode("utf-8")
    assert "No Verified Centers Found" in html_empty

def test_newly_registered_hospital_can_add_and_update_stock(client):
    """
    Validates:
    1. A hospital registers and logs in.
    2. Hospital dashboard shows Manage Blood Stock section.
    3. Hospital can add blood stock (Save Stock) with blood group, units, location, details.
    4. Hospital can update blood stock (Update Stock).
    5. Search reflects the newly added hospital stock.
    """
    # 1. Register hospital
    res_reg = client.post("/register/hospital", data={
        "hospital_name": "Apollo Speciality Blood Center",
        "license_number": "TN-BB-2026-APOLLO",
        "facility_type": "Private",
        "state": "Tamil Nadu",
        "district": "Chennai",
        "address": "21 Greams Lane, Thousand Lights, Chennai - 600006",
        "contact_person": "Dr. V. Ramanathan",
        "email": "apollo.bloodbank@chennai.org",
        "phone": "+91 44 2829 0200",
        "emergency_phone": "+91 44 2829 3333",
        "password": "Hospital@123",
        "confirm_password": "Hospital@123"
    }, follow_redirects=True)
    assert res_reg.status_code == 200

    # 2. Login
    res_login = client.post("/login", data={
        "email": "apollo.bloodbank@chennai.org",
        "password": "Hospital@123"
    }, follow_redirects=True)
    assert res_login.status_code == 200
    assert b"Apollo Speciality Blood Center" in res_login.data
    assert b"Manage Blood Stock" in res_login.data
    assert b"Add Blood Stock" in res_login.data

    # 3. Add Blood Stock (Save Stock)
    res_add = client.post("/hospital/stock", data={
        "blood_group": "B+",
        "units": 18,
        "location": "Cold Vault 3, Chennai",
        "reason": "Voluntary Donation Camp Collection",
        "action_type": "save",
        "redirect_to": "/hospital/dashboard"
    }, follow_redirects=True)
    assert res_add.status_code == 200
    assert b"successfully saved" in res_add.data

    # Verify in DB
    db = get_db()
    hosp = db.hospitals.find_one({"license_number": "TN-BB-2026-APOLLO"})
    assert hosp is not None
    stock_doc = db.blood_stock.find_one({"hospital_id": str(hosp["_id"]), "blood_group": "B+"})
    assert stock_doc is not None
    assert stock_doc["units"] == 18
    assert stock_doc["location"] == "Cold Vault 3, Chennai"

    # 4. Update Stock
    res_upd = client.post("/hospital/stock", data={
        "blood_group": "B+",
        "units": 24,
        "location": "Cold Vault 3, Chennai",
        "reason": "Routine Inventory Adjustment",
        "action_type": "update",
        "redirect_to": "/hospital/dashboard"
    }, follow_redirects=True)
    assert res_upd.status_code == 200
    assert b"successfully updated" in res_upd.data

    stock_doc_upd = db.blood_stock.find_one({"hospital_id": str(hosp["_id"]), "blood_group": "B+"})
    assert stock_doc_upd["units"] == 24

    # 5. Connect to Search: public search finds Apollo Speciality Blood Center with 24 units of B+
    res_search = client.get("/find-blood?state=Tamil+Nadu&blood_group=B%2B")
    assert res_search.status_code == 200
    html_search = res_search.data.decode("utf-8")
    assert "Apollo Speciality Blood Center" in html_search
    assert "24" in html_search
