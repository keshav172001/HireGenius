# app.py
from flask import Flask
from config import Config
from database import db, migrate
from auth import oidc
from routes import routes

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    oidc.init_app(app)

    with app.app_context():
        db.create_all()  # Ensure tables are created

    # Register blueprints
    app.register_blueprint(routes)

    return app

if __name__ == "__main__":
    app = create_app()
    app.run(debug=True,use_reloader=True)
