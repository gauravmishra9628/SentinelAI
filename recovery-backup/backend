from typing import Literal

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel


RiskLevel = Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
EngineStatus = Literal["ONLINE", "OFFLINE", "DEGRADED", "PROCESSING"]


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str


class Statistic(BaseModel):
    title: str
    value: int | str
    icon: str
    trend: Literal["up", "down", "neutral"]
    label: str
    status: str


class MonitoringCamera(BaseModel):
    id: str
    location: str
    status: EngineStatus
    trafficLevel: str
    detectedVehicles: int
    detectedPedestrians: int
    riskLevel: RiskLevel
    lastUpdate: str


class RiskEvent(BaseModel):
    id: int
    riskScore: int
    detectedIssue: str
    location: str
    camera: str
    timestamp: str
    confidence: int
    severity: RiskLevel
    status: str


class Alert(BaseModel):
    id: int
    type: str
    location: str
    timestamp: str
    severity: RiskLevel
    status: str


class AnalyticsMetric(BaseModel):
    label: str
    value: str
    percent: int
    tone: Literal["safe", "warning", "danger", "critical"]


class TrendPoint(BaseModel):
    label: str
    incidents: int
    riskScore: int


class AnalyticsResponse(BaseModel):
    metrics: list[AnalyticsMetric]
    trends: list[TrendPoint]


class AIEngineResponse(BaseModel):
    status: EngineStatus
    modelStatus: str
    inferenceStatus: EngineStatus
    cameraProcessingStatus: EngineStatus
    apiStatus: EngineStatus
    lastProcessedEvent: str
    uptime: str
    modelVersion: str


class DashboardResponse(BaseModel):
    statistics: list[Statistic]
    monitoring: list[MonitoringCamera]
    risks: list[RiskEvent]
    alerts: list[Alert]
    analytics: AnalyticsResponse
    aiEngineStatus: AIEngineResponse


statistics = [
    Statistic(title="Active Cameras", value=18, icon="CAM", trend="up", label="+2 since yesterday", status="ONLINE"),
    Statistic(title="Vehicles Monitored", value=1284, icon="CAR", trend="up", label="+12.4% this week", status="PROCESSING"),
    Statistic(title="High Risk Events", value=3, icon="RISK", trend="down", label="-18% from last hour", status="DEGRADED"),
    Statistic(title="Safety Score", value="94", icon="SAFE", trend="up", label="Regional average", status="ONLINE"),
]

monitoring = [
    MonitoringCamera(id="CAM-001", location="Main Highway - Sector 7", status="PROCESSING", trafficLevel="Moderate", detectedVehicles=47, detectedPedestrians=12, riskLevel="LOW", lastUpdate="Just now"),
    MonitoringCamera(id="CAM-014", location="Airport Road Junction", status="ONLINE", trafficLevel="Heavy", detectedVehicles=83, detectedPedestrians=21, riskLevel="HIGH", lastUpdate="45 sec ago"),
    MonitoringCamera(id="CAM-022", location="Downtown School Zone", status="ONLINE", trafficLevel="Light", detectedVehicles=19, detectedPedestrians=34, riskLevel="MEDIUM", lastUpdate="1 min ago"),
]

risks = [
    RiskEvent(id=1, riskScore=91, detectedIssue="Wrong-way vehicle", location="Airport Road Junction", camera="CAM-014", timestamp="2 min ago", confidence=97, severity="CRITICAL", status="Active"),
    RiskEvent(id=2, riskScore=78, detectedIssue="Overspeeding cluster", location="NH-24 Highway", camera="CAM-008", timestamp="5 min ago", confidence=93, severity="HIGH", status="Monitoring"),
    RiskEvent(id=3, riskScore=62, detectedIssue="Pedestrian near fast lane", location="Downtown School Zone", camera="CAM-022", timestamp="9 min ago", confidence=88, severity="MEDIUM", status="Active"),
    RiskEvent(id=4, riskScore=28, detectedIssue="Sudden braking event", location="Main Highway - Sector 7", camera="CAM-001", timestamp="15 min ago", confidence=81, severity="LOW", status="Resolved"),
]

alerts = [
    Alert(id=1, type="Collision warning", location="Airport Road Junction", timestamp="2 min ago", severity="CRITICAL", status="Active"),
    Alert(id=2, type="Overspeeding", location="NH-24 Highway", timestamp="5 min ago", severity="HIGH", status="Monitoring"),
    Alert(id=3, type="Pedestrian risk", location="Downtown School Zone", timestamp="9 min ago", severity="MEDIUM", status="Active"),
    Alert(id=4, type="Wrong-way driving", location="Sector 3 Ramp", timestamp="13 min ago", severity="CRITICAL", status="Resolved"),
    Alert(id=5, type="Accident risk", location="Ring Road Exit 11", timestamp="21 min ago", severity="MEDIUM", status="Monitoring"),
]

analytics = AnalyticsResponse(
    metrics=[
        AnalyticsMetric(label="Risk Trend", value="-18%", percent=82, tone="safe"),
        AnalyticsMetric(label="Incidents Today", value="12", percent=42, tone="warning"),
        AnalyticsMetric(label="Traffic Density", value="67%", percent=67, tone="warning"),
        AnalyticsMetric(label="Detection Accuracy", value="96%", percent=96, tone="safe"),
    ],
    trends=[
        TrendPoint(label="06:00", incidents=2, riskScore=34),
        TrendPoint(label="09:00", incidents=6, riskScore=58),
        TrendPoint(label="12:00", incidents=4, riskScore=49),
        TrendPoint(label="15:00", incidents=8, riskScore=72),
        TrendPoint(label="18:00", incidents=5, riskScore=61),
    ],
)

ai_engine_status = AIEngineResponse(
    status="ONLINE",
    modelStatus="RoadRisk-v2 active",
    inferenceStatus="PROCESSING",
    cameraProcessingStatus="PROCESSING",
    apiStatus="ONLINE",
    lastProcessedEvent="CAM-014 wrong-way vehicle, 2 min ago",
    uptime="99.9%",
    modelVersion="v2.4.1",
)


app = FastAPI(
    title="SentinelAI API",
    description="AI-powered intelligent road safety and accident prevention system",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root() -> dict[str, str]:
    return {"project": "SentinelAI", "status": "online", "message": "SentinelAI backend is running"}


@app.get("/api/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", service="SentinelAI", version="1.0.0")


@app.get("/api/dashboard", response_model=DashboardResponse)
def dashboard() -> DashboardResponse:
    return DashboardResponse(
        statistics=statistics,
        monitoring=monitoring,
        risks=risks,
        alerts=alerts,
        analytics=analytics,
        aiEngineStatus=ai_engine_status,
    )


@app.get("/api/live-monitoring", response_model=list[MonitoringCamera])
def live_monitoring() -> list[MonitoringCamera]:
    return monitoring


@app.get("/api/risk-detection", response_model=list[RiskEvent])
def risk_detection() -> list[RiskEvent]:
    return risks


@app.get("/api/alerts", response_model=list[Alert])
def recent_alerts() -> list[Alert]:
    return alerts


@app.get("/api/analytics", response_model=AnalyticsResponse)
def road_analytics() -> AnalyticsResponse:
    return analytics


@app.get("/api/ai-engine/status", response_model=AIEngineResponse)
def ai_engine() -> AIEngineResponse:
    return ai_engine_status
