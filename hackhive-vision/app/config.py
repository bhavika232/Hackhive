# app/config.py
from app.event_rules import EntranceLine

# camera_id -> doorway line (normalized 0-1). cam1 = tailgate_5.mp4 for now.
ENTRANCE_LINES = {
    "cam1": EntranceLine(x1=0.463, y1=0.229, x2=0.534, y2=0.125),
}