import azure.functions as func
import json
from shared.models import delete_archive


def main(req: func.HttpRequest) -> func.HttpResponse:
    try:
        data = req.get_json()
        archive_id = data.get('archive_id')
        if not archive_id:
            return func.HttpResponse(
                json.dumps({'error': 'archive_id is required'}),
                status_code=400,
                mimetype='application/json'
            )

        result = delete_archive(archive_id)
        if not result['success']:
            return func.HttpResponse(
                json.dumps({'error': result['error']}),
                status_code=400,
                mimetype='application/json'
            )

        return func.HttpResponse(
            json.dumps({'message': 'Deleted permanently'}),
            mimetype='application/json'
        )
    except Exception as e:
        return func.HttpResponse(
            json.dumps({'error': str(e)}),
            status_code=500,
            mimetype='application/json'
        )
