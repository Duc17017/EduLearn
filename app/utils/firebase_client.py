"""
Firebase Client
Initializes Firebase Admin SDK and provides database reference
"""
import os
import json
import firebase_admin
from firebase_admin import credentials, auth, db
from flask import current_app

# Global variables
firebase_app = None
_db_ref = None


def init_firebase():
    """
    Initialize Firebase Admin SDK
    Uses service account from environment or file
    """
    global firebase_app, _db_ref

    if firebase_app is not None:
        # Ensure _db_ref is also set
        if _db_ref is None:
            _db_ref = db.reference('/')
        return firebase_app

    # Check for GOOGLE_APPLICATION_CREDENTIALS file path first
    google_creds_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
    if google_creds_path and os.path.exists(google_creds_path):
        cred = credentials.Certificate(google_creds_path)
    else:
        # Try to find Firebase service account JSON in project root
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        
        # List of possible service account filenames
        possible_files = [
            'firebase-service-account.json',
            'edulearn-c5fb5-firebase-adminsdk-fbsvc-36c554a056.json',
            'service-account.json'
        ]
        
        cred = None
        for filename in possible_files:
            service_account_path = os.path.join(project_root, filename)
            if os.path.exists(service_account_path):
                cred = credentials.Certificate(service_account_path)
                break
        
        if not cred:
            # Try FIREBASE_CONFIG as JSON
            firebase_config = os.getenv('FIREBASE_CONFIG')
            if firebase_config:
                try:
                    config_dict = json.loads(firebase_config)
                    # Fix private key newlines if needed
                    if 'private_key' in config_dict:
                        config_dict['private_key'] = config_dict['private_key'].replace('\\n', '\n')
                    cred = credentials.Certificate(config_dict)
                except Exception as e:
                    raise ValueError(f"Invalid FIREBASE_CONFIG JSON: {e}")
            else:
                raise ValueError("Firebase credentials not found. Set GOOGLE_APPLICATION_CREDENTIALS or FIREBASE_CONFIG")

    # Initialize Firebase
    bucket_name = os.getenv('FIREBASE_STORAGE_BUCKET', 'edulearn-c5fb5.appspot.com')

    # Get database URL - must be set correctly for Firebase Admin SDK
    db_url = os.environ.get('FIREBASE_DATABASE_URL')
    if not db_url:
        # Try to get from environment or use default
        db_url = 'https://edulearn-c5fb5-default-rtdb.firebaseio.com'

    firebase_app = firebase_admin.initialize_app(cred, {
        'databaseURL': db_url,
        'storageBucket': bucket_name
    })

    _db_ref = db.reference('/')

    return firebase_app


def get_db():
    """
    Get Firebase Realtime Database reference
    """
    global firebase_app

    if firebase_app is None:
        # Try to initialize if not done yet
        try:
            init_firebase()
        except Exception as e:
            current_app.logger.error(f"Failed to initialize Firebase: {e}")
            raise

    # Return a fresh reference using the imported db module
    return db.reference('/')


def get_firebase_db_module():
    """
    Get the Firebase db module directly
    """
    global firebase_app

    if firebase_app is None:
        init_firebase()

    # Return the db module that was imported at the top
    return db


def verify_id_token(id_token):
    """
    Verify Firebase ID token
    """
    return auth.verify_id_token(id_token)


def get_user(uid):
    """
    Get Firebase user by UID
    """
    return auth.get_user(uid)


def create_user(email, password=None, **kwargs):
    """
    Create Firebase user
    """
    return auth.create_user(email=email, password=password, **kwargs)


def get_storage_bucket():
    """
    Get Firebase Storage bucket
    """
    global firebase_app
    if firebase_app is None:
        init_firebase()

    bucket_name = os.getenv('FIREBASE_STORAGE_BUCKET', 'edulearn-c5fb5.appspot.com')
    from firebase_admin import storage
    bucket = storage.bucket(bucket_name)
    return bucket
