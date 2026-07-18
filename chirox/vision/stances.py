"""Deterministic stance geometry — the unthinking combat algorithm.

No mediapipe, no opencv, no model here on purpose: this module is pure math over
named 2D points, so it is fully unit-testable without a camera. That is the
whole point — the reflex layer's correctness is *proven*, not asserted.

A point is ``(x, y, visibility)``. Visibility (0..1) comes from the tracker; when
the required joints are not clearly seen, the reading is flagged UNCERTAIN and no
confident verdict is given (SAFETY.md: explicit uncertainty, never confident
diagnosis on thin evidence).

Thresholds are honest heuristics for conditioning, not lineage-certified form
law. They are meant to be tightened as the practitioner advances (the Noret
Protocol) — never to impersonate a master's eye.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field

Point = tuple[float, float, float]  # (x, y, visibility)

UNCERTAINTY_THRESHOLD = 0.6

# Joint names Chirox reasons about.
LEFT_HIP, LEFT_KNEE, LEFT_ANKLE, LEFT_SHOULDER = "left_hip", "left_knee", "left_ankle", "left_shoulder"
RIGHT_HIP, RIGHT_KNEE, RIGHT_ANKLE, RIGHT_SHOULDER = "right_hip", "right_knee", "right_ankle", "right_shoulder"
LEFT_ELBOW, RIGHT_ELBOW, LEFT_WRIST, RIGHT_WRIST = "left_elbow", "right_elbow", "left_wrist", "right_wrist"


def angle(a: Point, b: Point, c: Point) -> float:
    """Angle at vertex ``b`` formed by a-b-c, in degrees [0, 180]."""
    rad = math.atan2(c[1] - b[1], c[0] - b[0]) - math.atan2(a[1] - b[1], a[0] - b[0])
    deg = abs(rad * 180.0 / math.pi)
    return 360 - deg if deg > 180 else deg


@dataclass
class StanceReading:
    stance: str
    metrics: dict[str, float]
    flags: list[str] = field(default_factory=list)
    assessment: str = ""
    confidence: float = 1.0     # min visibility of required joints
    uncertain: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


def _confidence(points: dict[str, Point], required: list[str]) -> float:
    if any(j not in points for j in required):
        return 0.0
    vis = [points[j][2] for j in required]
    return min(vis) if vis else 0.0


def _uncertain_reading(stance: str, required: list[str], confidence: float) -> StanceReading:
    return StanceReading(
        stance=stance,
        metrics={},
        flags=["low_visibility"],
        assessment=(
            "UNCERTAIN — required landmarks are not clearly visible; the measurement is "
            "unreliable. Fix the framing/lighting before trusting any verdict."
        ),
        confidence=round(confidence, 3),
        uncertain=True,
    )


# --- Ma Bu (Horse Stance) ------------------------------------------------------

HORSE_REQUIRED = [
    LEFT_HIP, LEFT_KNEE, LEFT_ANKLE, LEFT_SHOULDER,
    RIGHT_HIP, RIGHT_KNEE, RIGHT_ANKLE, RIGHT_SHOULDER,
]


def evaluate_horse_stance(points: dict[str, Point]) -> StanceReading:
    """Ma Bu: knees ~90-100°, spine upright (shoulder-hip-knee ≥ ~150°)."""
    conf = _confidence(points, HORSE_REQUIRED)
    if conf < UNCERTAINTY_THRESHOLD:
        return _uncertain_reading("Horse Stance (Ma Bu)", HORSE_REQUIRED, conf)

    lk = angle(points[LEFT_HIP], points[LEFT_KNEE], points[LEFT_ANKLE])
    rk = angle(points[RIGHT_HIP], points[RIGHT_KNEE], points[RIGHT_ANKLE])
    lb = angle(points[LEFT_SHOULDER], points[LEFT_HIP], points[LEFT_KNEE])
    rb = angle(points[RIGHT_SHOULDER], points[RIGHT_HIP], points[RIGHT_KNEE])

    metrics = {
        "left_knee_angle": round(lk, 2),
        "right_knee_angle": round(rk, 2),
        "left_back_angle": round(lb, 2),
        "right_back_angle": round(rb, 2),
    }
    flags: list[str] = []
    if lk > 120 or rk > 120:
        flags.append("stance_too_high")
    elif lk < 80 or rk < 80:
        flags.append("stance_collapsing")
    if lb < 150 or rb < 150:
        flags.append("spine_slouching")

    assessment = "Stable and rooted." if not flags else " | ".join(_HORSE_MESSAGES[f] for f in flags)
    return StanceReading("Horse Stance (Ma Bu)", metrics, flags, assessment, round(conf, 3), False)


_HORSE_MESSAGES = {
    "stance_too_high": "Stance too high — knees above 120°. Sink lower; drop your center.",
    "stance_collapsing": "Stance collapsing — knee below 80°. Rebuild structure; do not fold.",
    "spine_slouching": "Spine slouching — hold the trunk upright like a pine.",
}


# --- Gong Bu (Bow Stance) ------------------------------------------------------

BOW_REQUIRED = [LEFT_HIP, LEFT_KNEE, LEFT_ANKLE, RIGHT_HIP, RIGHT_KNEE, RIGHT_ANKLE]


def evaluate_bow_stance(points: dict[str, Point], front: str = "left") -> StanceReading:
    """Gong Bu: front knee bent ~90-120° over the ankle, rear leg near-straight (≥150°)."""
    conf = _confidence(points, BOW_REQUIRED)
    if conf < UNCERTAINTY_THRESHOLD:
        return _uncertain_reading("Bow Stance (Gong Bu)", BOW_REQUIRED, conf)

    if front == "left":
        fh, fk, fa = LEFT_HIP, LEFT_KNEE, LEFT_ANKLE
        bh, bk, ba = RIGHT_HIP, RIGHT_KNEE, RIGHT_ANKLE
    else:
        fh, fk, fa = RIGHT_HIP, RIGHT_KNEE, RIGHT_ANKLE
        bh, bk, ba = LEFT_HIP, LEFT_KNEE, LEFT_ANKLE

    front_knee = angle(points[fh], points[fk], points[fa])
    rear_knee = angle(points[bh], points[bk], points[ba])
    metrics = {"front_knee_angle": round(front_knee, 2), "rear_knee_angle": round(rear_knee, 2)}

    flags: list[str] = []
    if not (80 <= front_knee <= 120):
        flags.append("front_knee_out_of_range")
    if rear_knee < 150:
        flags.append("rear_leg_bent")

    messages = {
        "front_knee_out_of_range": "Front knee outside 80-120° — set the bend over the ankle, not past the toes.",
        "rear_leg_bent": "Rear leg bent — drive the back leg straight to root the stance.",
    }
    assessment = "Bow stance grounded." if not flags else " | ".join(messages[f] for f in flags)
    return StanceReading("Bow Stance (Gong Bu)", metrics, flags, assessment, round(conf, 3), False)


# --- Du Li Bu (Crane / One-Leg Stance) ------------------------------------------

CRANE_REQUIRED = [LEFT_HIP, LEFT_KNEE, LEFT_ANKLE, RIGHT_HIP, RIGHT_KNEE, RIGHT_ANKLE]


def evaluate_crane_stance(points: dict[str, Point]) -> StanceReading:
    """Du Li Bu: one knee lifted to hip height or above, standing leg near-straight.

    The lifted leg is inferred, not configured: it is the knee that sits clearly
    higher (screen y is inverted, so higher = smaller y). Thresholds are honest
    conditioning heuristics from published stance standards — never captured
    from a practitioner's body, so a bad day can never become the template.
    """
    conf = _confidence(points, CRANE_REQUIRED)
    if conf < UNCERTAINTY_THRESHOLD:
        return _uncertain_reading("Crane Stance (Du Li Bu)", CRANE_REQUIRED, conf)

    lk_y, rk_y = points[LEFT_KNEE][1], points[RIGHT_KNEE][1]
    # normalize by hip-to-ankle length so the numbers do not depend on framing
    leg_len = abs(points[LEFT_ANKLE][1] - points[LEFT_HIP][1]) or 1e-6
    knee_gap = abs(lk_y - rk_y) / leg_len

    if knee_gap < 0.15:
        return StanceReading(
            "Crane Stance (Du Li Bu)", {"knee_gap": round(knee_gap, 3)}, ["no_lift"],
            "No leg is lifted — raise one knee toward the chest to enter the crane.",
            round(conf, 3), False,
        )

    if lk_y < rk_y:
        lifted_hip, lifted_knee = LEFT_HIP, LEFT_KNEE
        sh, sk, sa = RIGHT_HIP, RIGHT_KNEE, RIGHT_ANKLE
        lifted = "left"
    else:
        lifted_hip, lifted_knee = RIGHT_HIP, RIGHT_KNEE
        sh, sk, sa = LEFT_HIP, LEFT_KNEE, LEFT_ANKLE
        lifted = "right"

    standing_knee = angle(points[sh], points[sk], points[sa])
    # positive = lifted knee above the hip line, in leg-lengths
    lift = (points[lifted_hip][1] - points[lifted_knee][1]) / leg_len

    metrics = {
        # numeric so session aggregation can average it (1.0 = left leg lifted);
        # the mean over a session reads as "fraction of hold spent on the left"
        "lifted_leg_left": 1.0 if lifted == "left" else 0.0,
        "standing_knee_angle": round(standing_knee, 2),
        "knee_lift": round(lift, 3),
    }
    flags: list[str] = []
    if standing_knee < 155:
        flags.append("standing_leg_bent")
    if lift < 0.0:
        flags.append("knee_below_hip")

    messages = {
        "standing_leg_bent": "Standing leg collapsing — press the root leg long and strong.",
        "knee_below_hip": "Lifted knee below the hip — draw it higher, toward the chest.",
    }
    assessment = "Crane balanced." if not flags else " | ".join(messages[f] for f in flags)
    return StanceReading("Crane Stance (Du Li Bu)", metrics, flags, assessment, round(conf, 3), False)


# --- The pose template engine ----------------------------------------------------
#
# One year of Kung Fu needs a catalog, not three functions. Every static pose
# from the reference charts is a declarative template over the same rule
# vocabulary; one engine evaluates them all, so every entry gets the same
# uncertainty gate, the same honest flags, and the same tests.

from typing import NamedTuple


class AngleRule(NamedTuple):
    metric: str
    joints: tuple[str, str, str]     # angle at the middle joint
    lo: float
    hi: float
    flag: str
    message: str


class AboveRule(NamedTuple):
    a: str                            # a must sit HIGHER on screen than b
    b: str
    margin: float                     # in units of the body scale (hip→ankle)
    flag: str
    message: str


class TiltRule(NamedTuple):
    a: str                            # segment a→b compared against an axis
    b: str
    axis: str                         # "vertical" | "horizontal"
    tol_deg: float
    flag: str
    message: str


class AsymRule(NamedTuple):
    """Two-sided legs where one is deep and the other extended (drop stance)."""
    deep_max: float                   # the bent knee must be at most this
    ext_min: float                    # the extended knee must be at least this
    flag: str
    message: str


class DistRule(NamedTuple):
    """Joint pair must stay within a body-scale distance (e.g. feet together)."""
    a: str
    b: str
    max_scale: float                  # max |a-b| / body_scale
    flag: str
    message: str


class PoseTemplate(NamedTuple):
    key: str
    label: str
    view: str                         # "front" | "side" — camera guidance
    required: tuple[str, ...]
    angle_rules: tuple = ()
    above_rules: tuple = ()
    tilt_rules: tuple = ()
    asym_rules: tuple = ()
    dist_rules: tuple = ()


def _body_scale(points: dict[str, Point]) -> float:
    """Hip→ankle length when visible, else shoulder→hip: framing-independent."""
    for a, b in ((LEFT_HIP, LEFT_ANKLE), (RIGHT_HIP, RIGHT_ANKLE),
                 (LEFT_SHOULDER, LEFT_HIP), (RIGHT_SHOULDER, RIGHT_HIP)):
        if a in points and b in points:
            d = abs(points[a][1] - points[b][1])
            if d > 1e-6:
                return d
    return 1.0


def _best_side(points: dict[str, Point]) -> str:
    """For side-view poses: judge the side the camera actually sees."""
    def vis(side):
        js = [j for j in points if j.startswith(side)]
        return sum(points[j][2] for j in js) / len(js) if js else 0.0
    return "left" if vis("left_") >= vis("right_") else "right"


def _resolve(joint: str, side: str) -> str:
    """'~knee' means 'the visible side's knee'; explicit names pass through."""
    return f"{side}_{joint[1:]}" if joint.startswith("~") else joint


def _seg_tilt_deg(pa: Point, pb: Point, axis: str) -> float:
    dx, dy = pb[0] - pa[0], pb[1] - pa[1]
    ang = abs(math.degrees(math.atan2(dy, dx)))          # 0 = horizontal
    from_horizontal = min(ang, 180 - ang)
    return abs(90 - from_horizontal) if axis == "vertical" else from_horizontal


def evaluate_template(t: PoseTemplate, points: dict[str, Point]) -> StanceReading:
    side = _best_side(points)
    required = tuple(_resolve(j, side) for j in t.required)
    conf = _confidence(points, list(required))
    if conf < UNCERTAINTY_THRESHOLD:
        return _uncertain_reading(t.label, list(required), conf)

    scale = _body_scale(points)
    metrics: dict[str, float] = {}
    flags: list[str] = []
    messages: dict[str, str] = {}

    def P(j):
        return points[_resolve(j, side)]

    for r in t.angle_rules:
        deg = angle(P(r.joints[0]), P(r.joints[1]), P(r.joints[2]))
        metrics[r.metric] = round(deg, 2)
        if not (r.lo <= deg <= r.hi):
            flags.append(r.flag)
            messages[r.flag] = r.message
    for r in t.above_rules:
        gap = (P(r.b)[1] - P(r.a)[1]) / scale        # positive = a higher than b
        metrics[f"{r.flag}_gap"] = round(gap, 3)
        if gap < r.margin:
            flags.append(r.flag)
            messages[r.flag] = r.message
    for r in t.tilt_rules:
        tilt = _seg_tilt_deg(P(r.a), P(r.b), r.axis)
        metrics[f"{r.flag}_deg"] = round(tilt, 1)
        if tilt > r.tol_deg:
            flags.append(r.flag)
            messages[r.flag] = r.message
    for r in t.asym_rules:
        lk = angle(points[LEFT_HIP], points[LEFT_KNEE], points[LEFT_ANKLE])
        rk = angle(points[RIGHT_HIP], points[RIGHT_KNEE], points[RIGHT_ANKLE])
        deep, ext = min(lk, rk), max(lk, rk)
        metrics["deep_knee_angle"] = round(deep, 2)
        metrics["extended_knee_angle"] = round(ext, 2)
        if deep > r.deep_max or ext < r.ext_min:
            flags.append(r.flag)
            messages[r.flag] = r.message
    for r in t.dist_rules:
        pa, pb = P(r.a), P(r.b)
        dist = math.hypot(pa[0] - pb[0], pa[1] - pb[1]) / scale
        metrics[f"{r.flag}_dist"] = round(dist, 3)
        if dist > r.max_scale:
            flags.append(r.flag)
            messages[r.flag] = r.message

    assessment = f"{t.label}: held." if not flags else " | ".join(messages[f] for f in dict.fromkeys(flags))
    return StanceReading(t.label, metrics, list(dict.fromkeys(flags)), assessment, round(conf, 3), False)


# --- The catalog: every measurable static pose from the ten reference charts -------

_LEGS_FRONT = (LEFT_HIP, LEFT_KNEE, LEFT_ANKLE, RIGHT_HIP, RIGHT_KNEE, RIGHT_ANKLE)
_ARMS_FRONT = (LEFT_SHOULDER, LEFT_ELBOW, LEFT_WRIST, RIGHT_SHOULDER, RIGHT_ELBOW, RIGHT_WRIST)

POSE_TEMPLATES: tuple[PoseTemplate, ...] = (
    # -- Stance chart --------------------------------------------------------------
    PoseTemplate(
        "drop_stance", "Drop Stance (Pu Bu, shallow)", "front", _LEGS_FRONT,
        asym_rules=(AsymRule(120, 148, "not_split",
                             "One leg sinks deep, the other extends long - split the levels."),),
        tilt_rules=(TiltRule(LEFT_SHOULDER, LEFT_HIP, "vertical", 35,
                             "torso_collapsed", "Keep the trunk tall while you sink."),),
    ),
    PoseTemplate(
        "t_stance", "T Stance (arms level)", "front",
        _LEGS_FRONT + _ARMS_FRONT,
        angle_rules=(
            AngleRule("left_knee_angle", (LEFT_HIP, LEFT_KNEE, LEFT_ANKLE), 160, 180,
                      "legs_bent", "Stand the legs straight and together."),
            AngleRule("right_knee_angle", (RIGHT_HIP, RIGHT_KNEE, RIGHT_ANKLE), 160, 180,
                      "legs_bent", "Stand the legs straight and together."),
            AngleRule("left_elbow_angle", (LEFT_SHOULDER, LEFT_ELBOW, LEFT_WRIST), 145, 180,
                      "arms_bent", "Extend the arms long like a crossbeam."),
            AngleRule("right_elbow_angle", (RIGHT_SHOULDER, RIGHT_ELBOW, RIGHT_WRIST), 145, 180,
                      "arms_bent", "Extend the arms long like a crossbeam."),
        ),
        tilt_rules=(
            TiltRule(LEFT_WRIST, RIGHT_WRIST, "horizontal", 12,
                     "arms_not_level", "Bring both arms to shoulder height, level."),
        ),
    ),
    PoseTemplate(
        "parallel_ready", "Parallel Ready Stance", "front", _LEGS_FRONT + (LEFT_SHOULDER, RIGHT_SHOULDER),
        angle_rules=(
            AngleRule("left_knee_angle", (LEFT_HIP, LEFT_KNEE, LEFT_ANKLE), 140, 174,
                      "knees_wrong", "Soften the knees - ready, not locked, not squatting."),
            AngleRule("right_knee_angle", (RIGHT_HIP, RIGHT_KNEE, RIGHT_ANKLE), 140, 174,
                      "knees_wrong", "Soften the knees - ready, not locked, not squatting."),
        ),
        tilt_rules=(TiltRule(LEFT_SHOULDER, LEFT_HIP, "vertical", 15,
                             "leaning", "Stack the trunk upright over the hips."),),
    ),
    PoseTemplate(
        "meditation_stance", "Narrow Meditation Stance", "front", _LEGS_FRONT + (LEFT_SHOULDER, RIGHT_SHOULDER),
        angle_rules=(
            AngleRule("left_knee_angle", (LEFT_HIP, LEFT_KNEE, LEFT_ANKLE), 166, 180,
                      "knees_bent", "Stand quietly tall - legs long."),
            AngleRule("right_knee_angle", (RIGHT_HIP, RIGHT_KNEE, RIGHT_ANKLE), 166, 180,
                      "knees_bent", "Stand quietly tall - legs long."),
        ),
        tilt_rules=(TiltRule(LEFT_SHOULDER, LEFT_HIP, "vertical", 12,
                             "leaning", "Center the spine - no lean."),),
    ),
    PoseTemplate(
        "empty_stance", "Empty / Cat Stance (Xu Bu)", "side", ("~hip", "~knee", "~ankle", "~shoulder"),
        angle_rules=(AngleRule("loaded_knee_angle", ("~hip", "~knee", "~ankle"), 95, 150,
                               "not_sitting", "Sit into the rear leg - the front foot stays empty."),),
        tilt_rules=(TiltRule("~shoulder", "~hip", "vertical", 25,
                             "leaning", "Trunk tall while the rear leg carries you."),),
    ),
    PoseTemplate(
        "rest_stance", "Rest Stance", "front",
        _LEGS_FRONT + (LEFT_SHOULDER, RIGHT_SHOULDER, LEFT_WRIST, RIGHT_WRIST),
        angle_rules=(
            AngleRule("left_knee_angle", (LEFT_HIP, LEFT_KNEE, LEFT_ANKLE), 165, 180,
                      "knees_bent", "Stand easy and tall — legs long."),
            AngleRule("right_knee_angle", (RIGHT_HIP, RIGHT_KNEE, RIGHT_ANKLE), 165, 180,
                      "knees_bent", "Stand easy and tall — legs long."),
        ),
        above_rules=(
            AboveRule(LEFT_HIP, LEFT_WRIST, 0.0, "hands_raised", "Let the arms hang at rest."),
            AboveRule(RIGHT_HIP, RIGHT_WRIST, 0.0, "hands_raised", "Let the arms hang at rest."),
        ),
        dist_rules=(
            DistRule(LEFT_ANKLE, RIGHT_ANKLE, 0.28, "feet_apart",
                     "Bring the feet together — rest stance is narrow."),
        ),
        tilt_rules=(TiltRule(LEFT_SHOULDER, LEFT_HIP, "vertical", 14,
                             "leaning", "Stand quietly upright."),),
    ),
    # -- Conditioning + floor charts (side view) ---------------------------------------
    PoseTemplate(
        "plank", "Plank / Pushup Top", "side", ("~shoulder", "~hip", "~ankle"),
        angle_rules=(AngleRule("body_line_angle", ("~shoulder", "~hip", "~ankle"), 155, 180,
                               "hips_broken", "One straight line - no sagging, no piking."),),
        tilt_rules=(TiltRule("~shoulder", "~ankle", "horizontal", 28,
                             "not_horizontal", "Lower the body into the plank line."),),
    ),
    PoseTemplate(
        "wall_sit", "Wall Sit", "side", ("~shoulder", "~hip", "~knee", "~ankle"),
        angle_rules=(AngleRule("knee_angle", ("~hip", "~knee", "~ankle"), 70, 115,
                               "too_high", "Slide down - thighs toward parallel."),),
        tilt_rules=(TiltRule("~shoulder", "~hip", "vertical", 20,
                             "torso_tilt", "Back flat against the wall, trunk vertical."),),
    ),
    PoseTemplate(
        "squat_hold", "Squat Hold", "side", ("~hip", "~knee", "~ankle"),
        angle_rules=(AngleRule("knee_angle", ("~hip", "~knee", "~ankle"), 60, 118,
                               "too_high", "Sink deeper - break parallel if the knees allow."),),
    ),
    PoseTemplate(
        "half_squat", "Half Squat Hold", "side", ("~hip", "~knee", "~ankle", "~shoulder"),
        angle_rules=(AngleRule("knee_angle", ("~hip", "~knee", "~ankle"), 105, 148,
                               "depth_wrong", "Half squat — knees soft, not a full sink."),),
        tilt_rules=(TiltRule("~shoulder", "~hip", "vertical", 22,
                             "leaning", "Keep the trunk upright over the hips."),),
    ),
    PoseTemplate(
        "deep_squat_hold", "Deep Squat Hold", "side", ("~hip", "~knee", "~ankle"),
        angle_rules=(AngleRule("knee_angle", ("~hip", "~knee", "~ankle"), 40, 95,
                               "too_high", "Sink into the deep squat — hips low."),),
    ),
    PoseTemplate(
        "cossack_hold", "Cossack Squat Hold (shallow)", "front", _LEGS_FRONT,
        asym_rules=(AsymRule(115, 145, "not_split",
                             "One leg sits, the other extends long to the side."),),
        tilt_rules=(TiltRule(LEFT_SHOULDER, LEFT_HIP, "vertical", 40,
                             "torso_collapsed", "Keep the chest open while you sit sideways."),),
    ),
    PoseTemplate(
        "side_plank", "Side Plank", "side", ("~shoulder", "~hip", "~ankle"),
        angle_rules=(AngleRule("body_line_angle", ("~shoulder", "~hip", "~ankle"), 150, 180,
                               "hips_broken", "One long side line — no sagging."),),
        tilt_rules=(TiltRule("~shoulder", "~ankle", "horizontal", 32,
                             "not_horizontal", "Stack the body into the side plank line."),),
    ),
    PoseTemplate(
        "hollow_hold", "Hollow Body Hold", "side", ("~shoulder", "~hip", "~ankle"),
        angle_rules=(AngleRule("fold_angle", ("~shoulder", "~hip", "~ankle"), 95, 158,
                               "fold_lost", "Fold at the center - shoulders and legs off the floor."),),
        above_rules=(AboveRule("~ankle", "~hip", 0.02, "legs_down",
                               "Lift the legs - heels above hip line."),),
    ),
    PoseTemplate(
        "glute_bridge", "Glute Bridge Hold", "side", ("~shoulder", "~hip", "~knee", "~ankle"),
        angle_rules=(
            AngleRule("hip_line_angle", ("~shoulder", "~hip", "~knee"), 150, 180,
                      "hips_low", "Drive the hips up - straight line shoulder to knee."),
            AngleRule("knee_angle", ("~hip", "~knee", "~ankle"), 55, 110,
                      "feet_far", "Walk the heels closer under the knees."),
        ),
        above_rules=(AboveRule("~hip", "~shoulder", 0.03, "hips_sagging",
                               "Hips higher than the chest line."),),
    ),
    PoseTemplate(
        "leg_raise_hold", "Leg Raise Hold", "side", ("~shoulder", "~hip", "~knee", "~ankle"),
        angle_rules=(AngleRule("knee_angle", ("~hip", "~knee", "~ankle"), 145, 180,
                               "knees_bent", "Long legs - bend only what the back demands."),),
        above_rules=(AboveRule("~ankle", "~hip", 0.25, "legs_low",
                               "Raise the legs - ankles well above the hip line."),),
    ),
    PoseTemplate(
        "superman_hold", "Superman Hold", "side", ("~shoulder", "~hip", "~ankle", "~wrist"),
        above_rules=(
            AboveRule("~wrist", "~hip", 0.02, "arms_down", "Lift the arms — chest and hands off the floor."),
            AboveRule("~ankle", "~hip", 0.02, "legs_down", "Lift the legs — heels off the floor."),
        ),
        tilt_rules=(TiltRule("~shoulder", "~hip", "horizontal", 35,
                             "not_prone", "Lie prone and extend long."),),
    ),
    # -- Qi Gong + breath charts ---------------------------------------------------------
    PoseTemplate(
        "arms_raised", "Arms Raised (Holding Up the Heavens)", "front",
        _ARMS_FRONT + (LEFT_HIP, RIGHT_HIP, LEFT_KNEE, RIGHT_KNEE, LEFT_ANKLE, RIGHT_ANKLE),
        angle_rules=(
            AngleRule("left_elbow_angle", (LEFT_SHOULDER, LEFT_ELBOW, LEFT_WRIST), 130, 180,
                      "arms_bent", "Press the sky - arms long."),
            AngleRule("right_elbow_angle", (RIGHT_SHOULDER, RIGHT_ELBOW, RIGHT_WRIST), 130, 180,
                      "arms_bent", "Press the sky - arms long."),
            AngleRule("left_knee_angle", (LEFT_HIP, LEFT_KNEE, LEFT_ANKLE), 155, 180,
                      "legs_bent", "Root the legs while the arms rise."),
            AngleRule("right_knee_angle", (RIGHT_HIP, RIGHT_KNEE, RIGHT_ANKLE), 155, 180,
                      "legs_bent", "Root the legs while the arms rise."),
        ),
        above_rules=(
            AboveRule(LEFT_WRIST, LEFT_SHOULDER, 0.18, "arms_low", "Hands above the head, palms to heaven."),
            AboveRule(RIGHT_WRIST, RIGHT_SHOULDER, 0.18, "arms_low", "Hands above the head, palms to heaven."),
        ),
    ),
    PoseTemplate(
        "wuji_standing", "Wuji Standing", "front",
        _LEGS_FRONT + (LEFT_SHOULDER, RIGHT_SHOULDER, LEFT_WRIST, RIGHT_WRIST),
        angle_rules=(
            AngleRule("left_knee_angle", (LEFT_HIP, LEFT_KNEE, LEFT_ANKLE), 162, 180,
                      "knees_bent", "Stand empty and tall."),
            AngleRule("right_knee_angle", (RIGHT_HIP, RIGHT_KNEE, RIGHT_ANKLE), 162, 180,
                      "knees_bent", "Stand empty and tall."),
        ),
        above_rules=(
            AboveRule(LEFT_HIP, LEFT_WRIST, 0.0, "hands_raised", "Let the arms hang - nothing to hold."),
            AboveRule(RIGHT_HIP, RIGHT_WRIST, 0.0, "hands_raised", "Let the arms hang - nothing to hold."),
        ),
        tilt_rules=(TiltRule(LEFT_SHOULDER, LEFT_HIP, "vertical", 12,
                             "leaning", "Suspended from the crown - no lean."),),
    ),
    PoseTemplate(
        "horse_guard", "Horse Stance, Guard Up", "front",
        _LEGS_FRONT + (LEFT_SHOULDER, RIGHT_SHOULDER, LEFT_WRIST, RIGHT_WRIST),
        angle_rules=(
            AngleRule("left_knee_angle", (LEFT_HIP, LEFT_KNEE, LEFT_ANKLE), 80, 120,
                      "stance_broken", "Sink the horse - knees toward ninety."),
            AngleRule("right_knee_angle", (RIGHT_HIP, RIGHT_KNEE, RIGHT_ANKLE), 80, 120,
                      "stance_broken", "Sink the horse - knees toward ninety."),
        ),
        above_rules=(
            AboveRule(LEFT_WRIST, LEFT_HIP, 0.15, "guard_down", "Bring the guard up - fists at chest height."),
            AboveRule(RIGHT_WRIST, RIGHT_HIP, 0.15, "guard_down", "Bring the guard up - fists at chest height."),
        ),
    ),
    PoseTemplate(
        "seated_meditation", "Seated Meditation", "front",
        (LEFT_SHOULDER, RIGHT_SHOULDER, LEFT_HIP, RIGHT_HIP, LEFT_KNEE, RIGHT_KNEE),
        tilt_rules=(
            TiltRule(LEFT_SHOULDER, LEFT_HIP, "vertical", 16,
                     "slumping", "Sit tall - the spine is the mountain."),
            TiltRule(LEFT_SHOULDER, RIGHT_SHOULDER, "horizontal", 12,
                     "tilted", "Level the shoulders."),
        ),
        above_rules=(AboveRule(LEFT_HIP, LEFT_KNEE, -0.6, "standing",
                               "Settle down onto the seat."),),
    ),
    PoseTemplate(
        "standing_tree", "Standing Tree (foot to knee)", "front",
        _LEGS_FRONT + (LEFT_SHOULDER, RIGHT_SHOULDER),
        # Softer than crane: clear one-leg lift without hip-height demand.
        asym_rules=(AsymRule(115, 155, "no_lift",
                             "Stand on one leg — lift the other foot toward the inner knee."),),
        tilt_rules=(TiltRule(LEFT_SHOULDER, LEFT_HIP, "vertical", 18,
                             "leaning", "Grow tall from the standing leg."),),
    ),
)


def template_specificity(key: str) -> int:
    """How constrained a hold is — used so detect prefers the more specific name."""
    if key == "horse":
        return 3
    if key == "bow":
        return 3
    if key == "crane":
        return 4
    if key == "one_leg_stand":
        return 3
    for t in POSE_TEMPLATES:
        if t.key == key:
            return (
                len(t.angle_rules) + len(t.above_rules)
                + len(t.tilt_rules) + len(t.asym_rules) + len(t.dist_rules)
            )
    return 1

# one_leg_stand needs direction-agnostic logic; replace the placeholder with a closure.


def evaluate_one_leg_stand(points: dict[str, Point]) -> StanceReading:
    """One-leg stand: like the crane but without demanding hip-height knee lift."""
    r = evaluate_crane_stance(points)
    if r.uncertain or "no_lift" in r.flags:
        return r
    flags = [f for f in r.flags if f != "knee_below_hip"]
    assessment = "One-leg stand: held." if not flags else r.assessment
    return StanceReading("One-Leg Stand", r.metrics, flags, assessment, r.confidence, False)


def _register_catalog() -> dict:
    stances = {
        "horse": evaluate_horse_stance,
        "ma_bu": evaluate_horse_stance,
        "bow": evaluate_bow_stance,
        "gong_bu": evaluate_bow_stance,
        "crane": evaluate_crane_stance,
        "du_li_bu": evaluate_crane_stance,
        "one_leg_stand": evaluate_one_leg_stand,
    }
    for t in POSE_TEMPLATES:
        if t.key == "one_leg_stand":
            continue
        stances[t.key] = (lambda tmpl: lambda pts: evaluate_template(tmpl, pts))(t)
    return stances


STANCES = _register_catalog()

# Display names + camera guidance for every trainable hold (UI + trainer).
HOLD_CATALOG: dict[str, dict] = {
    "horse": {"label": "Horse Stance (Ma Bu)", "view": "front"},
    "bow": {"label": "Bow Stance (Gong Bu)", "view": "front"},
    "crane": {"label": "Crane Stance (Du Li Bu)", "view": "front"},
    "one_leg_stand": {"label": "One-Leg Stand", "view": "front"},
    **{t.key: {"label": t.label, "view": t.view} for t in POSE_TEMPLATES if t.key != "one_leg_stand"},
}


# --- General motion measurement (flowing sequences, e.g. Eight Brocades) --------

_ANGLE_TRIPLETS = {
    "left_knee": (LEFT_HIP, LEFT_KNEE, LEFT_ANKLE),
    "right_knee": (RIGHT_HIP, RIGHT_KNEE, RIGHT_ANKLE),
    "left_elbow": (LEFT_SHOULDER, LEFT_ELBOW, LEFT_WRIST),
    "right_elbow": (RIGHT_SHOULDER, RIGHT_ELBOW, RIGHT_WRIST),
    "left_shoulder": (LEFT_HIP, LEFT_SHOULDER, LEFT_ELBOW),
    "right_shoulder": (RIGHT_HIP, RIGHT_SHOULDER, RIGHT_ELBOW),
}


def general_joint_angles(points: dict[str, Point], min_visibility: float = 0.5) -> dict[str, float]:
    """Raw joint angles for a flowing sequence. This is **measurement, not a
    verdict** — no pass/fail, no claim of correct form. It documents range of
    motion so a timeline can be built; the eye and the teacher judge the form."""
    out: dict[str, float] = {}
    for name, (a, b, c) in _ANGLE_TRIPLETS.items():
        if a in points and b in points and c in points:
            if min(points[a][2], points[b][2], points[c][2]) >= min_visibility:
                out[name] = round(angle(points[a], points[b], points[c]), 2)
    return out
