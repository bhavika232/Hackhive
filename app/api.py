
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException


from app.database import (
    init_db,
    insert_incident,
    get_incident,
    list_incidents as db_list_incidents,
)

from app.schemas import (
    IncidentCreate,
    Incident,
    Category,
    ReviewStatus,
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Sentinel Vision",
    description="Video incident detection and retrieval API",
    lifespan=lifespan,
)



@app.get("/incidents", response_model=list[Incident])
def read_incidents(
    category: Category | None = None,
    review_status: ReviewStatus | None = None,
):
    return db_list_incidents(
        category=category,
        review_status=review_status,
    )


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/incidents", response_model=Incident)
def create_incident(incident: IncidentCreate):
    return insert_incident(incident)


@app.get("/incidents/{incident_id}", response_model=Incident)
def read_incident(incident_id: int):
    incident = get_incident(incident_id)

    if incident is None:
        raise HTTPException(status_code=404, detail="Incident not found")

    return incident


@app.get("/incidents", response_model=list[Incident])
def list_incidents():
    from app.database import get_connection

    with get_connection() as conn:
        rows = conn.execute(
            "SELECT incident_id FROM incidents ORDER BY incident_id DESC"
        ).fetchall()

    incidents = [
        get_incident(row["incident_id"])
        for row in rows
    ]

    return incidents
