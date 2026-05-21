import azure.functions as func
import json
from shared.models import get_user_by_email


def main(req: func.HttpRequest) -> func.HttpResponse:
    try:
        data = req.get_json()
        email = data.get('email', '').strip().lower()

        if not email:
            return func.HttpResponse(
                json.dumps({'error': 'Email is required'}),
                status_code=400,
                mimetype='application/json'
            )

        # For now, we only verify that the email exists and return a neutral response.
        get_user_by_email(email)
        return func.HttpResponse(
            json.dumps({'message': 'If the email exists, password reset instructions have been sent.'}),
            mimetype='application/json'
        )
    except Exception as e:
        return func.HttpResponse(
            json.dumps({'error': str(e)}),
            status_code=500,
            mimetype='application/json'
        )
