import os
from flask import Flask, send_from_directory, render_template
from config import Config
from database import close_db, init_db, extract_youtube_id

def create_app():
    app = Flask(__name__, static_folder="static", template_folder="templates")
    app.config.from_object(Config)

    # Ensure uploads folder exists (safe for serverless read-only filesystems)
    try:
        os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
    except Exception:
        pass

    # Teardown database connection
    app.teardown_appcontext(close_db)

    # Register blueprints
    from routes.auth_routes import auth_bp
    from routes.student_routes import student_bp
    from routes.admin_routes import admin_bp
    from routes.api_routes import api_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(student_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(api_bp)

    # Custom Jinja Template Filters
    @app.template_filter('youtube_id')
    def filter_youtube_id(url):
        return extract_youtube_id(url)

    @app.template_filter('youtube_embed')
    def filter_youtube_embed(url):
        yid = extract_youtube_id(url)
        return f"https://www.youtube.com/embed/{yid}" if yid else ""

    # Route to serve uploads (question/option images)
    @app.route('/uploads/questions/<path:filename>')
    @app.route('/uploads/<path:filename>')
    def serve_uploads(filename):
        return send_from_directory(Config.UPLOAD_FOLDER, filename)

    # 404 and 500 error handlers
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('404.html'), 404

    @app.errorhandler(500)
    def internal_error(e):
        return render_template('500.html'), 500

    # Auto-initialize DB and ensure Admin exists if not already present
    try:
        with app.app_context():
            init_db()
    except Exception as e:
        print(f"Startup DB init notice: {e}")

    return app

app = create_app()

if __name__ == '__main__':
    print("=" * 60)
    print("TechEasy Tutorials - Engineering Mathematics Portal")
    print("Server running at: http://127.0.0.1:5000")
    print("Admin login: http://127.0.0.1:5000/admin/login")
    print("Credentials -> Admin: admin@techeasy.com / admin123")
    print("Credentials -> Student: student@techeasy.com / student123")
    print("=" * 60)
    app.run(host="0.0.0.0", port=5000, debug=True)
