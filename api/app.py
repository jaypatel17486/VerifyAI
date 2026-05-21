import base64
import json
import uuid
from datetime import datetime
import os
import sys

from flask import Flask, request, jsonify
from werkzeug.exceptions import HTTPException

# Load environment variables from local.settings.json
settings_file = os.path.join(os.path.dirname(__file__), 'local.settings.json')
if os.path.exists(settings_file):
    with open(settings_file, 'r') as f:
        settings = json.load(f)
        for key, value in settings.get('Values', {}).items():
            os.environ[key] = value

print("Loaded Azure OpenAI endpoint:", os.getenv("AZURE_OPENAI_ENDPOINT"))
print("Loaded Azure OpenAI deployment:", os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME"))

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'shared'))

from shared.models import (
    register_user, login_user, get_user_by_id, get_user_claims,
    create_claim, update_claim_analysis, get_claim,
    archive_claim, get_user_archives, restore_claim, delete_archive
)
from shared.ai import analyze, analyze_image
from shared.scraper import extract

app = Flask(__name__)


@app.after_request
def cors(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    return response


@app.errorhandler(Exception)
def handle_exception(error):
    if isinstance(error, HTTPException):
        return jsonify({"error": error.description}), error.code
    return jsonify({"error": str(error)}), 500


@app.route('/<path:path>', methods=['OPTIONS'])
@app.route('/', methods=['OPTIONS'])
def options(path=''):
    return '', 204


# ── Auth ───────────────────────────────────────────────────────────────────────

@app.route('/api/registerUser', methods=['POST'])
def register():
    data = request.get_json()
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')
    if not email or not password:
        return jsonify({"error": "Email and password required"}), 400
    result = register_user(email, password)
    if result['success']:
        return jsonify({"user_id": result['user_id']}), 201
    return jsonify({"error": result['error']}), 400


@app.route('/api/loginUser', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')
    if not email or not password:
        return jsonify({"error": "Email and password required"}), 400
    result = login_user(email, password)
    if result['success']:
        return jsonify({"user_id": result['user_id']}), 200
    return jsonify({"error": result['error']}), 401


@app.route('/api/user/<user_id>', methods=['GET'])
def get_user(user_id):
    user = get_user_by_id(user_id)
    if user:
        return jsonify(dict(user)), 200
    return jsonify({"error": "User not found"}), 404


@app.route('/api/forgotPassword', methods=['POST'])
def forgot_password():
    data = request.get_json()
    email = data.get('email', '').strip().lower()
    if not email:
        return jsonify({"error": "Email required"}), 400

    user = get_user_by_email(email)
    if not user:
        # Don't reveal if email exists for security
        return jsonify({"message": "If the email exists, a password reset link has been sent"}), 200

    # TODO: Implement actual email sending with reset token
    # For now, just return success message
    return jsonify({"message": "Password reset link sent to your email"}), 200


# ── Claims ─────────────────────────────────────────────────────────────────────

@app.route('/api/submitText', methods=['POST'])
def submit_text():
    data = request.get_json()
    user_id = data.get('user_id')
    text = data.get('text', '').strip()
    if not user_id or not text:
        return jsonify({"error": "user_id and text required"}), 400
    result = create_claim(user_id, 'TEXT', text)
    if result['success']:
        return jsonify({"submission_id": result['claim_id']}), 200
    return jsonify({"error": result['error']}), 400


@app.route('/api/submitURL', methods=['POST'])
def submit_url():
    data = request.get_json()
    user_id = data.get('user_id')
    url = data.get('url', '').strip()
    if not user_id or not url:
        return jsonify({"error": "user_id and url required"}), 400
    result = create_claim(user_id, 'URL', url)
    if result['success']:
        return jsonify({"submission_id": result['claim_id']}), 200
    return jsonify({"error": result['error']}), 400


@app.route('/api/submitImage', methods=['POST'])
def submit_image():
    user_id = request.form.get('user_id')
    if not user_id:
        return jsonify({"error": "user_id required"}), 400
    file = request.files.get('image')
    if not file:
        return jsonify({"error": "No image provided"}), 400

    image_b64 = base64.b64encode(file.read()).decode('utf-8')
    mime_type = file.content_type or 'image/jpeg'

    result = analyze_image(image_b64, mime_type)

    claim_text = f"[IMAGE] {file.filename or 'uploaded_image'}"
    claim_result = create_claim(
        user_id, 'IMAGE', claim_text,
        ai_research=result.get('summary', ''),
        ai_response=json.dumps({
            "label": result.get('label'),
            "forensics": result.get('forensics', {}),
            "metadata": result.get('metadata', {})
        }),
        credibility_score=result.get('score', 0)
    )
    if not claim_result['success']:
        return jsonify({"error": claim_result['error']}), 400

    return jsonify({
        "submission_id": claim_result['claim_id'],
        "analysis_id": claim_result['claim_id'],
        "label": result.get('label'),
        "score": result.get('score'),
        "summary": result.get('summary'),
        "forensics": result.get('forensics', {}),
        "metadata": result.get('metadata', {}),
        "created_at": datetime.now().isoformat()
    }), 200


@app.route('/api/runAnalysis', methods=['POST'])
def run_analysis():
    data = request.get_json()
    submission_id = data.get('submission_id')
    if not submission_id:
        return jsonify({"error": "submission_id required"}), 400

    claim = get_claim(submission_id)
    if not claim:
        return jsonify({"error": "Claim not found"}), 404

    claim_type = claim['claim_type']
    claim_text = claim['claim_text']

    # For URLs scrape the article text first
    if claim_type == 'URL':
        try:
            content = extract(claim_text)
        except Exception:
            content = claim_text
    else:
        content = claim_text

    result = analyze(content)

    update_claim_analysis(
        submission_id,
        result.get('research', ''),
        result.get('summary', ''),
        result.get('score', 0)
    )

    return jsonify({
        "analysis_id": submission_id,
        "submission_id": submission_id,
        "label": result.get('label'),
        "score": result.get('score'),
        "summary": result.get('summary'),
        "research": result.get('research'),
        "created_at": datetime.now().isoformat()
    }), 200


@app.route('/api/getAnalysis/<analysis_id>', methods=['GET'])
def get_analysis(analysis_id):
    claim = get_claim(analysis_id)
    if claim:
        return jsonify(dict(claim)), 200
    return jsonify({"error": "Analysis not found"}), 404


@app.route('/api/getHistory', methods=['GET'])
def get_history():
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({"error": "user_id required"}), 400
    claims = get_user_claims(user_id, archived=False)
    return jsonify({"claims": [dict(c) for c in claims]}), 200


# ── Archives ───────────────────────────────────────────────────────────────────

@app.route('/api/archiveClaim', methods=['POST'])
def archive_claim_endpoint():
    data = request.get_json()
    claim_id = data.get('claim_id')
    reason = data.get('reason', 'User archived')
    if not claim_id:
        return jsonify({"error": "claim_id required"}), 400
    result = archive_claim(claim_id, reason)
    if result['success']:
        return jsonify({"archive_id": result['archive_id']}), 200
    return jsonify({"error": result['error']}), 400


@app.route('/api/getArchives', methods=['GET'])
def get_archives():
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({"error": "user_id required"}), 400
    archives = get_user_archives(user_id)
    return jsonify({"archives": [dict(a) for a in archives]}), 200


@app.route('/api/restoreClaim', methods=['POST'])
def restore_claim_endpoint():
    data = request.get_json()
    archive_id = data.get('archive_id')
    if not archive_id:
        return jsonify({"error": "archive_id required"}), 400
    result = restore_claim(archive_id)
    if result['success']:
        return jsonify({"message": "Claim restored"}), 200
    return jsonify({"error": result['error']}), 400


@app.route('/api/deleteArchive', methods=['DELETE'])
def delete_archive_endpoint():
    data = request.get_json()
    archive_id = data.get('archive_id')
    if not archive_id:
        return jsonify({"error": "archive_id required"}), 400
    result = delete_archive(archive_id)
    if result['success']:
        return jsonify({"message": "Deleted permanently"}), 200
    return jsonify({"error": result['error']}), 400


# ── Health ─────────────────────────────────────────────────────────────────────

@app.route('/api/health', methods=['GET'])
@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "healthy"}), 200


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=7071)
