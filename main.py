
import ast
import pandas as pd
from fastapi import FastAPI, HTTPException
from event_explanations import explain_event
app = FastAPI(
    title="MarketLens API",
    description="Market anomaly detection and event surveillance API",
    version="1.0.0"
)


@app.get("/")
def root():
    return {
        "service": "MarketLens",
        "status": "running"
    }


@app.get("/events")
def get_events():

    df = pd.read_csv(
        "Dataset/market_events.csv"
    )

    df = df.where(
        pd.notnull(df),
        None
    )

    records = df.to_dict(
        orient="records"
    )

    for record in records:

        if record["Affected_Stocks"]:
            record["Affected_Stocks"] = ast.literal_eval(
                record["Affected_Stocks"]
            )
        else:
            record["Affected_Stocks"] = []

    return records


@app.get("/events/{event_id}")
def get_event(event_id: str):

    df = pd.read_csv(
        "Dataset/market_events.csv"
    )

    event = df[
        df["Event_ID"] == event_id
    ]

    if event.empty:
        raise HTTPException(
            status_code=404,
            detail=f"Event '{event_id}' not found"
        )

    record = event.iloc[0].where(
        pd.notnull(event.iloc[0]),
        None
    ).to_dict()

    if record["Affected_Stocks"]:
        record["Affected_Stocks"] = ast.literal_eval(
            record["Affected_Stocks"]
        )
    else:
        record["Affected_Stocks"] = []

    return record


@app.get("/events/{event_id}/explanation")
def get_event_explanation(event_id: str):

    df = pd.read_csv(
        "Dataset/market_events.csv"
    )

    event = df[
        df["Event_ID"] == event_id
    ]

    if event.empty:
        raise HTTPException(
            status_code=404,
            detail=f"Event '{event_id}' not found"
        )

    peak_date = event.iloc[0]["Peak_Date"]

    explanation = explain_event(
        peak_date
    )

    return explanation

