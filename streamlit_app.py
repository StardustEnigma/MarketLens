import datetime
import requests
import pandas as pd
import streamlit as st

# ============================================================
# CONFIG
# ============================================================

API_URL = "http://127.0.0.1:8000"

st.set_page_config(
    page_title="MarketLens — Market Surveillance System",
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
        padding-top: 1.5rem;
        padding-bottom: 3rem;
        max-width: 1500px;
    }
    .market-title {
        font-size: 2.8rem;
        font-weight: 700;
        margin-bottom: 0;
        letter-spacing: -0.5px;
    }
    .market-subtitle {
        color: #9ca3af;
        font-size: 1.05rem;
        margin-top: 0.2rem;
        margin-bottom: 1.5rem;
    }
    .event-card {
        padding: 1.2rem;
        border-radius: 12px;
        background: #171923;
        border: 1px solid #2a2d3a;
        margin-bottom: 1rem;
    }
    .badge-critical {
        display: inline-block;
        padding: 0.35rem 0.8rem;
        border-radius: 6px;
        background: rgba(255, 75, 75, 0.15);
        color: #ff4b4b;
        border: 1px solid rgba(255, 75, 75, 0.4);
        font-weight: 700;
        font-size: 1rem;
    }
    .badge-high {
        display: inline-block;
        padding: 0.35rem 0.8rem;
        border-radius: 6px;
        background: rgba(255, 166, 43, 0.15);
        color: #ffa62b;
        border: 1px solid rgba(255, 166, 43, 0.4);
        font-weight: 700;
        font-size: 1rem;
    }
    .badge-medium {
        display: inline-block;
        padding: 0.35rem 0.8rem;
        border-radius: 6px;
        background: rgba(245, 213, 71, 0.15);
        color: #f5d547;
        border: 1px solid rgba(245, 213, 71, 0.4);
        font-weight: 700;
        font-size: 1rem;
    }
    .badge-low {
        display: inline-block;
        padding: 0.35rem 0.8rem;
        border-radius: 6px;
        background: rgba(69, 212, 131, 0.15);
        color: #45d483;
        border: 1px solid rgba(69, 212, 131, 0.4);
        font-weight: 700;
        font-size: 1rem;
    }
    .stock-pill {
        display: inline-block;
        padding: 0.35rem 0.75rem;
        margin: 0.2rem;
        border-radius: 999px;
        background: #252938;
        border: 1px solid #35394b;
        font-size: 0.88rem;
        font-weight: 500;
    }
    .stock-pill-anom {
        display: inline-block;
        padding: 0.35rem 0.75rem;
        margin: 0.2rem;
        border-radius: 999px;
        background: rgba(255, 75, 75, 0.18);
        border: 1px solid rgba(255, 75, 75, 0.5);
        color: #ff6b6b;
        font-size: 0.88rem;
        font-weight: 600;
    }
    .callout-box {
        padding: 1rem 1.2rem;
        border-radius: 8px;
        background: #1e2230;
        border-left: 4px solid #3b82f6;
        margin-bottom: 1rem;
    }
    </style>
    """,
    unsafe_allow_html=True
)


# ============================================================
# API CLIENT (WITH DIRECT SERVICE FALLBACK)
# ============================================================

def check_backend_health():
    try:
        r = requests.get(f"{API_URL}/", timeout=1.5)
        return r.status_code == 200
    except Exception:
        return False


BACKEND_ONLINE = check_backend_health()

@st.cache_resource
def get_local_service():
    from api.services import MarketLensService
    return MarketLensService.get_instance()


def fetch_events(severity=None, event_type=None):
    if BACKEND_ONLINE:
        try:
            params = {}
            if severity:
                params["severity"] = severity
            if event_type:
                params["event_type"] = event_type
            r = requests.get(f"{API_URL}/events", params=params, timeout=10)
            if r.status_code == 200:
                return r.json()
        except Exception:
            pass
    svc = get_local_service()
    return svc.load_events(severity=severity, event_type=event_type)


def fetch_event(event_id):
    if BACKEND_ONLINE:
        try:
            r = requests.get(f"{API_URL}/events/{event_id}", timeout=10)
            if r.status_code == 200:
                return r.json()
        except Exception:
            pass
    svc = get_local_service()
    return svc.get_event_by_id(event_id)


def fetch_explanation(event_id):
    if BACKEND_ONLINE:
        try:
            r = requests.get(f"{API_URL}/events/{event_id}/explanation", timeout=60)
            if r.status_code == 200:
                return r.json()
        except Exception:
            pass
    svc = get_local_service()
    return svc.get_event_explanation(event_id)


def fetch_date_analysis(analysis_date_str):
    if BACKEND_ONLINE:
        try:
            r = requests.get(f"{API_URL}/analysis/date/{analysis_date_str}", timeout=30)
            if r.status_code in [200, 400, 404]:
                return r.json()
        except Exception:
            pass
    svc = get_local_service()
    return svc.analyze_historical_date(analysis_date_str)


def fetch_live_analysis(force_refresh=False):
    if BACKEND_ONLINE:
        try:
            params = {"force_refresh": force_refresh}
            r = requests.get(f"{API_URL}/analysis/live", params=params, timeout=45)
            if r.status_code == 200:
                return r.json()
        except Exception:
            pass
    svc = get_local_service()
    return svc.analyze_live_market(force_refresh=force_refresh)


# ============================================================
# SIDEBAR
# ============================================================

events = fetch_events()
events_df = pd.DataFrame(events) if events else pd.DataFrame()

with st.sidebar:
    st.markdown("## 📈 MarketLens")
    st.caption("Market Anomaly Detection & Event Surveillance")

    if BACKEND_ONLINE:
        st.success("● FastAPI Connected (Port 8000)")
    else:
        st.info("● Direct Engine Mode (Stand-alone)")

    st.divider()

    page = st.radio(
        "Navigation",
        [
            "Overview",
            "Historical Date Analysis",
            "Event Explorer",
            "Live Market Surveillance",
            "Model & Methodology"
        ]
    )

    st.divider()
    st.caption("Engine Specifications")
    st.markdown("""
    - **ML Model:** Isolation Forest
    - **Features:** Return, Volatility, Volume
    - **Contamination:** 1.0%
    - **Signals:** Anomaly + Correlation + Breadth
    - **Attribution:** SHAP TreeExplainer
    - **Observation Freq:** Daily Close
    """)


# ============================================================
# HEADER
# ============================================================

st.markdown('<div class="market-title">MarketLens</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="market-subtitle">'
    'Autonomous Market Anomaly Detection and Cross-Stock Event Surveillance System'
    '</div>',
    unsafe_allow_html=True
)


# ============================================================
# 1. OVERVIEW PAGE
# ============================================================

if page == "Overview":
    st.header("Consolidated Historical Events Overview")
    st.markdown(
        "MarketLens continuously evaluates stock-level anomalies, cross-asset correlation breaks, "
        "and market-wide breadth to identify and consolidate systemic market events."
    )

    if events_df.empty:
        st.warning("No consolidated events available in Dataset/market_events.csv.")
    else:
        events_df["Start_Date"] = pd.to_datetime(events_df["Start_Date"])
        events_df["End_Date"] = pd.to_datetime(events_df["End_Date"])
        events_df["Peak_Date"] = pd.to_datetime(events_df["Peak_Date"])
        events_df = events_df.sort_values("Start_Date")

        total_events = len(events_df)
        critical_events = (events_df["Severity"] == "CRITICAL").sum()
        high_events = (events_df["Severity"] == "HIGH").sum()
        medium_events = (events_df["Severity"] == "MEDIUM").sum()

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Consolidated Events", total_events)
        c2.metric("Critical Events", critical_events)
        c3.metric("High Stress Events", high_events)
        c4.metric("Medium Stress Events", medium_events)

        st.divider()

        st.subheader("Market Stress Trajectory")
        stress_chart_df = events_df[["Peak_Date", "Peak_Stress"]].copy().set_index("Peak_Date")
        st.line_chart(stress_chart_df, use_container_width=True)
        st.caption("Peak market stress score recorded across detected events (0–100 scale).")

        st.divider()

        c_left, c_right = st.columns([1, 2])
        with c_left:
            st.subheader("Severity Breakdown")
            sev_counts = (
                events_df["Severity"]
                .value_counts()
                .rename_axis("Severity")
                .reset_index(name="Count")
            )
            st.dataframe(sev_counts, hide_index=True, use_container_width=True)

        with c_right:
            st.subheader("Severity Distribution")
            st.bar_chart(sev_counts.set_index("Severity"))

        st.divider()

        st.subheader("Detected Consolidated Events Table")
        tbl_df = events_df.copy()
        tbl_df["Start_Date"] = tbl_df["Start_Date"].dt.strftime("%Y-%m-%d")
        tbl_df["End_Date"] = tbl_df["End_Date"].dt.strftime("%Y-%m-%d")
        tbl_df["Peak_Date"] = tbl_df["Peak_Date"].dt.strftime("%Y-%m-%d")

        st.dataframe(
            tbl_df[[
                "Event_ID", "Start_Date", "End_Date", "Event_Type",
                "Severity", "Duration", "Peak_Stress", "Peak_Date"
            ]],
            use_container_width=True,
            hide_index=True
        )


# ============================================================
# 2. HISTORICAL DATE ANALYSIS (FEATURE ONE)
# ============================================================

elif page == "Historical Date Analysis":
    st.header("Historical Date Surveillance & On-Demand Analysis")
    st.markdown(
        "Select **any historical trading date** across the 21-year historical dataset (2000–2021). "
        "The system extracts actual market observations, evaluates stock features with the trained "
        "Isolation Forest, calculates market-wide breadth and correlation, and delivers model explanations."
    )

    st.markdown(
        '<div class="callout-box">'
        '<strong>💡 Quick Presets:</strong> Test notable historical sessions:<br>'
        '• <code>2020-03-16</code>: Systemic Downside Shock (100% negative breadth, 0 IF anomalies, CRITICAL via breadth override)<br>'
        '• <code>2020-03-23</code>: Historic COVID Crash Peak (47 stocks, 7 anomalies, 100% negative breadth, CRITICAL)<br>'
        '• <code>2020-03-12</code>: Extreme Market Stress (47 stocks, 2 anomalies: ONGC, VEDL, Stress Score 65.14, CRITICAL)<br>'
        '• <code>2008-10-24</code>: Lehman Financial Crisis Trough (45 stocks, 10 anomalies, 100% negative breadth, CRITICAL)'
        '</div>',
        unsafe_allow_html=True
    )

    preset_col1, preset_col2, preset_col3, preset_col4 = st.columns(4)
    if preset_col1.button("Preset: 2020-03-16", use_container_width=True):
        st.session_state["selected_hist_date"] = datetime.date(2020, 3, 16)
        st.session_state["trigger_analysis"] = True
    if preset_col2.button("Preset: 2020-03-23", use_container_width=True):
        st.session_state["selected_hist_date"] = datetime.date(2020, 3, 23)
        st.session_state["trigger_analysis"] = True
    if preset_col3.button("Preset: 2020-03-12", use_container_width=True):
        st.session_state["selected_hist_date"] = datetime.date(2020, 3, 12)
        st.session_state["trigger_analysis"] = True
    if preset_col4.button("Preset: 2008-10-24", use_container_width=True):
        st.session_state["selected_hist_date"] = datetime.date(2008, 10, 24)
        st.session_state["trigger_analysis"] = True

    default_date = st.session_state.get("selected_hist_date", datetime.date(2020, 3, 16))

    col_input, col_btn = st.columns([2, 1])
    with col_input:
        selected_date = st.date_input(
            "Select Historical Trading Date",
            value=default_date,
            min_value=datetime.date(2000, 2, 1),
            max_value=datetime.date(2021, 4, 30),
            key="date_picker_input"
        )
    with col_btn:
        st.write("")
        st.write("")
        analyze_clicked = st.button("🔍 Analyze Date", type="primary", use_container_width=True)

    # Check if trigger requested
    should_run = analyze_clicked or st.session_state.get("trigger_analysis", False)
    if should_run:
        st.session_state["trigger_analysis"] = False
        date_str = selected_date.strftime("%Y-%m-%d")

        with st.spinner(f"Extracting observations and evaluating pipeline for {date_str}..."):
            result = fetch_date_analysis(date_str)
            st.session_state["last_analysis_result"] = result
            st.session_state["last_analyzed_date"] = date_str

    # Render results from session state
    result = st.session_state.get("last_analysis_result", None)

    if result:
        st.divider()
        st.subheader(f"Analysis Results: {result.get('analysis_date')}")

        if not result.get("observations_available", False):
            st.warning(f"⚠️ Observations Unavailable for {result.get('analysis_date')}")
            for w in result.get("warnings", []):
                st.info(w)
        else:
            sev = result.get("severity", "LOW")
            sev_class = f"badge-{sev.lower()}"
            ev_type = result.get("event_type", "Normal")

            st.markdown(
                f"""
                <div class="event-card">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <span style="font-size: 1.5rem; font-weight: 700; margin-right: 1rem;">{ev_type}</span>
                            <span class="{sev_class}">{sev}</span>
                        </div>
                        <div style="color: #9ca3af; font-size: 0.95rem;">
                            Source: <strong>{result.get('data_source').upper()}</strong> (market_stream.csv)
                        </div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

            # Metric Rows
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Stocks Analyzed", result.get("stocks_analyzed"))
            m2.metric("IF Anomalies Detected", result.get("anomalies_detected"))
            m3.metric("Anomaly Breadth", f"{result.get('anomaly_breadth', 0.0):.2%}")
            m4.metric("Mean Market Return", f"{result.get('mean_return', 0.0):.2%}")

            m5, m6, m7, m8 = st.columns(4)
            m5.metric("Negative Breadth (< 0%)", f"{result.get('negative_breadth', 0.0):.2%}")
            m6.metric("Severe Decline (<= -5%)", f"{result.get('severe_decline_breadth', 0.0):.2%}")

            corr = result.get("rolling_correlation")
            m7.metric("Rolling Correlation", f"{corr:.4f}" if corr is not None else "N/A")

            stress = result.get("market_stress_score")
            m8.metric("Market Stress Score", f"{stress:.2f}" if stress is not None else "N/A (Omitted)")

            # Warnings box
            if result.get("warnings"):
                for w in result["warnings"]:
                    st.caption(f"ℹ️ {w}")

            st.divider()

            # Affected Stocks
            st.subheader("Affected Stocks")
            aff = result.get("affected_stocks", [])
            if aff:
                pills = "".join([f'<span class="stock-pill-anom">{s}</span>' for s in aff])
                st.markdown(pills, unsafe_allow_html=True)
            else:
                st.info("No individual stock-level anomalies detected by Isolation Forest on this date.")

            st.divider()

            # Complete stock observations table
            st.subheader("Market Universe Observations")
            stock_results = result.get("stock_results", [])
            if stock_results:
                stock_df = pd.DataFrame(stock_results)
                stock_df["Return"] = (stock_df["Return"] * 100).round(2).astype(str) + "%"
                stock_df["Volatility_20"] = (stock_df["Volatility_20"] * 100).round(2).astype(str) + "%"
                stock_df["Volume_Ratio"] = stock_df["Volume_Ratio"].round(2).astype(str) + "x"
                stock_df["Anomaly_Score"] = stock_df["Anomaly_Score"].round(4)
                stock_df["Anomaly_Flag"] = stock_df["Is_Anomaly"].apply(lambda x: "🚨 ANOMALY" if x else "NORMAL")

                st.dataframe(
                    stock_df[["Symbol", "Return", "Volatility_20", "Volume_Ratio", "Anomaly_Flag", "Anomaly_Score"]],
                    use_container_width=True,
                    hide_index=True
                )

            # SHAP Explanations
            st.divider()
            st.subheader("SHAP Feature Contributions")
            explanations = result.get("explanations", [])

            if not explanations:
                st.info(
                    "No individual stock-level anomalies detected. Model-based SHAP attribution applies "
                    "only to stocks that breach the multivariate anomaly boundary."
                )
            else:
                st.caption(
                    "Local SHAP attribution explains how Return, 20D Volatility, and Volume Ratio drove each stock anomaly."
                )
                for expl in explanations:
                    with st.expander(f"📌 {expl['Symbol']} | Return: {expl['Return']:.2%} | Volatility: {expl['Volatility_20']:.2%}"):
                        shap_df = pd.DataFrame(expl["Features"])
                        shap_df["Abs_SHAP"] = shap_df["SHAP"].abs()

                        c_chart, c_tbl = st.columns([1, 1])
                        with c_chart:
                            st.bar_chart(shap_df.set_index("Feature")["SHAP"], horizontal=True)
                        with c_tbl:
                            st.dataframe(
                                shap_df[["Feature", "Value", "SHAP"]].sort_values("SHAP", key=lambda x: x.abs(), reverse=True),
                                hide_index=True,
                                use_container_width=True
                            )


# ============================================================
# 3. EVENT EXPLORER
# ============================================================

elif page == "Event Explorer":
    st.header("Consolidated Event Explorer")
    st.markdown("Detailed investigation of the seven consolidated historical market events.")

    if events_df.empty:
        st.warning("No events found.")
    else:
        event_ids = events_df["Event_ID"].tolist()
        selected_event_id = st.selectbox("Select a Consolidated Market Event", event_ids)

        event = fetch_event(selected_event_id)
        if not event:
            st.error(f"Event {selected_event_id} could not be loaded.")
        else:
            sev = event["Severity"]
            sev_class = f"badge-{sev.lower()}"

            st.markdown(
                f"""
                <div class="event-card">
                    <div style="font-size: 1.5rem; font-weight: 700;">{event["Event_Type"]}</div>
                    <div style="margin-top: 0.4rem;">
                        <span class="{sev_class}">{sev}</span>
                        <span style="color: #9ca3af; margin-left: 1rem;">ID: {event["Event_ID"]}</span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Peak Stress Score", f"{event['Peak_Stress']:.2f}")
            c2.metric("Duration", f"{event['Duration']} Day(s)")
            c3.metric("Peak Date", event["Peak_Date"])
            c4.metric("Severity", event["Severity"])

            st.write(f"**Surveillance Period:** {event['Start_Date']} → {event['End_Date']}")
            st.divider()

            st.subheader("Affected Stocks")
            aff = event.get("Affected_Stocks", [])
            if aff:
                pills = "".join([f'<span class="stock-pill-anom">{s}</span>' for s in aff])
                st.markdown(pills, unsafe_allow_html=True)
            else:
                st.info(
                    "No individual affected stocks recorded for this event. "
                    "(For instance, March 16 was driven by market-wide breadth without single-stock outliers)."
                )

            st.divider()
            st.subheader("Event SHAP Explanations")

            if st.button("Generate SHAP Explanation for Peak Date", type="primary"):
                with st.spinner("Computing SHAP attribution..."):
                    expl_res = fetch_explanation(selected_event_id)

                if not expl_res or expl_res.get("Anomalies", 0) == 0:
                    st.info("Zero stock-level anomalies recorded on the peak date of this event.")
                else:
                    st.success(f"Explained {expl_res['Anomalies']} anomalies on {expl_res['Event_Date']}:")
                    for stock_expl in expl_res.get("Explanations", []):
                        st.markdown(f"#### {stock_expl['Symbol']}")
                        sc1, sc2, sc3 = st.columns(3)
                        sc1.metric("Return", f"{stock_expl['Return']:.2%}")
                        sc2.metric("20D Volatility", f"{stock_expl['Volatility_20']:.2%}")
                        sc3.metric("Volume Ratio", f"{stock_expl['Volume_Ratio']:.2f}x")

                        sdf = pd.DataFrame(stock_expl["Features"])
                        c_plot, c_data = st.columns([1, 1])
                        with c_plot:
                            st.bar_chart(sdf.set_index("Feature")["SHAP"], horizontal=True)
                        with c_data:
                            st.dataframe(sdf[["Feature", "Value", "SHAP"]], hide_index=True, use_container_width=True)
                        st.divider()


# ============================================================
# 4. LIVE MARKET SURVEILLANCE (FEATURE TWO)
# ============================================================

elif page == "Live Market Surveillance":
    st.header("Live Daily Market Surveillance")
    st.markdown(
        "Active monitoring mode using latest available daily closing bars. "
        "Evaluates the active NIFTY equities universe through the trained Isolation Forest."
    )

    st.markdown(
        '<div class="callout-box">'
        '<strong>📡 Surveillance Frequency & Data Provider Notice:</strong><br>'
        '• <strong>Provider:</strong> Yahoo Finance (Daily Close / Delayed Daily Bars)<br>'
        '• <strong>Observation Frequency:</strong> Daily session frequency (End-of-Day / Latest closed session)<br>'
        '• <strong>Scope:</strong> This surveillance mode operates on daily closing bars. '
        'Genuine sub-second tick streaming surveillance requires an active enterprise WebSocket feed '
        '(such as Zerodha Kite Connect WebSocket or TrueData broker connection).'
        '</div>',
        unsafe_allow_html=True
    )

    col_ref, _ = st.columns([1, 3])
    with col_ref:
        force_fetch = st.button("🔄 Refresh Live Market Data", type="primary", use_container_width=True)

    with st.spinner("Retrieving latest market observations and running anomaly detection..."):
        live_res = fetch_live_analysis(force_refresh=force_fetch)

    if not live_res or not live_res.get("observations_available", False):
        st.warning("⚠️ Live Market Data Unavailable")
        for w in live_res.get("warnings", ["Unable to fetch market data from provider."]):
            st.info(w)
    else:
        sev = live_res.get("severity", "LOW")
        sev_class = f"badge-{sev.lower()}"
        ev_type = live_res.get("event_type", "Normal")

        st.markdown(
            f"""
            <div class="event-card">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <span style="font-size: 1.5rem; font-weight: 700; margin-right: 1rem;">{ev_type}</span>
                        <span class="{sev_class}">{sev}</span>
                    </div>
                    <div style="color: #9ca3af; font-size: 0.95rem;">
                        Session: <strong>{live_res.get('analysis_date')}</strong> | Updated: {live_res.get('last_updated', '')[:19]}
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        lc1, lc2, lc3, lc4 = st.columns(4)
        lc1.metric("Stocks Analyzed", live_res.get("stocks_analyzed"))
        lc2.metric("Anomalies Detected", live_res.get("anomalies_detected"))
        lc3.metric("Anomaly Breadth", f"{live_res.get('anomaly_breadth', 0.0):.2%}")
        lc4.metric("Mean Return", f"{live_res.get('mean_return', 0.0):.2%}")

        lc5, lc6, lc7, lc8 = st.columns(4)
        lc5.metric("Negative Breadth (< 0%)", f"{live_res.get('negative_breadth', 0.0):.2%}")
        lc6.metric("Severe Decline (<= -5%)", f"{live_res.get('severe_decline_breadth', 0.0):.2%}")
        lc7.metric("Rolling Correlation", "N/A (Daily Stream)")
        lc8.metric("Market Stress Score", "N/A (Omitted)")

        if live_res.get("warnings"):
            for w in live_res["warnings"]:
                st.caption(f"ℹ️ {w}")

        st.divider()

        st.subheader("Live Anomalies & Affected Stocks")
        live_aff = live_res.get("affected_stocks", [])
        if live_aff:
            pills = "".join([f'<span class="stock-pill-anom">{s}</span>' for s in live_aff])
            st.markdown(pills, unsafe_allow_html=True)
        else:
            st.info("No stocks currently breaching the multivariate anomaly threshold.")

        st.divider()

        st.subheader("Live Market Observations Table")
        live_stock_results = live_res.get("stock_results", [])
        if live_stock_results:
            ls_df = pd.DataFrame(live_stock_results)
            ls_df["Return"] = (ls_df["Return"] * 100).round(2).astype(str) + "%"
            ls_df["Volatility_20"] = (ls_df["Volatility_20"] * 100).round(2).astype(str) + "%"
            ls_df["Volume_Ratio"] = ls_df["Volume_Ratio"].round(2).astype(str) + "x"
            ls_df["Anomaly_Score"] = ls_df["Anomaly_Score"].round(4)
            ls_df["Anomaly_Flag"] = ls_df["Is_Anomaly"].apply(lambda x: "🚨 ANOMALY" if x else "NORMAL")

            st.dataframe(
                ls_df[["Symbol", "Return", "Volatility_20", "Volume_Ratio", "Anomaly_Flag", "Anomaly_Score"]],
                use_container_width=True,
                hide_index=True
            )

        if live_res.get("explanations"):
            st.divider()
            st.subheader("SHAP Explanations for Live Anomalies")
            for expl in live_res["explanations"]:
                with st.expander(f"🚨 {expl['Symbol']}"):
                    sdf = pd.DataFrame(expl["Features"])
                    st.bar_chart(sdf.set_index("Feature")["SHAP"], horizontal=True)
                    st.dataframe(sdf, hide_index=True, use_container_width=True)


# ============================================================
# 5. MODEL & METHODOLOGY PAGE
# ============================================================

elif page == "Model & Methodology":
    st.header("Methodology, Signals & Architecture")

    st.markdown(r"""
    ### 1. Stock-Level Anomaly Detection Layer
    - **Algorithm:** Isolation Forest (`n_estimators=200`, `contamination=0.01`, `random_state=42`).
    - **Temporal Split:** Trained on chronological observations prior to 2016-01-01; evaluated on 2016–2021.
    - **Feature Space (3 Core Features):**
      1. `Return`: Daily percentage price movement (corporate-action adjusted).
      2. `Volatility_20`: 20-trading-day rolling standard deviation of returns.
      3. `Volume_Ratio`: Current trading volume normalized against 20-day rolling average volume.

    ---

    ### 2. Market-Wide Breadth & Macro Signals
    Systemic liquidations often depress all stocks together without producing individual outliers.
    MarketLens addresses this detection gap through three macro breadth metrics:
    - `Negative_Breadth`: Percentage of active stocks recording negative daily returns.
    - `Severe_Decline_Breadth`: Percentage of stocks suffering severe losses ($\le -5.0\%$).
    - `Mean_Return`: Cross-sectional average equity return across the universe.

    ---

    ### 3. Three-Signal Market Stress Scoring
    $$\text{Market\_Stress\_Score} = 0.30 \times \text{Anomaly\_Score} + 0.30 \times \text{Correlation\_Score} + 0.40 \times \text{Breadth\_Stress\_Score}$$
    - **Anomaly Score:** $\text{Anomaly\_Breadth} \times 100$
    - **Correlation Score:** $\frac{\text{clip}(\text{Correlation\_Z}, 0, 6)}{6} \times 100$
    - **Breadth Stress Score:** $100 \times \text{Negative\_Breadth} \times \text{clip}(\text{Severe\_Decline\_Breadth}, 0, 1)$

    ---

    ### 4. Event Classification & Severity Rules
    - **Downside Override:** If `Negative_Breadth >= 0.90`, `Severe_Decline_Breadth >= 0.10`, and `Mean_Return <= -0.02`,
      classify as **Broad Market Downside Shock** with **CRITICAL** severity (ensuring dates like March 16, 2020 are correctly identified).
    - **Score Thresholds:** $\ge 40$ (CRITICAL), $\ge 25$ (HIGH), $\ge 15$ (MEDIUM), $< 15$ (LOW).

    ---

    ### 5. Explainable AI via TreeExplainer
    Local feature attribution is calculated using SHAP TreeExplainer on the Isolation Forest trees:
    - Quantifies exact directional contributions of Return, Volatility, and Volume Ratio.
    - Preserves mathematical honesty: descriptions describe model attribution, not financial causation.
    """)
