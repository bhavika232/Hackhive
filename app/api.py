
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException

from app.database import (
    init_db,
    insert_incident,
    get_incident,
    list_incidents as db_list_incidents,
    update_review_status,
)
from app.schemas import (
    IncidentCreate,
    Incident,
    Category,
    ReviewStatus,
    IncidentReviewUpdate,
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


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/incidents", response_model=Incident)
def create_incident(incident: IncidentCreate):
    return insert_incident(incident)


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


