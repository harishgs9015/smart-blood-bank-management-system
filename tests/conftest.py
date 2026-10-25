import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
import mongomock
from app import create_app
from config import Config
from extensions import db_manager
from seed_data import seed_database

class TestConfig(Config):
    TESTING = True
    SECRET_KEY = "test-secret-key-12345"
    MONGO_URI = ""  # Force demo/in-memory mode for isolated test execution
    DB_NAME = "test_smart_blood_bank"
    WTF_CSRF_ENABLED = False

@pytest.fixture
def app():
    app = create_app(TestConfig)
    with app.app_context():
        # Force re-seed in memory
        seed_database(force=True)
        yield app

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def runner(app):
    return app.test_cli_runner()
