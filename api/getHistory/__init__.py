import azure.functions as func
import json
from shared.models import get_user_claims

def main(req: func.HttpRequest) -> func.HttpResponse:
    user_id = req.params.get('user_id')
    if not user_id:
        return func.HttpResponse(
            json.dumps({'error': 'user_id is required'}),
            status_code=400,
            mimetype='application/json'
        )

    claims = get_user_claims(user_id, archived=False)
    return func.HttpResponse(
        json.dumps({'claims': claims}, default=str),
        mimetype='application/json'
    )