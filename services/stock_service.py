import logging
import re
import uuid
from bson import ObjectId
from extensions import get_db
from models import utc_now_iso
from models.stock import BLOOD_GROUPS, BloodStockModel, get_stock_status, normalize_blood_group, get_blood_group_full_name
from services.audit_service import AuditService

logger = logging.getLogger(__name__)

class StockService:
    @staticmethod
    def get_hospital_stock(hospital_id):
        db = get_db()
        from services.hospital_service import HospitalService
        hospital = HospitalService.get_hospital_by_id(hospital_id)
        h_keys = [str(hospital_id)]
        if hospital:
            h_keys.extend([str(hospital.get("hospital_id")), str(hospital.get("_id"))])
        h_keys = list(set([k for k in h_keys if k]))

        stocks = list(db.blood_stock.find({"hospital_id": {"$in": h_keys}}))
        # Ensure all 9 blood groups exist in the map
        stock_map = {}
        for s in stocks:
            bg_norm = normalize_blood_group(s.get("blood_group"))
            stock_map[bg_norm] = s

        full_list = []
        for bg in BLOOD_GROUPS:
            if bg in stock_map:
                s = stock_map[bg]
                u = s.get("available_units", s.get("units", 0))
                min_req = s.get("minimum_required", 10)
                status = get_stock_status(u, min_req)
                s["available_units"] = u
                s["units"] = u
                s["minimum_required"] = min_req
                s["status"] = status
                full_list.append(s)
            else:
                full_list.append({
                    "hospital_id": str(hospital.get("hospital_id", hospital_id) if hospital else hospital_id),
                    "blood_group": bg,
                    "available_units": 0,
                    "units": 0,
                    "minimum_required": 10,
                    "status": "Critical",
                    "location": hospital.get("address", "") if hospital else "",
                    "details": "Initial Inventory Record",
                    "last_updated": "Never",
                    "updated_by": "System"
                })
        return full_list

    @staticmethod
    def update_stock(hospital_id, hospital_name, blood_group, units, reason, user_email, ip_address="127.0.0.1", location="", minimum_required=None):
        db = get_db()
        units = max(0, int(units))
        norm_bg = normalize_blood_group(blood_group)

        from services.hospital_service import HospitalService
        hospital = HospitalService.get_hospital_by_id(hospital_id)
        h_id_to_store = str(hospital.get("hospital_id", hospital_id)) if hospital else str(hospital_id)
        h_keys = list(set([h_id_to_store, str(hospital_id), str(hospital.get("_id")) if hospital else ""]))
        h_keys = [k for k in h_keys if k]

        # Get existing stock
        existing = db.blood_stock.find_one({"hospital_id": {"$in": h_keys}, "blood_group": norm_bg})
        old_units = existing.get("available_units", existing.get("units", 0)) if existing else 0
        min_req = int(minimum_required) if minimum_required is not None else (existing.get("minimum_required", 10) if existing else 10)

        status = get_stock_status(units, min_req)
        now = utc_now_iso()
        set_data = {
            "hospital_id": h_id_to_store,
            "hospital_name": hospital_name or (hospital.get("name") if hospital else "Blood Center"),
            "blood_group": norm_bg,
            "available_units": units,
            "units": units,
            "minimum_required": min_req,
            "status": status,
            "details": reason,
            "last_updated": now,
            "updated_by": user_email
        }
        if location and location.strip():
            set_data["location"] = location.strip()
        elif existing and existing.get("location"):
            set_data["location"] = existing.get("location")

        db.blood_stock.update_one(
            {"hospital_id": {"$in": h_keys}, "blood_group": norm_bg},
            {
                "$set": set_data,
                "$setOnInsert": {"created_at": now, "stock_id": f"STK-{uuid.uuid4().hex[:6].upper()}"}
            },
            upsert=True
        )

        # Record in audit log
        diff_str = f"{old_units} -> {units} ({'+' if units >= old_units else ''}{units - old_units})"
        AuditService.log_action(
            "STOCK_UPDATE",
            user_email,
            "hospital",
            f"Stock changed for {hospital_name} [{norm_bg}]: {diff_str}. Minimum Required: {min_req}. Status: {status}. Details: {reason}",
            ip_address
        )

        return True, f"Blood stock for {norm_bg} saved successfully ({units} units, Status: {status})."

    @staticmethod
    def get_blood_group_details(hospital_id, blood_group):
        """
        Retrieves complete information for a specific blood group at this hospital:
        - Blood Group
        - Current Stock
        - Minimum Required Level
        - Automatically calculated Status
        - Donors for that blood group
        - Donation History (scrollable)
        """
        db = get_db()
        from services.hospital_service import HospitalService
        hospital = HospitalService.get_hospital_by_id(hospital_id)
        norm_bg = normalize_blood_group(blood_group)

        h_keys = [str(hospital_id)]
        if hospital:
            h_keys.extend([str(hospital.get("hospital_id")), str(hospital.get("_id"))])
        h_keys = list(set([k for k in h_keys if k]))

        stock_doc = db.blood_stock.find_one({"hospital_id": {"$in": h_keys}, "blood_group": norm_bg})
        if not stock_doc:
            stock_doc = {
                "hospital_id": str(hospital.get("hospital_id", hospital_id) if hospital else hospital_id),
                "hospital_name": hospital.get("name") if hospital else "Blood Center",
                "blood_group": norm_bg,
                "available_units": 0,
                "units": 0,
                "minimum_required": 10,
                "status": "Critical",
                "details": "No stock record yet",
                "last_updated": "Never"
            }

        curr_stock = stock_doc.get("available_units", stock_doc.get("units", 0))
        min_req = stock_doc.get("minimum_required", 10)
        status = get_stock_status(curr_stock, min_req)
        stock_doc["status"] = status
        stock_doc["available_units"] = curr_stock
        stock_doc["minimum_required"] = min_req

        # Donors matching this blood group:
        # Include donors connected to this hospital, or registered voluntary donors in district/platform
        hospital_donors = HospitalService.get_hospital_donors(hospital_id)
        connected_donors_bg = [d for d in hospital_donors if normalize_blood_group(d.get("blood_group")) == norm_bg]

        # Also get other registered voluntary donors with this blood group for emergency reachout
        other_profiles = list(db.donor_profiles.find({"blood_group": norm_bg}).limit(10))
        all_donors_map = {d.get("donor_id"): d for d in connected_donors_bg}
        for p in other_profiles:
            did = p.get("donor_id") or p.get("user_id")
            if did not in all_donors_map:
                u = db.users.find_one({"_id": p.get("user_id")}) or db.users.find_one({"email": p.get("user_id")})
                all_donors_map[did] = {
                    "donor_id": p.get("donor_id", f"D{did[:4] if did else '001'}"),
                    "name": u.get("name") if u else "Registered Voluntary Donor",
                    "blood_group": norm_bg,
                    "contact": (u.get("phone") if u else "") or p.get("phone", "Confidential"),
                    "location": f"{p.get('district', '')}, {p.get('state', '')}".strip(", ") or "Tamil Nadu",
                    "donation_history_count": p.get("total_donations", 0),
                    "last_donation_date": p.get("last_donation_date") or "None"
                }

        # Donation History for this hospital & blood group (scrollable)
        donations = list(db.donations.find({
            "hospital_id": {"$in": h_keys},
            "blood_group": norm_bg
        }).sort("donation_date", -1))

        # Also include completed appointments if any were recorded before
        comp_appts = list(db.appointments.find({
            "hospital_id": {"$in": h_keys},
            "status": {"$in": ["completed", "Completed"]},
            "$or": [{"blood_group": norm_bg}, {"donor_blood_group": norm_bg}]
        }))

        don_history_combined = []
        for d in donations:
            don_history_combined.append({
                "donation_id": d.get("donation_id", f"DON-{d.get('_id')}"),
                "donor_id": d.get("donor_id", "D001"),
                "donor_name": d.get("donor_name", "Voluntary Donor"),
                "blood_group": norm_bg,
                "donation_date": d.get("donation_date", "Recent"),
                "units_collected": d.get("units_collected", 1),
                "details": d.get("details", "Voluntary Donation")
            })

        for a in comp_appts:
            if not any(dh["donor_id"] == a.get("donor_id") and dh["donation_date"] == a.get("slot_date") for dh in don_history_combined):
                don_history_combined.append({
                    "donation_id": a.get("booking_reference") or a.get("request_id", "DON-APPT"),
                    "donor_id": a.get("donor_id", "D001"),
                    "donor_name": a.get("donor_name", "Voluntary Donor"),
                    "blood_group": norm_bg,
                    "donation_date": a.get("appointment_date") or a.get("slot_date", "Recent"),
                    "units_collected": 1,
                    "details": f"Appointment Completed (Bag #{a.get('donation_bag_id', 'Routine')})"
                })

        return {
            "hospital": hospital,
            "stock": stock_doc,
            "blood_group": norm_bg,
            "available_units": curr_stock,
            "minimum_required": min_req,
            "status": status,
            "donors": list(all_donors_map.values()),
            "donation_history": don_history_combined
        }

    @staticmethod
    def search_blood_availability(blood_group=None, state=None, district=None):
        """
        Public directory search for blood availability across verified and registered hospitals.
        Reads live inventory quantities directly from db.blood_stock without hardcoding.
        """
        db = get_db()
        norm_bg = normalize_blood_group(blood_group) if blood_group else None

        # Guarantee Tamil Nadu regional hospitals exist in DB if state is Tamil Nadu
        if state and "tamil nadu" in state.strip().lower():
            if db.hospitals.count_documents({"state": {"$regex": "^Tamil Nadu$", "$options": "i"}, "status": "verified"}) == 0:
                try:
                    from seed_data import ensure_tamil_nadu_and_regional_hospitals
                    ensure_tamil_nadu_and_regional_hospitals(db)
                except Exception as e:
                    logger.error(f"Error ensuring Tamil Nadu hospitals: {e}")

        # Find hospitals matching location (both verified and registered centers)
        h_query = {"status": {"$in": ["verified", "pending_verification"]}}
        if state and state.strip():
            # Robust case-insensitive exact matching
            h_query["state"] = {"$regex": f"^{re.escape(state.strip())}$", "$options": "i"}
        if district and district.strip():
            h_query["district"] = {"$regex": f"^{re.escape(district.strip())}$", "$options": "i"}

        hospitals = list(db.hospitals.find(h_query).sort("name", 1))
        if not hospitals:
            return []

        hospital_ids = [str(h["_id"]) for h in hospitals]
        query_ids = list(set(hospital_ids + [h["_id"] for h in hospitals if isinstance(h["_id"], ObjectId)]))

        # Retrieve ALL blood stocks for these hospitals from db.blood_stock
        stocks = list(db.blood_stock.find({"hospital_id": {"$in": query_ids}}))
        stock_lookup = {}
        for s in stocks:
            hid = str(s.get("hospital_id"))
            bg = s.get("blood_group")
            if hid not in stock_lookup:
                stock_lookup[hid] = {}
            stock_lookup[hid][bg] = s

        # Build combined directory results
        results = []
        for h in hospitals:
            hid = str(h["_id"])
            h_stocks = stock_lookup.get(hid, {})

            # Ensure every standard blood group has an entry with live database units
            formatted_stocks = {}
            for bg in BLOOD_GROUPS:
                if bg in h_stocks:
                    formatted_stocks[bg] = h_stocks[bg]
                else:
                    formatted_stocks[bg] = {
                        "hospital_id": hid,
                        "blood_group": bg,
                        "units": 0,
                        "status": "Critical",
                        "last_updated": "Never"
                    }

            target_stock = formatted_stocks.get(norm_bg) if norm_bg else None

            results.append({
                "hospital": h,
                "stocks": formatted_stocks,
                "target_stock": target_stock,
                "selected_blood_group": norm_bg
            })

        # Sort verified centers with available units first
        def _sort_key(item):
            is_verified = 1 if item["hospital"].get("status") == "verified" else 0
            units = item["target_stock"].get("units", 0) if item.get("target_stock") else 0
            return (is_verified, units)

        if norm_bg:
            results.sort(key=_sort_key, reverse=True)
        else:
            results.sort(key=lambda x: (1 if x["hospital"].get("status") == "verified" else 0), reverse=True)

        return results

    @staticmethod
    def get_stock_alerts_for_hospital(hospital_id):
        """Returns blood groups that are in Critical or Low stock"""
        db = get_db()
        return list(db.blood_stock.find({
            "hospital_id": str(hospital_id),
            "units": {"$lte": 7}
        }))

    # Hospital-to-Hospital Stock Assistance
    @staticmethod
    def create_assistance_request(requesting_hospital_id, requesting_hospital_name,
                                  blood_group, units_needed, urgency, reason, user_email):
        db = get_db()
        doc = BloodStockModel.create_assistance_request_doc(
            requesting_hospital_id=requesting_hospital_id,
            requesting_hospital_name=requesting_hospital_name,
            blood_group=blood_group,
            units_needed=units_needed,
            urgency=urgency,
            reason=reason
        )
        res = db.stock_assistance.insert_one(doc)
        AuditService.log_action("ASSISTANCE_REQUESTED", user_email, "hospital",
                                f"{requesting_hospital_name} requested {units_needed} units of {blood_group}")
        return True, str(res.inserted_id)

    @staticmethod
    def get_assistance_requests(exclude_hospital_id=None, status="Open"):
        db = get_db()
        query = {"status": status}
        if exclude_hospital_id:
            query["requesting_hospital_id"] = {"$ne": str(exclude_hospital_id)}
        return list(db.stock_assistance.find(query).sort("created_at", -1))

    @staticmethod
    def respond_to_assistance_request(request_id, responding_hospital_id, responding_hospital_name, user_email):
        db = get_db()
        try:
            query = {"_id": ObjectId(request_id)}
        except Exception:
            query = {"_id": request_id}

        req = db.stock_assistance.find_one(query)
        if not req:
            return False, "Assistance request not found."

        db.stock_assistance.update_one(query, {
            "$set": {
                "status": "Accepted",
                "accepted_by_hospital_id": str(responding_hospital_id),
                "accepted_by_hospital_name": responding_hospital_name,
                "updated_at": utc_now_iso()
            }
        })

        AuditService.log_action("ASSISTANCE_ACCEPTED", user_email, "hospital",
                                f"{responding_hospital_name} accepted inter-hospital assistance request for {req.get('blood_group')}")
        return True, "Assistance request accepted. Coordinate unit transfer with the requesting center."
