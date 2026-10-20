
import ast

import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

from event_explanations import explain_event


app = FastAPI(
    title="MarketLens API",
    description="Market anomaly detection and event surveillance API",
    version="1.0.0"
)


# ---------------------------------------
# Response Models
# ---------------------------------------

class Event(BaseModel):
    Event_ID: str
    Start_Date: str
    End_Date: str
    Event_Type: str
    Duration: int
    Peak_Stress: float
    Peak_Date: str
    Severity: str
    Affected_Stocks: list[str]


class FeatureExplanation(BaseModel):
    Feature: str
    Value: float
    SHAP: float


class StockExplanation(BaseModel):
    Symbol: str
    Return: float
    Volatility_20: float
    Volume_Ratio: float
    Features: list[FeatureExplanation]


class EventExplanation(BaseModel):
    Event_Date: str
    Anomalies: int
    Explanations: list[StockExplanation]


# ---------------------------------------
# Helpers
# ---------------------------------------

def load_events():

    df = pd.read_csv(
        "Dataset/market_events.csv"
    )

    return df


def parse_affected_stocks(value):

    if pd.isna(value) or value == "":
        return []

    if isinstance(value, list):
        return value

    return ast.literal_eval(value)


def convert_event_record(record):

    record = record.where(
        pd.notnull(record),
        None
    ).to_dict()

    record["Affected_Stocks"] = parse_affected_stocks(
        record["Affected_Stocks"]
    )

    return record


# ---------------------------------------
# Root
# ---------------------------------------

@app.get("/")
def root():

    return {
        "service": "MarketLens",
        "status": "running"
    }


# ---------------------------------------
# Get all events
# ---------------------------------------

@app.get(
    "/events",
    response_model=list[Event]
)
def get_events(
    severity: str | None = Query(
        default=None,
        description="Filter by severity"
    ),
    event_type: str | None = Query(
        default=None,
        description="Filter by event type"
    )
):

    df = load_events()

    if severity:
        df = df[
            df["Severity"].str.upper()
            == severity.upper()
        ]

    if event_type:
        df = df[
            df["Event_Type"].str.lower()
            == event_type.lower()
        ]

    records = [
        convert_event_record(row)
        for _, row in df.iterrows()
    ]

    return records


# ---------------------------------------
# Get single event
# ---------------------------------------

@app.get(
    "/events/{event_id}",
    response_model=Event
)
def get_event(event_id: str):

    df = load_events()

    event = df[
        df["Event_ID"] == event_id
    ]

    if event.empty:

        raise HTTPException(
            status_code=404,
            detail=f"Event '{event_id}' not found"
        )

    return convert_event_record(
        event.iloc[0]
    )


# ---------------------------------------
# Get SHAP explanation
# ---------------------------------------

@app.get(
    "/events/{event_id}/explanation",
    response_model=EventExplanation
)
def get_event_explanation(event_id: str):

    df = load_events()

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

