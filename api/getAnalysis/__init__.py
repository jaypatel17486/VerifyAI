import azure.functions as func
import json
from shared.models import get_claim

def main(req: func.HttpRequest) -> func.HttpResponse:
    claim_id = req.route_params.get('id')
    if not claim_id:
        return func.HttpResponse(
            json.dumps({'error': 'analysis id is required'}),
            status_code=400,
            mimetype='application/json'
        )

    claim = get_claim(claim_id)
    if not claim:
        return func.HttpResponse(
            json.dumps({'error': 'Analysis not found'}),
            status_code=404,
            mimetype='application/json'
        )

    return func.HttpResponse(
        json.dumps(claim, default=str),
        mimetype='application/json'
    )