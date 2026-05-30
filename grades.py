import numpy as np
import sqlite3
from datetime import date

DB_PATH = "data/beaches.db"

GRADE_ORDER = {"A": 5, "B": 4, "C": 3, "D": 2, "F": 1}  # higher = better

def geometric_mean(values):
    return np.exp(np.mean(np.log(values)))

def assign_grade(geo_mean):
    if geo_mean < 35:    return "A"
    elif geo_mean < 70:  return "B"
    elif geo_mean < 104: return "C"
    elif geo_mean < 200: return "D"
    else:                return "F"

def calculate_grade(beach_id: str) -> dict:
    """Calculate current grade from last 5 samples."""
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT entero_cfu, sample_date FROM samples WHERE beach_id = ? ORDER BY sample_date DESC LIMIT 5",
        (beach_id,)
    ).fetchall()
    conn.close()

    if not rows:
        return {"grade": None, "geo_mean": None, "sample_date": None}

    values = [r[0] for r in rows if r[0] and r[0] > 0]
    if not values:
        return {"grade": "?", "geo_mean": None, "sample_date": rows[0][1]}

    gm = geometric_mean(values)
    return {
        "grade": assign_grade(gm),
        "geo_mean": round(gm, 1),
        "sample_date": rows[0][1]
    }

def save_grade(beach_id: str):
    """Calculate and store today's grade in grade_history."""
    result = calculate_grade(beach_id)
    if not result["grade"]:
        return
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT INTO grade_history (beach_id, grade_date, geo_mean, grade) VALUES (?, ?, ?, ?)",
        (beach_id, date.today().isoformat(), result["geo_mean"], result["grade"])
    )
    conn.commit()
    conn.close()