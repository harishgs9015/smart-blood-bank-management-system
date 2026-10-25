from extensions import DatabaseManager
from flask import Flask

def test_mongodb_connection_failure_and_graceful_recovery():
    app = Flask(__name__)
    # Configure an unreachable MongoDB URI
    app.config["MONGO_URI"] = "mongodb://nonexistent.cluster.mongodb.net:27017/?serverSelectionTimeoutMS=500"
    app.config["DB_NAME"] = "test_failover_db"

    mgr = DatabaseManager()
    # Initializing app should NOT throw unhandled exception or crash
    mgr.init_app(app)

    # Must have fallen back to demo mode gracefully
    assert mgr.is_demo_mode is True
    assert "failed" in mgr.demo_mode_reason.lower() or "isolated" in mgr.demo_mode_reason.lower()

    # The database instance must be functional (mongomock fallback)
    db = mgr.get_db()
    assert db is not None

    # Test that standard operations work seamlessly on the fallback database
    res = db.users.insert_one({"email": "test@fallback.org", "name": "Failover User"})
    assert res.inserted_id is not None

    doc = db.users.find_one({"email": "test@fallback.org"})
    assert doc is not None
    assert doc["name"] == "Failover User"
