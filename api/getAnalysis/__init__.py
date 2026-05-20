import azure.functions as func
import json
from shared.db import get_conn

def main(req: func.HttpRequest) -> func.HttpResponse:
    aid = req.route_params.get('id')

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT result_label, credibility_score, summary_report FROM analysis_runs WHERE analysis_id=%s", (aid,))
    r = cur.fetchone()

    cur.close()
    conn.close()

    return func.HttpResponse(json.dumps({
        "label": r[0],
        "score": r[1],
        "summary": r[2]
    }), mimetype="application/json")