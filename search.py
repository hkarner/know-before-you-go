from rapidfuzz import process
import sqlite3

DB_PATH = "data/beaches.db"

def search_beaches(query: str, limit: int = 5) -> list:
    """Search across official beach names and surf spot aliases."""
    conn = sqlite3.connect(DB_PATH)
    official = conn.execute("SELECT id, name, state FROM beaches").fetchall()
    aliases  = conn.execute("SELECT beach_id, alias FROM beach_aliases").fetchall()
    conn.close()

    all_entries = [
        {"beach_id": r[0], "display": f"{r[1]}, {r[2]}"} for r in official
    ] + [
        {"beach_id": r[0], "display": r[1]} for r in aliases
    ]

    names = [e["display"] for e in all_entries]
    matches = process.extract(query, names, limit=limit, score_cutoff=55)
    return [{"display": m[0], "beach_id": all_entries[names.index(m[0])]["beach_id"], "score": m[1]} for m in matches]