import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    DATABASE_PATH = os.environ.get('DATABASE_PATH', 'database/health_diet_app.db')
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')
    GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')
    AI_PROVIDER = os.environ.get('AI_PROVIDER', 'gemini')  # 'openai' or 'gemini'
    DEBUG = os.environ.get('DEBUG', 'False').lower() == 'true'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max upload
