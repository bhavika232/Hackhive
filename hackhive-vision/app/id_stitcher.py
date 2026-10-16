"""Conservatively reconnect person tracks across short fall-related gaps."""

from app.schemas import Detection


def _center(bbox: tuple[float, float, float, float]) -> tuple[float, float]:
    return ((bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2)


def _ratio(bbox: tuple[float, float, float, float]) -> float:
    return (bbox[2] - bbox[0]) / max(1e-6, bbox[3] - bbox[1])


def _height(bbox: tuple[float, float, float, float]) -> float:
    return bbox[3] - bbox[1]


class IdStitcher:
    """Keep a stable person ID when a fall briefly interrupts tracking.

    A new track is linked only when its box looks horizontal and is near a recently
    lost person. Standing-to-standing tracks are never linked.
    """

    def __init__(
        self,
        max_gap_s: float = 3.0,
        max_dist: float = 1.2,
        wide_ratio: float = 0.9,
        shape_change: float = 0.2,
    ) -> None:
        if max_gap_s <= 0 or max_dist <= 0 or wide_ratio <= 0 or shape_change < 0:
            raise ValueError("stitcher thresholds must be positive (shape_change may be zero)")
        self.max_gap_s = max_gap_s
        self.max_dist = max_dist
        self.wide_ratio = wide_ratio
        self.shape_change = shape_change
        self.alias: dict[int, int] = {}  # raw tracker ID -> stable ID
        self.last_seen: dict[int, tuple[tuple[float, float, float, float], float]] = {}

    def _prune(self, video_time_s: float) -> None:
        expired = {
            stable_id
            for stable_id, (_, seen_time) in self.last_seen.items()
            if video_time_s - seen_time > 10 * self.max_gap_s
        }
        for stable_id in expired:
            del self.last_seen[stable_id]
        if expired:
            self.alias = {
                raw_id: stable_id
                for raw_id, stable_id in self.alias.items()
                if stable_id not in expired
            }

    def _find_lost_track(
        self,
        bbox: tuple[float, float, float, float],
        video_time_s: float,
        active: set[int],
    ) -> int | None:
        new_ratio = _ratio(bbox)
        if new_ratio < self.wide_ratio:
            return None

        cx, cy = _center(bbox)
        best: tuple[int, float] | None = None
        for stable_id, (old_bbox, old_time) in self.last_seen.items():
            gap = video_time_s - old_time
            if stable_id in active or gap < 0 or gap > self.max_gap_s:
                continue

            old_ratio = _ratio(old_bbox)
            # Require evidence of a change from upright to horizontal, or that
            # both observations are already horizontal. This avoids merging a
            # nearby unrelated person based on position alone.
            if old_ratio < self.wide_ratio and new_ratio - old_ratio < self.shape_change:
                continue

            ox, oy = _center(old_bbox)
            distance = ((cx - ox) ** 2 + (cy - oy) ** 2) ** 0.5
            if distance > self.max_dist * max(_height(bbox), _height(old_bbox)):
                continue
            if best is None or distance < best[1]:
                best = (stable_id, distance)
        return best[0] if best is not None else None

    def apply(self, detections: list[Detection], video_time_s: float) -> list[Detection]:
        """Return detections with stable IDs for eligible person tracks."""
        self._prune(video_time_s)
        stable_by_index: dict[int, int] = {}
        active: set[int] = set()
        new_indices: list[int] = []

        for index, detection in enumerate(detections):
            if detection.label != "person" or detection.track_id is None:
                continue
            stable_id = self.alias.get(detection.track_id)
            if stable_id is None:
                new_indices.append(index)
            else:
                stable_by_index[index] = stable_id
                active.add(stable_id)

        for index in new_indices:
            detection = detections[index]
            raw_id = detection.track_id
            # The None case was excluded above; keeping this guard narrows the
            # type for static checkers without changing runtime behavior.
            if raw_id is None:
                continue
            stable_id = self._find_lost_track(detection.bbox, video_time_s, active)
            if stable_id is None:
                stable_id = raw_id
            self.alias[raw_id] = stable_id
            stable_by_index[index] = stable_id
            active.add(stable_id)

        for index, stable_id in stable_by_index.items():
            self.last_seen[stable_id] = (detections[index].bbox, video_time_s)

        return [
            detection.model_copy(update={"track_id": stable_by_index[index]})
            if index in stable_by_index and stable_by_index[index] != detection.track_id
            else detection
            for index, detection in enumerate(detections)
        ]
