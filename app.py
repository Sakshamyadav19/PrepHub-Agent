# app.py
from flask import Flask
from routes.interview_routes import interview_bp
from dotenv import load_dotenv
from flask_cors import CORS

load_dotenv()  # loads from .env

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes
app.register_blueprint(interview_bp)

if __name__ == '__main__':
    app.run(debug=True)
