
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.database import (
    init_db,
    create_custom_rule,
    list_custom_rules,
    insert_incident,
    get_incident,
    list_incidents as db_list_incidents,
    update_review_status,
)
from app.event_ingestion import ingest_event
from app.custom_rules import parse_custom_rule
from app.schemas import CustomRule, CustomRuleCreate
from app.schemas import (
    IncidentCreate,
    Incident,
    Category,
    ReviewStatus,
    IncidentReviewUpdate,
    VisionEventIngest,
)
from app.query_parser import parse_query


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Sentinel Vision",
    description="Video incident detection and retrieval API",
    lifespan=lifespan,
)

# Local Vite dashboard origins only. Credentials are not used by this API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
    allow_credentials=False,
    allow_methods=["GET", "PATCH", "OPTIONS"],
    allow_headers=["Accept", "Content-Type"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/incidents", response_model=Incident)
def create_incident(incident: IncidentCreate):
    return insert_incident(incident)


@app.post(
    "/ingest/vision-event",
    response_model=Incident,
    status_code=201,
)
def ingest_vision_event(candidate: VisionEventIngest):
    return ingest_event(candidate)


@app.get("/incidents", response_model=list[Incident])
def read_incidents(
    category: Category | None = None,
    review_status: ReviewStatus | None = None,
):
    return db_list_incidents(
        category=category,
        review_status=review_status,
    )


@app.patch("/incidents/{incident_id}/review", response_model=Incident)
def review_incident(
    incident_id: int,
    review: IncidentReviewUpdate,
):
    incident = update_review_status(
        incident_id,
        review.review_status,
    )

    if incident is None:
        raise HTTPException(
            status_code=404,
            detail="Incident not found",
        )

    return incident

@app.get("/incidents/{incident_id}", response_model=Incident)
def read_incident(incident_id: int):
    incident = get_incident(incident_id)

    if incident is None:
        raise HTTPException(
            status_code=404,
            detail="Incident not found",
        )

    return incident


@app.get("/query")
def query_incidents(q: str):
    filters = parse_query(q)

    incidents = db_list_incidents(
        category=Category(filters["category"])
        if filters["category"] else None,
        review_status=ReviewStatus(filters["review_status"])
        if filters["review_status"] else None,
        camera_id=filters["camera_id"],
    )

    return {
        "query": q,
        "filters": filters,
        "count": len(incidents),
        "incidents": incidents,
    }





@app.post("/custom-rules", response_model=CustomRule, status_code=201)
def add_custom_rule(rule: CustomRuleCreate):
    try:
        parsed = parse_custom_rule(rule.description)
        return create_custom_rule(parsed)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/custom-rules", response_model=list[CustomRule])
def read_custom_rules(enabled: bool | None = None):
    return list_custom_rules(enabled=enabled)
