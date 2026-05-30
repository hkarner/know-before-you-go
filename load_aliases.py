import sqlite3
import csv

DB_PATH = "data/beaches.db"
CSV_PATH = "seed_data/surf_spots.csv"

conn = sqlite3.connect(DB_PATH)
with open(CSV_PATH) as f:
    reader = csv.DictReader(f)
    for row in reader:
        conn.execute(
            "INSERT OR REPLACE INTO beach_aliases (beach_id, alias, slug, surfline_id, source) VALUES (?, ?, ?, ?, 'manual')",
            (row["beacon_id"], row["alias"], row["slug"], row.get("surfline_id") or None)
        )
conn.commit()
conn.close()
print("Aliases loaded.")