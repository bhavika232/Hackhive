from app import detector, vlm_service


def test_ultralytics_telemetry_and_update_checks_are_disabled():
    from ultralytics.utils.events import events
    from ultralytics.utils import checks

    assert detector.SETTINGS["sync"] is False
    assert events.enabled is False
    assert checks.ONLINE is False


def test_vlm_verification_parser_accepts_only_clear_yes_or_no(monkeypatch):
    answers = iter(["Yes, clearly.", "No.", "Probably yes", ""])
    monkeypatch.setattr(vlm_service, "_generate", lambda *_args, **_kwargs: next(answers))

    assert vlm_service.verify_event("frame.jpg", "person_down") is True
    assert vlm_service.verify_event("frame.jpg", "person_down") is False
    assert vlm_service.verify_event("frame.jpg", "person_down") is None
    assert vlm_service.verify_event("frame.jpg", "person_down") is None


def test_vlm_model_load_is_cache_only(monkeypatch):
    processor_calls = []
    model_calls = []

    class FakeProcessor:
        @staticmethod
        def from_pretrained(*args, **kwargs):
            processor_calls.append((args, kwargs))
            return object()

    class FakeModel:
        def to(self, _device):
            return self

        def eval(self):
            return self

        @staticmethod
        def from_pretrained(*args, **kwargs):
            model_calls.append((args, kwargs))
            return FakeModel()

    monkeypatch.setattr(vlm_service, "AutoProcessor", FakeProcessor)
    monkeypatch.setattr(vlm_service, "AutoModelForImageTextToText", FakeModel)
    monkeypatch.setattr(vlm_service, "_processor", None)
    monkeypatch.setattr(vlm_service, "_model", None)
    vlm_service._load()

    assert processor_calls[0][1]["local_files_only"] is True
    assert model_calls[0][1]["local_files_only"] is True


def test_yolo_model_load_is_cache_only(monkeypatch):
    hub_calls = []
    yolo_calls = []
    monkeypatch.setattr(
        detector,
        "hf_hub_download",
        lambda **kwargs: hub_calls.append(kwargs) or "cached-yolo.pt",
    )
    monkeypatch.setattr(
        detector,
        "YOLO",
        lambda path: yolo_calls.append(path) or "model",
    )

    assert detector.load_model() == "model"
    assert hub_calls[0]["local_files_only"] is True
    assert yolo_calls == ["cached-yolo.pt"]
