import logging
from extensions import get_db
from models.audit import AuditLogModel

logger = logging.getLogger(__name__)

class AuditService:
    @staticmethod
    def log_action(action, performed_by, role, details, ip_address="127.0.0.1"):
        try:
            db = get_db()
            doc = AuditLogModel.create_log_doc(action, performed_by, role, details, ip_address)
            db.audit_logs.insert_one(doc)
            logger.info(f"AUDIT LOG: [{action}] by {performed_by} ({role})")
            return True
        except Exception as e:
            logger.error(f"Failed to record audit log: {e}")
            return False

    @staticmethod
    def get_recent_logs(limit=50):
        try:
            db = get_db()
            return list(db.audit_logs.find().sort("timestamp", -1).limit(limit))
        except Exception as e:
            logger.error(f"Failed to fetch audit logs: {e}")
            return []
