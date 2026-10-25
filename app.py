import os
import logging
from flask import Flask, render_template, session, request, send_from_directory
from werkzeug.middleware.proxy_fix import ProxyFix
from config import Config
from extensions import db_manager, get_db
from models import format_date_display
from seed_data import seed_database

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Enable ProxyFix to respect Cloudflare Tunnel reverse proxy headers (X-Forwarded-Host, X-Forwarded-Proto)
    # This prevents Cloudflare Error 1003 (Direct IP access) by ensuring absolute redirects and url_for stay on https and tunnel domain
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1, x_prefix=1)

    # Initialize MongoDB / In-memory fallback
    db_manager.init_app(app)

    # Auto-seed database if empty
    with app.app_context():
        try:
            seed_database()
        except Exception as e:
            logger.error(f"Auto-seed check error: {e}")

    # Register Blueprints
    from routes.auth_routes import auth_bp
    from routes.public_routes import public_bp
    from routes.donor_routes import donor_bp
    from routes.hospital_routes import hospital_bp
    from routes.admin_routes import admin_bp
    from routes.api_routes import api_bp

    app.register_blueprint(public_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(donor_bp)
    app.register_blueprint(hospital_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(api_bp)

    # Register template filters
    @app.template_filter("format_date")
    def _jinja2_filter_datetime(date_str):
        return format_date_display(date_str)

    from models.stock import normalize_blood_group, get_blood_group_full_name

    @app.template_filter("normalize_bg")
    def _jinja2_filter_normalize_bg(bg):
        return normalize_blood_group(bg)

    @app.template_filter("bg_full_name")
    def _jinja2_filter_bg_full_name(bg):
        return get_blood_group_full_name(bg)

    # Context processors for global template variables
    @app.context_processor
    def inject_global_data():
        user_info = None
        unread_count = 0
        user_id = session.get("user_id")

        if user_id:
            user_info = {
                "id": user_id,
                "donor_id": session.get("donor_id"),
                "hospital_id": session.get("hospital_id"),
                "email": session.get("email"),
                "name": session.get("name"),
                "role": session.get("role"),
                "blood_group": session.get("blood_group"),
                "hospital_name": session.get("hospital_name"),
                "hospital_status": session.get("hospital_status")
            }
            try:
                db = get_db()
                unread_count = db.notifications.count_documents({
                    "user_id": str(user_id),
                    "is_read": False
                })
            except Exception:
                unread_count = 0

        return {
            "current_user": user_info,
            "is_demo_mode": db_manager.is_demo_mode,
            "demo_mode_reason": db_manager.demo_mode_reason,
            "db_connection_str": db_manager.connection_string_masked,
            "unread_notifications_count": unread_count,
            "ALL_BLOOD_GROUPS": Config.BLOOD_GROUPS,
            "BLOOD_GROUP_FULL_NAMES": Config.BLOOD_GROUP_FULL_NAMES,
            "INDIAN_LOCATIONS": Config.INDIAN_LOCATIONS,
            "GOOGLE_MAPS_API_KEY": Config.GOOGLE_MAPS_API_KEY
        }

    # Error Handlers
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template("404.html"), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        logger.error(f"Server 500 error: {e}")
        return render_template("500.html"), 500

    @app.errorhandler(403)
    def forbidden(e):
        return render_template("403.html"), 403

    return app

if __name__ == "__main__":
    app = create_app()
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
