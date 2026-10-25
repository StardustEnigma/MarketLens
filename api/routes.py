import re
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from api.services import MarketLensService

router = APIRouter()
service = MarketLensService.get_instance()

# -------------------------------------------------------------
# Pydantic Schemas
# -------------------------------------------------------------
class Event(BaseModel):
    Event_ID: str
    Start_Date: str
    End_Date: str
    Event_Type: str
    Duration: int
    Peak_Stress: Optional[float] = None
    Peak_Date: str
    Severity: str
    Affected_Stocks: List[str]


class FeatureExplanation(BaseModel):
    Feature: str
    Value: Optional[float] = None
    SHAP: Optional[float] = None


class StockExplanation(BaseModel):
    Symbol: str
    Return: Optional[float] = None
    Volatility_20: Optional[float] = None
    Volume_Ratio: Optional[float] = None
    Features: List[FeatureExplanation]


class EventExplanation(BaseModel):
    Event_Date: str
    Anomalies: int
    Explanations: List[StockExplanation]
    Note: Optional[str] = None


class StockResult(BaseModel):
    Symbol: str
    Return: Optional[float] = None
    Volatility_20: Optional[float] = None
    Volume_Ratio: Optional[float] = None
    Anomaly: int
    Anomaly_Score: Optional[float] = None
    Is_Anomaly: bool


class DateAnalysisResponse(BaseModel):
    analysis_date: str
    data_source: str = "historical"
    observations_available: bool
    stocks_analyzed: int
    anomalies_detected: int
    anomaly_breadth: float
    negative_breadth: float
    severe_decline_breadth: float
    mean_return: float
    rolling_correlation: Optional[float] = None
    correlation_z: Optional[float] = None
    market_stress_score: Optional[float] = None
    event_type: str
    severity: str
    affected_stocks: List[str]
    stock_results: List[StockResult]
    explanations: List[StockExplanation]
    warnings: List[str]


class LiveAnalysisResponse(BaseModel):
    analysis_date: str
    data_source: str = "live_daily"
    provider: str
    observation_frequency: str
    is_intraday: bool = False
    observations_available: bool
    stocks_analyzed: int
    anomalies_detected: int
    anomaly_breadth: float
    negative_breadth: float
    severe_decline_breadth: float
    mean_return: float
    rolling_correlation: Optional[float] = None
    correlation_z: Optional[float] = None
    market_stress_score: Optional[float] = None
    event_type: str
    severity: str
    affected_stocks: List[str]
    stock_results: List[StockResult]
    explanations: List[StockExplanation]
    last_updated: str
    warnings: List[str]


class SystemStatusResponse(BaseModel):
    service: str = "MarketLens"
    status: str = "running"
    version: str = "1.0.0"
    model_loaded: bool
    historical_date_range: Dict[str, Any]
    active_universe_size: int
    consolidated_events_count: int


# -------------------------------------------------------------
# Endpoints
# -------------------------------------------------------------
@router.get("/", response_model=Dict[str, str])
def root():
    return {
        "service": "MarketLens",
        "status": "running"
    }


@router.get("/status", response_model=SystemStatusResponse)
def get_system_status():
    min_date, max_date, trading_days = service.get_historical_date_range()
    events = service.load_events()
    return SystemStatusResponse(
        service="MarketLens",
        status="running",
        version="1.0.0",
        model_loaded=service.model is not None,
        historical_date_range={
            "start": min_date,
            "end": max_date,
            "trading_days": trading_days
        },
        active_universe_size=len(service.get_stock_universe()),
        consolidated_events_count=len(events)
    )


@router.get("/events", response_model=List[Event])
def get_events(
    severity: Optional[str] = Query(default=None, description="Filter by severity (LOW, MEDIUM, HIGH, CRITICAL)"),
    event_type: Optional[str] = Query(default=None, description="Filter by event type")
):
    sev = severity if isinstance(severity, str) else None
    evt = event_type if isinstance(event_type, str) else None
    return service.load_events(severity=sev, event_type=evt)


@router.get("/events/{event_id}", response_model=Event)
def get_event(event_id: str):
    event = service.get_event_by_id(event_id)
    if not event:
        raise HTTPException(
            status_code=404,
            detail=f"Event '{event_id}' not found in consolidated events dataset."
        )
    return event


@router.get("/events/{event_id}/explanation", response_model=EventExplanation)
def get_event_explanation(event_id: str):
    explanation = service.get_event_explanation(event_id)
    if not explanation:
        raise HTTPException(
            status_code=404,
            detail=f"Event '{event_id}' not found or explanations unavailable."
        )
    return explanation


@router.get("/analysis/date/{analysis_date}", response_model=DateAnalysisResponse)
def analyze_date(analysis_date: str):
    """
    On-demand analysis of any historical trading date.
    Extracts actual observations, applies Isolation Forest, computes market breadth,
    correlation metrics, event classification, and SHAP explanations.
    """
    # Validate format regex YYYY-MM-DD
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", analysis_date):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid date format '{analysis_date}'. Expected format: YYYY-MM-DD."
        )

    try:
        result = service.analyze_historical_date(analysis_date)
        return result
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error executing historical analysis for {analysis_date}: {str(e)}"
        )


@router.get("/analysis/live", response_model=LiveAnalysisResponse)
def analyze_live(force_refresh: bool = Query(default=False, description="Bypass cache and force data fetch")):
    """
    Live market surveillance mode.
    Fetches the latest daily closing observations from Yahoo Finance,
    applies the Isolation Forest detector, and calculates market breadth.
    """
    try:
        force = bool(force_refresh) if not hasattr(force_refresh, "default") else False
        result = service.analyze_live_market(force_refresh=force)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error during live market surveillance: {str(e)}"
        )
