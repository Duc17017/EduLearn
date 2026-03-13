"""
Gemini AI Chatbot Routes
Context-aware chatbot for each course using Google Gemini
"""
import os
from flask import Blueprint, request, jsonify, session
from datetime import datetime
import google.generativeai as genai
from app.utils.firebase_client import get_db
from app.utils.auth_middleware import login_required, login_required_api

chatbot_bp = Blueprint('chatbot', __name__)

# Configure Gemini
def configure_gemini():
    """Configure Gemini API with key from config"""
    from flask import current_app
    api_key = current_app.config.get('GEMINI_API_KEY')
    if api_key:
        genai.configure(api_key=api_key)
    return api_key


def get_gemini_model():
    """Get configured Gemini model"""
    configure_gemini()
    return genai.GenerativeModel('gemini-2.0-flash')


def build_system_prompt(course_data, lesson_title=''):
    """
    Build context-aware system prompt from course data
    """
    prompt = f"""Bạn là trợ lý học tập thông minh cho khóa học online.

Thông tin khóa học:
- Tên khóa học: {course_data.get('title', 'Chưa có tiêu đề')}
- Mô tả: {course_data.get('description', 'Chưa có mô tả')}
- Giảng viên: {course_data.get('instructorName', 'Chưa có thông tin')}

"""

    if lesson_title:
        prompt += f"- Bài học hiện tại: {lesson_title}\n"

    prompt += """
Quy tắc trả lời:
1. Trả lời bằng tiếng Việt, ngắn gọn, dễ hiểu
2. Nếu câu hỏi ngoài phạm vi khóa học, hãy lịch sự hướng dẫn học viên quay lại nội dung bài giảng
3. Không trả lời các câu hỏi không liên quan đến học tập
4. Đưa ra ví dụ minh họa khi cần thiết
5. Nếu học viên hỏi về nội dung chưa học, hãy gợi ý học các bài trước đó
6. Khuyến khích học viên tự học và thực hành

Hãy trả lời câu hỏi của học viên một cách nhiệt tình và hữu ích!
"""
    return prompt


@chatbot_bp.route('/ask', methods=['POST'])
@login_required_api
def ask_question():
    """
    Ask a question to the chatbot
    Expected JSON: { message, courseId, lessonId (optional), history (optional) }
    """
    try:
        data = request.json
        message = data.get('message', '').strip()
        course_id = data.get('courseId')
        lesson_id = data.get('lessonId')
        provided_history = data.get('history', [])

        if not message:
            return jsonify({'error': 'Missing message', 'message': 'Vui lòng nhập câu hỏi'}), 400

        if not course_id:
            return jsonify({'error': 'Missing courseId', 'message': 'Thiếu ID khóa học'}), 400

        db = get_db()

        # Get course data for context
        course_ref = db.reference(f'courses/{course_id}')
        course = course_ref.get()

        if not course:
            return jsonify({'error': 'Course not found'}), 404

        # Get instructor name
        instructor_name = 'Giảng viên'
        if course.get('instructorId'):
            user_ref = db.reference(f'users/{course.get("instructorId")}')
            user_data = user_ref.get()
            if user_data:
                instructor_name = user_data.get('name', 'Giảng viên')

        course['instructorName'] = instructor_name

        # Get lesson title if provided
        lesson_title = ''
        if lesson_id:
            lesson_ref = db.reference(f'courses/{course_id}/lessons/{lesson_id}')
            lesson = lesson_ref.get()
            if lesson:
                lesson_title = lesson.get('title', '')

        # Build system prompt
        system_prompt = build_system_prompt(course, lesson_title)

        # Get or initialize chat history from session
        session_key = f'chat_history_{course_id}'
        chat_history = session.get(session_key, [])

        # Use provided history if different from session (allows client-side history management)
        if provided_history and len(provided_history) > len(chat_history):
            chat_history = provided_history

        # Convert history to Gemini format
        gemini_history = []
        for msg in chat_history[-20:]:  # Limit to last 20 messages
            role = 'user' if msg.get('role') == 'user' else 'model'
            gemini_history.append({
                'role': role,
                'parts': [msg.get('content', '')]
            })

        # Start chat with history
        model = get_gemini_model()
        chat = model.start_chat(history=gemini_history)

        # Send message with system prompt
        full_message = f"{system_prompt}\n\n---\n\nCâu hỏi của học viên: {message}"
        response = chat.send_message(full_message)

        # Update history
        chat_history.append({
            'role': 'user',
            'content': message,
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        })
        chat_history.append({
            'role': 'assistant',
            'content': response.text,
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        })

        # Keep only last 20 messages in session
        if len(chat_history) > 20:
            chat_history = chat_history[-20:]

        session[session_key] = chat_history

        return jsonify({
            'success': True,
            'reply': response.text,
            'history': chat_history
        })

    except Exception as e:
        return jsonify({'error': str(e), 'message': 'Đã xảy ra lỗi khi xử lý câu hỏi'}), 500


@chatbot_bp.route('/clear', methods=['POST'])
@login_required_api
def clear_history():
    """
    Clear chat history for a specific course
    Expected JSON: { courseId }
    """
    try:
        data = request.json
        course_id = data.get('courseId')

        if not course_id:
            return jsonify({'error': 'Missing courseId'}), 400

        # Clear session history
        session_key = f'chat_history_{course_id}'
        session.pop(session_key, None)

        return jsonify({
            'success': True,
            'message': 'Đã xóa lịch sử chat'
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@chatbot_bp.route('/history', methods=['GET'])
@login_required_api
def get_history():
    """
    Get chat history for a specific course
    Query params: courseId
    """
    try:
        course_id = request.args.get('courseId')

        if not course_id:
            return jsonify({'error': 'Missing courseId'}), 400

        session_key = f'chat_history_{course_id}'
        chat_history = session.get(session_key, [])

        return jsonify({
            'success': True,
            'history': chat_history
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@chatbot_bp.route('/suggest-questions', methods=['GET'])
@login_required_api
def suggest_questions():
    """
    Get suggested questions based on course content
    Query params: courseId
    """
    try:
        course_id = request.args.get('courseId')

        if not course_id:
            return jsonify({'error': 'Missing courseId'}), 400

        db = get_db()

        # Get course data
        course_ref = db.reference(f'courses/{course_id}')
        course = course_ref.get()

        if not course:
            return jsonify({'error': 'Course not found'}), 404

        # Get lessons
        lessons_ref = db.reference(f'courses/{course_id}/lessons')
        lessons = lessons_ref.get() or {}

        # Generate suggestions based on lessons
        suggestions = [
            f"Khóa học này có những bài học nào?",
            f"Giải thích về {course.get('title', 'nội dung khóa học')}?",
            "Tôi cần chuẩn bị gì để học khóa này?"
        ]

        # Add lesson-specific questions
        lessons_list = []
        for lesson_id, lesson_data in lessons.items():
            lessons_list.append((lesson_data.get('order', 0), lesson_data.get('title', '')))

        lessons_list.sort(key=lambda x: x[0])

        if lessons_list:
            suggestions.append(f"Nội dung chính của bài \"{lessons_list[0][1]}\" là gì?")

        return jsonify({
            'success': True,
            'suggestions': suggestions
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@chatbot_bp.route('/test', methods=['GET'])
def test_connection():
    """
    Test if Gemini API is configured
    """
    try:
        api_key = configure_gemini()

        if not api_key:
            return jsonify({
                'success': False,
                'message': 'GEMINI_API_KEY not configured'
            }), 500

        # Try to generate content
        model = get_gemini_model()
        response = model.generate_content("Say hello in Vietnamese")

        return jsonify({
            'success': True,
            'message': 'Gemini API connected successfully',
            'test_response': response.text
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500
