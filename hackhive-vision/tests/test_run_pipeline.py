# tests/test_run_pipeline.py
import io
import json
import sys
from urllib.error import HTTPError

from app.event_classifier import EventClassifier
from app.schemas import (
    Category,
    ConfidenceStatus,
    Detection,
    EventCandidate,
    FrameData,
)
import run_pipeline
from run_pipeline import run

STANDING = (100, 100, 150, 250)
LYING = (100, 200, 250, 250)


def make_frame(t, bbox):
    return FrameData(camera_id="cam1", frame_index=int(t * 5), video_time_s=t,
                     frame_path="x.jpg", width=640, height=480,
                     detections=[Detection(track_id=1, label="person", confidence=0.9, bbox=bbox)],
                     person_count=1)


def test_fall_sequence_produces_one_event():
    frames = [make_frame(0, STANDING)] + [make_frame(t / 2, LYING) for t in range(1, 9)]
    clf = EventClassifier(verifier=lambda p, c: True, describer=lambda p: "person on floor")
    events = []
    run(frames, clf, events.append)
    assert len(events) == 1  # cooldown stops repeat alerts for the same fall


def test_run_reports_count_metrics_and_bridges_short_crowd_dip():
    def frame_with_count(t, count):
        detections = [
            Detection(
                track_id=index,
                label="person",
                confidence=0.9,
                bbox=STANDING,
            )
            for index in range(count)
        ]
        return FrameData(
            camera_id="cam1",
            frame_index=round(t * 15),
            video_time_s=t,
            frame_path="frame.jpg",
            width=640,
            height=480,
            detections=detections,
            person_count=count,
        )

    frames = [
        frame_with_count(t / 4, 7 if t == 6 else 8)
        for t in range(13)
    ]
    classifier = EventClassifier(
        verifier=lambda _path, _category: None,
        describer=lambda _path: None,
    )
    events = []

    metrics = run(frames, classifier, events.append)

    assert metrics["processed_frames"] == 13
    assert metrics["min_person_count"] == 7
    assert metrics["max_person_count"] == 8
    assert metrics["frames_at_or_above_crowd_threshold"] == 12
    assert metrics["longest_qualifying_crowd_duration_s"] == 3.0
    assert metrics["brief_count_dips_bridged"] == 1
    assert metrics["effective_fps"] == 4.0
    assert metrics["events"] == {"crowd_incident": 1}
    assert len(events) == 1


def test_crashing_classifier_does_not_stop_run():
    class Boom:
        calls = 0

        def classify(self, frame, history):
            Boom.calls += 1
            raise RuntimeError("boom")

    frames = [make_frame(t, STANDING) for t in range(3)]
    run(frames, Boom(), lambda c: None)
    assert Boom.calls == 3


def make_event_candidate():
    return EventCandidate(
        camera_id="cam1",
        category=Category.TAILGATING,
        start_video_time_s=8.4,
        summary="Two people crossed the entrance together.",
        confidence=0.6,
        confidence_status=ConfidenceStatus.RULE_ONLY,
        keyframe_path="evidence/cam1/f000210.jpg",
        track_ids=[3, 8],
    )


def test_send_event_posts_vision_candidate_json(monkeypatch, capsys):
    captured = {}

    class FakeResponse:
        status = 201

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return b'{"incident_id": 42, "category": "tailgating"}'

    def fake_urlopen(request, timeout):
        captured["request"] = request
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr(run_pipeline, "BACKEND_URL", "http://localhost/test-ingest")
    monkeypatch.setattr(run_pipeline, "urlopen", fake_urlopen)

    run_pipeline.send_event(make_event_candidate())

    request = captured["request"]
    payload = json.loads(request.data.decode("utf-8"))
    assert request.full_url == "http://localhost/test-ingest"
    assert request.get_method() == "POST"
    assert request.get_header("Content-type") == "application/json"
    assert captured["timeout"] == 10
    assert payload["category"] == "tailgating"
    assert payload["start_video_time_s"] == 8.4
    assert payload["confidence_status"] == "rule_only"
    assert payload["track_ids"] == [3, 8]
    assert "POSTED incident_id=42 category=tailgating" in capsys.readouterr().out


def test_send_event_reports_backend_validation_rejection(monkeypatch, capsys):
    error = HTTPError(
        "http://localhost/test-ingest",
        422,
        "Unprocessable Entity",
        hdrs=None,
        fp=io.BytesIO(b'{"detail":"confidence must be between 0 and 1"}'),
    )

    def reject_request(_request, timeout):
        raise error

    monkeypatch.setattr(run_pipeline, "urlopen", reject_request)

    assert run_pipeline.send_event(make_event_candidate()) is False

    assert "POST_FAILED HTTP 422" in capsys.readouterr().out


def test_main_uses_configured_evidence_directory(monkeypatch, tmp_path):
    video = tmp_path / "sample.mov"
    video.touch()
    output = tmp_path / "evaluation-evidence"
    captured = {}

    class FakeTracker:
        pass

    def fake_process_video(_video, _camera, _tracker, **kwargs):
        captured["evidence_dir"] = kwargs["evidence_dir"]
        return []

    monkeypatch.setenv("SENTINEL_EVIDENCE_DIR", str(output))
    monkeypatch.setattr(sys, "argv", ["run_pipeline.py", str(video), "cam1"])
    monkeypatch.setattr(run_pipeline, "ObjectTracker", FakeTracker)
    monkeypatch.setattr(run_pipeline, "process_video", fake_process_video)
    monkeypatch.setattr(run_pipeline, "check_backend", lambda _url: True)

    run_pipeline.main()

    assert output.is_dir()
    assert captured["evidence_dir"] == str(output / "frames")


def test_run_counts_failed_ingestion(capsys):
    frames = [make_frame(0, STANDING)]

    class Emits:
        crowd_threshold = 8

        def classify(self, _frame, _history):
            return [make_event_candidate()]

    stats = run(frames, Emits(), lambda _candidate: False)

    assert stats["events"] == {"tailgating": 1}
    assert stats["posted"] == {}
    assert stats["ingestion_failures"] == 1
    assert "ingestion_failures=1" in capsys.readouterr().out


def test_send_event_requires_incident_id(monkeypatch, capsys):
    class FakeResponse:
        status = 201

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return b'{"category":"tailgating"}'

    monkeypatch.setattr(run_pipeline, "urlopen", lambda *_args, **_kwargs: FakeResponse())

    assert run_pipeline.send_event(make_event_candidate()) is False
    assert "POST_FAILED" in capsys.readouterr().out


def test_main_rejects_invalid_target_fps(monkeypatch, tmp_path, capsys):
    video = tmp_path / "sample.mov"
    video.touch()
    monkeypatch.setenv("SENTINEL_TARGET_FPS", "0")

    result = run_pipeline.main([str(video), "cam1"])

    assert result == 2
    assert "invalid target FPS" in capsys.readouterr().err
