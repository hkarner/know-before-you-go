import streamlit as st

def render_about():
    st.title("About Know Before You Go")
    st.caption("How beach water quality grades are calculated — and what they mean for swimmers and surfers.")

    st.divider()

    st.markdown("## What this app does")
    st.markdown("""
Know Before You Go shows current water quality grades for US beaches and surf spots.
Grades are calculated from Enterococcus bacteria measurements collected by EPA and USGS
monitoring programs under the BEACH Act.

Users can search by beach name, surf spot alias, city, or zip code and see:
- A current A–F water quality grade
- The date of the most recent sample
- A 5-year history of water quality at that location
- Live surf conditions (wave height, wind)
- Links to official reports and nonprofit resources
    """)

    st.divider()

    st.markdown("## How grades are calculated")
    st.markdown("""
Grades are based on **Enterococcus bacteria concentration** measured in colony-forming units
per 100 milliliters of water (CFU/100mL). Enterococcus is the EPA-recommended indicator
bacterium for recreational saltwater quality under the BEACH Act.

The grade reflects the **geometric mean** of the most recent 5 samples at each monitoring
site. The geometric mean is the standard method used by official beach monitoring programs
because it accurately represents typical conditions while reducing the weight of isolated spikes.
    """)

    st.markdown("### Grading scale")
    st.markdown("""
| Grade | CFU/100mL | Status |
|-------|-----------|--------|
| **A** | < 35 | Safe |
| **B** | 35–70 | Good |
| **C** | 70–104 | Caution |
| **D** | 104–200 | Poor |
| **F** | > 200 | Advisory / Closed |
    """)
    st.caption("Thresholds based on EPA BEACH Act recreational water quality criteria.")

    st.divider()

    st.markdown("## Data sources")
    st.markdown("""
- **EPA BEACON** (Beach Advisory and Closure Online Notification) — national beach monitoring
  data collected under the BEACH Act. Includes Enterococcus sample results, advisories, and
  closures. Data is collected by state and local health agencies and reported to EPA.
- **USGS Water Quality Portal** — historical water quality measurements going back decades.
  Used to calculate the 5-year history shown in the app.

Both sources are free, public, and updated regularly by federal agencies.
    """)

    st.divider()

    st.markdown("## Data freshness")
    st.markdown("""
Most beach monitoring programs sample weekly during swim season (roughly Memorial Day through
Labor Day) and less frequently in the off-season. The grade shown reflects the geometric mean
of the most recent available samples — the "Last sampled" date shown on each grade card
indicates when the most recent measurement was taken.

Grades are recalculated daily by an automated process. If no new sample data has been
collected recently, the grade reflects the most recent available data.
    """)

    st.divider()

    st.markdown("## Limitations")
    st.markdown("""
- **Coverage varies by location.** Not all beaches have active monitoring programs.
  Beaches without recent sample data will show no grade.
- **Grades are not real-time.** A grade reflects historical samples, not current conditions.
  Conditions can change rapidly after heavy rain.
- **Freshwater beaches** use E. coli rather than Enterococcus as the indicator bacterium.
  Thresholds may differ by state.
- **This app is not an official source.** Always check your local health department or
  official beach advisory systems before swimming.
    """)

    st.divider()

    st.markdown("## More resources")
    c1, c2 = st.columns(2)
    c1.link_button("🌊 Heal the Bay Beach Report Card", "https://beachreportcard.org")
    c2.link_button("🤙 Surfrider BWTF", "https://bwtf.surfrider.org")
    st.link_button("EPA BEACON", "https://beacon.epa.gov")
    st.link_button("USGS Water Quality Portal", "https://www.waterqualitydata.us")


render_about()