# EduLearn - Nền tảng học trực tuyến

Một nền tảng học trực tuyến hiện đại được xây dựng bằng Flask (Backend) và Firebase (Database + Storage), tích hợp AI chatbot sử dụng Google Gemini.

## 🚀 Tính năng

### Cho Học viên
- Đăng ký/đăng nhập bằng Firebase Authentication
- Danh sách khóa học với filter theo danh mục
- Xem video bài giảng với HTML5 player
- Tự động lưu vị trí xem video
- Đánh dấu hoàn thành bài học tự động khi xem 90%
- Theo dõi tiến độ học tập
- Chatbot AI hỗ trợ học tập (Gemini)

### Cho Giảng viên
- Tạo và quản lý khóa học
- Upload video bài giảng lên Firebase Storage
- Quản lý danh sách bài học
- Xem danh sách học viên đã đăng ký
- Xuất bản/ẩn khóa học

## 🛠️ Công nghệ

### Backend
- **Flask** - Python web framework
- **Firebase Admin SDK** - Realtime Database & Storage
- **Google Gemini API** - AI Chatbot

### Frontend  
- **HTML5/CSS3** - Giao diện hiện đại
- **Vanilla JavaScript** - Không framework
- **Firebase JS SDK** - Authentication

### Database & Storage
- **Firebase Realtime Database** - Lưu trữ dữ liệu
- **Firebase Storage** - Lưu trữ video

## 📁 Cấu trúc dự án

```
EduLearn/
├── app/
│   ├── routes/
│   │   ├── auth.py         # Authentication
│   │   ├── courses.py      # Course CRUD
│   │   ├── lessons.py      # Lessons & Upload
│   │   ├── progress.py     # Progress tracking
│   │   ├── chatbot.py      # Gemini AI
│   │   └── main.py        # Page routes
│   ├── utils/
│   │   ├── firebase_client.py
│   │   └── auth_middleware.py
│   ├── templates/          # Jinja2 templates
│   └── static/            # CSS, JS, images
├── config.py               # Configuration
├── run.py                 # Entry point
└── requirements.txt       # Dependencies
```

## ⚙️ Cài đặt

### 1. Clone project
```bash
git clone <repo-url>
cd EduLearn
```

### 2. Tạo virtual environment
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# hoặc
venv\Scripts\activate     # Windows
```

### 3. Cài đặt dependencies
```bash
pip install -r requirements.txt
```

### 4. Cấu hình Firebase

1. Tạo project tại [Firebase Console](https://console.firebase.google.com)
2. Enable **Authentication** (Email/Password, Google nếu dùng đăng nhập Google)
3. Enable **Realtime Database**
4. Enable **Storage**
5. **Backend (Admin SDK)**: Tải Service Account Key (JSON) → đặt vào thư mục project
6. **Frontend (Web SDK)**: Vào Project Settings → General → Your apps → Add app (Web) → Copy cấu hình

### 5. Cấu hình file .env
```env
SECRET_KEY=your-secret-key
FIREBASE_CREDENTIALS=path/to/serviceAccountKey.json
FIREBASE_DATABASE_URL=https://your-project.firebaseio.com
FIREBASE_STORAGE_BUCKET=your-project.appspot.com
GEMINI_API_KEY=your-gemini-api-key
FLASK_ENV=development

# Firebase Web SDK (cho đăng ký/đăng nhập trên trình duyệt - lấy từ Firebase Console > Project Settings > Your apps > Web)
FIREBASE_WEB_API_KEY=AIza...
FIREBASE_WEB_PROJECT_ID=edulearn-c5fb5
FIREBASE_WEB_AUTH_DOMAIN=edulearn-c5fb5.firebaseapp.com
FIREBASE_WEB_STORAGE_BUCKET=edulearn-c5fb5.appspot.com
FIREBASE_WEB_MESSAGING_SENDER_ID=123456789
FIREBASE_WEB_APP_ID=1:123456789:web:xxxx
```

> **Lưu ý**: `FIREBASE_WEB_API_KEY` là bắt buộc để đăng ký/đăng nhập hoạt động. Lấy từ Firebase Console → Project Settings → General → Your apps → Web app config.

### 6. Chạy ứng dụng
```bash
python run.py
```

Truy cập `http://localhost:5000`

## 🔐 Security Rules

### Firebase Realtime Database
```json
{
  "rules": {
    "users": {
      "$uid": {
        ".read": "$uid === auth.uid",
        ".write": "$uid === auth.uid"
      }
    },
    "courses": {
      ".read": true,
      "$courseId": {
        ".write": "auth != null && data.child('instructorId').val() === auth.uid"
      }
    },
    "progress": {
      "$uid": {
        ".read": "$uid === auth.uid",
        ".write": "$uid === auth.uid"
      }
    }
  }
}
```

### Firebase Storage
```json
{
  "rules": {
    "videos": {
      ".read": "auth != null",
      ".write": "auth != null && request.resource.size < 500000000"
    },
    "thumbnails": {
      ".read": true,
      ".write": "auth != null"
    }
  }
}
```

## 📝 API Endpoints

### Authentication
- `POST /auth/login` - Đăng nhập
- `POST /auth/register` - Đăng ký
- `GET /auth/logout` - Đăng xuất
- `GET /auth/current-user` - Lấy thông tin user

### Courses
- `GET /courses/` - Danh sách khóa học
- `GET /courses/<id>` - Chi tiết khóa học
- `POST /courses/create` - Tạo khóa học (Instructor)
- `PUT /courses/<id>/update` - Cập nhật khóa học
- `DELETE /courses/<id>/delete` - Xóa khóa học
- `POST /courses/<id>/enroll` - Đăng ký khóa học

### Lessons
- `POST /lessons/upload` - Upload video
- `POST /lessons/create` - Tạo bài học
- `PUT /lessons/<id>/update` - Cập nhật bài học
- `DELETE /lessons/<id>/delete` - Xóa bài học

### Progress
- `POST /progress/mark-complete` - Đánh dấu hoàn thành
- `POST /progress/save-position` - Lưu vị trí xem
- `GET /progress/<courseId>` - Lấy tiến độ

### Chatbot
- `POST /chatbot/ask` - Hỏi chatbot
- `POST /chatbot/clear` - Xóa lịch sử chat

## 📄 License

MIT License
edulearn_admin_2026