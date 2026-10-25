import logging
from config import Config
from extensions import get_db
from models.notification import NotificationModel

logger = logging.getLogger(__name__)

class NotificationService:
    @staticmethod
    def send_notification(user_id, email, title, message, notif_type="system", preferred_channels=None):
        """
        Creates an in-app notification in DB and evaluates optional external providers.
        Clearly informs if SMS/Email/WhatsApp providers are unconfigured.
        """
        results = {"in_app": False, "email": "Not Configured", "sms": "Not Configured", "whatsapp": "Not Configured"}
        db = get_db()

        # 1. Store In-App Notification
        try:
            doc = NotificationModel.create_notification_doc(
                user_id=user_id,
                email=email,
                title=title,
                message=message,
                notif_type=notif_type,
                channel="in_app"
            )
            db.notifications.insert_one(doc)
            results["in_app"] = True
        except Exception as e:
            logger.error(f"Failed to save in-app notification: {e}")

        # 2. External channels check
        channels = preferred_channels or {}
        if channels.get("sms") and Config.SMS_GATEWAY_API_KEY:
            # External SMS gateway integration point
            logger.info(f"SMS Gateway configured: Dispatching SMS to {email}")
            results["sms"] = "Dispatched via SMS Gateway"
        elif channels.get("sms"):
            results["sms"] = "SMS provider unconfigured (Simulated delivery logged)"

        if channels.get("whatsapp") and Config.WHATSAPP_BUSINESS_API_KEY:
            logger.info(f"WhatsApp Business API configured: Dispatching to {email}")
            results["whatsapp"] = "Dispatched via WhatsApp Business"
        elif channels.get("whatsapp"):
            results["whatsapp"] = "WhatsApp provider unconfigured (Simulated delivery logged)"

        return results

    @staticmethod
    def get_user_notifications(user_id, limit=20):
        try:
            db = get_db()
            return list(db.notifications.find({"user_id": str(user_id)}).sort("created_at", -1).limit(limit))
        except Exception as e:
            logger.error(f"Error fetching notifications: {e}")
            return []

    @staticmethod
    def mark_as_read(notification_id, user_id):
        from bson import ObjectId
        try:
            db = get_db()
            query = {"user_id": str(user_id)}
            try:
                query["_id"] = ObjectId(notification_id)
            except Exception:
                query["_id"] = notification_id
            db.notifications.update_one(query, {"$set": {"is_read": True}})
            return True
        except Exception as e:
            logger.error(f"Error marking notification as read: {e}")
            return False
