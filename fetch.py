import sqlite3
import requests
from datetime import date

DB_PATH = "data/beaches.db"

# CEDEN CA Open Data Portal — Surface Water Chemistry Results
# Resource IDs by year (add older years here for more history)
CEDEN_RESOURCES = [
    "7c2faf29-d5d3-4ad6-a429-442ed337febb",  # 2026
    "97b8bb60-8e58-4c97-a07f-d51a48cd36d4",  # 2025
]
CKAN_API = "https://data.ca.gov/api/3/action/datastore_search"
PAGE_SIZE = 1000  # records per API call


def fetch_enterococcus_page(resource_id: str, offset: int) -> dict:
    """Fetch one page of Enterococcus records from a CEDEN resource."""
    params = {
        "resource_id": resource_id,
        "filters": '{"Analyte": "Enterococcus"}',
        "limit": PAGE_SIZE,
        "offset": offset,
    }
    resp = requests.get(CKAN_API, params=params, timeout=60)
    resp.raise_for_status()
    return resp.json()["result"]


def fetch_all_enterococcus(resource_id: str) -> list:
    """Page through all Enterococcus records in a single resource."""
    records = []
    offset = 0
    print(f"  Fetching resource {resource_id}...")
    while True:
        result = fetch_enterococcus_page(resource_id, offset)
        batch = result["records"]
        records.extend(batch)
        print(f"    offset={offset}, got {len(batch)} records (total so far: {len(records)})")
        if len(batch) < PAGE_SIZE:
            break  # last page
        offset += PAGE_SIZE
    print(f"  Done: {len(records)} total Enterococcus records")
    return records


def parse_records(records: list) -> tuple:
    """
    Parse raw CEDEN records into samples and stations dicts.
    Returns:
        samples: list of dicts for the `samples` table
        stations: dict of StationCode -> station info for the `beaches` table
    """
    samples = []
    stations = {}  # StationCode -> {name, lat, lon}

    for row in records:
        station_code = row.get("StationCode", "").strip()
        station_name = row.get("StationName", "").strip()
        sample_date_raw = row.get("SampleDate", "")
        result = row.get("Result")
        qual_code = row.get("ResultQualCode", "").strip()
        lat = row.get("Latitude")
        lon = row.get("Longitude")

        # Skip if missing key fields
        if not station_code or result is None:
            continue

        # Only accept actual quantified results ("=" means result is the measured value)
        # Skip non-detects ("<"), estimated values, or missing qualifiers
        if qual_code not in ("=", ">"):
            continue

        # Parse result value
        try:
            cfu = float(result)
        except (ValueError, TypeError):
            continue
        if cfu < 0:
            continue

        # Parse date (format: "2026-03-02T00:00:00" → "2026-03-02")
        sample_date = str(sample_date_raw)[:10] if sample_date_raw else ""
        if not sample_date or sample_date == "1950-01-01":  # default/unknown date
            continue

        # Collect station info (for beaches table)
        if station_code not in stations:
            try:
                lat_f = float(lat) if lat is not None else None
                lon_f = float(lon) if lon is not None else None
            except (ValueError, TypeError):
                lat_f = lon_f = None
            stations[station_code] = {
                "id": station_code,
                "name": station_name or station_code,
                "state": "CA",
                "lat": lat_f,
                "lon": lon_f,
            }

        samples.append({
            "beach_id": station_code,
            "sample_date": sample_date,
            "entero_cfu": cfu,
            "source": "CEDEN",
        })

    return samples, stations


def upsert_stations(stations: dict):
    """Insert or update station records in the beaches table."""
    if not stations:
        return
    conn = sqlite3.connect(DB_PATH)
    # Update lat/lon if we have them, but don't overwrite name with blank
    conn.executemany(
        """
        INSERT INTO beaches (id, name, state, lat, lon)
        VALUES (:id, :name, :state, :lat, :lon)
        ON CONFLICT(id) DO UPDATE SET
            name = excluded.name,
            lat  = COALESCE(excluded.lat, beaches.lat),
            lon  = COALESCE(excluded.lon, beaches.lon)
        """,
        stations.values(),
    )
    conn.commit()
    conn.close()
    print(f"  Upserted {len(stations)} stations into beaches table.")


def store_samples(samples: list):
    """Insert new samples; skip duplicates (beach_id + sample_date + entero_cfu)."""
    if not samples:
        print("  No samples to store.")
        return
    conn = sqlite3.connect(DB_PATH)
    conn.executemany(
        "INSERT OR IGNORE INTO samples (beach_id, sample_date, entero_cfu, source) "
        "VALUES (:beach_id, :sample_date, :entero_cfu, :source)",
        samples,
    )
    conn.commit()
    inserted = conn.execute("SELECT COUNT(*) FROM samples WHERE source = 'CEDEN'").fetchone()[0]
    conn.close()
    print(f"  Stored {len(samples)} samples (total CEDEN rows in DB: {inserted}).")


def run_fetch():
    """Main entry point: fetch all CEDEN Enterococcus data and load into SQLite."""
    today = date.today().isoformat()
    print(f"CEDEN fetch started: {today}")
    print(f"Resources to fetch: {len(CEDEN_RESOURCES)}")

    all_samples = []
    all_stations = {}

    for resource_id in CEDEN_RESOURCES:
        records = fetch_all_enterococcus(resource_id)
        samples, stations = parse_records(records)
        all_samples.extend(samples)
        all_stations.update(stations)  # later years overwrite earlier (fresher coords)
        print(f"  Parsed: {len(samples)} valid samples, {len(stations)} unique stations")

    print(f"\nTotal across all resources: {len(all_samples)} samples, {len(all_stations)} stations")
    upsert_stations(all_stations)
    store_samples(all_samples)
    print("\nFetch complete.")


if __name__ == "__main__":
    run_fetch()