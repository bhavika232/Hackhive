# HackHive Vision

Local video detection and incident generation for person-down, tailgating, and count-based crowd alerts. The pipeline uses local YOLO person detection/tracking, local rules/classification, optional local SmolVLM verification, and the separate HackHive FastAPI backend with SQLite.

## Requirements and local setup

The tested environment is Windows, Python 3.11.9, and CUDA 12.6 with an NVIDIA GPU. CPU inference is possible, but will be slower. Use a virtual environment in this repository:

```powershell
cd C:\Users\Bhavika\Desktop\codes\hackhive\Hackhive\hackhive-vision
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install --index-url https://download.pytorch.org/whl/cu126 "torch==2.14.1+cu126"
python -m pip install -r requirements.txt
```

If PowerShell blocks activation, run `Set-ExecutionPolicy -Scope Process Bypass` in that terminal and activate again. On a CPU-only machine, install the matching CPU PyTorch wheel from the official PyTorch package index, then install the remaining requirements; the tested GPU performance does not apply.

The repository ignores `.venv/` and `.env` files. Do not add either to Git.

## Model weights and offline inference

The detector loads `yolov8n.pt` from the Hugging Face repository `Ultralytics/YOLOv8`. `app/detector.py` calls `hf_hub_download(..., local_files_only=True)`, so it will **not** fetch weights during a video run. Optional VLM mode loads `HuggingFaceTB/SmolVLM-256M-Instruct` through Transformers with `local_files_only=True`; it also will not download during inference.

Perform any required model download separately while setting up the machine, then enable offline mode for inference:

```powershell
# One-time detector weight download, if not already cached:
python -c "from huggingface_hub import hf_hub_download; print(hf_hub_download(repo_id='Ultralytics/YOLOv8', filename='yolov8n.pt'))"

# Optional one-time local VLM snapshot download (only needed for USE_VLM=1):
hf download HuggingFaceTB/SmolVLM-256M-Instruct
```

Both model downloads use Hugging Face Hub for obtaining model files only; the project does not use hosted inference. Review the upstream model licenses before redistribution or deployment. The YOLOv8 weights/repository are AGPL-3.0, and SmolVLM is Apache-2.0. The primary demo can use rule-only mode and does not require SmolVLM weights.

## Start the backend

In a second PowerShell terminal, start the separate backend repository:

```powershell
cd C:\Users\Bhavika\Desktop\codes\hackhive\hackhive-backend
\.venv\Scripts\Activate.ps1
python -m uvicorn app.api:app --reload
```

The runner checks the backend's existing `GET http://127.0.0.1:8000/health` endpoint before processing. Its default ingestion URL is `http://127.0.0.1:8000/ingest/vision-event`.

## Run one video

In the vision terminal, with the environment activated:

```powershell
$env:USE_VLM = '0'
$env:HF_HUB_OFFLINE = '1'
$env:SENTINEL_BACKEND_URL = 'http://127.0.0.1:8000/ingest/vision-event'
$env:SENTINEL_TARGET_FPS = '15'
$env:SENTINEL_EVIDENCE_DIR = (Join-Path (Get-Location) 'evidence\demo')
python run_pipeline.py 'sample_videos\fall_30fps.mp4' cam1
```

The CLI accepts `video_path camera_id`. `--target-fps` overrides `SENTINEL_TARGET_FPS`; the default is 15 FPS. `cam0` and `cam1` use their configured entrance line for tailgating. Use a camera ID with no entrance-line configuration (for example `ucf_eval`) for crowd clips, so an unrelated doorway rule is not applied. `USE_VLM=0` runs the rules locally; omit it or set it to `1` to enable the optional local VLM, which requires its weights to be cached. Set `HF_HUB_OFFLINE=1` for offline runs.

### Scenario commands

After setting the environment variables above, run one command per scenario:

```powershell
# Fall/person-down positive clip
python run_pipeline.py 'sample_videos\fall_30fps.mp4' cam1

# Tailgating positive clip; cam1 has the configured entrance line
python run_pipeline.py 'sample_videos\tailgate_5.mp4' cam1

# Dense crowd clip; no entrance line is configured for ucf_eval
python run_pipeline.py 'sample_videos\UCF_CrowdsDataset\879-38_l.mov' ucf_eval

# Sparse crowd negative control
python run_pipeline.py 'sample_videos\UCF_CrowdsDataset\620-72_l.mov' ucf_eval
```

These are expected scenarios, not guaranteed model outcomes. The crowd rule is based on person count and duration; it does not measure physical proximity/clustering. The fall rule can produce geometric false positives, including on people who are walking. Inspect events and evidence before treating them as confirmed.

The runner prints processed frames, elapsed wall time, achieved video sampling FPS, processing FPS, person-count statistics, classified categories, successful POSTs, and failed ingestion/classification counts. `CLASSIFIED` means the vision pipeline emitted an event candidate; only `POSTED incident_id=...` confirms the backend accepted and returned a persisted incident. `POST_FAILED` or a nonzero process exit indicates a failed run. Evidence frames and the append-only `events.jsonl` are written under `SENTINEL_EVIDENCE_DIR`.

## Verify incidents

The ingestion endpoint accepts the serialized vision event fields: `camera_id`, `category`, `start_video_time_s`, optional `end_video_time_s` and `start_wall_time`, `summary`, `confidence`, `confidence_status`, `keyframe_path`, and `track_ids`. A successful ingestion returns HTTP 201 and an incident object with `incident_id` and `review_status`.

List incidents from PowerShell:

```powershell
Invoke-RestMethod 'http://127.0.0.1:8000/incidents' | ConvertTo-Json -Depth 8
```

`keyframe_path` is currently a path on the machine running vision. The backend stores that path; it does not serve the file as an HTTP URL. A frontend must either access the shared/local evidence filesystem or a separate evidence-serving route must be added before browser clients can display it.

## Tests and local validation

```powershell
python -m pytest -q
git diff --check
git status --short
```

Unit tests mock HTTP for event posting; the scenario commands above exercise the live API and SQLite store. To review only new incidents, record the existing IDs before a run and compare with the subsequent `GET /incidents` output. Do not clear the database between scenarios.

## Troubleshooting

- `Video not found`: use a path relative to the vision repository or an existing absolute path.
- `Backend unavailable`: start the backend and verify `Invoke-RestMethod http://127.0.0.1:8000/health`.
- Missing detector or VLM weights in offline mode: run the one-time download while online; do not disable `local_files_only` to make inference silently use a hosted service.
- `POST_FAILED HTTP 422`: the backend rejected the serialized event; inspect the displayed response body and compare it with `app/schemas.py` in the backend.
- No events: zero emitted events can be a valid result; inspect processed-frame and person-count metrics, the appropriate camera configuration, and the clip/evidence. Do not manufacture an event to test ingestion.
- Partial or corrupt video decodes: OpenCV can stop at the first unreadable frame; the CLI reports zero processed frames as failure, but a partially readable file may end without a reliable codec-level corruption signal.
