This is the backend server of the TestYourself flashcard web application. It is built with Flask (Python) and provides a REST API for user authentication, flashcard management, quiz features, and file uploads.

⚙️ Tech Stack
- Python + Flask
- SQLAlchemy (ORM)
- SQLite / PostgreSQL (configurable)
- JWT-based Authentication
- Flask-Migrate (for database migrations)

📂 Main Files
- run.py – Application entry point
- requirements.txt – Python dependencies
- init_db.py – DB initialization script
- app/ – Main Flask app (routes, models, services)
- migrations/ – Database migration files
- uploads/ – Uploaded media (e.g., images for flashcards)

🚀 Getting Started
- python -m venv venv
- source venv/bin/activate 
- pip install -r requirements.txt
- export FLASK_APP=run.py
- export FLASK_ENV=development
- flask db upgrade
- flask run

📌 Features
- Google OAuth integration 
- Flashcard CRUD APIs
- Quiz logic API
- User progress tracking
- Upload + serve media files
