from datetime import datetime, timezone, timedelta
from extensions import get_db
from services.appointment_service import AppointmentService

def test_appointment_booking_and_duplicate_prevention(client):
    db = get_db()
    # Find AIIMS hospital ID and Rahul user ID
    hosp = db.hospitals.find_one({"license_number": "DL-BB-2021-0012"})
    assert hosp is not None
    hosp_id = str(hosp["_id"])

    user = db.users.find_one({"email": "rahul.sharma@gmail.com"})
    donor_id = str(user["_id"])

    target_date = (datetime.now(timezone.utc).date() + timedelta(days=10)).strftime("%Y-%m-%d")
    slot_time = "11:00 AM - 12:00 PM"

    # 1. Book appointment
    success, appt = AppointmentService.book_appointment(
        donor_id=donor_id,
        donor_name="Rahul Sharma",
        donor_email="rahul.sharma@gmail.com",
        donor_phone="+91 98765 43210",
        donor_blood_group="O+",
        hospital_id=hosp_id,
        slot_date=target_date,
        slot_time=slot_time
    )
    assert success is True
    assert appt["booking_reference"].startswith("BD-2026-")
    assert appt["status"] == "pending"

    # 2. Prevent same donor booking again on same date
    dup_success, msg = AppointmentService.book_appointment(
        donor_id=donor_id,
        donor_name="Rahul Sharma",
        donor_email="rahul.sharma@gmail.com",
        donor_phone="+91 98765 43210",
        donor_blood_group="O+",
        hospital_id=hosp_id,
        slot_date=target_date,
        slot_time="02:00 PM - 03:00 PM"
    )
    assert dup_success is False
    assert "already have an active appointment" in msg

def test_slot_capacity_limit_enforcement(client):
    db = get_db()
    hosp = db.hospitals.find_one({"license_number": "DL-BB-2021-0012"})
    hosp_id = str(hosp["_id"])
    capacity = hosp.get("daily_slot_capacity", 5)

    test_date = (datetime.now(timezone.utc).date() + timedelta(days=15)).strftime("%Y-%m-%d")
    test_slot = "09:00 AM - 10:00 AM"

    # Fill the slot up to capacity with simulated unique donors
    for i in range(capacity):
        ok, _ = AppointmentService.book_appointment(
            donor_id=f"donor_test_{i}",
            donor_name=f"Test Donor {i}",
            donor_email=f"donor{i}@test.com",
            donor_phone="+91 90000 00000",
            donor_blood_group="B+",
            hospital_id=hosp_id,
            slot_date=test_date,
            slot_time=test_slot
        )
        assert ok is True

    # Next attempt must be rejected because slot is full
    over_capacity_ok, err_msg = AppointmentService.book_appointment(
        donor_id="donor_overflow",
        donor_name="Overflow Donor",
        donor_email="overflow@test.com",
        donor_phone="+91 90000 00000",
        donor_blood_group="B+",
        hospital_id=hosp_id,
        slot_date=test_date,
        slot_time=test_slot
    )
    assert over_capacity_ok is False
    assert "fully booked" in err_msg

def test_reschedule_cancel_and_completion_lifecycle(client):
    db = get_db()
    hosp = db.hospitals.find_one({"license_number": "DL-BB-2021-0012"})
    hosp_id = str(hosp["_id"])
    user = db.users.find_one({"email": "priya.deshmukh@gmail.com"})
    donor_id = str(user["_id"])

    date_1 = (datetime.now(timezone.utc).date() + timedelta(days=5)).strftime("%Y-%m-%d")
    date_2 = (datetime.now(timezone.utc).date() + timedelta(days=6)).strftime("%Y-%m-%d")

    # 1. Book appointment
    ok, appt = AppointmentService.book_appointment(
        donor_id=donor_id,
        donor_name="Priya Deshmukh",
        donor_email="priya.deshmukh@gmail.com",
        donor_phone="+91 98220 12345",
        donor_blood_group="B+",
        hospital_id=hosp_id,
        slot_date=date_1,
        slot_time="10:00 AM - 11:00 AM"
    )
    assert ok is True
    appt_id = str(appt["_id"])

    # 2. Reschedule
    resch_ok, _ = AppointmentService.reschedule_appointment(
        appointment_id=appt_id,
        new_date=date_2,
        new_slot_time="03:00 PM - 04:00 PM",
        rescheduled_by_email="priya.deshmukh@gmail.com",
        role="donor"
    )
    assert resch_ok is True
    updated = AppointmentService.get_appointment_by_id(appt_id)
    assert updated["status"] == "rescheduled"
    assert updated["slot_date"] == date_2

    # 3. Hospital confirms appointment
    conf_ok, _ = AppointmentService.confirm_appointment(
        appointment_id=appt_id,
        staff_email="aiims.bloodbank@delhi.gov.in"
    )
    assert conf_ok is True
    confirmed = AppointmentService.get_appointment_by_id(appt_id)
    assert confirmed["status"] == "confirmed"

    # 4. Check stock of B+ prior to donation completion
    stock_before = db.blood_stock.find_one({"hospital_id": hosp_id, "blood_group": "B+"})
    initial_units = stock_before.get("units", 0)

    # 5. Complete donation with bag ID & volume
    comp_ok, _ = AppointmentService.record_donation_completion(
        appointment_id=appt_id,
        donation_bag_id="DL-AIIMS-TEST-55",
        volume_ml=450,
        staff_email="aiims.bloodbank@delhi.gov.in"
    )
    assert comp_ok is True

    # 6. Verify completion flags:
    # a) Appointment marked completed
    final_appt = AppointmentService.get_appointment_by_id(appt_id)
    assert final_appt["status"] == "completed"
    assert final_appt["donation_bag_id"] == "DL-AIIMS-TEST-55"

    # b) Hospital stock automatically incremented by 1
    stock_after = db.blood_stock.find_one({"hospital_id": hosp_id, "blood_group": "B+"})
    assert stock_after["units"] == initial_units + 1

    # c) Donor profile last_donation_date updated
    donor_prof = db.donor_profiles.find_one({"user_id": donor_id})
    assert donor_prof["last_donation_date"] == date_2
    assert donor_prof["total_donations"] >= 1
