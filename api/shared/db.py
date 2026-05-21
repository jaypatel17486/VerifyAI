import psycopg2
import os

def get_conn():
    return psycopg2.connect(
        host=os.getenv("DATABASE_HOST", "verifyai-postgres-server.postgres.database.azure.com"),
        database=os.getenv("DATABASE_NAME", "verifyaidb"),
        user=os.getenv("DATABASE_USER", "dbadmin"),
        password=os.getenv("DATABASE_PASSWORD", "Verifyai!"),
        port=os.getenv("DATABASE_PORT", "5432"),
        sslmode="require",
        connect_timeout=int(os.getenv("DATABASE_CONNECT_TIMEOUT", "5"))
    )