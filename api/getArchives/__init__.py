import azure.functions as func
import json
from shared.models import get_user_archives


def main(req: func.HttpRequest) -> func.HttpResponse:
    try:
        user_id = req.params.get('user_id')
        if not user_id:
            return func.HttpResponse(
                json.dumps({'error': 'user_id is required'}),
                status_code=400,
                mimetype='application/json'
            )

        archives = get_user_archives(user_id)
        return func.HttpResponse(
            json.dumps({'archives': archives}, default=str),
            mimetype='application/json'
        )
    except Exception as e:
        return func.HttpResponse(
            json.dumps({'error': str(e)}),
            status_code=500,
            mimetype='application/json'
        )
