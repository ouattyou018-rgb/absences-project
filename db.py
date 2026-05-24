import pg8000

def get_connection():
    return pg8000.connect(
        host="localhost",
        port=5432,
        database="absences_db",
        user="postgres",
        password="MonMdp2024"
    )

def query(sql, params=None, fetchall=True):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(sql, params or [])
        cols = [d[0] for d in cur.description] if cur.description else []
        rows = cur.fetchall()
        result = [dict(zip(cols, row)) for row in rows]
        if fetchall:
            return result
        return result[0] if result else None
    finally:
        conn.close()

def execute(sql, params=None):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(sql, params or [])
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
