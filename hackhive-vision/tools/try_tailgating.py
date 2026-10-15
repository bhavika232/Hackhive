# tools/try_tailgating.py
import os
import sys

import cv2
from ultralytics import YOLO

sys.path.insert(0, ".")
from app.config import ENTRANCE_LINES  # noqa: E402
from app.event_rules import _ref_point, check_tailgating  # noqa: E402
from app.schemas import Detection, FrameData  # noqa: E402

video, camera_id = sys.argv[1], sys.argv[2]
line = ENTRANCE_LINES[camera_id]

weights = os.getenv("YOLO_WEIGHTS")  # set this to a local .pt path if the HF download fails
if not weights:
    from huggingface_hub import hf_hub_download
    weights = hf_hub_download(repo_id="Ultralytics/YOLOv8", filename="yolov8n.pt")
model = YOLO(weights)

cap = cv2.VideoCapture(video)
fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
w, h = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
cap.release()
stride = max(1, round(fps / 5))  # about 5 sampled frames per second
a, b = (int(line.x1 * w), int(line.y1 * h)), (int(line.x2 * w), int(line.y2 * h))

os.makedirs("evidence", exist_ok=True)
out = cv2.VideoWriter("evidence/try_tailgating.mp4", cv2.VideoWriter_fourcc(*"mp4v"),
                      fps / stride, (w, h))
history, seen_ids, reported = [], set(), set()

results = model.track(source=video, stream=True, persist=True, tracker="bytetrack.yaml",
                      classes=[0], vid_stride=stride, verbose=False)
for i, r in enumerate(results):
    t = i * stride / fps
    img = r.orig_img.copy()
    boxes = r.boxes
    ids = boxes.id.int().tolist() if boxes.id is not None else [None] * len(boxes)
    dets = []
    for xyxy, conf, tid in zip(boxes.xyxy.tolist(), boxes.conf.tolist(), ids):
        dets.append(Detection(track_id=tid, label="person", confidence=conf, bbox=tuple(xyxy)))
        if tid is not None:
            seen_ids.add(tid)
        x1, y1, x2, y2 = map(int, xyxy)
        px, py = map(int, _ref_point(xyxy, line.ref))
        cv2.rectangle(img, (x1, y1), (x2, y2), (255, 200, 0), 2)
        cv2.circle(img, (px, py), 6, (0, 0, 255), -1)
        cv2.putText(img, f"id{tid}", (x1, y1 - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 200, 0), 2)
    cv2.line(img, a, b, (0, 255, 0), 2)

    frame = FrameData(camera_id=camera_id, frame_index=i * stride, video_time_s=t,
                      frame_path="debug", width=w, height=h,
                      detections=dets, person_count=len(dets))
    hit = check_tailgating(frame, history, line)
    if hit:
        cv2.putText(img, "TAILGATING", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 255), 3)
        key = tuple(hit.track_ids)
        if key not in reported:
            reported.add(key)
            print(f"HIT at t={t:.1f}s tracks={hit.track_ids}: {hit.evidence}")
    out.write(img)
    history.append(frame)
    history = [f for f in history if t - f.video_time_s <= 15.0]

out.release()
print(f"Track IDs seen: {sorted(seen_ids)}")
print("Saved evidence/try_tailgating.mp4")