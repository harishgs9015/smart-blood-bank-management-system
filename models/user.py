from werkzeug.security import generate_password_hash, check_password_hash
from models import utc_now_iso

class UserModel:
    @staticmethod
    def create_user_doc(email, password, role, name, phone=""):
        return {
            "email": email.strip().lower(),
            "password_hash": generate_password_hash(password),
            "role": role,  # 'donor', 'hospital', 'admin'
            "name": name.strip(),
            "phone": phone.strip(),
            "is_active": True,
            "created_at": utc_now_iso(),
            "updated_at": utc_now_iso()
        }

    @staticmethod
    def verify_password(stored_hash, candidate_password):
        return check_password_hash(stored_hash, candidate_password)
