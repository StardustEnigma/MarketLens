
import requests
import pandas as pd
import streamlit as st


# ============================================================
# CONFIG
# ============================================================

API_URL = "http://127.0.0.1:8000"

st.set_page_config(
    page_title="MarketLens",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ============================================================
# CUSTOM CSS
# ============================================================

st.markdown(
    """
    <style>

    .main {
        padding-top: 1rem;
    }

    .block-container {
        padding-top: 2rem;
        padding-bottom: 3rem;
        max-width: 1500px;
    }

    .market-title {
        font-size: 3rem;
        font-weight: 700;
        margin-bottom: 0;
    }

    .market-subtitle {
        color: #9ca3af;
        font-size: 1rem;
        margin-top: 0.2rem;
        margin-bottom: 2rem;
    }

    .event-card {
        padding: 1.2rem;
        border-radius: 12px;
        background: #171923;
        border: 1px solid #2a2d3a;
        margin-bottom: 1rem;
    }

    .critical {
        color: #ff4b4b;
        font-weight: 700;
    }

    .high {
        color: #ffa62b;
        font-weight: 700;
    }

    .medium {
        color: #f5d547;
        font-weight: 700;
    }

    .low {
        color: #45d483;
        font-weight: 700;
    }

    .stock-pill {
        display: inline-block;
        padding: 0.35rem 0.7rem;
        margin: 0.2rem;
        border-radius: 999px;
        background: #252938;
        border: 1px solid #35394b;
        font-size: 0.85rem;
    }

    </style>
    """,
    unsafe_allow_html=True
)


# ============================================================
# API FUNCTIONS
# ============================================================

def get_events():

    response = requests.get(
        f"{API_URL}/events",
        timeout=10
    )

    response.raise_for_status()

    return response.json()


def get_event(event_id):

    response = requests.get(
        f"{API_URL}/events/{event_id}",
        timeout=10
    )

    response.raise_for_status()

    return response.json()


def get_explanation(event_id):

    response = requests.get(
        f"{API_URL}/events/{event_id}/explanation",
        timeout=60
    )

    response.raise_for_status()

    return response.json()


# ============================================================
# LOAD DATA
# ============================================================

try:

    events = get_events()

except requests.exceptions.RequestException:

    st.error(
        "Unable to connect to MarketLens API."
    )

    st.code(
        "uvicorn main:app --reload"
    )

    st.stop()


if not events:

    st.warning(
        "No market events available."
    )

    st.stop()


events_df = pd.DataFrame(events)


# ============================================================
# DATA PREPARATION
# ============================================================

events_df["Start_Date"] = pd.to_datetime(
    events_df["Start_Date"]
)

events_df["End_Date"] = pd.to_datetime(
    events_df["End_Date"]
)

events_df["Peak_Date"] = pd.to_datetime(
    events_df["Peak_Date"]
)

events_df = events_df.sort_values(
    "Start_Date"
)


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.markdown(
        "# 📈 MarketLens"
    )

    st.caption(
        "Market anomaly detection & event surveillance"
    )

    st.divider()

    page = st.radio(
        "Navigation",
        [
            "Overview",
            "Event Explorer"
        ]
    )

    st.divider()

    st.caption(
        "Detection Engine"
    )

    st.write(
        "Isolation Forest"
    )

    st.caption(
        "Explanation Engine"
    )

    st.write(
        "SHAP"
    )

    st.caption(
        "Backend"
    )

    st.write(
        "FastAPI"
    )


# ============================================================
# HEADER
# ============================================================

st.markdown(
    '<div class="market-title">MarketLens</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="market-subtitle">'
    'Market anomaly detection and event surveillance system'
    '</div>',
    unsafe_allow_html=True
)


# ============================================================
# OVERVIEW PAGE
# ============================================================

if page == "Overview":

    st.header(
        "Market Overview"
    )

    # --------------------------------------------------------
    # Metrics
    # --------------------------------------------------------

    total_events = len(events_df)

    critical_events = (
        events_df["Severity"] == "CRITICAL"
    ).sum()

    high_events = (
        events_df["Severity"] == "HIGH"
    ).sum()

    medium_events = (
        events_df["Severity"] == "MEDIUM"
    ).sum()

    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        "Total Events",
        total_events
    )

    col2.metric(
        "Critical Events",
        critical_events
    )

    col3.metric(
        "High Events",
        high_events
    )

    col4.metric(
        "Medium Events",
        medium_events
    )

    st.divider()

    # --------------------------------------------------------
    # Stress Timeline
    # --------------------------------------------------------

    st.header(
        "Market Stress Timeline"
    )

    stress_df = events_df[
        [
            "Peak_Date",
            "Peak_Stress"
        ]
    ].copy()

    stress_df = stress_df.set_index(
        "Peak_Date"
    )

    st.line_chart(
        stress_df,
        use_container_width=True
    )

    st.caption(
        "Peak market stress recorded for each detected event."
    )

    st.divider()

    # --------------------------------------------------------
    # Severity Distribution
    # --------------------------------------------------------

    st.header(
        "Event Severity Distribution"
    )

    severity_counts = (
        events_df["Severity"]
        .value_counts()
        .rename_axis("Severity")
        .reset_index(name="Events")
    )

    col1, col2 = st.columns(
        [1, 2]
    )

    with col1:

        st.dataframe(
            severity_counts,
            use_container_width=True,
            hide_index=True
        )

    with col2:

        chart_data = (
            severity_counts
            .set_index("Severity")
        )

        st.bar_chart(
            chart_data
        )

    st.divider()

    # --------------------------------------------------------
    # Event Timeline Table
    # --------------------------------------------------------

    st.header(
        "Detected Market Events"
    )

    display_df = events_df.copy()

    display_df["Start_Date"] = (
        display_df["Start_Date"]
        .dt.strftime("%Y-%m-%d")
    )

    display_df["End_Date"] = (
        display_df["End_Date"]
        .dt.strftime("%Y-%m-%d")
    )

    display_df["Peak_Date"] = (
        display_df["Peak_Date"]
        .dt.strftime("%Y-%m-%d")
    )

    st.dataframe(
        display_df[
            [
                "Event_ID",
                "Start_Date",
                "End_Date",
                "Event_Type",
                "Severity",
                "Duration",
                "Peak_Stress",
                "Peak_Date"
            ]
        ],
        use_container_width=True,
        hide_index=True
    )


# ============================================================
# EVENT EXPLORER
# ============================================================

if page == "Event Explorer":

    st.header(
        "Event Explorer"
    )

    event_ids = events_df[
        "Event_ID"
    ].dropna().tolist()

    selected_event_id = st.selectbox(
        "Select a market event",
        event_ids
    )

    try:

        event = get_event(
            selected_event_id
        )

    except requests.exceptions.RequestException as error:

        st.error(
            f"Unable to load event: {error}"
        )

        st.stop()


    # --------------------------------------------------------
    # Event Header
    # --------------------------------------------------------

    st.subheader(
        event["Event_Type"]
    )

    severity = event["Severity"]

    severity_class = severity.lower()

    st.markdown(
        f"""
        <div class="event-card">

        <div style="font-size:1.4rem;">
            <span class="{severity_class}">
                {severity}
            </span>
        </div>

        <div style="color:#9ca3af;">
            Event ID: {event["Event_ID"]}
        </div>

        </div>
        """,
        unsafe_allow_html=True
    )


    # --------------------------------------------------------
    # Event Metrics
    # --------------------------------------------------------

    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        "Peak Stress",
        f'{event["Peak_Stress"]:.2f}'
    )

    col2.metric(
        "Duration",
        f'{event["Duration"]} day(s)'
    )

    col3.metric(
        "Peak Date",
        event["Peak_Date"]
    )

    col4.metric(
        "Severity",
        event["Severity"]
    )


    st.write(
        f'**Period:** {event["Start_Date"]} → '
        f'{event["End_Date"]}'
    )


    st.divider()


    # --------------------------------------------------------
    # Affected Stocks
    # --------------------------------------------------------

    st.header(
        "Affected Stocks"
    )

    affected_stocks = event.get(
        "Affected_Stocks",
        []
    )

    if affected_stocks:

        stock_html = ""

        for stock in affected_stocks:

            stock_html += (
                f'<span class="stock-pill">'
                f'{stock}'
                f'</span>'
            )

        st.markdown(
            stock_html,
            unsafe_allow_html=True
        )

    else:

        st.info(
            "No individual affected stocks recorded."
        )


    st.divider()


    # --------------------------------------------------------
    # SHAP Explanation
    # --------------------------------------------------------

    st.header(
        "SHAP Event Explanation"
    )

    st.caption(
        "Explains which features contributed most "
        "to each detected stock anomaly."
    )


    if st.button(
        "Generate SHAP Explanation",
        type="primary",
        use_container_width=False
    ):

        try:

            with st.spinner(
                "Running SHAP explanation..."
            ):

                explanation = get_explanation(
                    selected_event_id
                )

        except requests.exceptions.RequestException as error:

            st.error(
                f"Unable to generate explanation: {error}"
            )

            st.stop()


        anomaly_count = explanation[
            "Anomalies"
        ]


        st.success(
            f'{anomaly_count} anomalous stocks detected '
            f'on {explanation["Event_Date"]}'
        )


        if anomaly_count == 0:

            st.info(
                "This event has no individual stock anomalies "
                "to explain."
            )

        else:

            # ------------------------------------------------
            # Stock explanations
            # ------------------------------------------------

            for stock in explanation[
                "Explanations"
            ]:

                st.subheader(
                    stock["Symbol"]
                )

                col1, col2, col3 = st.columns(3)

                col1.metric(
                    "Return",
                    f'{stock["Return"]:.4f}'
                )

                col2.metric(
                    "Volatility 20D",
                    f'{stock["Volatility_20"]:.4f}'
                )

                col3.metric(
                    "Volume Ratio",
                    f'{stock["Volume_Ratio"]:.2f}'
                )


                shap_df = pd.DataFrame(
                    stock["Features"]
                )


                shap_df["Abs_SHAP"] = (
                    shap_df["SHAP"].abs()
                )


                shap_df = shap_df.sort_values(
                    "Abs_SHAP",
                    ascending=True
                )


                # --------------------------------------------
                # SHAP chart
                # --------------------------------------------

                st.bar_chart(
                    shap_df.set_index(
                        "Feature"
                    )["SHAP"],
                    horizontal=True
                )


                st.dataframe(
                    shap_df[
                        [
                            "Feature",
                            "Value",
                            "SHAP"
                        ]
                    ].sort_values(
                        "SHAP",
                        key=lambda x: x.abs(),
                        ascending=False
                    ),
                    use_container_width=True,
                    hide_index=True
                )


                st.divider()

