import logging
from datetime import datetime, timezone, timedelta
from bson import ObjectId
from extensions import get_db
from models import utc_now_iso
from models.appointment import AppointmentModel
from models.hospital import DEFAULT_TIME_SLOTS
from services.audit_service import AuditService
from services.notification_service import NotificationService
from services.stock_service import StockService

logger = logging.getLogger(__name__)

class AppointmentService:
    @staticmethod
    def get_hospital_slot_availability(hospital_id, date_str):
        """
        Calculates remaining capacity for each slot on the chosen date.
        """
        db = get_db()
        from services.hospital_service import HospitalService
        hospital = HospitalService.get_hospital_by_id(hospital_id)
        if not hospital:
            return None, "Hospital not found."

        slots = hospital.get("available_slots", DEFAULT_TIME_SLOTS)
        capacity_per_slot = hospital.get("daily_slot_capacity", 4)

        # Count active appointments for each slot on this date
        active_appts = list(db.appointments.find({
            "hospital_id": str(hospital["_id"]),
            "slot_date": date_str,
            "status": {"$in": ["pending", "confirmed", "rescheduled"]}
        }))

        slot_counts = {}
        for appt in active_appts:
            s_time = appt.get("slot_time")
            slot_counts[s_time] = slot_counts.get(s_time, 0) + 1

        slot_availability = []
        for s in slots:
            booked = slot_counts.get(s, 0)
            remaining = max(0, capacity_per_slot - booked)
            slot_availability.append({
                "slot_time": s,
                "capacity": capacity_per_slot,
                "booked": booked,
                "remaining": remaining,
                "is_available": remaining > 0
            })

        return slot_availability, "Success"

    @staticmethod
    def book_appointment(donor_id, donor_name, donor_email, donor_phone, donor_blood_group,
                         hospital_id, slot_date, slot_time, is_regular_pledge=False, notes="",
                         ip_address="127.0.0.1", donor_custom_id=None):
        db = get_db()
        from services.hospital_service import HospitalService
        hospital = HospitalService.get_hospital_by_id(hospital_id)
        if not hospital:
            return False, "Selected hospital was not found."

        # Support flexible date format (e.g. YYYY-MM-DD or readable like '25 Oct 2026')
        slot_date = slot_date.strip()
        slot_time = slot_time.strip()

        # Find donor profile if donor_custom_id not passed
        actual_donor_id = donor_custom_id
        if not actual_donor_id:
            prof = db.donor_profiles.find_one({"user_id": str(donor_id)})
            if prof and prof.get("donor_id"):
                actual_donor_id = prof.get("donor_id")
            else:
                actual_donor_id = str(donor_id)

        # Primary hospital_id key (e.g., 'H001')
        actual_hospital_id = hospital.get("hospital_id") or str(hospital["_id"])
        h_keys = list(set([actual_hospital_id, str(hospital["_id"])]))

        # Check if donor already has an active booking on this date for this hospital
        existing_donor_booking = db.appointments.find_one({
            "$and": [
                {"$or": [{"donor_id": str(donor_id)}, {"donor_id": str(actual_donor_id)}, {"donor_user_id": str(donor_id)}]},
                {"$or": [{"slot_date": slot_date}, {"appointment_date": slot_date}]},
                {"hospital_id": {"$in": h_keys}},
                {"status": {"$in": ["Pending", "pending", "Confirmed", "confirmed", "Rescheduled", "rescheduled"]}}
            ]
        })
        if existing_donor_booking:
            ref = existing_donor_booking.get("request_id") or existing_donor_booking.get("booking_reference")
            return False, f"You already have an active request scheduled with {hospital.get('name')} for {slot_date} (Ref: {ref})."

        # Create appointment document
        appt_doc = AppointmentModel.create_appointment_doc(
            donor_id=actual_donor_id,
            donor_name=donor_name,
            donor_email=donor_email,
            donor_phone=donor_phone,
            donor_blood_group=donor_blood_group,
            hospital_id=actual_hospital_id,
            hospital_name=hospital.get("name", "Blood Bank"),
            hospital_district=hospital.get("district", ""),
            hospital_state=hospital.get("state", ""),
            slot_date=slot_date,
            slot_time=slot_time,
            is_regular_pledge=is_regular_pledge,
            notes=notes
        )
        # Also store donor_user_id for user account lookup
        appt_doc["donor_user_id"] = str(donor_id)
        appt_doc["hospital_obj_id"] = str(hospital["_id"])

        res = db.appointments.insert_one(appt_doc)
        booking_ref = appt_doc["request_id"]

        # Audit and notifications
        AuditService.log_action("DONATION_REQUEST_SUBMITTED", donor_email, "donor",
                                f"Donation request sent to {hospital['name']} on {slot_date} at {slot_time}. Ref: {booking_ref}",
                                ip_address)

        # Notify Donor
        NotificationService.send_notification(
            user_id=donor_id,
            email=donor_email,
            title="Donation Request Sent",
            message=f"Donation Request Sent to {hospital['name']} for {slot_date} at {slot_time}. Reference: {booking_ref}. Status: Pending.",
            notif_type="appointment"
        )

        # Notify Hospital
        NotificationService.send_notification(
            user_id=hospital.get("user_id"),
            email=hospital.get("email"),
            title="New Blood Donation Request",
            message=f"New donation request from donor {donor_name} ({donor_blood_group}, ID: {actual_donor_id}) for {slot_date} at {slot_time}. Ref: {booking_ref}.",
            notif_type="appointment"
        )

        return True, appt_doc

    @staticmethod
    def get_donor_appointments(donor_id):
        db = get_db()
        prof = db.donor_profiles.find_one({"$or": [{"user_id": str(donor_id)}, {"donor_id": str(donor_id)}]})
        d_keys = [str(donor_id)]
        if prof:
            if prof.get("donor_id"):
                d_keys.append(str(prof.get("donor_id")))
            if prof.get("user_id"):
                d_keys.append(str(prof.get("user_id")))
        d_keys = list(set([k for k in d_keys if k]))
        return list(db.appointments.find({
            "$or": [
                {"donor_id": {"$in": d_keys}},
                {"donor_user_id": {"$in": d_keys}}
            ]
        }).sort([("created_at", -1), ("slot_date", -1)]))

    @staticmethod
    def get_hospital_appointments(hospital_id, date_filter=None, status_filter=None):
        db = get_db()
        from services.hospital_service import HospitalService
        hospital = HospitalService.get_hospital_by_id(hospital_id)
        h_keys = [str(hospital_id)]
        if hospital:
            h_keys.extend([str(hospital.get("hospital_id")), str(hospital.get("_id"))])
        h_keys = list(set([k for k in h_keys if k]))

        query = {
            "$or": [
                {"hospital_id": {"$in": h_keys}},
                {"hospital_obj_id": {"$in": h_keys}}
            ]
        }
        if date_filter:
            query["$and"] = [{"$or": [{"slot_date": date_filter}, {"appointment_date": date_filter}]}]
        if status_filter:
            query["status"] = {"$regex": f"^{status_filter}$", "$options": "i"}

        return list(db.appointments.find(query).sort([("created_at", -1), ("slot_date", -1)]))

    @staticmethod
    def get_appointment_by_ref(booking_reference):
        db = get_db()
        clean = booking_reference.strip().upper()
        return db.appointments.find_one({
            "$or": [
                {"booking_reference": clean},
                {"request_id": clean}
            ]
        })

    @staticmethod
    def get_appointment_by_id(appointment_id):
        db = get_db()
        if not appointment_id:
            return None
        clean_id = str(appointment_id).strip()
        # 1. By request_id or booking_reference
        appt = db.appointments.find_one({"$or": [{"request_id": clean_id}, {"booking_reference": clean_id}]})
        if appt:
            return appt
        # 2. By ObjectId
        try:
            appt = db.appointments.find_one({"_id": ObjectId(clean_id)})
            if appt:
                return appt
        except Exception:
            pass
        # 3. By raw string _id
        return db.appointments.find_one({"_id": clean_id})

    @staticmethod
    def cancel_appointment(appointment_id, cancelled_by_email, role, reason, ip_address="127.0.0.1"):
        db = get_db()
        appt = AppointmentService.get_appointment_by_id(appointment_id)
        if not appt:
            return False, "Appointment not found."

        now = utc_now_iso()
        status_entry = {
            "status": "Rejected" if role == "hospital" else "Cancelled",
            "timestamp": now,
            "note": f"{'Rejected' if role == 'hospital' else 'Cancelled'} by {role} ({cancelled_by_email}). Reason: {reason}"
        }

        q_id = appt["_id"]
        new_status = "Rejected" if role == "hospital" else "Cancelled"
        db.appointments.update_one({"_id": q_id}, {
            "$set": {
                "status": new_status,
                "cancellation_reason": reason,
                "updated_at": now
            },
            "$push": {
                "status_history": status_entry
            }
        })

        AuditService.log_action("APPOINTMENT_STATUS_CHANGE", cancelled_by_email, role,
                                f"Appointment {appt.get('request_id', appt.get('booking_reference'))} status changed to {new_status}. Reason: {reason}",
                                ip_address)

        NotificationService.send_notification(
            user_id=appt.get("donor_id"),
            email=appt.get("donor_email"),
            title=f"Appointment {new_status}",
            message=f"Your appointment {appt.get('request_id', appt.get('booking_reference'))} for {appt.get('slot_date')} has been {new_status.lower()}. Reason: {reason}.",
            notif_type="appointment"
        )

        return True, f"Appointment status updated to {new_status}."

    @staticmethod
    def reject_appointment(appointment_id, staff_email, reason="Slot unavailable or scheduling conflict", ip_address="127.0.0.1"):
        return AppointmentService.cancel_appointment(appointment_id, staff_email, "hospital", reason, ip_address)

    @staticmethod
    def reschedule_appointment(appointment_id, new_date, new_slot_time, rescheduled_by_email,
                               role="hospital", ip_address="127.0.0.1"):
        db = get_db()
        appt = AppointmentService.get_appointment_by_id(appointment_id)
        if not appt:
            return False, "Appointment not found."

        now = utc_now_iso()
        prev_slot_info = f"{appt.get('slot_date', appt.get('appointment_date'))} at {appt.get('slot_time', appt.get('appointment_time'))}"
        status_entry = {
            "status": "Rescheduled",
            "timestamp": now,
            "note": f"Rescheduled from {prev_slot_info} to {new_date} at {new_slot_time} by {role} ({rescheduled_by_email})."
        }

        q_id = appt["_id"]
        db.appointments.update_one({"_id": q_id}, {
            "$set": {
                "appointment_date": new_date,
                "slot_date": new_date,
                "appointment_time": new_slot_time,
                "slot_time": new_slot_time,
                "rescheduled_from": prev_slot_info,
                "status": "Rescheduled",
                "updated_at": now
            },
            "$push": {
                "status_history": status_entry
            }
        })

        ref = appt.get('request_id', appt.get('booking_reference'))
        AuditService.log_action("APPOINTMENT_RESCHEDULED", rescheduled_by_email, role,
                                f"Appointment {ref} moved to {new_date} at {new_slot_time}",
                                ip_address)

        NotificationService.send_notification(
            user_id=appt.get("donor_id"),
            email=appt.get("donor_email"),
            title="Appointment Rescheduled",
            message=f"Your blood donation appointment {ref} has been rescheduled to {new_date} at {new_slot_time}.",
            notif_type="appointment"
        )

        return True, "Appointment has been successfully rescheduled."

    @staticmethod
    def confirm_appointment(appointment_id, staff_email, ip_address="127.0.0.1"):
        db = get_db()
        appt = AppointmentService.get_appointment_by_id(appointment_id)
        if not appt:
            return False, "Appointment not found."

        now = utc_now_iso()
        q_id = appt["_id"]
        db.appointments.update_one({"_id": q_id}, {
            "$set": {
                "status": "Confirmed",
                "updated_at": now
            },
            "$push": {
                "status_history": {
                    "status": "Confirmed",
                    "timestamp": now,
                    "note": f"Confirmed by hospital staff ({staff_email})."
                }
            }
        })

        ref = appt.get('request_id', appt.get('booking_reference'))
        NotificationService.send_notification(
            user_id=appt.get("donor_id"),
            email=appt.get("donor_email"),
            title="Appointment Confirmed",
            message=f"Good news! Your blood donation appointment ({ref}) at {appt.get('hospital_name')} on {appt.get('slot_date')} at {appt.get('slot_time')} is officially Confirmed.",
            notif_type="appointment"
        )

        return True, "Appointment confirmed."

    @staticmethod
    def record_donation(donor_id, hospital_id, blood_group, donation_date, units_collected, details, staff_email, appointment_id=None, ip_address="127.0.0.1"):
        """
        Implements Section 14:
        After a successful donation, hospital management records:
        - Donor
        - Blood Group
        - Donation Date
        - Units Collected
        - Details
        When saved:
        1. The donation is added to Donation History (db.donations).
        2. The corresponding hospital's blood stock increases.
        3. The donor's donation history is updated.
        4. The record remains linked to the correct donor and hospital.
        """
        db = get_db()
        from services.hospital_service import HospitalService
        from models.donation import DonationModel
        from models.stock import normalize_blood_group

        hospital = HospitalService.get_hospital_by_id(hospital_id)
        h_id_to_store = str(hospital.get("hospital_id", hospital_id)) if hospital else str(hospital_id)
        h_name = hospital.get("name", "Blood Center") if hospital else "Blood Center"
        norm_bg = normalize_blood_group(blood_group)

        try:
            units = max(1, int(units_collected))
        except (ValueError, TypeError):
            units = 1

        # Look up donor name
        donor_name = "Voluntary Donor"
        prof = db.donor_profiles.find_one({"$or": [{"donor_id": str(donor_id)}, {"user_id": str(donor_id)}]})
        if prof:
            u = db.users.find_one({"_id": prof.get("user_id")}) or db.users.find_one({"email": prof.get("user_id")})
            if u:
                donor_name = u.get("name", donor_name)
        else:
            u = db.users.find_one({"_id": str(donor_id)}) or db.users.find_one({"email": str(donor_id)})
            if u:
                donor_name = u.get("name", donor_name)

        # 1. Create donation document in db.donations
        don_doc = DonationModel.create_donation_doc(
            donor_id=donor_id,
            donor_name=donor_name,
            hospital_id=h_id_to_store,
            hospital_name=h_name,
            blood_group=norm_bg,
            donation_date=donation_date,
            units_collected=units,
            details=details,
            recorded_by=staff_email
        )
        db.donations.insert_one(don_doc)

        # 2. Increment hospital blood stock by units_collected
        stocks = StockService.get_hospital_stock(h_id_to_store)
        curr_stock_entry = next((s for s in stocks if s.get("blood_group") == norm_bg), None)
        curr_units = curr_stock_entry.get("available_units", 0) if curr_stock_entry else 0
        new_units = curr_units + units

        StockService.update_stock(
            hospital_id=h_id_to_store,
            hospital_name=h_name,
            blood_group=norm_bg,
            units=new_units,
            reason=f"Donation Collected: {units} unit(s) from {donor_name} ({donor_id}). Details: {details}",
            user_email=staff_email,
            ip_address=ip_address
        )

        # 3. Update donor's profile donation history
        now = utc_now_iso()
        if prof:
            db.donor_profiles.update_one({"_id": prof["_id"]}, {
                "$set": {
                    "last_donation_date": donation_date,
                    "updated_at": now
                },
                "$inc": {"total_donations": units}
            })

        # 4. If linked to an appointment, mark appointment as Completed
        if appointment_id:
            appt = AppointmentService.get_appointment_by_id(appointment_id)
            if appt:
                db.appointments.update_one({"_id": appt["_id"]}, {
                    "$set": {
                        "status": "Completed",
                        "completed_at": now,
                        "volume_ml": units * 350,
                        "updated_at": now
                    },
                    "$push": {
                        "status_history": {
                            "status": "Completed",
                            "timestamp": now,
                            "note": f"Donation recorded: {units} unit(s) collected. Linked donation {don_doc['donation_id']}."
                        }
                    }
                })

        # 5. Audit Log
        AuditService.log_action(
            "DONATION_RECORDED",
            staff_email,
            "hospital",
            f"Recorded {units} unit(s) of {norm_bg} donated by {donor_name} ({donor_id}) at {h_name}. Stock increased to {new_units}.",
            ip_address
        )

        return True, don_doc

    @staticmethod
    def record_donation_completion(appointment_id, donation_bag_id, volume_ml, staff_email, ip_address="127.0.0.1"):
        appt = AppointmentService.get_appointment_by_id(appointment_id)
        if not appt:
            return False, "Appointment not found."

        donor_id = appt.get("donor_id")
        hospital_id = appt.get("hospital_id")
        blood_group = appt.get("blood_group") or appt.get("donor_blood_group")
        date_str = appt.get("slot_date") or appt.get("appointment_date") or utc_now_iso()[:10]
        details = f"Bag #{donation_bag_id}, {volume_ml}ml collected for Appt {appt.get('request_id', appt.get('booking_reference'))}"

        return AppointmentService.record_donation(
            donor_id=donor_id,
            hospital_id=hospital_id,
            blood_group=blood_group,
            donation_date=date_str,
            units_collected=1,
            details=details,
            staff_email=staff_email,
            appointment_id=appointment_id,
            ip_address=ip_address
        )
