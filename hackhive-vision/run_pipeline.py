
import json
import os
import sys
import time
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

from app.config import ENTRANCE_LINES
from app.event_classifier import EventClassifier
from app.frame_pipeline import process_video
from app.tracker import ObjectTracker

HISTORY_S = 15.0
BACKEND_URL = os.getenv(
    "SENTINEL_BACKEND_URL",
    "http://127.0.0.1:8000/ingest/vision-event",
)


def send_event(candidate):
    payload = candidate.model_dump(mode="json")
    request = Request(
        BACKEND_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urlopen(request, timeout=10) as response:
            result = json.loads(response.read().decode("utf-8"))
            print(
                f"SAVED incident_id={result.get('incident_id')} "
                f"category={result.get('category')}"
            )
    except HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")
        print(f"Backend rejected event ({exc.code}): {details}")
    except (URLError, TimeoutError) as exc:
        print(f"Could not reach backend: {exc}")


def run(frames, classifier, on_event, history_s=HISTORY_S):
    history = []
    frame_times_s = []

    for frame in frames:
        start = time.time()

        try:
            candidates = classifier.classify(frame, history)
        except Exception as exc:
            print(
                f"[run_pipeline] classify failed "
                f"at t={frame.video_time_s}: {exc}"
            )
            candidates = []

        frame_times_s.append(time.time() - start)

        for candidate in candidates:
            on_event(candidate)

        history.append(frame)
        history = [
            item for item in history
            if frame.video_time_s - item.video_time_s <= history_s
        ]

    if frame_times_s:
        mean_time = sum(frame_times_s) / len(frame_times_s)
        print(
            f"Processed {len(frame_times_s)} frames; "
            f"mean classification time {mean_time:.3f}s"
        )


def main():
    if len(sys.argv) < 3:
        print(
            "Usage: python run_pipeline.py <video_path> <camera_id>"
        )
        raise SystemExit(2)

    video = sys.argv[1]
    camera_id = sys.argv[2]

    if not Path(video).is_file():
        raise FileNotFoundError(f"Video not found: {video}")

    tracker = ObjectTracker()

    kwargs = {"entrance_line": ENTRANCE_LINES.get(camera_id)}
    if os.getenv("USE_VLM", "1") == "0":
        kwargs["verifier"] = lambda path, category: None
        kwargs["describer"] = lambda path: None

    classifier = EventClassifier(**kwargs)

    vision_dir = Path(__file__).resolve().parent
    evidence_dir = vision_dir / "evidence"
    evidence_dir.mkdir(parents=True, exist_ok=True)

    events_path = evidence_dir / "events.jsonl"

    def on_event(candidate):
        print(
            f"EVENT {candidate.category.value} "
            f"t={candidate.start_video_time_s:.1f}s "
            f"{candidate.confidence_status.value} "
            f"conf={candidate.confidence}: {candidate.summary}"
        )

        with events_path.open("a", encoding="utf-8") as out:
            out.write(candidate.model_dump_json() + "\n")

        send_event(candidate)

    frames = process_video(
        video,
        camera_id,
        tracker,
        evidence_dir=str(evidence_dir / "frames"),
    )
    run(frames, classifier, on_event)


if __name__ == "__main__":
    main()
