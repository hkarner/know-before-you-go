import streamlit as st
import folium
from streamlit_folium import st_folium
from streamlit_geolocation import streamlit_geolocation
import requests
import math
import json
import plotly.express as px
import pandas as pd
import sqlite3
from supabase import create_client
from grades import calculate_grade, GRADE_ORDER
from search import search_beaches

# ---------------------------------------------------------------------------
# SEO: dynamic page title based on query param (must be first st call)
# ---------------------------------------------------------------------------
_beach_param = st.query_params.get("beach", None)
_page_title = (
    f"{_beach_param.replace('-', ' ').title()} Water Quality Grade | Know Before You Go"
    if _beach_param
    else "Know Before You Go"
)
st.set_page_config(
    page_title=_page_title,
    page_icon="🌊",
    layout="wide"
)

# ---------------------------------------------------------------------------
# Supabase client (reads secrets from Streamlit Cloud or local secrets.toml)
# ---------------------------------------------------------------------------
supabase = create_client(
    st.secrets["SUPABASE_URL"],
    st.secrets["SUPABASE_KEY"]
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
GRADE_COLOR = {"A": "#2ec4b6", "B": "#57cc99", "C": "#f4a261", "D": "#e76f51", "F": "#d62828"}
GRADE_LABEL = {"A": "Safe", "B": "Good", "C": "Caution", "D": "Poor", "F": "Advisory / Closed"}

# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------
def inject_jsonld(beach_name: str, slug: str, sample_date: str):
    """Inject JSON-LD structured data for GEO / AI search visibility."""
    schema = {
        "@context": "https://schema.org",
        "@type": "Dataset",
        "name": f"{beach_name} Water Quality Grade",
        "description": (
            f"Weekly water quality grade for {beach_name} based on "
            "EPA BEACON and USGS monitoring data."
        ),
        "url": f"https://hkarner-know-before-you-go.streamlit.app/?beach={slug}",
        "variableMeasured": "Enterococcus bacteria (CFU/100mL)",
        "measurementTechnique": "EPA BEACH Act monitoring, geometric mean of last 5 samples",
        "dateModified": sample_date,
        "publisher": {"@type": "Organization", "name": "Know Before You Go"}
    }
    st.markdown(
        f'<script type="application/ld+json">{json.dumps(schema)}</script>',
        unsafe_allow_html=True
    )


def alert_preferences_form(beach_id: str, beach_name: str):
    """Let users subscribe to grade-change email alerts for a beach."""
    with st.expander("🔔 Get email alerts for this beach"):
        email = st.text_input("Your email", key=f"email_{beach_id}")
        threshold = st.selectbox(
            "Alert me when grade is:",
            ["any change", "C or worse", "D or worse", "F only"],
            key=f"thresh_{beach_id}"
        )
        if st.button("Subscribe", key=f"sub_{beach_id}"):
            if email:
                supabase.table("alert_subscriptions").upsert({
                    "email": email,
                    "beach_id": beach_id,
                    "beach_name": beach_name,
                    "threshold": threshold,
                }).execute()
                st.success(f"Subscribed! You'll get alerts for {beach_name}.")
            else:
                st.warning("Please enter your email.")


def display_grade_card(beach_id: str, display_name: str):
    result = calculate_grade(beach_id)
    grade = result["grade"] or "?"
    color = GRADE_COLOR.get(grade, "#aaa")
    label = GRADE_LABEL.get(grade, "No data")
    sample_date = result["sample_date"] or "Unknown"
    st.markdown(f"""
    <div style='border:2px solid {color}; border-radius:12px; padding:20px; text-align:center;'>
        <h2 style='color:{color}; font-size:72px; margin:0;'>{grade}</h2>
        <p style='font-size:18px; margin:4px 0;'>{label} — Last sampled {sample_date}</p>
    </div>
    """, unsafe_allow_html=True)
    return result.get("sample_date", "")


def get_swell_data(lat: float, lon: float) -> dict:
    try:
        url = f"https://api.swellcloud.net/forecast?lat={lat}&lon={lon}"
        resp = requests.get(url, timeout=8)
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass
    return {}


def display_swell(lat, lon):
    swell = get_swell_data(lat, lon)
    if swell:
        wave = swell.get("wave_height")
        wind = swell.get("wind_speed")
        c1, c2 = st.columns(2)
        if wave: c1.metric("🌊 Wave Height", f"{wave} ft")
        if wind: c2.metric("💨 Wind", f"{wind} mph")


def display_action_buttons(beach_name: str, state: str, lat: float, lon: float, surfline_id: str = None, slug: str = None):
    c1, c2, c3, c4 = st.columns(4)
    c1.link_button("📍 Get Directions", f"https://www.google.com/maps/dir/?api=1&destination={lat},{lon}")
    if state in ("CA", "OR", "WA"):
        c2.link_button("🌊 Heal the Bay", f"https://beachreportcard.org/?search={beach_name.lower().replace(' ', '+')}")
    if surfline_id and slug:
        c3.link_button("🏄 Surfline Report", f"https://www.surfline.com/surf-report/{slug}/{surfline_id}")
    c4.link_button("🤙 Surfrider BWTF", "https://bwtf.surfrider.org/explore")


def display_history_chart(beach_id: str):
    conn = sqlite3.connect("data/beaches.db")
    df = pd.read_sql(
        "SELECT grade_date, grade, geo_mean FROM grade_history WHERE beach_id = ? ORDER BY grade_date",
        conn, params=(beach_id,)
    )
    conn.close()
    if df.empty:
        st.info("No grade history available yet.")
        return
    time_range = st.selectbox("Time range", ["30 days", "90 days", "1 year", "5 years"], index=2)
    days = {"30 days": 30, "90 days": 90, "1 year": 365, "5 years": 1825}[time_range]
    df["grade_date"] = pd.to_datetime(df["grade_date"])
    df = df[df["grade_date"] >= pd.Timestamp.now() - pd.Timedelta(days=days)]
    fig = px.line(df, x="grade_date", y="geo_mean",
                  title=f"Enterococcus levels (geo mean) — {time_range}",
                  labels={"grade_date": "Date", "geo_mean": "CFU/100mL"})
    for level, lbl in [(35, "A/B"), (70, "B/C"), (104, "C/D"), (200, "D/F")]:
        fig.add_hline(y=level, line_dash="dot", annotation_text=lbl, line_color="gray")
    st.plotly_chart(fig, use_container_width=True)


def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    return R * 2 * math.asin(math.sqrt(a))


def display_map(beaches_with_grades: list, center_lat: float, center_lon: float):
    color_map = {"A": "green", "B": "lightgreen", "C": "orange", "D": "red", "F": "darkred"}
    m = folium.Map(location=[center_lat, center_lon], zoom_start=11)
    for beach in beaches_with_grades:
        folium.Marker(
            [beach["lat"], beach["lon"]],
            popup=f"{beach['name']}: {beach['grade']}",
            icon=folium.Icon(color=color_map.get(beach["grade"], "gray"))
        ).add_to(m)
    st_folium(m, width=700)


def display_footer():
    st.divider()
    st.markdown("##### More resources:")
    c1, c2 = st.columns(2)
    c1.link_button("🌊 Heal the Bay", "https://healthebay.org")
    c2.link_button("🤙 Surfrider Foundation", "https://bwtf.surfrider.org")
    st.image("assets/hk_creator_mark_blue.png", width=220)


# ---------------------------------------------------------------------------
# Main app
# ---------------------------------------------------------------------------

# Header
st.image("assets/kbyg_welcome_banner.png", use_container_width=True)
st.caption(
    "US beach water quality grades for surf spots and swimming beaches — "
    "powered by EPA + USGS data 🌊"
)
st.divider()

# Search
query = st.text_input("", placeholder="Search by beach name, surf spot, city, or zip...")
location = streamlit_geolocation()

if query:
    results = search_beaches(query)
    if results:
        options = {r["display"]: r for r in results}
        selected_name = st.selectbox("Select a beach:", list(options.keys()))
        selected = options[selected_name]
        selected_beach_id = selected["beach_id"]
        selected_slug = selected.get("slug", selected_beach_id)
        selected_state = selected.get("state", "")

        # Grade card (returns sample_date for JSON-LD)
        st.markdown(f"## {selected_name}")
        sample_date = display_grade_card(selected_beach_id, selected_name)

        # GEO: inject JSON-LD structured data
        inject_jsonld(selected_name, selected_slug, sample_date or "")

        # Alert preferences
        alert_preferences_form(selected_beach_id, selected_name)

        # History chart
        st.divider()
        st.markdown("### 📈 Water Quality History")
        display_history_chart(selected_beach_id)

        st.divider()
        display_footer()
    else:
        st.warning("No beaches found. Try a different name or zip code.")

# Use My Location
if location and location.get("latitude"):
    user_lat = location["latitude"]
    user_lon = location["longitude"]
    radius_km = 16
    conn = sqlite3.connect("data/beaches.db")
    all_beaches = conn.execute("SELECT id, name, state, latitude, longitude FROM beaches").fetchall()
    conn.close()
    nearby = [b for b in all_beaches if b[3] and b[4] and haversine(user_lat, user_lon, b[3], b[4]) <= radius_km]
    nearby.sort(key=lambda b: haversine(user_lat, user_lon, b[3], b[4]))
    st.markdown(f"### 📍 Beaches near you ({len(nearby)} found)")
    for beach in nearby[:5]:
        st.markdown(f"**{beach[1]}, {beach[2]}**")
        display_grade_card(beach[0], beach[1])