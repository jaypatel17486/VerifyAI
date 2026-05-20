import azure.functions as func
import json
import logging
from shared.ai import analyze

def main(req: func.HttpRequest) -> func.HttpResponse:
    try:
        data = req.get_json()
        claim = data.get('claim', '')
        
        if not claim:
            return func.HttpResponse("Missing claim", status_code=400)
            
        # Call AI analysis
        ai_result = analyze(claim)
        
        # Map to frontend expected format
        status = str(ai_result.get('label', 'unverified')).lower()
        if status not in ['true', 'false', 'misleading', 'unverified', 'authentic', 'manipulated']:
            status = 'unverified'
            
        result = {
            "status": status,
            "credibility": ai_result.get('score', 0),
            "reasoning": ai_result.get('summary', 'No reasoning provided.'),
            "sources": []
        }
        
        return func.HttpResponse(json.dumps(result), mimetype="application/json")
    except Exception as e:
        logging.error(f"Error in analyze API: {str(e)}")
        return func.HttpResponse(json.dumps({"error": str(e)}), status_code=500, mimetype="application/json")
