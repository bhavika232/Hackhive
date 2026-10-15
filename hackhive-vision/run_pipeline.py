# run_pipeline.py
import json
import os
import sys
import time

from app.config import ENTRANCE_LINES
from app.event_classifier import EventClassifier

HISTORY_S = 15.0  # seconds of past frames the rules can see
frame_times_s: list[float] = []  # per-frame classify cost, for the evaluation report


def run(frames, classifier, on_event, history_s: float = HISTORY_S):
    """frames: iterable of FrameData from ONE camera, in time order."""
    history = []
    for frame in frames:
        start = time.time()
        try:
            candidates = classifier.classify(frame, history)
        except Exception as e:  # one bad frame must not kill the run
            print(f"[run_pipeline] classify failed at t={frame.video_time_s}: {e}")
            candidates = []
        frame_times_s.append(time.time() - start)
        for c in candidates:
            on_event(c)
        history.append(frame)
        history = [f for f in history if frame.video_time_s - f.video_time_s <= history_s]


def main():
    video, camera_id = sys.argv[1], sys.argv[2]
    from app.video_reader import process_video  # Shreya's module

    kwargs = {"entrance_line": ENTRANCE_LINES.get(camera_id)}
    if os.getenv("USE_VLM", "1") == "0":  # rules-only fallback mode
        kwargs["verifier"] = lambda path, category: None
        kwargs["describer"] = lambda path: None
    classifier = EventClassifier(**kwargs)

    os.makedirs("evidence", exist_ok=True)
    with open("evidence/events.jsonl", "a", encoding="utf-8") as out:
        def on_event(c):
            print(f"EVENT {c.category.value} t={c.start_video_time_s:.1f}s "
                  f"{c.confidence_status.value} conf={c.confidence}: {c.summary}")
            out.write(c.model_dump_json() + "\n")
            out.flush()

        run(process_video(video, camera_id), classifier, on_event)

    if frame_times_s:
        print(f"Processed {len(frame_times_s)} frames, "
              f"mean classify time {sum(frame_times_s) / len(frame_times_s):.3f}s")


if __name__ == "__main__":
    main()