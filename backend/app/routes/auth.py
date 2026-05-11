from flask import Blueprint, request, jsonify, current_app, url_for, redirect
from werkzeug.security import generate_password_hash, check_password_hash
import uuid
import re
from .. import db
from ..models import User
from ..email import send_verification_email, send_password_reset_email
from flask_cors import cross_origin
import os
import time
from datetime import datetime, timedelta
import pytz
from ..models.cycle import get_central_time
from sqlalchemy import func
from ..utils.auth import generate_session_token, set_session_cookie, clear_session_cookie
from ..utils.csrf import set_csrf_cookie, clear_csrf_cookie, csrf_protect

auth = Blueprint('auth', __name__)

def get_current_time():
    """Get current time in Central timezone"""
    return get_central_time()

def localize_chicago(naive_dt):
    """Convert naive datetime to Chicago timezone"""
    chicago_tz = pytz.timezone('America/Chicago')
    return chicago_tz.localize(naive_dt)

@auth.route('/register', methods=['POST'])
@cross_origin(origins=[
    "https://wucupid.com",
    "https://www.wucupid.com",
    "http://localhost:3000"
], supports_credentials=True, allow_headers=[
    "Content-Type",
    "X-CSRF-Token",
    "X-Requested-With",
    "baggage",
    "sentry-trace"
])
def register():
    try:
        current_app.logger.info("Received registration request")
        data = request.get_json()
        if not data:
            current_app.logger.error("No JSON data received")
            return jsonify({'message': 'No data provided'}), 400
            
        # Avoid logging full registration payloads (may contain passwords)
        current_app.logger.info(f"Registration request for email={data.get('email', '').strip()}")
        
        # Validate email and password
        email = data.get('email', '').strip()
        password = data.get('password', '')
        
        # Check if email is valid WUSTL email 
        if not email or not re.match(r'.+@wustl\.edu$', email):
            return jsonify({'message': 'Invalid WUSTL email address'}), 400
        
        # Basic email validation (just check if email contains @)
        # if not email or '@' not in email:
        #     return jsonify({'message': 'Invalid email address'}), 400
        
        # Check password length
        if not password or len(password) < 8:
            return jsonify({'message': 'Password must be at least 8 characters long'}), 400
        
        # Check if user already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            # Log information about the existing user
            current_app.logger.info(f"User {email} already exists, verified: {existing_user.is_email_verified}, token: {existing_user.verification_token}")
            return jsonify({'message': 'Email already registered. Try logging in!'}), 400
        
        # Create verification token
        verification_token = str(uuid.uuid4())
        verification_token_expires = get_current_time() + timedelta(hours=24)
        # Avoid logging secrets (token)
        current_app.logger.info(f"REGISTER: Created token for {email}")
        
        # Hash password
        password_hash = generate_password_hash(password, method='pbkdf2:sha256')
        
        # Create new user - EXPLICITLY set verification to False
        new_user = User(
            email=email,
            password_hash=password_hash,
            verification_token=verification_token,
            verification_token_expires=verification_token_expires,
            is_email_verified=False,  # Explicitly set to False
            gender="unspecified"  # Add temporary gender value
        )
        
        # Set verification status directly before saving
        new_user.is_email_verified = False
        
        # Save to database
        db.session.add(new_user)

        # CRITICAL: Flush but don't commit yet to get the ID
        db.session.flush()
        
        # Commit transaction
        db.session.commit()

        # Send verification email
        email_sent, verification_url = send_verification_email(email, verification_token)
        
        # Log the new user creation
        current_app.logger.info(f"REGISTER: Created new user: {email}, verified: {new_user.is_email_verified}")
        
        # Generate a unique tracking ID for this registration session
        tracking_id = f"reg_{int(time.time())}_{verification_token[:8]}"
        current_app.logger.info(f"REGISTER TRACKING [{tracking_id}]: Created user {email}, verified=False")
        
        # Double check DB state by querying again - use a separate query to avoid caching
        check_user = db.session.query(User).filter_by(email=email).first()
        current_app.logger.info(f"REGISTER TRACKING [{tracking_id}]: After commit - User {email}, verified: {check_user.is_email_verified}")
        
        # Explicitly double-check verification status - it MUST be False at this point
        if check_user.is_email_verified:
            current_app.logger.error(f"REGISTER TRACKING [{tracking_id}]: CRITICAL ERROR: User {email} got auto-verified immediately after creation!")
            # Force set it back to False
            check_user.is_email_verified = False
            db.session.commit()
            current_app.logger.info(f"REGISTER TRACKING [{tracking_id}]: Fixed user {email}, now verified: {check_user.is_email_verified}")

        # Check if we're in development mode
        # is_dev = os.environ.get('FLASK_ENV') == 'development'
        
        # Double-check that user's verification status is still False - use a completely fresh query
        db.session.expire_all()  # Clear SQLAlchemy's cache
        user_check = db.session.query(User).filter_by(email=email).first()
        current_app.logger.info(f"REGISTER TRACKING [{tracking_id}]: After email sent - User {email}, verified: {user_check.is_email_verified}")
        
        # Ensure verification is still False
        if user_check.is_email_verified:
            current_app.logger.error(f"REGISTER TRACKING [{tracking_id}]: CRITICAL ERROR: User {email} got auto-verified after email sending!")
            # Force set it back to False
            user_check.is_email_verified = False
            db.session.commit()
            current_app.logger.info(f"REGISTER TRACKING [{tracking_id}]: Fixed user {email} after email, now verified: {user_check.is_email_verified}")
       
        # Schedule a verification check in 20 seconds to detect auto-verification
        def schedule_verification_check():
            import threading
            
            def delayed_check():
                time.sleep(20)  # Wait 20 seconds
                with current_app.app_context():
                    try:
                        # Query with clear cache
                        db.session.expire_all()
                        delayed_user = db.session.query(User).filter_by(email=email).first()
                        current_app.logger.info(f"REGISTER TRACKING [{tracking_id}]: 20-second check - User {email}, verified: {delayed_user.is_email_verified}")
                        
                        if delayed_user.is_email_verified:
                            current_app.logger.error(f"REGISTER TRACKING [{tracking_id}]: AUTO-VERIFICATION DETECTED after 20 seconds!")
                            # Log database status for debugging
                            all_users = User.query.all()
                        for u in all_users:
                            if u.email == email:
                                current_app.logger.error(f"REGISTER TRACKING [{tracking_id}]: User state in DB: email={u.email}, verified={u.is_email_verified}")
                            
                            # Fix the verification status
                            delayed_user.is_email_verified = False
                            db.session.commit()
                            current_app.logger.info(f"REGISTER TRACKING [{tracking_id}]: Reset verification status to FALSE")
                    except Exception as e:
                        current_app.logger.error(f"REGISTER TRACKING [{tracking_id}]: Error in delayed verification check: {str(e)}")
            
            # Start the thread
            thread = threading.Thread(target=delayed_check)
            thread.daemon = True
            thread.start()
        
        # Schedule the verification check
        # schedule_verification_check()

        if not email_sent:
            # Return the verification URL only in development
            return jsonify({
                'message': 'Registration successful, but email sending failed.',
                #'verification_url': verification_url if is_dev else None
            }), 201

        return jsonify({
            'message': 'Registration successful. Please check your email for verification link.',
            # 'verification_url': verification_url if is_dev else None  # Only include in development mode
        }), 201
    
    except Exception as e:
        current_app.logger.error(f"Registration error: {str(e)}")
        import traceback
        current_app.logger.error(traceback.format_exc())
        db.session.rollback()
        return jsonify({'message': f'Registration failed: {str(e)}'}), 500

@auth.route('/verify/<token>', methods=['GET', 'POST'])
def verify_email(token):
    tracking_id = f"verify_{int(time.time())}_{token[:8]}"
    current_app.logger.info(f"VERIFY TRACKING [{tracking_id}]: Received verification request for token: {token}")
    headers = dict(request.headers)
    current_app.logger.info(f"VERIFY TRACKING [{tracking_id}]: Headers: {headers}")
    current_app.logger.info(f"VERIFY TRACKING [{tracking_id}]: IP: {request.remote_addr}")
    
    if not token or len(token) < 10:
        current_app.logger.error(f"VERIFY TRACKING [{tracking_id}]: Invalid token format: {token}")
        # For GET, redirect to frontend with error; for POST, return JSON
        redirect_to = request.args.get("redirect_to", os.environ.get("FRONTEND_URL", "http://localhost:3000"))
        if request.method == 'GET':
            return redirect(f"{redirect_to}?verified=false&message=Invalid%20token%20format")
        return jsonify({'message': 'Invalid token format'}), 400
    
    try:
        # If this is a GET, never perform verification directly; send user to the frontend verify page
        if request.method == 'GET':
            redirect_to = request.args.get("redirect_to", os.environ.get("FRONTEND_URL", "http://localhost:3000"))
            return redirect(f"{redirect_to}/auth/verify?token={token}")

        # Normalize token (handle accidental casing/whitespace)
        token = (token or "").strip()
        token_lower = token.lower()
        # Create an explicit transaction
        with db.session.begin_nested():
            # Check for users with this token
            all_users = User.query.all()
            for u in all_users:
                current_app.logger.info(f"VERIFY TRACKING [{tracking_id}]: Known user {u.email}, verified: {u.is_email_verified}, token: {u.verification_token}")
            
            # Clear session cache
            db.session.expire_all()
            
            # Get the user with this token (case-insensitive match for safety)
            user = User.query.filter(func.lower(User.verification_token) == token_lower).first()
            
            if not user:
                current_app.logger.warning(f"VERIFY TRACKING [{tracking_id}]: No user found with token: {token}")
                redirect_to = request.args.get("redirect_to", os.environ.get("FRONTEND_URL", "http://localhost:3000"))
                if request.method == 'GET':
                    return redirect(f"{redirect_to}?verified=false&message=Invalid%20or%20used%20verification%20link")
                return jsonify({'message': 'Invalid verification token or account already verified'}), 400
            
            current_app.logger.info(f"VERIFY TRACKING [{tracking_id}]: Found user for token {token}: {user.email}, currently verified: {user.is_email_verified}")
            
            # Check if already verified - don't produce an error, just let them know
            if user.is_email_verified:
                current_app.logger.info(f"VERIFY TRACKING [{tracking_id}]: User {user.email} was already verified")
                redirect_to = request.args.get("redirect_to", os.environ.get("FRONTEND_URL", "http://localhost:3000"))
                return redirect(f"{redirect_to}?verified=true")
            
            # Log before verification
            current_app.logger.info(f"VERIFY TRACKING [{tracking_id}]: About to verify user {user.email} with token {token}")
            
            # Check expiry if present (handle naive vs aware datetimes)
            if user.verification_token_expires:
                if isinstance(user.verification_token_expires, datetime) and user.verification_token_expires.tzinfo is None:
                    expiry = localize_chicago(user.verification_token_expires)
                else:
                    expiry = user.verification_token_expires
                if get_current_time() > expiry:
                    current_app.logger.warning(f"VERIFY TRACKING [{tracking_id}]: Token expired for {user.email}")
                    redirect_to = request.args.get("redirect_to", os.environ.get("FRONTEND_URL", "http://localhost:3000"))
                    if request.method == 'GET':
                        return redirect(f"{redirect_to}?verified=false&message=Verification%20token%20expired")
                    return jsonify({'message': 'Verification token has expired. Please request a new verification email.'}), 400

            # Mark as verified and clear token
            user.is_email_verified = True
            user.verification_token = None
            user.verification_token_expires = None
            
            # Log the change
            current_app.logger.info(f"VERIFY TRACKING [{tracking_id}]: Set user {user.email} verified=True and cleared token")
    
        # Commit the transaction
        db.session.commit()
        current_app.logger.info(f"VERIFY TRACKING [{tracking_id}]: Committed verification changes for {user.email}")
        
        # Double check the verification happened with a fresh query
        db.session.expire_all()
        check_user = User.query.filter_by(email=user.email).first()
        current_app.logger.info(f"VERIFY TRACKING [{tracking_id}]: After verification - User {check_user.email}, verified: {check_user.is_email_verified}, token: {check_user.verification_token}")
        
        if not check_user.is_email_verified:
            current_app.logger.error(f"VERIFY TRACKING [{tracking_id}]: VERIFICATION FAILED for {user.email}!")
            # Avoid raw SQL; rely on ORM retry
            user.is_email_verified = True
            user.verification_token = None
            db.session.commit()
        
        # POST: return JSON so frontend can decide navigation; GET path doesn't reach here
        if request.method == 'POST':
            return jsonify({'message': 'Email verified', 'verified': True}), 200
        # Fallback (shouldn't hit): redirect
        redirect_to = request.args.get("redirect_to", os.environ.get("FRONTEND_URL", "http://localhost:3000"))
        current_app.logger.info(f"VERIFY TRACKING [{tracking_id}]: Redirecting verified user {user.email} to {redirect_to}")
        return redirect(f"{redirect_to}?verified=true")
    
    except Exception as e:
        current_app.logger.error(f"VERIFY TRACKING [{tracking_id}]: Error during verification: {str(e)}")
        import traceback
        current_app.logger.error(f"VERIFY TRACKING [{tracking_id}]: {traceback.format_exc()}")
        db.session.rollback()
        
        # Get redirect target even for error case
        redirect_to = request.args.get("redirect_to", os.environ.get("FRONTEND_URL", "http://localhost:3000"))
        return redirect(f"{redirect_to}?verified=false&message={str(e)}")


@auth.route('/login', methods=['POST'])
@cross_origin(origins=[
    "https://wucupid.com",
    "https://www.wucupid.com",
    "http://localhost:3000"
], supports_credentials=True)
def login():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'message': 'No data provided'}), 400
            
        # Get email and password
        email = data.get('email', '').strip()
        password = data.get('password', '')
        
        # Check if email is valid WUSTL email (disabled for testing)
        if not email or not re.match(r'.+@wustl\.edu$', email):
            return jsonify({'message': 'Invalid WUSTL email address'}), 400
        
        # Basic email validation (just check if email contains @)
        # if not email or '@' not in email:
        #     return jsonify({'message': 'Invalid email address'}), 400
        
        # Find user
        user = User.query.filter_by(email=email).first()
        if not user:
            current_app.logger.warning(f"LOGIN: User {email} not found")
            return jsonify({'message': 'Invalid email or password'}), 401
        
        # Log user status
        current_app.logger.info(f"LOGIN: User {email} found, verified: {user.is_email_verified}")
        
        # Check if email is verified
        if not user.is_email_verified:
            current_app.logger.info(f"LOGIN: User {email} attempted login but is not verified")
            return jsonify({'message': 'Email not verified. Please check your inbox for verification link.'}), 401
        
        # Check password
        if not check_password_hash(user.password_hash, password):
            current_app.logger.warning(f"LOGIN: Invalid password for user {email}")
            return jsonify({'message': 'Invalid email or password'}), 401
        
        # Issue session as HttpOnly cookie (extend lifetime to 24h to cover long surveys)
        token = generate_session_token(user_id=user.id, email=user.email, expires_in_seconds=86400)
        resp = jsonify({'message': 'Login successful'})
        set_session_cookie(resp, token, max_age_seconds=86400)
        set_csrf_cookie(resp)
        current_app.logger.info(f"LOGIN: User {email} logged in successfully; session issued")
        return resp, 200
    
    except Exception as e:
        current_app.logger.error(f"Login error: {str(e)}")
        return jsonify({'message': f'Login failed: {str(e)}'}), 500

@auth.route('/forgot-password', methods=['POST'])
@cross_origin(origins=[
    "https://wucupid.com",
    "https://www.wucupid.com",
    "http://localhost:3000"
], supports_credentials=True)
def forgot_password():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'message': 'No data provided'}), 400
            
        email = data.get('email', '').strip()
        
        # Validate email
        if not email or not re.match(r'.+@wustl\.edu$', email):
            return jsonify({'message': 'Invalid WUSTL email address'}), 400
        
        # Find user
        user = User.query.filter_by(email=email).first()
        if not user:
            # Only registered users can reset passwords
            return jsonify({'message': 'Email not found. Please register first.'}), 400
        
        # Generate password reset token
        reset_token = str(uuid.uuid4())
        # Use Chicago time for expiration
        reset_expires = get_current_time() + timedelta(hours=1)  # Token expires in 1 hour
        
        # Update user with reset token
        user.password_reset_token = reset_token
        user.password_reset_expires = reset_expires
        db.session.commit()
        
        # Send password reset email (generic response)
        email_sent = send_password_reset_email(email, reset_token)
        
        # Always return generic response to avoid account enumeration
        if not email_sent:
            current_app.logger.warning("Password reset email dispatch attempted")
        return jsonify({'message': 'If the account exists, you will receive an email with reset instructions.'}), 200
    
    except Exception as e:
        current_app.logger.error(f"Forgot password error: {str(e)}")
        db.session.rollback()
        return jsonify({'message': f'Password reset request failed: {str(e)}'}), 500

@auth.route('/reset-password', methods=['POST'])
@cross_origin(origins=[
    "https://wucupid.com",
    "https://www.wucupid.com",
    "http://localhost:3000"
], supports_credentials=True)
def reset_password():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'message': 'No data provided'}), 400
            
        token = data.get('token', '')
        password = data.get('password', '')
        
        # Validate inputs
        if not token:
            return jsonify({'message': 'Reset token is required'}), 400
            
        if not password or len(password) < 8:
            return jsonify({'message': 'Password must be at least 8 characters long'}), 400
        
        # Find user with valid reset token
        user = User.query.filter_by(password_reset_token=token).first()
        if not user:
            return jsonify({'message': 'Invalid or expired reset token'}), 400
        
        # Check if token has expired - use Chicago time
        if user.password_reset_expires:
            # Ensure the expiry time is timezone-aware in Chicago time
            if isinstance(user.password_reset_expires, datetime) and user.password_reset_expires.tzinfo is None:
                expiry = localize_chicago(user.password_reset_expires)
            else:
                expiry = user.password_reset_expires
                
            if get_current_time() > expiry:
                # Clear expired token
                user.password_reset_token = None
                user.password_reset_expires = None
                db.session.commit()
                return jsonify({'message': 'Reset token has expired. Please request a new password reset.'}), 400
        
        # Update password
        user.password_hash = generate_password_hash(password, method='pbkdf2:sha256')
        # Clear reset token after successful reset
        user.password_reset_token = None
        user.password_reset_expires = None
        
        db.session.commit()
        
        current_app.logger.info(f"Password successfully reset for user {user.email}")
        return jsonify({'message': 'Password successfully updated'}), 200
    
    except Exception as e:
        current_app.logger.error(f"Reset password error: {str(e)}")
        db.session.rollback()
        return jsonify({'message': f'Password reset failed: {str(e)}'}), 500

@auth.route('/logout', methods=['POST'])
@cross_origin(origins=[
    "https://wucupid.com",
    "https://www.wucupid.com",
    "http://localhost:3000"
], supports_credentials=True)
@csrf_protect
def logout():
    resp = jsonify({'message': 'Logged out'})
    clear_session_cookie(resp)
    clear_csrf_cookie(resp)
    return resp, 200

# Debug endpoint removed in production for security reasons

@auth.route('/csrf', methods=['GET'])
@cross_origin(origins=[
    "https://wucupid.com",
    "https://www.wucupid.com",
    "http://localhost:3000"
], supports_credentials=True)
def get_csrf():
    resp = jsonify({"message": "ok"})
    set_csrf_cookie(resp)
    return resp, 200
