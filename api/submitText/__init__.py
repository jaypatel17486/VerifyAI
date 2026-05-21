import azure.functions as func
import json
from shared.models import create_claim

def main(req: func.HttpRequest) -> func.HttpResponse:
    try:
        data = req.get_json()
        user_id = data.get('user_id')
        text = data.get('text', '').strip()

        if not user_id or not text:
            return func.HttpResponse(
                json.dumps({'error': 'user_id and text are required'}),
                status_code=400,
                mimetype='application/json'
            )

        result = create_claim(user_id, 'TEXT', text)
        if not result['success']:
            return func.HttpResponse(
                json.dumps({'error': result['error']}),
                status_code=500,
                mimetype='application/json'
            )

        return func.HttpResponse(
            json.dumps({'submission_id': result['claim_id']}),
            mimetype='application/json'
        )
    except Exception as e:
        return func.HttpResponse(
            json.dumps({'error': str(e)}),
            status_code=500,
            mimetype='application/json'
        )