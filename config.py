# config.py
import os

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "default_secret_key")  # Change in production
    SQLALCHEMY_DATABASE_URI = "postgresql://postgres:admin@localhost/postgres"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    OIDC_CLIENT_SECRETS = "client_secrets.json"
    OIDC_COOKIE_SECURE = False  # Set to True in production with HTTPS
    OIDC_CALLBACK_ROUTE = "/oidc/callback"
    OIDC_SCOPES = ["openid", "email", "profile"]
    OIDC_ID_TOKEN_COOKIE_NAME = "oidc_token"
    UPLOAD_FOLDER = "uploads/resumes"
