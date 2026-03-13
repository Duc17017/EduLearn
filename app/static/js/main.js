// ========================================
// EduLearn - Main JavaScript
// ========================================

// API Base URL
const API_BASE = '';

// Firebase Configuration (injected from backend via base.html, or use defaults)
const firebaseConfig = window.firebaseWebConfig || {
    apiKey: "",
    authDomain: "",
    projectId: "",
    storageBucket: "",
    messagingSenderId: "",
    appId: ""
};

// Global state
let currentUser = null;
let chatHistory = [];
let currentCourseId = null;

// ========================================
// Utility Functions
// ========================================

/**
 * Make API request
 */
async function apiRequest(endpoint, options = {}) {
    const url = API_BASE + endpoint;
    const defaultOptions = {
        headers: {
            'Content-Type': 'application/json',
        },
        credentials: 'include'
    };

    const response = await fetch(url, { ...defaultOptions, ...options });

    // Check content type before parsing
    const contentType = response.headers.get('content-type');
    let data;
    if (contentType && contentType.includes('application/json')) {
        data = await response.json();
    } else {
        // If not JSON, get text and throw error
        const text = await response.text();
        throw new Error(`Server error: ${response.status} - ${text.substring(0, 100)}`);
    }

    if (!response.ok) {
        throw new Error(data.message || data.error || `Request failed with status ${response.status}`);
    }

    return data;
}

/**
 * Show toast notification
 */
function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `alert alert-${type}`;
    toast.textContent = message;
    toast.style.position = 'fixed';
    toast.style.top = '20px';
    toast.style.right = '20px';
    toast.style.zIndex = '10000';
    toast.style.animation = 'slideIn 0.3s ease';

    document.body.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transition = 'opacity 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

/**
 * Show/hide loading overlay
 */
function showLoading() {
    const overlay = document.createElement('div');
    overlay.className = 'loading-overlay';
    overlay.id = 'loadingOverlay';
    overlay.innerHTML = '<div class="spinner"></div>';
    document.body.appendChild(overlay);
}

function hideLoading() {
    const overlay = document.getElementById('loadingOverlay');
    if (overlay) overlay.remove();
}

/**
 * Format date
 */
function formatDate(dateString) {
    if (!dateString) return '';
    const date = new Date(dateString);
    return date.toLocaleDateString('vi-VN', {
        year: 'numeric',
        month: 'long',
        day: 'numeric'
    });
}

/**
 * Format time duration (seconds to mm:ss or hh:mm:ss)
 */
function formatDuration(seconds) {
    if (!seconds || seconds === 0) return '0:00';

    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);

    if (hours > 0) {
        return `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    }
    return `${minutes}:${secs.toString().padStart(2, '0')}`;
}

// ========================================
// Authentication
// ========================================

/**
 * Check if user is logged in
 */
async function checkAuth() {
    try {
        const data = await apiRequest('/auth/current-user');
        currentUser = data;
        return data.authenticated;
    } catch (error) {
        console.error('Auth check failed:', error);
        return false;
    }
}

/**
 * Login with Firebase
 */
async function login(email, password) {
    showLoading();

    try {
        // Sign in with Firebase
        const firebaseAuth = getFirebaseAuth();
        const credential = await signInWithEmailAndPassword(firebaseAuth, email, password);
        const idToken = await credential.user.getIdToken();

        // Send token to backend
        const data = await apiRequest('/auth/login', {
            method: 'POST',
            body: JSON.stringify({ idToken })
        });

        hideLoading();
        showToast('Đăng nhập thành công!', 'success');

        // Redirect based on role
        setTimeout(() => {
            if (data.role === 'instructor' || data.role === 'admin') {
                window.location.href = '/instructor/dashboard';
            } else {
                window.location.href = '/dashboard';
            }
        }, 500);

        return data;
    } catch (error) {
        hideLoading();
        showToast(error.message || 'Đăng nhập thất bại', 'error');
        throw error;
    }
}

/**
 * Register new user
 */
async function register(name, email, password, role = 'student') {
    showLoading();

    try {
        const firebaseAuth = getFirebaseAuth();
        const credential = await createUserWithEmailAndPassword(firebaseAuth, email, password);
        const idToken = await credential.user.getIdToken();

        const data = await apiRequest('/auth/register', {
            method: 'POST',
            body: JSON.stringify({ idToken, name, role })
        });

        hideLoading();
        showToast('Đăng ký thành công!', 'success');

        setTimeout(() => {
            window.location.href = '/dashboard';
        }, 500);

        return data;
    } catch (error) {
        hideLoading();
        showToast(error.message || 'Đăng ký thất bại', 'error');
        throw error;
    }
}

/**
 * Logout
 */
async function logout() {
    try {
        await apiRequest('/auth/api/logout', { method: 'POST' });

        const firebaseAuth = getFirebaseAuth();
        await signOut(firebaseAuth);

        window.location.href = '/auth/login';
    } catch (error) {
        showToast('Đăng xuất thất bại', 'error');
    }
}

// ========================================
// Courses
// ========================================

/**
 * Get all courses
 */
async function getCourses(category = '', limit = 50, offset = 0) {
    let url = `/courses/?limit=${limit}&offset=${offset}`;
    if (category) url += `&category=${category}`;

    return await apiRequest(url);
}

/**
 * Get course details
 */
async function getCourse(courseId) {
    return await apiRequest(`/courses/${courseId}`);
}

/**
 * Enroll in a course
 */
async function enrollCourse(courseId) {
    showLoading();

    try {
        const data = await apiRequest(`/courses/${courseId}/enroll`, {
            method: 'POST'
        });

        hideLoading();
        showToast('Đăng ký khóa học thành công!', 'success');
        return data;
    } catch (error) {
        hideLoading();
        showToast(error.message || 'Đăng ký thất bại', 'error');
        throw error;
    }
}

// ========================================
// Lessons & Progress
// ========================================

/**
 * Get lesson details
 */
async function getLesson(courseId, lessonId) {
    return await apiRequest(`/lessons/${lessonId}?courseId=${courseId}`);
}

/**
 * Mark lesson as complete
 */
async function markLessonComplete(courseId, lessonId) {
    try {
        const data = await apiRequest('/progress/mark-complete', {
            method: 'POST',
            body: JSON.stringify({ courseId, lessonId })
        });

        // Update UI
        updateProgressUI(data.percentage);
        return data;
    } catch (error) {
        showToast('Lỗi khi đánh dấu hoàn thành', 'error');
    }
}

/**
 * Save video position
 */
async function saveVideoPosition(courseId, lessonId, position) {
    try {
        await apiRequest('/progress/save-position', {
            method: 'POST',
            body: JSON.stringify({ courseId, lessonId, position })
        });
    } catch (error) {
        console.error('Failed to save position:', error);
    }
}

/**
 * Get video position
 */
async function getVideoPosition(courseId, lessonId) {
    try {
        const data = await apiRequest(`/progress/get-position?courseId=${courseId}&lessonId=${lessonId}`);
        return data.position || 0;
    } catch (error) {
        return 0;
    }
}

/**
 * Update progress UI
 */
function updateProgressUI(percentage) {
    const progressBar = document.querySelector('.progress-fill');
    const progressText = document.querySelector('.progress-text');

    if (progressBar) {
        progressBar.style.width = `${percentage}%`;
    }
    if (progressText) {
        progressText.textContent = `${percentage}% hoàn thành`;
    }
}

// ========================================
// Chatbot
// ========================================

/**
 * Send message to chatbot
 */
async function sendChatMessage(message, courseId, lessonId = null) {
    try {
        const data = await apiRequest('/chatbot/ask', {
            method: 'POST',
            body: JSON.stringify({
                message,
                courseId,
                lessonId,
                history: chatHistory
            })
        });

        chatHistory = data.history || [];
        return data.reply;
    } catch (error) {
        showToast('Lỗi khi gửi tin nhắn', 'error');
        throw error;
    }
}

/**
 * Clear chat history
 */
async function clearChatHistory(courseId) {
    try {
        await apiRequest('/chatbot/clear', {
            method: 'POST',
            body: JSON.stringify({ courseId })
        });
        chatHistory = [];
    } catch (error) {
        console.error('Failed to clear chat:', error);
    }
}

// ========================================
// Initialize
// ========================================

document.addEventListener('DOMContentLoaded', function() {
    // Check authentication status
    checkAuth().then(isLoggedIn => {
        if (!isLoggedIn && window.location.pathname !== '/auth/login' && window.location.pathname !== '/auth/register') {
            // Store intended destination
            sessionStorage.setItem('redirectAfterLogin', window.location.href);
        }
    });

    // Search functionality
    const searchInput = document.getElementById('searchInput');
    if (searchInput) {
        searchInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                const query = e.target.value.trim();
                if (query) {
                    window.location.href = `/courses?search=${encodeURIComponent(query)}`;
                }
            }
        });
    }

    // Logout button
    const logoutBtn = document.getElementById('logoutBtn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', logout);
    }
});

// Export for use in other scripts
window.EduLearn = {
    apiRequest,
    showToast,
    showLoading,
    hideLoading,
    formatDate,
    formatDuration,
    checkAuth,
    login,
    register,
    logout,
    getCourses,
    getCourse,
    enrollCourse,
    getLesson,
    markLessonComplete,
    saveVideoPosition,
    getVideoPosition,
    sendChatMessage,
    clearChatHistory
};
