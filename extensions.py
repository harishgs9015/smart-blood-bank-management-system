import logging
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
import mongomock
from config import Config

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self):
        self.client = None
        self.db = None
        self.is_demo_mode = False
        self.demo_mode_reason = ""
        self.connection_string_masked = "Not Configured"

    def init_app(self, app):
        mongo_uri = app.config.get("MONGO_URI", "")
        db_name = app.config.get("DB_NAME", "smart_blood_bank")

        if mongo_uri:
            # Mask credentials for logging and UI display
            try:
                if "@" in mongo_uri:
                    parts = mongo_uri.split("@")
                    prefix = parts[0].split("://")[0] + "://***:***@"
                    self.connection_string_masked = prefix + parts[1].split("?")[0]
                else:
                    self.connection_string_masked = mongo_uri
                
                logger.info(f"Connecting to MongoDB at: {self.connection_string_masked}")
                # Real PyMongo Client with short timeout to prevent blocking if cluster unreachable
                real_client = MongoClient(mongo_uri, serverSelectionTimeoutMS=3000)
                # Test connectivity
                real_client.admin.command("ping")
                self.client = real_client
                self.db = self.client[db_name]
                self.is_demo_mode = False
                logger.info("Successfully connected to live MongoDB Atlas / Server.")
            except (ConnectionFailure, ServerSelectionTimeoutError, Exception) as err:
                logger.warning(f"Failed to connect to live MongoDB ({err}). Falling back to Demo Mode.")
                self.is_demo_mode = True
                self.demo_mode_reason = f"MongoDB connection failed ({str(err)[:80]}...). Using isolated in-memory engine."
                self._init_demo_db(db_name)
        else:
            self.is_demo_mode = True
            self.demo_mode_reason = "MONGO_URI not configured in .env. Running in interactive Demo Mode."
            self._init_demo_db(db_name)

        self._ensure_indexes()

    def _init_demo_db(self, db_name):
        self.client = mongomock.MongoClient()
        self.db = self.client[db_name]

    def _ensure_indexes(self):
        """Create indexes and constraints on collections"""
        try:
            self.db.users.create_index("email", unique=True)
            self.db.hospitals.create_index("license_number", unique=True, sparse=True)
            self.db.appointments.create_index("booking_reference", unique=True)
            self.db.blood_requests.create_index("tracking_code", unique=True)
            self.db.blood_stock.create_index([("hospital_id", 1), ("blood_group", 1)], unique=True)
            self.db.audit_logs.create_index("timestamp")
        except Exception as e:
            logger.warning(f"Index creation notice: {e}")

    def get_db(self):
        return self.db

db_manager = DatabaseManager()

def get_db():
    return db_manager.get_db()
