"""
Authentication Middleware
Decorators for protecting routes and role-based access control
"""
from functools import wraps
from flask import session, jsonify, redirect, url_for, flash


def login_required(f):
    """
    Decorator to require user authentication
    Redirects to login page if user is not authenticated
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'uid' not in session:
            flash('Vui lòng đăng nhập để tiếp tục.', 'warning')
            return redirect(url_for('auth.login_page'))
        return f(*args, **kwargs)
    return decorated_function


def login_required_api(f):
    """
    Decorator for API routes - returns JSON error instead of redirect
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'uid' not in session:
            return jsonify({'error': 'Unauthorized', 'message': 'Vui lòng đăng nhập'}), 401
        return f(*args, **kwargs)
    return decorated_function


def instructor_required(f):
    """
    Decorator to require instructor or admin role
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'uid' not in session:
            flash('Vui lòng đăng nhập để tiếp tục.', 'warning')
            return redirect(url_for('auth.login_page'))

        role = session.get('role')
        if role not in ['instructor', 'admin']:
            flash('Bạn không có quyền truy cập trang này.', 'error')
            return redirect(url_for('main.dashboard'))

        return f(*args, **kwargs)
    return decorated_function


def instructor_required_api(f):
    """
    Decorator for API routes - returns JSON error for instructor check
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'uid' not in session:
            return jsonify({'error': 'Unauthorized', 'message': 'Vui lòng đăng nhập'}), 401

        role = session.get('role')
        if role not in ['instructor', 'admin']:
            return jsonify({'error': 'Forbidden', 'message': 'Bạn không có quyền thực hiện thao tác này'}), 403

        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """
    Decorator to require admin role only
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'uid' not in session:
            flash('Vui lòng đăng nhập để tiếp tục.', 'warning')
            return redirect(url_for('auth.login_page'))

        if session.get('role') != 'admin':
            flash('Bạn không có quyền truy cập trang này.', 'error')
            return redirect(url_for('main.dashboard'))

        return f(*args, **kwargs)
    return decorated_function


def get_current_user():
    """
    Get current authenticated user info from session
    Returns dict with uid, role, name, email
    """
    if 'uid' not in session:
        return None

    return {
        'uid': session.get('uid'),
        'role': session.get('role', 'student'),
        'name': session.get('name', ''),
        'email': session.get('email', '')
    }
