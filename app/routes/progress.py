"""
Progress Tracking Routes
Track student progress, mark lessons complete, save video position
"""
from flask import Blueprint, request, jsonify, session
from datetime import datetime
from app.utils.firebase_client import get_db
from app.utils.auth_middleware import login_required, login_required_api

progress_bp = Blueprint('progress', __name__)


@progress_bp.route('/mark-complete', methods=['POST'])
@login_required_api
def mark_complete():
    """
    Mark a lesson as complete
    Expected JSON: { courseId, lessonId }
    """
    try:
        data = request.json
        course_id = data.get('courseId')
        lesson_id = data.get('lessonId')

        if not course_id or not lesson_id:
            return jsonify({'error': 'Missing required fields'}), 400

        uid = session.get('uid')
        db = get_db()

        # Get current progress
        progress_ref = db.reference(f'progress/{uid}/{course_id}')
        current_progress = progress_ref.get() or {}

        completed_lessons = current_progress.get('completedLessons', {})

        # Check if already completed
        if lesson_id in completed_lessons:
            return jsonify({
                'success': True,
                'message': 'Bài học đã được hoàn thành trước đó',
                'percentage': current_progress.get('percentage', 0)
            })

        # Add to completed lessons
        completed_lessons[lesson_id] = {
            'completedAt': datetime.utcnow().isoformat() + 'Z'
        }

        # Get total lessons count
        lessons_ref = db.reference(f'courses/{course_id}/lessons')
        lessons = lessons_ref.get() or {}
        total_lessons = len(lessons)

        # Calculate percentage
        if total_lessons > 0:
            percentage = int((len(completed_lessons) / total_lessons) * 100)
        else:
            percentage = 0

        # Update progress
        progress_ref.update({
            'completedLessons': completed_lessons,
            'percentage': percentage,
            'lastWatched': lesson_id,
            'lastCompleted': datetime.utcnow().isoformat() + 'Z',
            'totalLessons': total_lessons
        })

        return jsonify({
            'success': True,
            'percentage': percentage,
            'completedCount': len(completed_lessons),
            'totalLessons': total_lessons,
            'message': 'Đánh dấu hoàn thành bài học'
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@progress_bp.route('/mark-incomplete', methods=['POST'])
@login_required_api
def mark_incomplete():
    """
    Mark a lesson as incomplete (undo completion)
    Expected JSON: { courseId, lessonId }
    """
    try:
        data = request.json
        course_id = data.get('courseId')
        lesson_id = data.get('lessonId')

        if not course_id or not lesson_id:
            return jsonify({'error': 'Missing required fields'}), 400

        uid = session.get('uid')
        db = get_db()

        # Get current progress
        progress_ref = db.reference(f'progress/{uid}/{course_id}')
        current_progress = progress_ref.get() or {}

        completed_lessons = current_progress.get('completedLessons', {})

        # Remove from completed lessons
        if lesson_id in completed_lessons:
            del completed_lessons[lesson_id]

        # Get total lessons count
        lessons_ref = db.reference(f'courses/{course_id}/lessons')
        lessons = lessons_ref.get() or {}
        total_lessons = len(lessons)

        # Calculate percentage
        if total_lessons > 0:
            percentage = int((len(completed_lessons) / total_lessons) * 100)
        else:
            percentage = 0

        # Update progress
        progress_ref.update({
            'completedLessons': completed_lessons,
            'percentage': percentage,
            'totalLessons': total_lessons
        })

        return jsonify({
            'success': True,
            'percentage': percentage,
            'completedCount': len(completed_lessons),
            'totalLessons': total_lessons
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@progress_bp.route('/save-position', methods=['POST'])
@login_required_api
def save_position():
    """
    Save video watching position
    Expected JSON: { courseId, lessonId, position (seconds) }
    """
    try:
        data = request.json
        course_id = data.get('courseId')
        lesson_id = data.get('lessonId')
        position = data.get('position', 0)

        if not course_id or not lesson_id:
            return jsonify({'error': 'Missing required fields'}), 400

        uid = session.get('uid')
        db = get_db()

        # Get current progress
        progress_ref = db.reference(f'progress/{uid}/{course_id}')
        current_progress = progress_ref.get() or {}

        # Update position for specific lesson
        lesson_positions = current_progress.get('lessonPositions', {})
        lesson_positions[lesson_id] = {
            'position': position,
            'updatedAt': datetime.utcnow().isoformat() + 'Z'
        }

        # Update progress
        progress_ref.update({
            'lastWatched': lesson_id,
            'lastPosition': position,
            'lessonPositions': lesson_positions,
            'lastActivity': datetime.utcnow().isoformat() + 'Z'
        })

        return jsonify({
            'success': True,
            'message': 'Lưu vị trí xem thành công'
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@progress_bp.route('/get-position', methods=['GET'])
@login_required_api
def get_position():
    """
    Get saved video position for a lesson
    Query params: courseId, lessonId
    """
    try:
        course_id = request.args.get('courseId')
        lesson_id = request.args.get('lessonId')

        if not course_id or not lesson_id:
            return jsonify({'error': 'Missing required parameters'}), 400

        uid = session.get('uid')
        db = get_db()

        # Get progress
        progress_ref = db.reference(f'progress/{uid}/{course_id}')
        progress = progress_ref.get() or {}

        lesson_positions = progress.get('lessonPositions', {})
        lesson_pos = lesson_positions.get(lesson_id, {})

        return jsonify({
            'success': True,
            'position': lesson_pos.get('position', 0),
            'lastWatched': progress.get('lastWatched')
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@progress_bp.route('/<course_id>', methods=['GET'])
@login_required_api
def get_course_progress(course_id):
    """
    Get all progress for a specific course
    """
    try:
        uid = session.get('uid')
        db = get_db()

        # Get progress
        progress_ref = db.reference(f'progress/{uid}/{course_id}')
        progress = progress_ref.get() or {}

        # Get course info
        course_ref = db.reference(f'courses/{course_id}')
        course = course_ref.get()

        if not course:
            return jsonify({'error': 'Course not found'}), 404

        # Get lessons
        lessons_ref = db.reference(f'courses/{course_id}/lessons')
        lessons = lessons_ref.get() or {}

        lessons_list = []
        completed_lessons = progress.get('completedLessons', {})

        for lesson_id, lesson_data in lessons.items():
            lesson_data['id'] = lesson_id
            lesson_data['isCompleted'] = lesson_id in completed_lessons
            lessons_list.append(lesson_data)

        # Sort by order
        lessons_list.sort(key=lambda x: x.get('order', 0))

        progress['lessons'] = lessons_list
        progress['courseTitle'] = course.get('title', '')

        return jsonify({
            'success': True,
            'progress': progress
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@progress_bp.route('/all', methods=['GET'])
@login_required_api
def get_all_progress():
    """
    Get all progress for current user across all courses
    """
    try:
        uid = session.get('uid')
        db = get_db()

        # Get user data
        user_ref = db.reference(f'users/{uid}')
        user_data = user_ref.get() or {}
        enrolled_courses = user_data.get('enrolledCourses', {})

        # Get progress for each course
        all_progress = []

        for course_id in enrolled_courses.keys():
            progress_ref = db.reference(f'progress/{uid}/{course_id}')
            progress = progress_ref.get() or {}

            # Get course info
            course_ref = db.reference(f'courses/{course_id}')
            course = course_ref.get()

            if course:
                progress['courseId'] = course_id
                progress['courseTitle'] = course.get('title', '')
                progress['courseThumbnail'] = course.get('thumbnail', '')
                all_progress.append(progress)

        # Sort by last activity
        all_progress.sort(
            key=lambda x: x.get('lastActivity', ''),
            reverse=True
        )

        return jsonify({
            'success': True,
            'progress': all_progress,
            'totalCourses': len(all_progress)
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@progress_bp.route('/stats', methods=['GET'])
@login_required_api
def get_stats():
    """
    Get overall learning stats for current user
    """
    try:
        uid = session.get('uid')
        db = get_db()

        # Get user data
        user_ref = db.reference(f'users/{uid}')
        user_data = user_ref.get() or {}
        enrolled_courses = user_data.get('enrolledCourses', {})

        total_courses = len(enrolled_courses)
        total_completed = 0
        total_watch_time = 0

        # Calculate stats
        for course_id in enrolled_courses.keys():
            progress_ref = db.reference(f'progress/{uid}/{course_id}')
            progress = progress_ref.get() or {}

            if progress.get('percentage', 0) == 100:
                total_completed += 1

        # Get user info
        name = user_data.get('name', 'Học viên')

        return jsonify({
            'success': True,
            'stats': {
                'totalCourses': total_courses,
                'completedCourses': total_completed,
                'inProgressCourses': total_courses - total_completed,
                'averageProgress': 0  # Can be calculated if needed
            },
            'userName': name
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500
