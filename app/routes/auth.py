"""
Authentication Routes
Handle user login, register, logout using Firebase Auth
"""
from flask import Blueprint, request, jsonify, session, redirect, url_for, flash, render_template
import firebase_admin.auth as fb_auth
from app.utils.firebase_client import verify_id_token, get_firebase_db_module, get_db
from app.utils.auth_middleware import login_required

auth_bp = Blueprint('auth', __name__)

# Secret key to create admin (change this to something secure)
ADMIN_SECRET_KEY = "edulearn_admin_2026"


@auth_bp.route('/create-admin-page')
def create_admin_page():
    """Render create admin page"""
    return render_template('auth/create_admin.html')


@auth_bp.route('/create-admin', methods=['POST'])
def create_admin():
    """
    Create admin account (requires secret key)
    Expected JSON: { "secretKey": "...", "email": "...", "name": "..." }
    """
    data = request.json
    secret_key = data.get('secretKey')
    email = data.get('email')
    name = data.get('name', 'Admin')

    if secret_key != ADMIN_SECRET_KEY:
        return jsonify({'error': 'Invalid secret key'}), 403

    if not email:
        return jsonify({'error': 'Email required'}), 400

    try:
        # Create user in Firebase Auth
        user = fb_auth.create_user(
            email=email,
            email_verified=True,
            display_name=name
        )

        # Save to database with admin role
        db = get_firebase_db_module()
        user_ref = db.reference(f'users/{user.uid}')
        user_ref.set({
            'name': name,
            'email': email,
            'role': 'admin',
            'avatarUrl': '',
            'enrolledCourses': {},
            'createdAt': get_current_timestamp()
        })

        return jsonify({
            'success': True,
            'message': f'Admin created: {email}',
            'uid': user.uid
        })

    except fb_auth.EmailAlreadyExistsError:
        return jsonify({'error': 'Email already exists'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@auth_bp.route('/login', methods=['GET'])
def login_page():
    """Render login page"""
    if 'uid' in session:
        # Already logged in, redirect to dashboard
        role = session.get('role')
        if role == 'admin':
            return redirect(url_for('main.admin_dashboard'))
        elif role == 'instructor':
            return redirect(url_for('main.instructor_dashboard'))
        return redirect(url_for('main.dashboard'))
    return render_template('auth/login.html')


@auth_bp.route('/login', methods=['POST'])
def login():
    """
    Login endpoint - verify Firebase ID Token and create session
    Expected JSON: { "idToken": "firebase_id_token" }
    """
    id_token = request.json.get('idToken')

    if not id_token:
        return jsonify({'error': 'Missing token', 'message': 'Vui lòng cung cấp ID token'}), 400

    try:
        # Verify the Firebase ID token
        decoded_token = verify_id_token(id_token)
        uid = decoded_token['uid']
        email = decoded_token.get('email', '')
        name = decoded_token.get('name', email.split('@')[0] if email else 'User')

        # Get or create user profile from database
        db = get_firebase_db_module()
        user_ref = db.reference(f'users/{uid}')
        user_data = user_ref.get()

        if not user_data:
            # Create new user profile
            user_ref.set({
                'name': name,
                'email': email,
                'role': 'student',
                'avatarUrl': '',
                'enrolledCourses': {},
                'createdAt': get_current_timestamp()
            })
            user_data = user_ref.get()

        # Create Flask session
        session['uid'] = uid
        session['email'] = email
        session['name'] = user_data.get('name', name)
        session['role'] = user_data.get('role', 'student')
        session.permanent = True

        # Determine redirect URL based on role
        role = session['role']
        if role == 'admin':
            redirect_url = url_for('main.admin_dashboard')
        elif role == 'instructor':
            redirect_url = url_for('main.instructor_dashboard')
        else:
            redirect_url = url_for('main.dashboard')

        return jsonify({
            'success': True,
            'role': role,
            'name': session['name'],
            'redirect': redirect_url,
            'message': 'Đăng nhập thành công'
        })

    except Exception as e:
        error_msg = str(e)
        if 'InvalidIdToken' in error_msg or 'invalid' in error_msg.lower():
            return jsonify({'error': 'Invalid token', 'message': 'Token không hợp lệ hoặc đã hết hạn'}), 401
        elif 'ExpiredIdToken' in error_msg or 'expired' in error_msg.lower():
            return jsonify({'error': 'Expired token', 'message': 'Token đã hết hạn, vui lòng đăng nhập lại'}), 401
        return jsonify({'error': 'Login failed', 'message': error_msg}), 500


@auth_bp.route('/register', methods=['GET'])
def register_page():
    """Render registration page"""
    if 'uid' in session:
        role = session.get('role')
        if role == 'admin':
            return redirect(url_for('main.admin_dashboard'))
        elif role == 'instructor':
            return redirect(url_for('main.instructor_dashboard'))
        return redirect(url_for('main.dashboard'))
    return render_template('auth/register.html')


@auth_bp.route('/register', methods=['POST'])
def register():
    """
    Register endpoint - save user profile after Firebase Auth creates account
    Expected JSON: { "idToken": "firebase_id_token", "name": "User Name", "role": "student" }
    """
    id_token = request.json.get('idToken')
    name = request.json.get('name', '')
    role = request.json.get('role', 'student')
    admin_secret = request.json.get('adminSecret', '')

    if not id_token:
        return jsonify({'error': 'Missing token', 'message': 'Vui lòng cung cấp ID token'}), 400

    if not name:
        return jsonify({'error': 'Missing name', 'message': 'Vui lòng nhập tên của bạn'}), 400

    # Validate admin role
    if role == 'admin':
        if admin_secret != ADMIN_SECRET_KEY:
            return jsonify({'error': 'Invalid secret', 'message': 'Mã bảo mật Admin không đúng'}), 403
        role = 'admin'

    try:
        # Verify the Firebase ID token
        decoded_token = verify_id_token(id_token)
        uid = decoded_token['uid']
        email = decoded_token.get('email', '')

        # Save user profile to database
        db = get_firebase_db_module()
        user_ref = db.reference(f'users/{uid}')

        # Check if user already exists
        existing_user = user_ref.get()
        if existing_user:
            return jsonify({'error': 'User exists', 'message': 'Tài khoản đã tồn tại'}), 400

        # Create new user profile
        user_ref.set({
            'name': name,
            'email': email,
            'role': role,
            'avatarUrl': '',
            'enrolledCourses': {},
            'createdAt': get_current_timestamp()
        })

        # Create session
        session['uid'] = uid
        session['email'] = email
        session['name'] = name
        session['role'] = role
        session.permanent = True

        return jsonify({
            'success': True,
            'role': role,
            'name': name,
            'message': 'Đăng ký thành công'
        })

    except fb_auth.InvalidIdTokenError:
        return jsonify({'error': 'Invalid token', 'message': 'Token không hợp lệ'}), 401
    except Exception as e:
        import traceback
        import sys
        # Print to stderr for debugging
        print(f"Registration error: {str(e)}", file=sys.stderr)
        traceback.print_exc()
        return jsonify({'error': 'Registration failed', 'message': str(e)}), 500


@auth_bp.route('/forgot-password')
def forgot_password_page():
    """Render forgot password page"""
    if 'uid' in session:
        return redirect(url_for('main.dashboard'))
    return render_template('auth/forgot_password.html')


@auth_bp.route('/logout')
def logout():
    """Logout endpoint - clear session and redirect to home"""
    session.clear()
    flash('Bạn đã đăng xuất thành công.', 'success')
    return redirect(url_for('auth.login_page'))


@auth_bp.route('/api/logout', methods=['POST'])
def api_logout():
    """API logout endpoint - returns JSON"""
    session.clear()
    return jsonify({'success': True, 'message': 'Đăng xuất thành công'})


@auth_bp.route('/session-login', methods=['POST'])
def session_login():
    """
    Alternative login using session cookie (for SSR)
    Expected JSON: { "idToken": "firebase_id_token" }
    """
    id_token = request.json.get('idToken')

    if not id_token:
        return jsonify({'error': 'Missing token'}), 400

    try:
        decoded_token = verify_id_token(id_token)
        uid = decoded_token['uid']

        # Create session cookie (5 days)
        expires_in = 60 * 60 * 24 * 5
        session_cookie = fb_auth.create_session_cookie(id_token, expires_in=expires_in)

        session['uid'] = uid
        session.permanent = True

        return jsonify({
            'success': True,
            'message': 'Session created'
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 401


@auth_bp.route('/current-user', methods=['GET'])
def current_user():
    """Get current authenticated user info"""
    if 'uid' not in session:
        return jsonify({'authenticated': False}), 401

    return jsonify({
        'authenticated': True,
        'uid': session.get('uid'),
        'email': session.get('email'),
        'name': session.get('name'),
        'role': session.get('role')
    })


@auth_bp.route('/update-profile', methods=['POST'])
@login_required
def update_profile():
    """Update user profile"""
    data = request.json
    uid = session.get('uid')

    if not uid:
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        db = get_db()
        user_ref = db.reference(f'users/{uid}')

        # Fields that can be updated
        updatable_fields = ['name', 'avatarUrl']
        update_data = {}

        for field in updatable_fields:
            if field in data:
                update_data[field] = data[field]

        if update_data:
            user_ref.update(update_data)
            # Update session
            if 'name' in update_data:
                session['name'] = update_data['name']

        return jsonify({
            'success': True,
            'message': 'Cập nhật hồ sơ thành công'
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============== ADMIN ROUTES ==============

@auth_bp.route('/admin/users', methods=['GET'])
@login_required
def admin_list_users():
    """Get all users (admin only)"""
    if session.get('role') != 'admin':
        return jsonify({'error': 'Forbidden', 'message': 'Chỉ admin mới có quyền truy cập'}), 403

    try:
        db = get_db()
        users_ref = db.reference('users')
        users = users_ref.get()

        if not users:
            return jsonify({'users': []})

        user_list = []
        for uid, data in users.items():
            user_list.append({
                'uid': uid,
                'name': data.get('name', ''),
                'email': data.get('email', ''),
                'role': data.get('role', 'student'),
                'avatarUrl': data.get('avatarUrl', ''),
                'createdAt': data.get('createdAt', '')
            })

        return jsonify({'users': user_list})

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@auth_bp.route('/admin/update-user-role', methods=['POST'])
@login_required
def admin_update_user_role():
    """Update user role (admin only)"""
    if session.get('role') != 'admin':
        return jsonify({'error': 'Forbidden', 'message': 'Chỉ admin mới có quyền truy cập'}), 403

    data = request.json
    target_uid = data.get('uid')
    new_role = data.get('role')

    if not target_uid or not new_role:
        return jsonify({'error': 'Missing required fields'}), 400

    if new_role not in ['student', 'instructor', 'admin']:
        return jsonify({'error': 'Invalid role', 'message': 'Vai trò không hợp lệ'}), 400

    try:
        db = get_db()
        user_ref = db.reference(f'users/{target_uid}')
        user_data = user_ref.get()

        if not user_data:
            return jsonify({'error': 'User not found', 'message': 'Không tìm thấy user'}), 404

        user_ref.update({'role': new_role})

        return jsonify({
            'success': True,
            'message': f'Đã cập nhật vai trò thành {new_role}'
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@auth_bp.route('/admin/delete-user', methods=['DELETE'])
@login_required
def admin_delete_user():
    """Delete user (admin only)"""
    if session.get('role') != 'admin':
        return jsonify({'error': 'Forbidden', 'message': 'Chỉ admin mới có quyền truy cập'}), 403

    target_uid = request.json.get('uid')

    if not target_uid:
        return jsonify({'error': 'Missing uid'}), 400

    # Prevent admin from deleting themselves
    if target_uid == session.get('uid'):
        return jsonify({'error': 'Cannot delete yourself'}), 400

    try:
        db = get_db()
        user_ref = db.reference(f'users/{target_uid}')
        user_ref.delete()

        return jsonify({
            'success': True,
            'message': 'Đã xóa user'
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


def get_current_timestamp():
    """Helper function to get current ISO timestamp"""
    from datetime import datetime
    return datetime.utcnow().isoformat() + 'Z'
