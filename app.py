"""Philadelphia 311 dashboard.

The notebook used START_DATE and END_DATE to filter request_date, then
drew two charts from that filtered table. Those two variables are now
the date controls in the sidebar. The charts use the same rules as the
notebook.
"""

import json
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import pydeck as pdk
import streamlit as st

DATA_FILE = Path(__file__).parent / "311_2025_dashboard.csv"
ZIP_SHAPES = Path(__file__).parent / "philadelphia_zip_codes.geojson"

FOCUS_TYPES = [
    "Maintenance Complaint",
    "Rubbish/Recyclable Material Collection",
    "Abandoned Vehicle",
    "Illegal Dumping",
    "Graffiti Removal",
]
SHORT_LABELS = {
    "Maintenance Complaint": "Maintenance",
    "Rubbish/Recyclable Material Collection": "Rubbish / recycling",
    "Abandoned Vehicle": "Abandoned vehicle",
    "Illegal Dumping": "Illegal dumping",
    "Graffiti Removal": "Graffiti",
    "Other": "Other",
}
COLORS = {
    "Maintenance Complaint": "#3182bd",
    "Rubbish/Recyclable Material Collection": "#31a354",
    "Abandoned Vehicle": "#fd8d3c",
    "Illegal Dumping": "#de2d26",
    "Graffiti Removal": "#756bb1",
    "Other": "#bdbdbd",
}


st.set_page_config(
    page_title="Philadelphia 311",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
        .stApp { background: #f4f7f8; }
        [data-testid="stHeader"] { background: transparent; }
        .dash-kicker {
            color: #1f6f8b;
            font-size: 0.78rem;
            font-weight: 700;
            letter-spacing: 0.14em;
            text-transform: uppercase;
            margin-bottom: 0.15rem;
        }
        .dash-title {
            color: #16303a;
            font-size: 2rem;
            font-weight: 700;
            line-height: 1.15;
            margin: 0 0 0.35rem 0;
        }
        .dash-sub {
            color: #4d626b;
            font-size: 1.02rem;
            margin: 0;
        }
        [data-testid="stMetric"] {
            background: #ffffff;
            border: 1px solid #e1e8eb;
            border-radius: 12px;
            padding: 0.85rem 1rem 0.7rem 1rem;
        }
        [data-testid="stMetricLabel"] { color: #5c727b; }
        [data-testid="stMetricValue"] { color: #16303a; }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data
def load_requests():
    """Read the reduced 2025 file and restore request_date as a real date."""
    df = pd.read_csv(DATA_FILE)
    df["request_date"] = pd.to_datetime(df["request_date"], errors="coerce")
    return df.dropna(subset=["request_date"])


def located_requests(filtered_df):
    """Service requests that have a Philadelphia ZIP code.

    Information Requests stay in the full file, but about 96% of them
    have no ZIP code. Leaving them in a ZIP chart would make most areas
    look empty. ZIP codes outside 19102–19154 are not Philadelphia.
    """
    zipcode = pd.to_numeric(filtered_df["zipcode"], errors="coerce")
    located = filtered_df.loc[
        zipcode.between(19102, 19154)
        & (filtered_df["service_name"] != "Information Request")
    ].copy()
    located["zip"] = zipcode.loc[located.index].astype("int64")
    return located


def zip_summary(located):
    """Top 10 ZIP codes and the median used for the dashed line."""
    zip_counts = located.groupby("zip").size().sort_values(ascending=False)
    top10 = zip_counts.head(10)

    # The dashed line compares the leaders with a typical busy ZIP.
    # A short date range may never reach 1,000 requests, so then the
    # line uses ZIP codes with at least 20 requests.
    comparable = zip_counts[zip_counts >= 1000]
    median_label = "1,000+ requests"
    if len(comparable) < 5:
        comparable = zip_counts[zip_counts >= 20]
        median_label = "20+ requests"

    median_requests = comparable.median() if len(comparable) else None
    top_share = top10.sum() / len(located)
    return top10, median_requests, median_label, top_share


def request_mix(located, top_zips):
    """Share of each focus service inside the busiest ZIP codes."""
    high_volume = located[located["zip"].isin(top_zips)]
    shares = high_volume.groupby(["zip", "service_name"]).size().unstack(fill_value=0)
    for service in FOCUS_TYPES:
        if service not in shares.columns:
            shares[service] = 0
    shares = shares.div(shares.sum(axis=1), axis=0).reindex(list(top_zips))
    shares["Other"] = 1 - shares[FOCUS_TYPES].sum(axis=1)
    return shares.fillna(0)


@st.cache_data
def load_zip_shapes():
    """Philadelphia ZIP code outlines from the city's open data."""
    with ZIP_SHAPES.open() as shapes:
        return json.load(shapes)


def zip_fill(count, max_count):
    """Gray when a ZIP has no requests in the selected dates, blue when it does."""
    if count <= 0 or max_count <= 0:
        return 214, 221, 224, 150
    # The quietest active ZIP still reads as blue. Darker means more requests.
    strength = 0.28 + 0.72 * (count / max_count)
    start = (198, 224, 235)
    end = (23, 92, 122)
    return tuple(
        int(light + (dark - light) * strength) for light, dark in zip(start, end)
    ) + (225,)


def zip_map(located):
    """Color each ZIP outline by how many located requests it has."""
    counts = located.groupby("zip").size()
    max_count = int(counts.max()) if len(counts) else 0
    features = []
    for feature in load_zip_shapes()["features"]:
        zip_code = int(feature["properties"]["code"])
        count = int(counts.get(zip_code, 0))
        red, green, blue, alpha = zip_fill(count, max_count)
        features.append(
            {
                "type": "Feature",
                "geometry": feature["geometry"],
                "properties": {
                    "zip": str(zip_code),
                    "requests": f"{count:,}",
                    "r": red,
                    "g": green,
                    "b": blue,
                    "a": alpha,
                },
            }
        )

    layer = pdk.Layer(
        "GeoJsonLayer",
        {"type": "FeatureCollection", "features": features},
        stroked=True,
        filled=True,
        get_fill_color="[properties.r, properties.g, properties.b, properties.a]",
        get_line_color=[22, 48, 58, 120],
        line_width_min_pixels=1,
        pickable=True,
        auto_highlight=True,
    )
    view = pdk.ViewState(latitude=40.005, longitude=-75.15, zoom=10.3)
    return pdk.Deck(
        layers=[layer],
        initial_view_state=view,
        map_provider="carto",
        map_style="light",
        tooltip={"text": "ZIP {zip}\n{requests} located requests"},
    )


def style_axes(ax):
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.tick_params(colors="#33464d")
    ax.xaxis.label.set_color("#33464d")
    ax.yaxis.label.set_color("#33464d")
    ax.title.set_color("#16303a")


def chart_busiest_zips(top10, median_requests, median_label, top_share, start_date, end_date):
    plot_counts = top10.sort_values()
    fig, ax = plt.subplots(figsize=(11, 5.2), facecolor="white")
    ax.set_facecolor("white")
    ax.barh(plot_counts.index.astype(str), plot_counts.values, color="#2c7fb8", height=0.72)
    if median_requests is not None and pd.notna(median_requests):
        ax.axvline(median_requests, color="#e34a33", linestyle="--", linewidth=1.5)
        line_note = f"dashed line = median ZIP with {median_label}: {median_requests:,.0f}"
    else:
        line_note = "not enough ZIP codes to draw a median line"
    ax.set_xlabel("Located service requests")
    ax.set_ylabel("ZIP code")
    zip_count = len(top10)
    zip_word = "Ten" if zip_count == 10 else str(zip_count)
    ax.set_title(
        f"{zip_word} ZIP codes account for {top_share:.0%} of located 311 requests\n"
        f"({start_date:%b %d, %Y} through {end_date:%b %d, %Y}; {line_note})",
        loc="left",
        fontsize=13,
        pad=12,
    )
    style_axes(ax)
    fig.tight_layout()
    return fig


def chart_request_mix(shares, start_date, end_date):
    zip_count = len(shares)
    zip_order = list(shares.index)[::-1]
    stack_order = FOCUS_TYPES + ["Other"]
    left = [0] * len(zip_order)

    fig, ax = plt.subplots(figsize=(11, 6.2), facecolor="white")
    ax.set_facecolor("white")
    for service in stack_order:
        values = shares.loc[zip_order, service].tolist()
        ax.barh(
            [str(zip_code) for zip_code in zip_order],
            values,
            left=left,
            color=COLORS[service],
            label=SHORT_LABELS[service],
            height=0.72,
        )
        left = [so_far + added for so_far, added in zip(left, values)]

    ax.set_xlim(0, 1)
    ax.set_xlabel("Share of that ZIP's located requests")
    ax.set_ylabel("ZIP code")
    ax.set_title(
        f"Request mix in the {zip_count} highest-volume ZIP codes\n"
        f"({start_date:%b %d, %Y} through {end_date:%b %d, %Y})",
        loc="left",
        fontsize=13,
        pad=12,
    )
    ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda value, _pos: f"{value:.0%}"))
    ax.legend(
        loc="upper center",
        bbox_to_anchor=(0.5, -0.16),
        ncol=3,
        frameon=False,
    )
    style_axes(ax)
    fig.tight_layout()
    fig.subplots_adjust(bottom=0.2)
    return fig


df = load_requests()
min_date = df["request_date"].min().date()
max_date = df["request_date"].max().date()

st.sidebar.markdown("### Date range")
st.sidebar.caption("The map and both charts use only requests filed inside this window.")
start_date = st.sidebar.date_input(
    "Start date",
    value=min_date,
    min_value=min_date,
    max_value=max_date,
)
end_date = st.sidebar.date_input(
    "End date",
    value=max_date,
    min_value=min_date,
    max_value=max_date,
)
st.sidebar.caption(
    "The map and ZIP charts leave out Information Requests. Most of those "
    "calls have no ZIP code, so they are not a neighborhood workload."
)

st.markdown('<p class="dash-kicker">Philadelphia 311</p>', unsafe_allow_html=True)
st.markdown('<p class="dash-title">Where service requests concentrate</p>', unsafe_allow_html=True)
st.markdown(
    '<p class="dash-sub">Located requests by ZIP code, and the problems those busy ZIP codes report.</p>',
    unsafe_allow_html=True,
)

if start_date > end_date:
    st.error("Start date must be on or before the end date.")
    st.stop()

filtered_df = df[
    (df["request_date"] >= pd.to_datetime(start_date))
    & (df["request_date"] <= pd.to_datetime(end_date))
].copy()
located = located_requests(filtered_df)

st.caption(
    f"Showing {start_date:%B %d, %Y} through {end_date:%B %d, %Y}. "
    f"{len(filtered_df):,} requests in this period."
)

if located.empty:
    st.warning("No located service requests fall in these dates. Widen the date range.")
    st.stop()

top10, median_requests, median_label, top_share = zip_summary(located)
shares = request_mix(located, top10.index)
busiest_zip = int(top10.index[0])
busiest_count = int(top10.iloc[0])
graffiti_zip = int(shares["Graffiti Removal"].idxmax())
vehicle_zip = int(shares["Abandoned Vehicle"].idxmax())
graffiti_share = shares.loc[graffiti_zip, "Graffiti Removal"]
vehicle_share = shares.loc[vehicle_zip, "Abandoned Vehicle"]

metric_cols = st.columns(4, gap="medium")
metric_cols[0].metric("Requests in period", f"{len(filtered_df):,}")
metric_cols[1].metric("Located service requests", f"{len(located):,}")
metric_cols[2].metric("Share in top 10 ZIPs", f"{top_share:.0%}")
metric_cols[3].metric(
    "Busiest ZIP",
    str(busiest_zip),
    help=f"{busiest_count:,} located service requests",
)

st.write("")
st.subheader("Active ZIP codes")
st.pydeck_chart(zip_map(located), height=520)
st.caption(
    "A ZIP code lights up when it has located service requests in the dates "
    "you chose. Darker blue means more requests. ZIP codes with none in this "
    "period stay gray. Hover a ZIP code to see its count."
)

st.subheader("Busiest ZIP codes")
st.pyplot(
    chart_busiest_zips(
        top10, median_requests, median_label, top_share, start_date, end_date
    ),
    clear_figure=True,
)
st.caption(
    "Bars are counts of requests, not requests per resident. A larger ZIP can "
    "rank high without having a higher rate. The dashed line is a typical busy "
    f"ZIP in this period ({median_label.lower()})."
)

st.subheader("Request mix in those ZIP codes")
st.pyplot(
    chart_request_mix(shares, start_date, end_date),
    clear_figure=True,
)
local_notes = []
if graffiti_share > 0:
    local_notes.append(f"graffiti is the widest in {graffiti_zip} ({graffiti_share:.0%})")
if vehicle_share > 0:
    local_notes.append(
        f"abandoned vehicles are the widest in {vehicle_zip} ({vehicle_share:.0%})"
    )
local_sentence = ""
if local_notes:
    local_sentence = " In this period, " + " and ".join(local_notes) + "."

st.caption(
    "Each bar totals 100% of that ZIP code. Similar bands mean these areas need "
    f"the same core services.{local_sentence}"
)
