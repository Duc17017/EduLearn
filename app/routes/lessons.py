"""
Lesson Management Routes
Upload video, manage lessons within courses
"""
import os
import uuid
from flask import Blueprint, request, jsonify, session, render_template
from datetime import datetime
from firebase_admin import storage
from app.utils.firebase_client import get_db, get_storage_bucket
from app.utils.auth_middleware import login_required, login_required_api, instructor_required, instructor_required_api

lessons_bp = Blueprint('lessons', __name__)

# Allowed file extensions
ALLOWED_VIDEO_EXTENSIONS = {'mp4', 'webm', 'mov', 'avi', 'mkv'}
ALLOWED_IMAGE_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif', 'webp'}
ALLOWED_DOCUMENT_EXTENSIONS = {'pdf', 'doc', 'docx'}


def allowed_file(filename, allowed_extensions):
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in allowed_extensions


def get_file_extension(filename):
    """Get file extension"""
    return filename.rsplit('.', 1)[1].lower() if '.' in filename else ''


@lessons_bp.route('/upload', methods=['POST'])
@instructor_required_api
def upload_lesson():
    """
    Upload video file to Firebase Storage
    Expected form-data: video (file), courseId, title
    """
    try:
        if 'video' not in request.files:
            return jsonify({'error': 'No video file', 'message': 'Vui lòng chọn file video'}), 400

        video_file = request.files['video']
        course_id = request.form.get('courseId')
        title = request.form.get('title', 'Untitled Lesson')

        if not course_id:
            return jsonify({'error': 'Missing courseId', 'message': 'Thiếu ID khóa học'}), 400

        if video_file.filename == '':
            return jsonify({'error': 'Empty filename', 'message': 'Tên file không hợp lệ'}), 400

        if not allowed_file(video_file.filename, ALLOWED_VIDEO_EXTENSIONS):
            return jsonify({
                'error': 'Invalid file type',
                'message': 'Chỉ chấp nhận file video: mp4, webm, mov, avi, mkv'
            }), 400

        # Generate unique filename
        ext = get_file_extension(video_file.filename)
        filename = f"courses/{course_id}/lessons/{uuid.uuid4()}.{ext}"

        # Upload to Firebase Storage
        bucket = get_storage_bucket()
        blob = bucket.blob(filename)

        # Set content type
        content_type = f"video/{ext}"
        if ext == 'webm':
            content_type = 'video/webm'
        elif ext == 'mov':
            content_type = 'video/quicktime'

        blob.upload_from_file(
            video_file.stream,
            content_type=content_type
        )

        # Make public or generate signed URL (using public for simplicity)
        blob.make_public()
        video_url = blob.public_url

        # Get file size
        file_size = blob.size

        return jsonify({
            'success': True,
            'videoUrl': video_url,
            'filename': filename,
            'fileSize': file_size,
            'message': 'Upload video thành công'
        })

    except Exception as e:
        return jsonify({'error': str(e), 'message': 'Lỗi khi upload video'}), 500


@lessons_bp.route('/<lesson_id>', methods=['GET'])
@login_required_api
def get_lesson(lesson_id):
    """
    Get lesson details
    """
    try:
        course_id = request.args.get('courseId')
        if not course_id:
            return jsonify({'error': 'Missing courseId'}), 400

        db = get_db()
        lesson_ref = db.reference(f'courses/{course_id}/lessons/{lesson_id}')
        lesson = lesson_ref.get()

        if not lesson:
            return jsonify({'error': 'Lesson not found', 'message': 'Bài học không tồn tại'}), 404

        lesson['id'] = lesson_id

        # Get progress for this lesson
        uid = session.get('uid')
        progress_ref = db.reference(f'progress/{uid}/{course_id}')
        progress = progress_ref.get() or {}
        completed_lessons = progress.get('completedLessons', {})

        lesson['isCompleted'] = lesson_id in completed_lessons

        return jsonify({
            'success': True,
            'lesson': lesson
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@lessons_bp.route('/create', methods=['POST'])
@instructor_required_api
def create_lesson():
    """
    Create a new lesson in a course
    Expected JSON: { courseId, title, description, videoUrl, duration, order }
    """
    try:
        data = request.json
        course_id = data.get('courseId')
        title = data.get('title')

        if not course_id or not title:
            return jsonify({'error': 'Missing required fields'}), 400

        uid = session.get('uid')
        db = get_db()

        # Verify course ownership
        course_ref = db.reference(f'courses/{course_id}')
        course = course_ref.get()

        if not course:
            return jsonify({'error': 'Course not found'}), 404

        if course.get('instructorId') != uid and session.get('role') != 'admin':
            return jsonify({'error': 'Forbidden'}), 403

        # Get current max order
        lessons_ref = db.reference(f'courses/{course_id}/lessons')
        lessons = lessons_ref.get() or {}
        max_order = 0
        for _, lesson in lessons.items():
            order = lesson.get('order', 0)
            if order > max_order:
                max_order = order

        # Create new lesson
        new_lesson = lessons_ref.push({
            'title': title,
            'description': data.get('description', ''),
            'videoUrl': data.get('videoUrl', ''),
            'duration': data.get('duration', 0),
            'order': data.get('order', max_order + 1),
            'videoId': data.get('videoId', ''),
            'resources': data.get('resources', []),
            'createdAt': datetime.utcnow().isoformat() + 'Z'
        })

        lesson_id = new_lesson.key

        # Update total lessons count in progress for all enrolled students
        total_lessons = len(lessons) + 1
        enrolled_users = course.get('enrolledCount', 0)

        return jsonify({
            'success': True,
            'lessonId': lesson_id,
            'message': 'Tạo bài học thành công'
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@lessons_bp.route('/<lesson_id>/update', methods=['PUT'])
@instructor_required_api
def update_lesson(lesson_id):
    """
    Update lesson information
    Expected JSON: { courseId, title, description, videoUrl, duration, order }
    """
    try:
        data = request.json
        course_id = data.get('courseId')

        if not course_id:
            return jsonify({'error': 'Missing courseId'}), 400

        uid = session.get('uid')
        db = get_db()

        # Verify course ownership
        course_ref = db.reference(f'courses/{course_id}')
        course = course_ref.get()

        if not course:
            return jsonify({'error': 'Course not found'}), 404

        if course.get('instructorId') != uid and session.get('role') != 'admin':
            return jsonify({'error': 'Forbidden'}), 403

        # Build update data
        updatable_fields = ['title', 'description', 'videoUrl', 'duration', 'order', 'videoId', 'resources']
        update_data = {}

        for field in updatable_fields:
            if field in data:
                update_data[field] = data[field]

        update_data['updatedAt'] = datetime.utcnow().isoformat() + 'Z'

        # Update lesson
        lesson_ref = db.reference(f'courses/{course_id}/lessons/{lesson_id}')
        lesson_ref.update(update_data)

        return jsonify({
            'success': True,
            'message': 'Cập nhật bài học thành công'
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@lessons_bp.route('/<lesson_id>/delete', methods=['DELETE'])
@instructor_required_api
def delete_lesson(lesson_id):
    """
    Delete a lesson from a course
    Query param: courseId
    """
    try:
        course_id = request.args.get('courseId')

        if not course_id:
            return jsonify({'error': 'Missing courseId'}), 400

        uid = session.get('uid')
        db = get_db()

        # Verify course ownership
        course_ref = db.reference(f'courses/{course_id}')
        course = course_ref.get()

        if not course:
            return jsonify({'error': 'Course not found'}), 404

        if course.get('instructorId') != uid and session.get('role') != 'admin':
            return jsonify({'error': 'Forbidden'}), 403

        # Get lesson to delete video from storage
        lesson_ref = db.reference(f'courses/{course_id}/lessons/{lesson_id}')
        lesson = lesson_ref.get()

        if lesson:
            # Delete video from storage if exists
            video_id = lesson.get('videoId')
            if video_id:
                try:
                    bucket = get_storage_bucket()
                    blob = bucket.blob(f"courses/{course_id}/lessons/{video_id}")
                    blob.delete()
                except:
                    pass  # Continue even if video deletion fails

        # Delete lesson from database
        lesson_ref.delete()

        return jsonify({
            'success': True,
            'message': 'Xóa bài học thành công'
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@lessons_bp.route('/<lesson_id>/reorder', methods=['POST'])
@instructor_required_api
def reorder_lessons(lesson_id):
    """
    Reorder lessons within a course
    Expected JSON: { courseId, newOrder }
    """
    try:
        data = request.json
        course_id = data.get('courseId')
        new_order = data.get('newOrder')

        if not course_id or new_order is None:
            return jsonify({'error': 'Missing required fields'}), 400

        uid = session.get('uid')
        db = get_db()

        # Verify course ownership
        course_ref = db.reference(f'courses/{course_id}')
        course = course_ref.get()

        if not course:
            return jsonify({'error': 'Course not found'}), 404

        if course.get('instructorId') != uid and session.get('role') != 'admin':
            return jsonify({'error': 'Forbidden'}), 403

        # Update lesson order
        lesson_ref = db.reference(f'courses/{course_id}/lessons/{lesson_id}')
        lesson_ref.update({'order': new_order})

        return jsonify({
            'success': True,
            'message': 'Cập nhật thứ tự thành công'
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@lessons_bp.route('/batch-reorder', methods=['POST'])
@instructor_required_api
def batch_reorder_lessons():
    """
    Reorder multiple lessons at once
    Expected JSON: { courseId, lessons: [{id, order}, ...] }
    """
    try:
        data = request.json
        course_id = data.get('courseId')
        lessons_data = data.get('lessons', [])

        if not course_id or not lessons_data:
            return jsonify({'error': 'Missing required fields'}), 400

        uid = session.get('uid')
        db = get_db()

        # Verify course ownership
        course_ref = db.reference(f'courses/{course_id}')
        course = course_ref.get()

        if not course:
            return jsonify({'error': 'Course not found'}), 404

        if course.get('instructorId') != uid and session.get('role') != 'admin':
            return jsonify({'error': 'Forbidden'}), 403

        # Update all lessons order
        for lesson_item in lessons_data:
            lesson_id = lesson_item.get('id')
            order = lesson_item.get('order')
            if lesson_id and order is not None:
                db.reference(f'courses/{course_id}/lessons/{lesson_id}').update({
                    'order': order
                })

        return jsonify({
            'success': True,
            'message': 'Cập nhật thứ tự thành công'
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@lessons_bp.route('/upload-thumbnail', methods=['POST'])
@instructor_required_api
def upload_thumbnail():
    """
    Upload course thumbnail
    Expected form-data: thumbnail (file)
    """
    try:
        if 'thumbnail' not in request.files:
            return jsonify({'error': 'No file'}), 400

        thumbnail_file = request.files['thumbnail']

        if thumbnail_file.filename == '':
            return jsonify({'error': 'Empty filename'}), 400

        if not allowed_file(thumbnail_file.filename, ALLOWED_IMAGE_EXTENSIONS):
            return jsonify({'error': 'Invalid file type'}), 400

        ext = get_file_extension(thumbnail_file.filename)
        filename = f"thumbnails/{uuid.uuid4()}.{ext}"

        bucket = get_storage_bucket()
        blob = bucket.blob(filename)

        content_type = f"image/{ext}"
        if ext == 'jpg':
            content_type = 'image/jpeg'

        blob.upload_from_file(
            thumbnail_file.stream,
            content_type=content_type
        )

        blob.make_public()
        thumbnail_url = blob.public_url

        return jsonify({
            'success': True,
            'thumbnailUrl': thumbnail_url
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500
