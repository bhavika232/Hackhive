
# tools/try_tailgating.py

import os
import sys

import cv2
from ultralytics import YOLO

sys.path.insert(0, ".")

from app.config import ENTRANCE_LINES
from app.event_rules import _ref_point, _orient, check_tailgating
from app.schemas import Detection, FrameData


def main():
    if len(sys.argv) < 3:
        print(
            "Usage: python tools/try_tailgating.py "
            "<video_path> <camera_id>"
        )
        sys.exit(1)

    video, camera_id = sys.argv[1], sys.argv[2]

    if camera_id not in ENTRANCE_LINES:
        print(f"Unknown camera ID: {camera_id}")
        print(f"Available cameras: {list(ENTRANCE_LINES.keys())}")
        sys.exit(1)

    line = ENTRANCE_LINES[camera_id]

    # Load YOLO weights.
    weights = os.getenv("YOLO_WEIGHTS")

    if not weights:
        from huggingface_hub import hf_hub_download

        weights = hf_hub_download(
            repo_id="Ultralytics/YOLOv8",
            filename="yolov8n.pt",
        )

    model = YOLO(weights)

    # Read video properties.
    cap = cv2.VideoCapture(video)

    if not cap.isOpened():
        print(f"Could not open video: {video}")
        sys.exit(1)

    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cap.release()

    print(
        f"Video: {width}x{height}, "
        f"{fps:.1f} FPS, "
        f"{total_frames} frames"
    )

    # Sample approximately 15 frames per second.
    target_fps = 15
    stride = max(1, round(fps / target_fps))

    print(f"Sampling approximately {fps / stride:.1f} FPS")

    # Convert normalized entrance-line coordinates to pixels.
    line_a = (int(line.x1 * width), int(line.y1 * height))
    line_b = (int(line.x2 * width), int(line.y2 * height))

    # Output video.
    os.makedirs("evidence", exist_ok=True)

    output_path = "evidence/try_tailgating.mp4"

    out = cv2.VideoWriter(
        output_path,
        cv2.VideoWriter_fourcc(*"mp4v"),
        fps / stride,
        (width, height),
    )

    if not out.isOpened():
        print("Could not create output video.")
        sys.exit(1)

    history = []
    seen_ids = set()
    reported = set()

    # Track people throughout the video.
    results = model.track(
        source=video,
        stream=True,
        persist=True,
        tracker="bytetrack.yaml",
        classes=[0],
        vid_stride=stride,
        verbose=False,
    )

    for i, result in enumerate(results):
        t = i * stride / fps
        image = result.orig_img.copy()
        boxes = result.boxes

        if boxes.id is not None:
            track_ids = boxes.id.int().tolist()
        else:
            track_ids = [None] * len(boxes)

        detections = []

        # Draw detections and collect tracking data.
        for xyxy, confidence, track_id in zip(
            boxes.xyxy.tolist(),
            boxes.conf.tolist(),
            track_ids,
        ):
            bbox = tuple(xyxy)

            detections.append(
                Detection(
                    track_id=track_id,
                    label="person",
                    confidence=confidence,
                    bbox=bbox,
                )
            )

            if track_id is not None:
                seen_ids.add(track_id)

            x1, y1, x2, y2 = map(int, xyxy)

            point_x, point_y = map(
                int,
                _ref_point(bbox, line.ref),
            )

            # Bounding box.
            cv2.rectangle(
                image,
                (x1, y1),
                (x2, y2),
                (255, 200, 0),
                2,
            )

            # Reference point used by the crossing rule.
            cv2.circle(
                image,
                (point_x, point_y),
                6,
                (0, 0, 255),
                -1,
            )

            # Track ID.
            cv2.putText(
                image,
                f"ID {track_id}",
                (x1, max(20, y1 - 6)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (255, 200, 0),
                2,
            )

            # Debug: print which side of the line the person is on.
            side = _orient(
                (line.x1 * width, line.y1 * height),
                (line.x2 * width, line.y2 * height),
                (point_x, point_y),
            )

            print(
                f"t={t:.1f}s ID={track_id} "
                f"point=({point_x},{point_y}) "
                f"side={side:.0f}"
            )

        # Draw the entrance line.
        cv2.line(
            image,
            line_a,
            line_b,
            (0, 255, 0),
            2,
        )

        frame = FrameData(
            camera_id=camera_id,
            frame_index=i * stride,
            video_time_s=t,
            frame_path="debug",
            width=width,
            height=height,
            detections=detections,
            person_count=len(detections),
        )

        # Check whether multiple people crossed in the same direction.
        hit = check_tailgating(frame, history, line)

        if hit:
            cv2.putText(
                image,
                "TAILGATING",
                (20, 45),
                cv2.FONT_HERSHEY_SIMPLEX,
                1.2,
                (0, 0, 255),
                3,
            )

            key = tuple(sorted(hit.track_ids))

            if key not in reported:
                reported.add(key)
                print(
                    f"HIT at t={t:.1f}s "
                    f"tracks={hit.track_ids}: {hit.evidence}"
                )

        # Write exactly one output frame per sampled frame.
        out.write(image)

        # Keep history for the crossing window.
        history.append(frame)
        history = [
            previous
            for previous in history
            if t - previous.video_time_s <= 15.0
        ]

    out.release()

    print(f"Track IDs seen: {sorted(seen_ids)}")
    print(f"Saved annotated video: {output_path}")


if __name__ == "__main__":
    main()
