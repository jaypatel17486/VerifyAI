import azure.functions as func
import json
from shared.db import get_conn

def main(req: func.HttpRequest) -> func.HttpResponse:
    data = req.get_json()

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT user_id, password_hash FROM users WHERE email=%s", (data['email'],))
    user = cur.fetchone()

    cur.close()
    conn.close()

    if user and user[1] == data['password']:
        return func.HttpResponse(json.dumps({"user_id": user[0]}), mimetype="application/json")

    return func.HttpResponse("Invalid", status_code=401)