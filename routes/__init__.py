from functools import wraps
from flask import session, redirect, url_for, flash, request

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("user_id"):
            flash("Please sign in to access this page.", "warning")
            return redirect(url_for("auth.login", next=request.path))
        return f(*args, **kwargs)
    return decorated_function

def role_required(allowed_roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not session.get("user_id"):
                flash("Please sign in to continue.", "warning")
                return redirect(url_for("auth.login", next=request.path))
            
            user_role = session.get("role")
            if user_role not in allowed_roles:
                flash("Access denied. You do not have permission to view this resource.", "danger")
                if user_role == "donor":
                    return redirect(url_for("donor.dashboard"))
                elif user_role == "hospital":
                    return redirect(url_for("hospital.dashboard"))
                elif user_role == "admin":
                    return redirect(url_for("admin.dashboard"))
                return redirect(url_for("public.index"))
            return f(*args, **kwargs)
        return decorated_function
    return decorator
