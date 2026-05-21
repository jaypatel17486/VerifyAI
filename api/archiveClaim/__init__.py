import azure.functions as func
import json
from shared.models import archive_claim


def main(req: func.HttpRequest) -> func.HttpResponse:
    try:
        data = req.get_json()
        claim_id = data.get('claim_id')
        reason = data.get('reason', 'User archived')

        if not claim_id:
            return func.HttpResponse(
                json.dumps({'error': 'claim_id is required'}),
                status_code=400,
                mimetype='application/json'
            )

        result = archive_claim(claim_id, reason)
        if not result['success']:
            return func.HttpResponse(
                json.dumps({'error': result['error']}),
                status_code=400,
                mimetype='application/json'
            )

        return func.HttpResponse(
            json.dumps({'archive_id': result['archive_id']}),
            mimetype='application/json'
        )
    except Exception as e:
        return func.HttpResponse(
            json.dumps({'error': str(e)}),
            status_code=500,
            mimetype='application/json'
        )
