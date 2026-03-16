from app import app, init_db
import os, threading

if __name__ == '__main__':
    print('Starting via application.py')
    init_db()
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
