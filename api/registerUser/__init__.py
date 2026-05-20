import azure.functions as func
import json, uuid
from datetime import datetime
from shared.db import get_conn

def main(req: func.HttpRequest) -> func.HttpResponse:
    try:
        print("REGISTER API CALLED")

        data = req.get_json()
        print("DATA:", data)

        conn = get_conn()
        cur = conn.cursor()

        user_id = str(uuid.uuid4())

        cur.execute("""
            INSERT INTO users (user_id, full_name, email, password_hash, created_at)
            VALUES (%s,%s,%s,%s,%s)
        """, (
            user_id,
            data['name'],
            data['email'],
            data['password'],
            datetime.now()
        ))

        conn.commit()
        cur.close()
        conn.close()

        print("USER INSERTED")

        return func.HttpResponse(json.dumps({"user_id": user_id}), mimetype="application/json")

    except Exception as e:
        print("ERROR:", str(e))
        return func.HttpResponse(str(e), status_code=500)