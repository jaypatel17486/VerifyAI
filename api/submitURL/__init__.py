import azure.functions as func
import json, uuid
from datetime import datetime
from shared.db import get_conn

def main(req: func.HttpRequest) -> func.HttpResponse:
    data = req.get_json()
    sid = str(uuid.uuid4())

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("INSERT INTO submissions VALUES (%s,%s,%s,%s)",
                (sid, data["user_id"], "URL", datetime.now()))

    cur.execute("INSERT INTO url_submissions VALUES (%s,%s,%s,%s,%s)",
                (sid, data["url"], "", "", datetime.now()))

    conn.commit()
    cur.close()
    conn.close()

    return func.HttpResponse(json.dumps({"submission_id": sid}), mimetype="application/json")