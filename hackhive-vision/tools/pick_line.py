# tools/pick_line.py
import sys
import cv2

cap = cv2.VideoCapture(sys.argv[1])
ok, frame = cap.read()
cap.release()
if not ok:
    sys.exit("Could not read video")
h, w = frame.shape[:2]
pts = []


def on_click(event, x, y, flags, param):
    if event == cv2.EVENT_LBUTTONDOWN and len(pts) < 2:
        pts.append((x, y))
        cv2.circle(frame, (x, y), 5, (0, 0, 255), -1)
        if len(pts) == 2:
            cv2.line(frame, pts[0], pts[1], (0, 255, 0), 2)


cv2.namedWindow("click 2 points along the doorway, then press any key")
cv2.setMouseCallback("click 2 points along the doorway, then press any key", on_click)
while True:
    cv2.imshow("click 2 points along the doorway, then press any key", frame)
    if cv2.waitKey(20) != -1:
        break
cv2.destroyAllWindows()
if len(pts) == 2:
    (x1, y1), (x2, y2) = pts
    print(f"EntranceLine(x1={x1/w:.3f}, y1={y1/h:.3f}, x2={x2/w:.3f}, y2={y2/h:.3f})")