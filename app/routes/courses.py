"""
Course Management Routes
CRUD operations for courses - create, read, update, delete, enroll
"""
from flask import Blueprint, request, jsonify, session, redirect, url_for, flash, render_template
from datetime import datetime
from app.utils.firebase_client import get_db
from app.utils.auth_middleware import login_required, login_required_api, instructor_required, instructor_required_api

courses_bp = Blueprint('courses', __name__)


@courses_bp.route('/', methods=['GET'])
def list_courses():
    """
    Get all courses - public endpoint
    Query params: category, limit, offset
    """
    try:
        db = get_db()
        courses_ref = db.reference('courses')
        courses = courses_ref.get() or {}

        # Convert to list and filter
        course_list = []
        category = request.args.get('category', '').lower()

        for course_id, course_data in courses.items():
            # Only show published courses for public listing
            if course_data.get('isPublished', False):
                if category and course_data.get('category', '').lower() != category:
                    continue

                course_data['id'] = course_id
                # Get instructor name
                instructor_id = course_data.get('instructorId', '')
                if instructor_id:
                    user_ref = db.reference(f'users/{instructor_id}')
                    user_data = user_ref.get()
                    if user_data:
                        course_data['instructorName'] = user_data.get('name', 'Giảng viên')
                # Count enrolled students
                enrolled = course_data.get('enrolledCount', 0)
                course_data['enrolledCount'] = enrolled
                course_list.append(course_data)

        # Sort by created date (newest first)
        course_list.sort(key=lambda x: x.get('createdAt', ''), reverse=True)

        # Pagination
        limit = int(request.args.get('limit', 50))
        offset = int(request.args.get('offset', 0))
        total = len(course_list)
        course_list = course_list[offset:offset + limit]

        return jsonify({
            'success': True,
            'courses': course_list,
            'total': total,
            'limit': limit,
            'offset': offset
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@courses_bp.route('/<course_id>', methods=['GET'])
def get_course(course_id):
    """
    Get course details by ID
    Returns course info with lessons list
    """
    try:
        db = get_db()

        # Get course
        course_ref = db.reference(f'courses/{course_id}')
        course = course_ref.get()

        if not course:
            return jsonify({'error': 'Course not found', 'message': 'Khóa học không tồn tại'}), 404

        # Get instructor info
        instructor_id = course.get('instructorId', '')
        if instructor_id:
            user_ref = db.reference(f'users/{instructor_id}')
            user_data = user_ref.get()
            if user_data:
                course['instructorName'] = user_data.get('name', 'Giảng viên')
                course['instructorAvatar'] = user_data.get('avatarUrl', '')

        # Get lessons
        lessons_ref = db.reference(f'courses/{course_id}/lessons')
        lessons = lessons_ref.get() or {}

        lessons_list = []
        for lesson_id, lesson_data in lessons.items():
            lesson_data['id'] = lesson_id
            lessons_list.append(lesson_data)

        # Sort by order
        lessons_list.sort(key=lambda x: x.get('order', 0))

        course['lessons'] = lessons_list
        course['totalLessons'] = len(lessons_list)
        course['id'] = course_id

        return jsonify({
            'success': True,
            'course': course
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@courses_bp.route('/my-courses', methods=['GET'])
@login_required_api
def get_my_courses():
    """
    Get courses for current user
    - For students: enrolled courses
    - For instructors: created courses
    """
    try:
        uid = session.get('uid')
        role = session.get('role')
        db = get_db()

        if role in ['instructor', 'admin']:
            # Get courses created by this instructor
            courses_ref = db.reference('courses')
            all_courses = courses_ref.get() or {}

            my_courses = []
            for course_id, course_data in all_courses.items():
                if course_data.get('instructorId') == uid:
                    course_data['id'] = course_id
                    my_courses.append(course_data)

            my_courses.sort(key=lambda x: x.get('createdAt', ''), reverse=True)

            return jsonify({
                'success': True,
                'courses': my_courses,
                'type': 'created'
            })
        else:
            # Get enrolled courses for students
            user_ref = db.reference(f'users/{uid}')
            user_data = user_ref.get() or {}
            enrolled = user_data.get('enrolledCourses', {})

            enrolled_courses = []
            for course_id, _ in enrolled.items():
                course_ref = db.reference(f'courses/{course_id}')
                course = course_ref.get()
                if course:
                    course['id'] = course_id
                    # Get progress
                    progress_ref = db.reference(f'progress/{uid}/{course_id}')
                    progress = progress_ref.get() or {}
                    course['progress'] = progress.get('percentage', 0)
                    enrolled_courses.append(course)

            return jsonify({
                'success': True,
                'courses': enrolled_courses,
                'type': 'enrolled'
            })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@courses_bp.route('/create', methods=['GET'])
@instructor_required
def create_course_page():
    """Render create course page"""
    return render_template('instructor/create_course.html')


@courses_bp.route('/create', methods=['POST'])
@instructor_required_api
def create_course():
    """
    Create a new course (instructor only)
    Expected JSON: { "title", "description", "category", "thumbnail" }
    """
    try:
        data = request.json
        uid = session.get('uid')

        # Validate required fields
        if not data.get('title'):
            return jsonify({'error': 'Missing title', 'message': 'Vui lòng nhập tên khóa học'}), 400

        db = get_db()
        courses_ref = db.reference('courses')

        # Create new course
        new_course = courses_ref.push({
            'title': data.get('title'),
            'description': data.get('description', ''),
            'category': data.get('category', 'general'),
            'thumbnail': data.get('thumbnail', ''),
            'instructorId': uid,
            'isPublished': False,  # Draft by default
            'enrolledCount': 0,
            'createdAt': datetime.utcnow().isoformat() + 'Z',
            'updatedAt': datetime.utcnow().isoformat() + 'Z'
        })

        course_id = new_course.key

        return jsonify({
            'success': True,
            'courseId': course_id,
            'message': 'Tạo khóa học thành công'
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@courses_bp.route('/<course_id>/update', methods=['PUT'])
@instructor_required_api
def update_course(course_id):
    """
    Update course information
    Expected JSON: { "title", "description", "category", "thumbnail", "isPublished" }
    """
    try:
        uid = session.get('uid')
        data = request.json
        db = get_db()

        # Check if course exists
        course_ref = db.reference(f'courses/{course_id}')
        course = course_ref.get()

        if not course:
            return jsonify({'error': 'Course not found'}), 404

        # Check ownership
        if course.get('instructorId') != uid and session.get('role') != 'admin':
            return jsonify({'error': 'Forbidden', 'message': 'Bạn không có quyền cập nhật khóa học này'}), 403

        # Build update data
        updatable_fields = ['title', 'description', 'category', 'thumbnail', 'isPublished']
        update_data = {}

        for field in updatable_fields:
            if field in data:
                update_data[field] = data[field]

        update_data['updatedAt'] = datetime.utcnow().isoformat() + 'Z'

        # Update course
        course_ref.update(update_data)

        return jsonify({
            'success': True,
            'message': 'Cập nhật khóa học thành công'
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@courses_bp.route('/<course_id>/delete', methods=['DELETE'])
@instructor_required_api
def delete_course(course_id):
    """
    Delete a course (instructor or admin only)
    """
    try:
        uid = session.get('uid')
        db = get_db()

        # Check if course exists
        course_ref = db.reference(f'courses/{course_id}')
        course = course_ref.get()

        if not course:
            return jsonify({'error': 'Course not found'}), 404

        # Check ownership or admin
        if course.get('instructorId') != uid and session.get('role') != 'admin':
            return jsonify({'error': 'Forbidden', 'message': 'Bạn không có quyền xóa khóa học này'}), 403

        # Delete course and all its lessons
        course_ref.delete()

        # Also delete lessons
        lessons_ref = db.reference(f'courses/{course_id}/lessons')
        lessons_ref.delete()

        return jsonify({
            'success': True,
            'message': 'Xóa khóa học thành công'
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@courses_bp.route('/<course_id>/enroll', methods=['POST'])
@login_required_api
def enroll_course(course_id):
    """
    Enroll in a course
    """
    try:
        uid = session.get('uid')
        db = get_db()

        # Check if course exists
        course_ref = db.reference(f'courses/{course_id}')
        course = course_ref.get()

        if not course:
            return jsonify({'error': 'Course not found', 'message': 'Khóa học không tồn tại'}), 404

        # Check if already enrolled
        user_ref = db.reference(f'users/{uid}')
        user_data = user_ref.get() or {}
        enrolled = user_data.get('enrolledCourses', {})

        if course_id in enrolled:
            return jsonify({'error': 'Already enrolled', 'message': 'Bạn đã đăng ký khóa học này'}), 400

        # Enroll user
        db.reference(f'users/{uid}/enrolledCourses/{course_id}').set({
            'enrolledAt': datetime.utcnow().isoformat() + 'Z'
        })

        # Increment enrolled count
        current_count = course.get('enrolledCount', 0)
        course_ref.update({'enrolledCount': current_count + 1})

        # Initialize progress for this course
        lessons_ref = db.reference(f'courses/{course_id}/lessons')
        lessons = lessons_ref.get() or {}
        total_lessons = len(lessons)

        db.reference(f'progress/{uid}/{course_id}').set({
            'percentage': 0,
            'completedLessons': {},
            'lastWatched': None,
            'lastPosition': 0,
            'totalLessons': total_lessons,
            'enrolledAt': datetime.utcnow().isoformat() + 'Z'
        })

        return jsonify({
            'success': True,
            'message': 'Đăng ký khóa học thành công'
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@courses_bp.route('/<course_id>/unenroll', methods=['POST'])
@login_required_api
def unenroll_course(course_id):
    """
    Unenroll from a course
    """
    try:
        uid = session.get('uid')
        db = get_db()

        # Remove from user's enrolled courses
        db.reference(f'users/{uid}/enrolledCourses/{course_id}').delete()

        # Decrement enrolled count
        course_ref = db.reference(f'courses/{course_id}')
        course = course_ref.get()
        if course:
            current_count = course.get('enrolledCount', 0)
            course_ref.update({'enrolledCount': max(0, current_count - 1)})

        # Delete progress
        db.reference(f'progress/{uid}/{course_id}').delete()

        return jsonify({
            'success': True,
            'message': 'Hủy đăng ký khóa học thành công'
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@courses_bp.route('/categories', methods=['GET'])
def get_categories():
    """Get all available categories"""
    categories = [
        {'id': 'programming', 'name': 'Lập trình', 'icon': 'code'},
        {'id': 'design', 'name': 'Thiết kế', 'icon': 'palette'},
        {'id': 'business', 'name': 'Kinh doanh', 'icon': 'briefcase'},
        {'id': 'marketing', 'name': 'Marketing', 'icon': 'megaphone'},
        {'id': 'language', 'name': 'Ngoại ngữ', 'icon': 'globe'},
        {'id': 'data-science', 'name': 'Khoa học dữ liệu', 'icon': 'chart'},
        {'id': 'mobile-dev', 'name': 'Phát triển Mobile', 'icon': 'mobile'},
        {'id': 'cloud', 'name': 'Điện toán đám mây', 'icon': 'cloud'},
        {'id': 'security', 'name': 'An ninh mạng', 'icon': 'shield'},
        {'id': 'general', 'name': 'Chung', 'icon': 'book'}
    ]
    return jsonify({'success': True, 'categories': categories})
