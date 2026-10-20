"""Flask application factory for SCA Web."""

import os
from flask import Flask, jsonify, send_from_directory, request
from werkzeug.exceptions import HTTPException
from sca.web.api import api_bp

def create_app(test_config=None) -> Flask:
    """Create and configure the SCA Flask application."""
    static_dir = os.path.join(os.path.dirname(__file__), "static")
    app = Flask(
        __name__,
        static_folder=static_dir,
        static_url_path="",
    )

    # Security configuration
    app.config["MAX_CONTENT_LENGTH"] = 100 * 1024  # 100 KB max payload
    app.config["JSON_SORT_KEYS"] = False

    if test_config:
        app.config.update(test_config)

    # Register API blueprint
    app.register_blueprint(api_bp)

    @app.route("/")
    def index():
        """Serve index.html from static directory."""
        if os.path.exists(os.path.join(static_dir, "index.html")):
            return send_from_directory(static_dir, "index.html")
        return (
            "<!DOCTYPE html><html><head><title>SCA Analyzer</title></head>"
            "<body><h1>SCA Analyzer Backend Ready</h1><p>API is active at /api/health</p></body></html>"
        )

    # Standard JSON error handlers for API requests
    @app.errorhandler(413)
    def request_entity_too_large(e):
        return jsonify({
            "ok": False,
            "error": {
                "code": "PAYLOAD_TOO_LARGE",
                "message": "Request payload exceeds 100 KB limit",
            }
        }), 413

    @app.errorhandler(400)
    def bad_request(e):
        msg = getattr(e, "description", "Bad request")
        return jsonify({
            "ok": False,
            "error": {
                "code": "BAD_REQUEST",
                "message": str(msg),
            }
        }), 400

    @app.errorhandler(404)
    def not_found(e):
        if request.path.startswith("/api/"):
            return jsonify({
                "ok": False,
                "error": {
                    "code": "NOT_FOUND",
                    "message": f"Resource not found: {request.path}",
                }
            }), 404
        if os.path.exists(os.path.join(static_dir, "index.html")):
            return send_from_directory(static_dir, "index.html")
        return jsonify({
            "ok": False,
            "error": {
                "code": "NOT_FOUND",
                "message": "Not found",
            }
        }), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        # Never leak internal server paths or stack traces
        return jsonify({
            "ok": False,
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An internal server error occurred.",
            }
        }), 500

    @app.errorhandler(Exception)
    def handle_unhandled_exception(e):
        if isinstance(e, HTTPException):
            return jsonify({
                "ok": False,
                "error": {
                    "code": e.name.upper().replace(" ", "_"),
                    "message": e.description,
                }
            }), e.code
        # Generic unhandled exception
        return jsonify({
            "ok": False,
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An internal server error occurred.",
            }
        }), 500

    return app
