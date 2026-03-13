import os
from dotenv import load_dotenv

load_dotenv()

if __name__ == '__main__':
    # Get port from environment (for Render.com deployment)
    port = int(os.getenv('PORT', 5000))

    # Import create_app here to avoid circular imports
    from app import create_app
    app = create_app()

    # Run the app
    app.run(host='0.0.0.0', port=port, debug=True)
