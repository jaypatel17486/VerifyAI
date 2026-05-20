import azure.functions as func
import json, uuid
from datetime import datetime
from shared.db import get_conn
from shared.ai import analyze
from shared.scraper import extract

def main(req: func.HttpRequest) -> func.HttpResponse:
    data = req.get_json()
    sid = data['submission_id']
    aid = str(uuid.uuid4())

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT input_text FROM text_submissions WHERE submission_id=%s", (sid,))
    row = cur.fetchone()

    if row:
        content = row[0]
    else:
        cur.execute("SELECT url FROM url_submissions WHERE submission_id=%s", (sid,))
        url = cur.fetchone()[0]
        content = extract(url)

    result = analyze(content)

    cur.execute("""
        INSERT INTO analysis_runs
        (analysis_id, submission_id, status, model_name, started_at, completed_at, result_label, credibility_score, summary_report)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """, (
        aid, sid, 'completed', 'gpt-4o', datetime.now(), datetime.now(),
        result['label'], result['score'], result['summary']
    ))

    conn.commit()
    cur.close()
    conn.close()

    return func.HttpResponse(json.dumps({"analysis_id": aid}), mimetype="application/json")