import sqlite3
import requests
import pandas as pd
from io import StringIO
from datetime import date, timedelta

DB_PATH = "data/beaches.db"
START_DATE = (date.today() - timedelta(days=5*365)).isoformat()
END_DATE = date.today().isoformat()
WQP = "https://www.waterqualitydata.us/data"

BEACH_COORDS = {
    "Zuma":         (34.0177, -118.8226, 5),
    "Venice":       (33.9850, -118.4695, 3),
    "Santa Monica": (34.0050, -118.4959, 3),
    "Malibu":       (34.0366, -118.6922, 5),
    "Hermosa":      (33.8622, -118.3995, 3),
    "Redondo":      (33.8447, -118.3951, 3),
    "Huntington":   (33.6595, -118.0000, 5),
    "Newport":      (33.6103, -117.9281, 5),
    "Laguna":       (33.5427, -117.7854, 5),
    "Doheny":       (33.4613, -117.6811, 3),
}

def find_stations(beach_name: str, lat: float, lon: float, radius_miles: float) -> list:
    """Step 1: find WQP monitoring station IDs near a beach via Station/search."""
    params = {
        "characteristicName": "Enterococcus",
        "within": str(radius_miles),
        "lat": str(lat),
        "long": str(lon),  # NOTE: WQP uses 'long', not 'lon'
        "mimeType": "csv",
        "zip": "no",
        "providers": ["NWIS", "STORET"],
    }
    resp = requests.get(f"{WQP}/Station/search", params=params, timeout=30)
    if resp.status_code != 200:
        print(f"  Station search failed {resp.status_code}: {resp.text[:200]}")
        return []
    df = pd.read_csv(StringIO(resp.text), low_memory=False)
    if df.empty:
        return []
    site_ids = df["MonitoringLocationIdentifier"].dropna().tolist()
    print(f"  Found {len(site_ids)} monitoring stations near {beach_name}")
    return site_ids

def fetch_results(site_ids: list, beach_name: str) -> list:
    """Step 2: fetch Enterococcus results for specific site IDs via Result/search."""
    if not site_ids:
        return []
    all_samples = []
    batch_size = 5
    for i in range(0, len(site_ids), batch_size):
        batch = site_ids[i:i + batch_size]
        params = {
            "siteid": batch,
            "characteristicName": "Enterococcus",
            "startDateLo": START_DATE,
            "startDateHi": END_DATE,
            "mimeType": "csv",
            "zip": "no",
        }
        resp = requests.get(f"{WQP}/Result/search", params=params, timeout=120)
        if resp.status_code != 200:
            print(f"  Batch {i//batch_size + 1} failed {resp.status_code}: {resp.text[:100]}")
            continue
        df = pd.read_csv(StringIO(resp.text), low_memory=False)
        print(f"  Batch {i//batch_size + 1}: {len(df)} rows")
        for _, row in df.iterrows():
            try:
                raw = str(row.get("ResultMeasureValue", "") or "").strip().replace(",", "")
                val = float(raw) if raw else None
            except (ValueError, TypeError):
                continue
            if val is None or val < 0:
                continue
            all_samples.append({
                "beach_id": str(row.get("MonitoringLocationIdentifier", beach_name))[:100],
                "sample_date": str(row.get("ActivityStartDate", ""))[:10],
                "entero_cfu": val,
                "source": "WQP",
            })
    print(f"  Got {len(all_samples)} total samples for {beach_name}")
    return all_samples

def fetch_wqp(beach_name: str) -> list:
    """Fetch Enterococcus samples for a named beach — two-step: stations then results."""
    coords = next(
        ((lat, lon, r) for key, (lat, lon, r) in BEACH_COORDS.items()
         if key.lower() in beach_name.lower() or beach_name.lower() in key.lower()),
        None
    )
    if not coords:
        print(f"  No coordinates found for '{beach_name}'.")
        print(f"  Available: {list(BEACH_COORDS.keys())}")
        return []

    lat, lon, radius = coords
    print(f"  Looking up stations near ({lat}, {lon}), radius={radius}mi...")
    site_ids = find_stations(beach_name, lat, lon, radius)
    if not site_ids:
        print(f"  No monitoring stations found near {beach_name}.")
        return []
    return fetch_results(site_ids, beach_name)

def store_samples(samples: list):
    if not samples:
        print("  No samples to store.")
        return
    conn = sqlite3.connect(DB_PATH)
    conn.executemany(
        "INSERT OR IGNORE INTO samples (beach_id, sample_date, entero_cfu, source) "
        "VALUES (:beach_id, :sample_date, :entero_cfu, :source)",
        samples
    )
    conn.commit()
    conn.close()
    print(f"  Stored {len(samples)} samples.")

if __name__ == "__main__":
    beach_name = "Zuma"
    print(f"Fetching samples for {beach_name}...")
    samples = fetch_wqp(beach_name)
    print(f"Fetched {len(samples)} samples")
    store_samples(samples)
    print("Done.")