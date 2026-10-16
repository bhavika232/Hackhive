from app.schemas import Detection


def _center(b):
    return ((b[0] + b[2]) / 2, (b[1] + b[3]) / 2)


def _ratio(b):
    return (b[2] - b[0]) / max(1e-6, (b[3] - b[1]))   # width / height


def _height(b):
    return b[3] - b[1]


class IdStitcher:
    """Keeps one ID for a person who falls down.

    When someone falls, the detector often loses them for a second and the tracker
    gives them a new ID. This reconnects a NEW person track to a recently LOST one
    if it is close by AND the body got wider (standing -> lying) or both are lying.
    Standing -> standing is never stitched, so different people keep different IDs.
    """

    def __init__(self, max_gap_s=3.0, max_dist=1.2, wide_ratio=0.9, shape_change=0.3):
        self.max_gap_s = max_gap_s          # max seconds a track can be missing
        self.max_dist = max_dist            # max centre distance, x the larger box height
        self.wide_ratio = wide_ratio        # width/height at or above this = lying down
        self.shape_change = shape_change    # min increase in width/height to count as a fall
        self.alias = {}                     # raw tracker id -> stable id
        self.last_seen = {}                 # stable id -> (bbox, time)

    def _find_lost_track(self, bbox, t, active):
        best, best_dist = None, None
        cx, cy = _center(bbox)
        new_ratio = _ratio(bbox)

        for stable, (old_bbox, old_t) in self.last_seen.items():
            if stable in active or t - old_t > self.max_gap_s:
                continue
            if new_ratio < self.wide_ratio:
                continue   # only link boxes that look lying down (wide)
            ox, oy = _center(old_bbox)
            dist = ((cx - ox) ** 2 + (cy - oy) ** 2) ** 0.5
            if dist > self.max_dist * max(_height(bbox), _height(old_bbox)):
                continue
            if best is None or dist < best_dist:
                best, best_dist = stable, dist
        return best

    def apply(self, detections: list[Detection], video_time_s: float) -> list[Detection]:
        """Return the detections with stitched track IDs for people."""
        stable_of = {}   # detection index -> stable id
        active = set()
        new_idx = []

        for i, d in enumerate(detections):
            if d.label != "person" or d.track_id is None:
                continue
            if d.track_id in self.alias:
                stable_of[i] = self.alias[d.track_id]
                active.add(stable_of[i])
            else:
                new_idx.append(i)

        for i in new_idx:
            d = detections[i]
            match = self._find_lost_track(d.bbox, video_time_s, active)
            stable = match if match is not None else d.track_id
            self.alias[d.track_id] = stable
            stable_of[i] = stable
            active.add(stable)

        for i, stable in stable_of.items():
            self.last_seen[stable] = (detections[i].bbox, video_time_s)

        # forget tracks missing for a long time
        for stable in [s for s, (_, t) in self.last_seen.items() if video_time_s - t > 10 * self.max_gap_s]:
            del self.last_seen[stable]

        out = []
        for i, d in enumerate(detections):
            if i in stable_of and stable_of[i] != d.track_id:
                d = d.model_copy(update={"track_id": stable_of[i]})
            out.append(d)
        return out