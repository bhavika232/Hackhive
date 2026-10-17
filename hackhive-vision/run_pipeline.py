"""Run one local video through detection, rules, classification, and ingestion."""

import argparse
import json
import os
import sys
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit, urlunsplit
from urllib.request import Request, urlopen

from app.config import ENTRANCE_LINES
from app.event_classifier import EventClassifier
from app.event_memory import EventMemory
from app.frame_pipeline import process_video
from app.tracker import ObjectTracker

HISTORY_S = 15.0
DEFAULT_BACKEND_URL = "http://127.0.0.1:8000/ingest/vision-event"
BACKEND_URL = os.getenv("SENTINEL_BACKEND_URL", DEFAULT_BACKEND_URL)
DEFAULT_TARGET_FPS = 15.0


def _health_url(ingest_url: str) -> str:
    parts = urlsplit(ingest_url)
    if parts.scheme not in {"http", "https"} or not parts.netloc:
        raise ValueError(f"Invalid backend URL: {ingest_url}")
    return urlunsplit((parts.scheme, parts.netloc, "/health", "", ""))


def check_backend(ingest_url: str | None = None) -> bool:
    """Confirm the backend's documented health endpoint before processing."""
    ingest_url = ingest_url or BACKEND_URL
    try:
        request = Request(_health_url(ingest_url), method="GET")
        with urlopen(request, timeout=5) as response:
            result = json.loads(response.read().decode("utf-8"))
            if response.status != 200 or not isinstance(result, dict) or result.get("status") != "ok":
                print(f"Backend health check failed: HTTP {response.status}: {result}")
                return False
        print(f"BACKEND_READY url={ingest_url}")
        return True
    except (HTTPError, URLError, TimeoutError, OSError, ValueError) as exc:
        print(f"Backend unavailable at {ingest_url}: {exc}")
        return False


def send_event(candidate, backend_url: str | None = None) -> bool:
    """POST a candidate; success requires a valid incident response body."""
    backend_url = backend_url or BACKEND_URL
    payload = candidate.model_dump(mode="json")
    request = Request(
        backend_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urlopen(request, timeout=10) as response:
            result = json.loads(response.read().decode("utf-8"))
            if response.status not in (200, 201) or not isinstance(result, dict):
                raise ValueError(f"unexpected HTTP/body: {response.status}, {result!r}")
            if not isinstance(result.get("incident_id"), int):
                raise ValueError(f"response has no incident_id: {result!r}")
            category = result.get("category", payload["category"])
            print(f"POSTED incident_id={result['incident_id']} category={category}")
            return True
    except HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")
        print(f"POST_FAILED HTTP {exc.code}: {details}")
    except (URLError, TimeoutError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"POST_FAILED {exc}")
    return False


def run(frames, classifier, on_event, history_s=HISTORY_S, use_event_memory=False):
    history = []
    classify_times_s = []
    person_counts = []
    frame_times = []
    event_counts = {}
    posted_counts = {}
    ingestion_failures = 0
    classification_failures = 0
    crowd_threshold = getattr(classifier, "crowd_threshold", 8)
    max_observation_gap_s = getattr(classifier, "crowd_max_observation_gap_s", 0.5)
    max_below_threshold_s = getattr(classifier, "crowd_max_below_threshold_s", 0.5)
    qualifying_start_s = None
    below_threshold_start_s = None
    longest_crowded_s = 0.0
    bridged_count_dips = 0
    max_observation_gap = 0.0
    event_memory = EventMemory() if use_event_memory else None
    started = time.monotonic()

    def submit_events(completed_events):
        nonlocal ingestion_failures
        for candidate in completed_events:
            category = getattr(candidate.category, "value", str(candidate.category))
            event_counts[category] = event_counts.get(category, 0) + 1
            try:
                posted = on_event(candidate)
            except Exception as exc:
                posted = False
                print(f"POST_FAILED {exc}")
            if posted:
                posted_counts[category] = posted_counts.get(category, 0) + 1
            else:
                ingestion_failures += 1

    def submit_completed_memory_events():
        completed_events = event_memory.completed_events
        event_memory.completed_events = []
        submit_events(completed_events)

    for frame in frames:
        start = time.monotonic()
        now = frame.video_time_s
        count = frame.person_count
        person_counts.append(count)
        frame_times.append(now)

        if len(frame_times) > 1:
            observation_gap_s = now - frame_times[-2]
            max_observation_gap = max(max_observation_gap, observation_gap_s)
            if observation_gap_s > max_observation_gap_s + 1e-9:
                qualifying_start_s = None
                below_threshold_start_s = None

        if count >= crowd_threshold:
            if qualifying_start_s is None or (
                below_threshold_start_s is not None
                and now - below_threshold_start_s > max_below_threshold_s + 1e-9
            ):
                qualifying_start_s = now
            elif below_threshold_start_s is not None:
                bridged_count_dips += 1
            below_threshold_start_s = None
            longest_crowded_s = max(longest_crowded_s, now - qualifying_start_s)
        elif qualifying_start_s is not None:
            if below_threshold_start_s is None:
                below_threshold_start_s = now
            elif now - below_threshold_start_s > max_below_threshold_s + 1e-9:
                qualifying_start_s = None
                below_threshold_start_s = None

        try:
            candidates = classifier.classify(frame, history)
        except Exception as exc:
            classification_failures += 1
            print(f"CLASSIFICATION_FAILED t={now:.2f}s: {exc}")
            candidates = []
        classify_times_s.append(time.monotonic() - start)

        for candidate in candidates:
            category = getattr(candidate.category, "value", str(candidate.category))
            print(f"CLASSIFIED category={category} t={candidate.start_video_time_s:.2f}s")

        if event_memory is None:
            submit_events(candidates)
        else:
            for candidate in candidates:
                event_memory.add_event(candidate)
            event_memory.flush(now)
            submit_completed_memory_events()

        history.append(frame)
        history = [item for item in history if now - item.video_time_s <= history_s]

    if event_memory is not None:
        event_memory.flush(float("inf"))
        submit_completed_memory_events()

    elapsed_s = time.monotonic() - started
    processed = len(frame_times)
    video_duration_s = frame_times[-1] - frame_times[0] if processed > 1 else 0.0
    effective_fps = (processed - 1) / video_duration_s if video_duration_s > 0 else 0.0
    wall_fps = processed / elapsed_s if elapsed_s > 0 else 0.0
    if processed:
        print(f"Processed {processed} frames in {elapsed_s:.2f}s; mean classification time {sum(classify_times_s) / processed:.3f}s")
        print(f"Detection counts: min={min(person_counts)} max={max(person_counts)} avg={sum(person_counts) / processed:.2f}; >={crowd_threshold} people in {sum(c >= crowd_threshold for c in person_counts)}/{processed} frames")
        print(f"Sampling: effective_video_fps={effective_fps:.2f}; processing_fps={wall_fps:.2f}; max_observation_gap={max_observation_gap:.3f}s; longest_crowd_run={longest_crowded_s:.2f}s; brief_count_dips_bridged={bridged_count_dips}")
    else:
        print("Processed 0 frames; video could not be decoded or yielded no frames.")
    print(f"Run summary: events={event_counts or '{}'} posted={posted_counts or '{}'} ingestion_failures={ingestion_failures} classification_failures={classification_failures}")

    return {
        "processed_frames": processed,
        "elapsed_s": elapsed_s,
        "effective_fps": effective_fps,
        "processing_fps": wall_fps,
        "min_person_count": min(person_counts) if person_counts else None,
        "max_person_count": max(person_counts) if person_counts else None,
        "average_person_count": sum(person_counts) / processed if processed else None,
        "frames_at_or_above_crowd_threshold": sum(c >= crowd_threshold for c in person_counts),
        "longest_qualifying_crowd_duration_s": longest_crowded_s,
        "brief_count_dips_bridged": bridged_count_dips,
        "max_observation_gap_s": max_observation_gap,
        "events": event_counts,
        "posted": posted_counts,
        "ingestion_failures": ingestion_failures,
        "classification_failures": classification_failures,
    }


def _positive_fps(value: str) -> float:
    try:
        fps = float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("FPS must be a number") from exc
    if fps <= 0:
        raise argparse.ArgumentTypeError("FPS must be greater than zero")
    return fps


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Process a video and ingest detected events.")
    parser.add_argument("video_path", help="input video path")
    parser.add_argument("camera_id", help="camera identifier (cam0/cam1 use configured entrance line)")
    parser.add_argument("--target-fps", type=_positive_fps, default=None, help="sampling FPS (default: SENTINEL_TARGET_FPS or 15)")
    args = parser.parse_args(argv)

    video = Path(args.video_path)
    if not video.is_file():
        print(f"ERROR video not found: {video}", file=sys.stderr)
        return 2
    try:
        target_fps = args.target_fps or _positive_fps(
            os.getenv("SENTINEL_TARGET_FPS", str(DEFAULT_TARGET_FPS))
        )
    except argparse.ArgumentTypeError as exc:
        print(f"ERROR invalid target FPS: {exc}", file=sys.stderr)
        return 2
    backend_url = os.getenv("SENTINEL_BACKEND_URL", DEFAULT_BACKEND_URL)
    if not check_backend(backend_url):
        return 3

    try:
        tracker = ObjectTracker()
        kwargs = {"entrance_line": ENTRANCE_LINES.get(args.camera_id)}
        use_vlm = os.getenv("USE_VLM", "1") != "0"
        if not use_vlm:
            kwargs["verifier"] = lambda _path, _category: None
            kwargs["describer"] = lambda _path: None
        classifier = EventClassifier(**kwargs)

        vision_dir = Path(__file__).resolve().parent
        evidence_dir = Path(os.getenv("SENTINEL_EVIDENCE_DIR", str(vision_dir / "evidence")))
        evidence_dir.mkdir(parents=True, exist_ok=True)
        events_path = evidence_dir / "events.jsonl"

        def on_event(candidate):
            with events_path.open("a", encoding="utf-8") as out:
                out.write(candidate.model_dump_json() + "\n")
            return send_event(candidate, backend_url)

        metrics = run(
            process_video(
                str(video), args.camera_id, tracker,
                target_fps=target_fps,
                evidence_dir=str(evidence_dir / "frames"),
            ),
            classifier,
            on_event,
            use_event_memory=True,
        )
        if metrics["processed_frames"] == 0:
            return 4
        if metrics["ingestion_failures"] or metrics["classification_failures"]:
            return 5
        return 0
    except Exception as exc:
        print(f"ERROR pipeline failed: {exc}", file=sys.stderr)
        return 6


if __name__ == "__main__":
    raise SystemExit(main())
