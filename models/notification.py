from models import utc_now_iso

class NotificationModel:
    @staticmethod
    def create_notification_doc(user_id, email, title, message, notif_type="system", channel="in_app"):
        return {
            "user_id": str(user_id),
            "email": email.strip().lower(),
            "title": title.strip(),
            "message": message.strip(),
            "type": notif_type,  # 'appointment', 'emergency', 'stock', 'system'
            "channel": channel,  # 'in_app', 'sms', 'email', 'whatsapp'
            "is_read": False,
            "created_at": utc_now_iso()
        }
