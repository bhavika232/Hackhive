# tools/check_line.py
import os
import sys

import cv2

sys.path.insert(0, ".")
from app.config import ENTRANCE_LINES  # noqa: E402

video, camera_id = sys.argv[1], sys.argv[2]
line = ENTRANCE_LINES[camera_id]
cap = cv2.VideoCapture(video)
n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
fps = cap.get(cv2.CAP_PROP_FPS)
w, h = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
print(f"{w}x{h}, {fps:.1f} fps, {n} frames, {n / fps:.1f} s")

a, b = (int(line.x1 * w), int(line.y1 * h)), (int(line.x2 * w), int(line.y2 * h))
# The "+1 side" of the line: this is the direction used by entry_direction=1
nx, ny = -(b[1] - a[1]), (b[0] - a[0])
norm = max((nx ** 2 + ny ** 2) ** 0.5, 1)
mid = ((a[0] + b[0]) // 2, (a[1] + b[1]) // 2)
tip = (int(mid[0] + nx / norm * 80), int(mid[1] + ny / norm * 80))

os.makedirs("evidence/line_check", exist_ok=True)
for i in range(6):
    cap.set(cv2.CAP_PROP_POS_FRAMES, int(n * (i + 0.5) / 6))
    ok, frame = cap.read()
    if not ok:
        continue
    cv2.line(frame, a, b, (0, 255, 0), 2)
    cv2.arrowedLine(frame, mid, tip, (0, 0, 255), 2)
    cv2.putText(frame, "+1 side", tip, cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
    cv2.imwrite(f"evidence/line_check/frame_{i}.jpg", frame)
print("Saved 6 frames to evidence/line_check/")