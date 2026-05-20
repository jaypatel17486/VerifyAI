import azure.functions as func
import json
from shared.db import get_conn

def main(req: func.HttpRequest) -> func.HttpResponse:
    user_id = req.route_params.get('user_id')

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT s.submission_id, s.submission_type, a.result_label, a.credibility_score
        FROM submissions s
        LEFT JOIN analysis_runs a ON s.submission_id = a.submission_id
        WHERE s.user_id=%s
    """, (user_id,))

    rows = cur.fetchall()

    cur.close()
    conn.close()

    return func.HttpResponse(json.dumps([
        {"submission_id": r[0], "type": r[1], "label": r[2], "score": r[3]}
        for r in rows
    ]), mimetype="application/json")