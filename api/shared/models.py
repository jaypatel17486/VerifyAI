import psycopg2
from psycopg2.extras import RealDictCursor
import bcrypt
from datetime import datetime
from .db import get_conn


def hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(rounds=12)).decode('utf-8')


def verify_password(password, password_hash):
    return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))


# ── Users ──────────────────────────────────────────────────────────────────────

def register_user(email, password, full_name=None):
    email = email.strip().lower()
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO users (full_name, email, password_hash, created_at, is_deleted)
            VALUES (%s, %s, %s, %s, FALSE)
            RETURNING user_id
        """, (full_name or email.split('@')[0], email, hash_password(password), datetime.now()))
        user_id = str(cur.fetchone()[0])
        conn.commit()
        return {"success": True, "user_id": user_id}
    except psycopg2.IntegrityError:
        conn.rollback()
        return {"success": False, "error": "Email already registered"}
    except Exception as e:
        conn.rollback()
        return {"success": False, "error": str(e)}
    finally:
        cur.close()
        conn.close()


def login_user(email, password):
    email = email.strip().lower()
    try:
        conn = get_conn()
    except Exception as e:
        return {"success": False, "error": str(e)}
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cur.execute(
            "SELECT user_id, password_hash FROM users WHERE email = %s AND is_deleted = FALSE",
            (email,)
        )
        user = cur.fetchone()
        if user and verify_password(password, user['password_hash']):
            return {"success": True, "user_id": str(user['user_id'])}
        return {"success": False, "error": "Invalid email or password"}
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        cur.close()
        conn.close()


def get_user_by_id(user_id):
    conn = get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cur.execute(
            "SELECT user_id, email, full_name, created_at FROM users WHERE user_id = %s",
            (user_id,)
        )
        return cur.fetchone()
    except Exception as e:
        print(f"get_user_by_id error: {e}")
        return None
    finally:
        cur.close()
        conn.close()

def get_user_by_email(email):
    conn = get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cur.execute(
            "SELECT user_id, email, full_name FROM users WHERE email = %s AND is_deleted = FALSE",
            (email.strip().lower(),)
        )
        return cur.fetchone()
    except Exception as e:
        print(f"get_user_by_email error: {e}")
        return None
    finally:
        cur.close()
        conn.close()

# ── Claims ─────────────────────────────────────────────────────────────────────

def create_claim(user_id, claim_type, claim_text, ai_research=None, ai_response=None, credibility_score=None):
    conn = get_conn()
    cur = conn.cursor()
    try:
        now = datetime.now()
        cur.execute("""
            INSERT INTO claims (user_id, claim_type, claim_text, ai_research, ai_response,
                               credibility_score, is_archived, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, FALSE, %s, %s)
            RETURNING claim_id
        """, (user_id, claim_type, claim_text, ai_research, ai_response, credibility_score, now, now))
        claim_id = str(cur.fetchone()[0])
        conn.commit()
        return {"success": True, "claim_id": claim_id}
    except Exception as e:
        conn.rollback()
        return {"success": False, "error": str(e)}
    finally:
        cur.close()
        conn.close()


def update_claim_analysis(claim_id, ai_research, ai_response, credibility_score):
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("""
            UPDATE claims
            SET ai_research = %s, ai_response = %s, credibility_score = %s, updated_at = %s
            WHERE claim_id = %s
        """, (ai_research, ai_response, credibility_score, datetime.now(), claim_id))
        conn.commit()
        return {"success": True}
    except Exception as e:
        conn.rollback()
        return {"success": False, "error": str(e)}
    finally:
        cur.close()
        conn.close()


def get_claim(claim_id):
    conn = get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cur.execute("SELECT * FROM claims WHERE claim_id = %s", (claim_id,))
        return cur.fetchone()
    except Exception as e:
        print(f"get_claim error: {e}")
        return None
    finally:
        cur.close()
        conn.close()


def get_user_claims(user_id, archived=False):
    conn = get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cur.execute("""
            SELECT * FROM claims
            WHERE user_id = %s AND is_archived = %s
            ORDER BY created_at DESC
        """, (user_id, archived))
        return cur.fetchall()
    except Exception as e:
        print(f"get_user_claims error: {e}")
        return []
    finally:
        cur.close()
        conn.close()


# ── Archives ───────────────────────────────────────────────────────────────────

def archive_claim(claim_id, reason=None):
    conn = get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        now = datetime.now()
        cur.execute("""
            SELECT user_id, claim_text, claim_type, ai_research, ai_response, credibility_score
            FROM claims WHERE claim_id = %s
        """, (claim_id,))
        claim = cur.fetchone()
        if not claim:
            return {"success": False, "error": "Claim not found"}

        cur.execute("""
            INSERT INTO archives (user_id, claim_id, original_claim_text, original_claim_type,
                                 original_ai_research, original_ai_response, original_credibility_score,
                                 archived_reason, archived_at, is_restored)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, FALSE)
            RETURNING archive_id
        """, (
            claim['user_id'], claim_id, claim['claim_text'], claim['claim_type'],
            claim['ai_research'], claim['ai_response'], claim['credibility_score'],
            reason, now
        ))
        archive_id = str(cur.fetchone()[0])

        cur.execute("""
            UPDATE claims SET is_archived = TRUE, archived_at = %s, updated_at = %s
            WHERE claim_id = %s
        """, (now, now, claim_id))

        conn.commit()
        return {"success": True, "archive_id": archive_id}
    except Exception as e:
        conn.rollback()
        return {"success": False, "error": str(e)}
    finally:
        cur.close()
        conn.close()


def get_user_archives(user_id):
    conn = get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cur.execute("""
            SELECT a.*
            FROM archives a
            WHERE a.user_id = %s AND a.is_restored = FALSE
            ORDER BY a.archived_at DESC
        """, (user_id,))
        return cur.fetchall()
    except Exception as e:
        print(f"get_user_archives error: {e}")
        return []
    finally:
        cur.close()
        conn.close()


def restore_claim(archive_id):
    conn = get_conn()
    cur = conn.cursor()
    try:
        now = datetime.now()
        cur.execute("SELECT claim_id FROM archives WHERE archive_id = %s", (archive_id,))
        row = cur.fetchone()
        if not row:
            return {"success": False, "error": "Archive not found"}

        claim_id = row[0]
        cur.execute("""
            UPDATE claims SET is_archived = FALSE, archived_at = NULL, updated_at = %s
            WHERE claim_id = %s
        """, (now, claim_id))
        cur.execute("""
            UPDATE archives SET is_restored = TRUE, restored_at = %s WHERE archive_id = %s
        """, (now, archive_id))
        conn.commit()
        return {"success": True}
    except Exception as e:
        conn.rollback()
        return {"success": False, "error": str(e)}
    finally:
        cur.close()
        conn.close()


def delete_archive(archive_id):
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM archives WHERE archive_id = %s", (archive_id,))
        conn.commit()
        return {"success": True}
    except Exception as e:
        conn.rollback()
        return {"success": False, "error": str(e)}
    finally:
        cur.close()
        conn.close()
