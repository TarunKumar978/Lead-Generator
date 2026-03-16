from app import app, init_db
import os

if __name__ == '__main__':
    print("🚀 Starting via application.py")
    init_db()
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'True').lower() == 'true'
    app.run(host='0.0.0.0', port=port, debug=debug)
