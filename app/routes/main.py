"""
Main Routes
Page routes for rendering templates - student, instructor, auth pages
"""
from flask import Blueprint, render_template, redirect, url_for, session, request, flash
from app.utils.auth_middleware import login_required, instructor_required, admin_required
from app.utils.firebase_client import get_db

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    """Home page - list all published courses"""
    return render_template('student/index.html')


@main_bp.route('/dashboard')
@login_required
def dashboard():
    """Student dashboard - enrolled courses and progress"""
    return render_template('student/dashboard.html')


@main_bp.route('/courses')
def courses():
    """All courses page"""
    category = request.args.get('category', '')
    return render_template('student/courses.html', category=category)


@main_bp.route('/course/<course_id>')
@login_required
def course_detail(course_id):
    """Course detail page"""
    return render_template('student/course_detail.html', course_id=course_id)


@main_bp.route('/lesson/<course_id>/<lesson_id>')
@login_required
def lesson_view(course_id, lesson_id):
    """Lesson/video viewing page"""
    return render_template('student/lesson.html', course_id=course_id, lesson_id=lesson_id)


# Instructor routes
@main_bp.route('/instructor')
@main_bp.route('/instructor/dashboard')
@instructor_required
def instructor_dashboard():
    """Instructor dashboard"""
    return render_template('instructor/dashboard.html')


@main_bp.route('/instructor/courses')
@instructor_required
def instructor_courses():
    """Instructor courses management"""
    return render_template('instructor/courses.html')


@main_bp.route('/instructor/course/<course_id>')
@instructor_required
def instructor_course_edit(course_id):
    """Edit course and manage lessons"""
    return render_template('instructor/edit_course.html', course_id=course_id)


@main_bp.route('/instructor/create-course')
@instructor_required
def instructor_create_course():
    """Create new course"""
    return render_template('instructor/create_course.html')


@main_bp.route('/instructor/students')
@instructor_required
def instructor_students():
    """View enrolled students"""
    return render_template('instructor/students.html')


@main_bp.route('/profile')
@login_required
def profile():
    """User profile page"""
    return render_template('student/profile.html')


@main_bp.route('/settings')
@login_required
def settings():
    """User settings page"""
    return render_template('student/settings.html')


# Admin routes
@main_bp.route('/admin')
@main_bp.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    """Admin dashboard"""
    return render_template('admin/dashboard.html')


@main_bp.route('/admin/users')
@admin_required
def admin_users():
    """Admin user management"""
    return render_template('admin/users.html')
