from models import utc_now_iso

class AuditLogModel:
    @staticmethod
    def create_log_doc(action, performed_by, role, details, ip_address="127.0.0.1"):
        return {
            "action": action,
            "performed_by": performed_by,
            "role": role,
            "details": details,
            "ip_address": ip_address,
            "timestamp": utc_now_iso()
        }
