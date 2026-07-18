// Chirox mode deck: training mirror, learning desk, and voice-driven controls.
// No terminal in the practitioner's path; the browser is the working surface.

const ROLES = ["front"];

const $ = (id) => document.getElementById(id);

const views = {};
for (const role of ROLES) {
  views[role] = {
    canvas: $(`${role}Canvas`),
    conf: $(`${role}Conf`),
    msg: $(`${role}Msg`),
    assess: $(`${role}Assess`),
    socket: null,
    image: new Image(),
    frameCount: 0,
    uncertain: 0,
    lastState: "idle",
  };
}

const state = {
  running: false,
  pair: ["front"],
  stance: "auto",
  sources: { front: 0 },
  opacity: 0.9,
  startedAt: null,
  timer: null,
  guides: { drills: new Map(), references: [] },
  mode: "training",
  recordDay: null,
  gotFirstFrame: false,
  camLoadTimer: null,
  holdStartedAt: null,
  formSeconds: 0,
  lastFrameAt: null,
  selectedRecordKey: null,
  playback: null,
  routineActive: false,
};

const bones = [
  // torso
  ["left_shoulder", "right_shoulder"],
  ["left_hip", "right_hip"],
  ["left_shoulder", "left_hip"],
  ["right_shoulder", "right_hip"],
  // arms
  ["left_shoulder", "left_elbow"],
  ["left_elbow", "left_wrist"],
  ["right_shoulder", "right_elbow"],
  ["right_elbow", "right_wrist"],
  // hands (wrist out to the thumb / index / pinky knuckles)
  ["left_wrist", "left_thumb"],
  ["left_wrist", "left_index"],
  ["left_wrist", "left_pinky"],
  ["left_index", "left_pinky"],
  ["right_wrist", "right_thumb"],
  ["right_wrist", "right_index"],
  ["right_wrist", "right_pinky"],
  ["right_index", "right_pinky"],
  // legs
  ["left_hip", "left_knee"],
  ["left_knee", "left_ankle"],
  ["right_hip", "right_knee"],
  ["right_knee", "right_ankle"],
  // feet (ankle -> heel -> toe, a closed little foot)
  ["left_ankle", "left_heel"],
  ["left_heel", "left_foot_index"],
  ["left_ankle", "left_foot_index"],
  ["right_ankle", "right_heel"],
  ["right_heel", "right_foot_index"],
  ["right_ankle", "right_foot_index"],
];

async function post(url, body) {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : "{}",
  });
  return res.json();
}

// --- skeleton rendering (unchanged truth: visibility-weighted, amber when uncertain)

// Head landmarks (nose + ears) drive the head circle and neck, not scattered
// dots — the wireguy gets a head that follows the practitioner, not a face full
// of markers.
const HEAD_POINTS = new Set(["nose", "left_ear", "right_ear"]);

function pointOf(landmarks, name) {
  return landmarks.find((lm) => lm.name === name);
}

function toCanvasPoint(canvas, lm) {
  const mirrored = $("mirrorToggle").checked;
  const x = mirrored ? (1 - lm.x) * canvas.width : lm.x * canvas.width;
  return { x, y: lm.y * canvas.height, visibility: lm.visibility };
}

// Neck (shoulder midpoint -> head) and a floating head circle. Head centre is
// the midpoint of the ears when visible (the middle of the skull); radius comes
// from the ear span, falling back to shoulder width when the head is turned so
// the head never vanishes. Returns nothing when there is no head to draw.
function drawHeadAndNeck(ctx, canvas, landmarks, stroke) {
  const nose = pointOf(landmarks, "nose");
  const ls = pointOf(landmarks, "left_shoulder");
  const rs = pointOf(landmarks, "right_shoulder");
  const le = pointOf(landmarks, "left_ear");
  const re = pointOf(landmarks, "right_ear");
  if (!nose && !(le && re)) return;

  let head;
  if (le && re) {
    const pl = toCanvasPoint(canvas, le);
    const pr = toCanvasPoint(canvas, re);
    head = { x: (pl.x + pr.x) / 2, y: (pl.y + pr.y) / 2, visibility: Math.min(pl.visibility, pr.visibility) };
  } else {
    head = toCanvasPoint(canvas, nose);
  }

  let radius = canvas.width / 22;
  if (le && re) {
    const pl = toCanvasPoint(canvas, le);
    const pr = toCanvasPoint(canvas, re);
    radius = Math.max(radius, Math.hypot(pl.x - pr.x, pl.y - pr.y) * 0.7);
  }

  let neckBase = null;
  if (ls && rs) {
    const pl = toCanvasPoint(canvas, ls);
    const pr = toCanvasPoint(canvas, rs);
    neckBase = {
      x: (pl.x + pr.x) / 2,
      y: (pl.y + pr.y) / 2,
      visibility: Math.min(pl.visibility, pr.visibility),
    };
  }

  // Neck: from the shoulders up to the bottom of the head circle (trimmed so the
  // line meets the head cleanly instead of stabbing through it).
  if (neckBase) {
    const dx = head.x - neckBase.x;
    const dy = head.y - neckBase.y;
    const dist = Math.hypot(dx, dy) || 1;
    const top = { x: head.x - (dx / dist) * radius, y: head.y - (dy / dist) * radius };
    const alpha = Math.max(0.12, Math.min(neckBase.visibility, head.visibility) * state.opacity);
    ctx.strokeStyle = `rgba(${stroke}, ${alpha})`;
    ctx.beginPath();
    ctx.moveTo(neckBase.x, neckBase.y);
    ctx.lineTo(top.x, top.y);
    ctx.stroke();
  }

  // Head: an open circle that rides the practitioner's head.
  const headAlpha = Math.max(0.18, head.visibility * state.opacity);
  ctx.strokeStyle = `rgba(${stroke}, ${headAlpha})`;
  ctx.beginPath();
  ctx.arc(head.x, head.y, radius, 0, Math.PI * 2);
  ctx.stroke();
}

// Head orientation from the face landmarks. Overlay-only; never touches stance
// geometry. Worked in canvas space (mirror flip already applied).
//   yaw   — nose left/right of the ear midpoint (side to side)
//   pitch — nose above/below a neutral rest on the ear line (up / down)
// Both are scaled by ear span so distance to camera does not invent degrees.
function headOrientation(canvas, landmarks) {
  const nose = pointOf(landmarks, "nose");
  const le = pointOf(landmarks, "left_ear");
  const re = pointOf(landmarks, "right_ear");
  if (!nose || !le || !re) return null;
  const pn = toCanvasPoint(canvas, nose);
  const pl = toCanvasPoint(canvas, le);
  const pr = toCanvasPoint(canvas, re);
  const earMid = { x: (pl.x + pr.x) / 2, y: (pl.y + pr.y) / 2 };
  const earSpan = Math.hypot(pr.x - pl.x, pr.y - pl.y) || 1;
  const half = earSpan / 2;
  const yaw = Math.max(-90, Math.min(90, ((pn.x - earMid.x) / half) * 50));
  // Image y grows downward. A face looking forward has the nose a little below
  // the ear line; subtract that bias so level reads near 0°, up is negative,
  // down is positive.
  const NEUTRAL_PITCH = 0.45;
  const pitch = Math.max(-90, Math.min(90, (((pn.y - earMid.y) / half) - NEUTRAL_PITCH) * 55));
  const conf = Math.min(nose.visibility, le.visibility, re.visibility);
  return { yaw, pitch, conf, earMid, earSpan };
}

function _drawHeadArrow(ctx, x0, y0, x1, y1, tint, alpha, lineW) {
  const dx = x1 - x0;
  const dy = y1 - y0;
  const len = Math.hypot(dx, dy) || 1;
  const ux = dx / len;
  const uy = dy / len;
  const ah = Math.max(5, lineW * 3);
  ctx.strokeStyle = `rgba(${tint}, ${alpha})`;
  ctx.lineWidth = lineW;
  ctx.beginPath();
  ctx.moveTo(x0, y0);
  ctx.lineTo(x1, y1);
  ctx.stroke();
  ctx.beginPath();
  ctx.moveTo(x1, y1);
  ctx.lineTo(x1 - ux * ah + uy * ah * 0.55, y1 - uy * ah - ux * ah * 0.55);
  ctx.moveTo(x1, y1);
  ctx.lineTo(x1 - ux * ah - uy * ah * 0.55, y1 - uy * ah + ux * ah * 0.55);
  ctx.stroke();
}

// Draw head-orientation feedback: arrows for yaw (L/R) and pitch (up/down),
// plus a degree readout so the practitioner sees both axes.
function drawHeadOrientation(ctx, canvas, landmarks) {
  const o = headOrientation(canvas, landmarks);
  if (!o || o.conf < 0.3) return;
  const tint = "130, 200, 255";
  const alpha = Math.max(0.4, o.conf * state.opacity);
  const yawDeg = Math.round(Math.abs(o.yaw));
  const pitchDeg = Math.round(Math.abs(o.pitch));
  const yawed = yawDeg > 6;
  const pitched = pitchDeg > 6;
  const lineW = Math.max(2, canvas.width / 300);
  const x0 = o.earMid.x;
  const y0 = o.earMid.y;

  if (yawed) {
    const dir = o.yaw > 0 ? 1 : -1;
    const arrow = o.earSpan * 0.4 + (Math.min(yawDeg, 90) / 90) * o.earSpan * 1.6;
    _drawHeadArrow(ctx, x0, y0, x0 + dir * arrow, y0, tint, alpha, lineW);
  }
  if (pitched) {
    // Canvas y grows down: positive pitch (looking down) → arrow down.
    const dir = o.pitch > 0 ? 1 : -1;
    const arrow = o.earSpan * 0.35 + (Math.min(pitchDeg, 90) / 90) * o.earSpan * 1.4;
    _drawHeadArrow(ctx, x0, y0, x0, y0 + dir * arrow, tint, alpha, lineW);
  }

  let label = "head • level";
  if (yawed || pitched) {
    const parts = [];
    if (yawed) parts.push(`${yawDeg}° ${o.yaw > 0 ? "right" : "left"}`);
    if (pitched) parts.push(`${pitchDeg}° ${o.pitch > 0 ? "down" : "up"}`);
    label = `head ${parts.join(" · ")}`;
  }
  const fontPx = Math.max(12, Math.round(canvas.width / 42));
  ctx.font = `600 ${fontPx}px system-ui, -apple-system, sans-serif`;
  ctx.textAlign = "center";
  ctx.textBaseline = "bottom";
  // Sit above the head, but never let a high/close head push the readout off-frame.
  const ty = Math.max(fontPx + 4, o.earMid.y - o.earSpan * 1.2 - fontPx * 0.3);
  ctx.lineWidth = Math.max(3, fontPx / 5);
  ctx.strokeStyle = "rgba(6, 12, 20, 0.85)";
  ctx.strokeText(label, o.earMid.x, ty);
  ctx.fillStyle = `rgba(${tint}, ${Math.max(0.75, alpha)})`;
  ctx.fillText(label, o.earMid.x, ty);
  ctx.textAlign = "start";
  ctx.textBaseline = "alphabetic";
}

function drawSkeleton(view, landmarks, reading) {
  if (!landmarks.length) return;
  const canvas = view.canvas;
  const ctx = canvas.getContext("2d");
  const stroke = reading && reading.uncertain ? "242, 184, 75" : "66, 211, 146";
  ctx.lineWidth = Math.max(3, canvas.width / 260);
  ctx.lineCap = "round";
  for (const [aName, bName] of bones) {
    const a = pointOf(landmarks, aName);
    const b = pointOf(landmarks, bName);
    if (!a || !b) continue;
    const pa = toCanvasPoint(canvas, a);
    const pb = toCanvasPoint(canvas, b);
    ctx.strokeStyle = `rgba(${stroke}, ${Math.max(0.12, Math.min(pa.visibility, pb.visibility) * state.opacity)})`;
    ctx.beginPath();
    ctx.moveTo(pa.x, pa.y);
    ctx.lineTo(pb.x, pb.y);
    ctx.stroke();
  }
  drawHeadAndNeck(ctx, canvas, landmarks, stroke);
  drawHeadOrientation(ctx, canvas, landmarks);
  for (const lm of landmarks) {
    if (HEAD_POINTS.has(lm.name)) continue; // the head is a circle, not three face dots
    const p = toCanvasPoint(canvas, lm);
    ctx.fillStyle = `rgba(${stroke}, ${Math.max(0.18, p.visibility * state.opacity)})`;
    ctx.beginPath();
    ctx.arc(p.x, p.y, Math.max(4, canvas.width / 180), 0, Math.PI * 2);
    ctx.fill();
  }
}

// Frame messages are binary: 4-byte big-endian header length, JSON header, raw JPEG.
function unpackFrame(buffer) {
  const headerLength = new DataView(buffer).getUint32(0);
  const header = JSON.parse(new TextDecoder().decode(new Uint8Array(buffer, 4, headerLength)));
  const jpeg = new Uint8Array(buffer, 4 + headerLength);
  return { header, jpeg };
}

function drawFrame(view, payload, jpeg) {
  const url = URL.createObjectURL(new Blob([jpeg], { type: "image/jpeg" }));
  view.image.onload = () => {
    URL.revokeObjectURL(url);
    const canvas = view.canvas;
    const ctx = canvas.getContext("2d");
    if (canvas.width !== view.image.naturalWidth || canvas.height !== view.image.naturalHeight) {
      canvas.width = view.image.naturalWidth;
      canvas.height = view.image.naturalHeight;
    }
    ctx.save();
    if ($("mirrorToggle").checked) {
      ctx.translate(canvas.width, 0);
      ctx.scale(-1, 1);
    }
    ctx.drawImage(view.image, 0, 0, canvas.width, canvas.height);
    ctx.restore();
    drawSkeleton(view, payload.landmarks || [], payload.reading);
  };
  view.image.src = url;
}

function formatAngleName(name) {
  return String(name || "").replace(/_/g, " ");
}

function updateMetricsHud(reading, truthKind) {
  const angles = $("hudAngles");
  const form = $("hudForm");
  const timer = $("hudTimer");
  if (!angles || !form || !timer) return;

  const now = Date.now();
  if (!state.holdStartedAt) state.holdStartedAt = now;
  const elapsed = Math.max(0, Math.floor((now - state.holdStartedAt) / 1000));
  timer.textContent = `${elapsed}s hold`;

  if (!reading || truthKind === "no-body") {
    form.textContent = "no body";
    angles.innerHTML = "";
    state.lastFrameAt = now;
    return;
  }

  const dt = state.lastFrameAt ? Math.min(0.25, (now - state.lastFrameAt) / 1000) : 0;
  state.lastFrameAt = now;
  if (truthKind === "measured" && !(reading.flags || []).length) {
    state.formSeconds += dt;
  }
  form.textContent = truthKind === "uncertain"
    ? "uncertain"
    : `${Math.floor(state.formSeconds)}s in form`;

  const metrics = reading.metrics || {};
  const keys = Object.keys(metrics)
    .filter((k) => typeof metrics[k] === "number" && /angle|deg|knee|hip|spine|back|elbow|shoulder/i.test(k))
    .slice(0, 4);
  const fallback = Object.keys(metrics)
    .filter((k) => typeof metrics[k] === "number")
    .slice(0, 4);
  const show = keys.length ? keys : fallback;
  angles.innerHTML = "";
  for (const key of show) {
    const span = document.createElement("span");
    const val = metrics[key];
    span.textContent = `${formatAngleName(key)} ${Number(val).toFixed(0)}°`;
    angles.append(span);
  }
}

function resetHoldMetrics() {
  state.holdStartedAt = Date.now();
  state.formSeconds = 0;
  state.lastFrameAt = null;
  if ($("hudTimer")) $("hudTimer").textContent = "0s hold";
  if ($("hudForm")) $("hudForm").textContent = "—";
  if ($("hudAngles")) $("hudAngles").innerHTML = "";
}

function updateView(role, payload) {
  const view = views[role];
  view.frameCount = payload.frame_index || view.frameCount + 1;
  if (!payload.reading) {
    view.lastState = "no_body";
    view.conf.textContent = "no body";
    view.msg.textContent = "No body detected. Step fully into frame.";
    view.assess.textContent = "";
    updateMetricsHud(null, "no-body");
    return;
  }
  const reading = payload.reading;
  view.conf.textContent = `conf ${Number(reading.confidence || 0).toFixed(2)}`;
  view.assess.textContent = reading.assessment || "";
  if (reading.uncertain || payload.state === "uncertain") {
    view.lastState = "uncertain";
    view.uncertain += 1;
    view.msg.textContent = "Uncertain - reframe before trusting numbers.";
    updateMetricsHud(reading, "uncertain");
  } else {
    view.lastState = "measured";
    view.msg.textContent = "";
    updateMetricsHud(reading, "measured");
  }
}

function setTruth(kind, text) {
  const el = $("truthState");
  el.className = `truth ${kind}`;
  el.textContent = text;
}

function updateGlobalTruth() {
  const live = state.pair.filter((r) => views[r].socket);
  const totalUncertain = ROLES.reduce((n, r) => n + views[r].uncertain, 0);
  $("flags").textContent = totalUncertain ? `uncertain frames: ${totalUncertain}` : "";
  if (!state.running || !live.length) {
    setTruth("no-body", "Idle");
    return;
  }
  const states = live.map((r) => views[r].lastState);
  if (states.includes("no_body")) setTruth("no-body", "No body");
  else if (states.includes("uncertain")) setTruth("uncertain", "Uncertain");
  else if (states.includes("measured")) setTruth("measured", "Measured");
  else setTruth("no-body", "Connecting");
}

function updateRoutineHud(payload) {
  const phaseEl = $("hudPhase");
  const repsEl = $("hudReps");
  const nextBtn = $("routineNextBtn");
  const stopBtn = $("routineStopBtn");
  const routine = payload && payload.routine;
  if (routine && routine.phase_label) {
    const idx = (routine.phase_index || 0) + 1;
    const total = routine.phase_count || "?";
    phaseEl.textContent = `${routine.label || "Routine"} · ${idx}/${total}: ${routine.phase_label}`;
    if (routine.target_reps != null) {
      repsEl.textContent = `reps ${routine.reps || 0}/${routine.target_reps}`;
    } else {
      repsEl.textContent = `hold ${routine.hold_s || 0}s`;
    }
    if (nextBtn) nextBtn.hidden = false;
    if (stopBtn) stopBtn.hidden = false;
    state.routineActive = true;
  } else {
    const tag = payload && payload.free_tag;
    const auto = state.stance === "auto" || (payload && payload.auto);
    if (tag && tag.label) {
      const chartBit = tag.chart ? ` · chart ${tag.chart}` : "";
      phaseEl.textContent = tag.form_clean
        ? (auto ? `Detected · ${tag.label}${chartBit}` : `Free train · ${tag.label}`)
        : (auto ? `Detected · ${tag.label}${chartBit} (flags)` : `Free train · ${tag.label} (flags)`);
      if (auto) {
        $("guideName").textContent = tag.label;
        $("trackedStance").textContent = tag.chart_title
          ? `auto · ${tag.chart_title}`
          : "auto-detected";
      }
    } else if (!state.routineActive) {
      if (auto) {
        phaseEl.textContent = "Detecting — hold a known shape, or pick one.";
        $("guideName").textContent = "Detecting…";
        $("trackedStance").textContent = "watching for a known hold";
      } else {
        phaseEl.textContent = "No routine — free train or begin Eight Brocades.";
      }
    }
    if (!routine) {
      if (nextBtn) nextBtn.hidden = true;
      if (stopBtn) stopBtn.hidden = true;
      state.routineActive = false;
      if (repsEl) repsEl.textContent = "reps —";
    }
  }
}

function renderPayload(role, payload, jpeg) {
  noteFirstFrame();  // a real frame is painting: the camera is up
  drawFrame(views[role], payload, jpeg);
  updateView(role, payload);
  updateRoutineHud(payload);
  updateGlobalTruth();
}

// --- live sessions ---------------------------------------------------------------

function openSocket(role) {
  const protocol = window.location.protocol === "https:" ? "wss" : "ws";
  const view = views[role];
  view.socket = new WebSocket(`${protocol}://${window.location.host}/ws/live/${role}`);
  view.socket.binaryType = "arraybuffer";
  view.socket.onmessage = (event) => {
    if (typeof event.data === "string") {
      const payload = JSON.parse(event.data);
      if (payload.type === "error") {
        view.msg.textContent = payload.message;
        showCamLoading(payload.message);  // the camera failed to open — say why
      }
      return;
    }
    const { header, jpeg } = unpackFrame(event.data);
    renderPayload(role, header, jpeg);
  };
  view.socket.onclose = () => {
    view.lastState = "idle";
  };
}

function closeSocket(role) {
  const view = views[role];
  if (view.socket) {
    view.socket.close();
    view.socket = null;
  }
}

function resetView(role) {
  const view = views[role];
  view.frameCount = 0;
  view.uncertain = 0;
  view.lastState = "idle";
  view.conf.textContent = "--";
  view.assess.textContent = "";
  view.msg.textContent = "Ready.";
}

function startTimer() {
  state.startedAt = Date.now();
  clearInterval(state.timer);
  state.timer = setInterval(() => {
    $("runtime").textContent = `${((Date.now() - state.startedAt) / 1000).toFixed(0)}s`;
  }, 500);
}

// --- camera-loading notification -------------------------------------------------
// Opening the webcam on Windows can take a few seconds; the mirror says so
// instead of showing a blank stage, and clears itself the moment a frame lands.

function showCamLoading(text) {
  const box = $("camLoading");
  if (!box) return;
  $("camLoadingText").textContent = text || "Waking the camera…";
  box.hidden = false;
}

function hideCamLoading() {
  const box = $("camLoading");
  if (box) box.hidden = true;
  clearTimeout(state.camLoadTimer);
}

function noteFirstFrame() {
  if (state.gotFirstFrame) return;
  state.gotFirstFrame = true;
  hideCamLoading();
}

async function mirrorOn() {
  ROLES.forEach(resetView);
  state.gotFirstFrame = false;
  showCamLoading("Waking the camera…");
  try {
    await post("/api/session/start", { source: state.sources.front, stance: state.stance, role: "front" });
  } catch (err) {
    showCamLoading("Could not reach the camera. Is another app using it?");
    return;
  }
  openSocket("front");
  state.running = true;
  resetHoldMetrics();
  startTimer();
  updateGlobalTruth();
  // If no frame has painted after a while, keep the notice honest rather than
  // spinning forever.
  clearTimeout(state.camLoadTimer);
  state.camLoadTimer = setTimeout(() => {
    if (state.running && !state.gotFirstFrame) {
      showCamLoading("Camera is taking longer than usual to open…");
    }
  }, 8000);
}

async function mirrorOff() {
  ROLES.forEach(closeSocket);
  await post("/api/session/stop").catch(() => {});
  state.running = false;
  state.gotFirstFrame = false;
  hideCamLoading();
  clearInterval(state.timer);
  ROLES.forEach(resetView);
  resetHoldMetrics();
  setTruth("no-body", "Idle");
}

// --- exercise guide + the Training Hall ---------------------------------------------

function selectGuideImage(image) {
  const img = $("guideImage");
  if (!img || !image) return;
  img.src = image.url;
  img.alt = image.title || "Exercise reference";
  img.dataset.chartIndex = image.index;
}

const HALL_GROUPS = [
  { kinds: ["stance"], label: "Stances & Balance" },
  { kinds: ["leg_strength"], label: "Legs & Conditioning" },
  { kinds: ["floor"], label: "Floor & Core" },
  { kinds: ["qigong"], label: "Qigong & Meditation" },
];

function renderTrainingHall() {
  const box = $("hallGroups");
  if (!box) return;
  box.innerHTML = "";
  const drills = [...state.guides.drills.values()];
  for (const group of HALL_GROUPS) {
    const members = drills.filter((d) => group.kinds.includes(d.guide_kind));
    if (!members.length) continue;
    const section = document.createElement("div");
    section.className = "hall-group";
    const head = document.createElement("h3");
    head.textContent = `${group.label} (${members.length})`;
    section.append(head);
    const grid = document.createElement("div");
    grid.className = "hall-grid";
    for (const d of members) {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "hall-drill";
      btn.dataset.key = d.key;
      const name = document.createElement("strong");
      name.textContent = d.label;
      const meta = document.createElement("span");
      meta.textContent = d.kind === "reps" ? "counted reps" : "timed hold";
      btn.append(name, meta);
      btn.title = d.guide_image ? `Chart: ${d.guide_image.title}` : d.label;
      btn.addEventListener("click", () => {
        showGuide(d.key);
        if (d.kind === "hold") setTrackedStance(d.key, d.label);
        state.selectedRecordKey = d.key;
        document.querySelectorAll("#recordList .ex-chip").forEach((c) => {
          c.classList.toggle("sel", c.dataset.key === d.key);
        });
        closeWorkDrawer();
      });
      grid.append(btn);
    }
    section.append(grid);
    box.append(section);
  }
}

function renderChartShelf() {
  const shelf = $("chartShelf");
  if (!shelf) return;
  shelf.innerHTML = "";
  if (!state.guides.references.length) {
    shelf.textContent = "No charts found in chirox/reference.";
    return;
  }
  for (const ref of state.guides.references) {
    const tile = document.createElement("button");
    tile.type = "button";
    tile.className = "chart-tile";
    tile.title = `${ref.title} — click to fill the screen`;
    const img = document.createElement("img");
    img.src = ref.url;
    img.alt = ref.title;
    img.loading = "lazy";
    const cap = document.createElement("span");
    cap.textContent = ref.title;
    tile.append(img, cap);
    tile.addEventListener("click", () => openLightbox(ref.index));
    shelf.append(tile);
  }
}

function showGuide(key) {
  const drill = state.guides.drills.get(key);
  if (!drill) return;
  if ($("guideName")) $("guideName").textContent = drill.label || key;
  if ($("guideInstruction")) {
    $("guideInstruction").textContent = drill.instruction
      || "Move deliberately and keep the whole body in frame.";
  }
  if ($("guideKind")) {
    $("guideKind").textContent = drill.kind === "reps" ? "Counted reps" : "Timed hold";
  }
  if ($("guideCamera")) {
    $("guideCamera").textContent = drill.camera_instruction
      || "Built-in webcam (front). Stand far enough back for head to ankles.";
  }
  if ($("guideTruth")) {
    $("guideTruth").textContent = drill.guide_image
      ? drill.guide_image.title
      : (drill.guide_title || "Measured by Chirox vision.");
  }
  if ($("trackedStance") && !state.running) {
    $("trackedStance").textContent = drill.label || key;
  }
  if (drill.guide_image) selectGuideImage(drill.guide_image);
  document.querySelectorAll(".hall-drill").forEach((b) => {
    b.classList.toggle("sel", b.dataset.key === key);
  });
}

async function loadGuides() {
  try {
    const data = await (await fetch("/api/guides")).json();
    state.guides.references = data.references || [];
    state.guides.drills = new Map((data.drills || []).map((d) => [d.key, d]));
    renderTrainingHall();
    renderChartShelf();
    if (state.stance !== "auto") showGuide(state.stance);
  } catch (err) {
    $("guideInstruction").textContent = "Exercise guide unavailable.";
  }
}

// The mirror follows the practitioner: any hold picked in the Training Hall
// becomes the stance the live wireframe measures. "auto" watches first and names
// what it can see among known holds — it does not invent a form.
async function setTrackedStance(key, label) {
  if (state.stance === key) {
    $("trackedStance").textContent = label || key;
    return;
  }
  state.stance = key;
  if (key === "auto") {
    $("guideName").textContent = "Detecting…";
    $("trackedStance").textContent = "watching for a known hold";
    $("guideInstruction").textContent =
      "Wireguy watches first. When a known hold is clear, he names it. Pick Work locks a stance.";
  } else {
    $("trackedStance").textContent = label || key;
    showGuide(key);
  }
  const autoBtn = $("autoDetectBtn");
  if (autoBtn) autoBtn.classList.toggle("on", key === "auto");
  resetHoldMetrics();
  if (state.running) {
    await mirrorOff();
    await mirrorOn();
  }
}

// --- lightbox: the charts at human scale ---------------------------------------------

function openLightbox(index) {
  const refs = state.guides.references;
  if (!refs.length) return;
  state.lightboxIndex = ((index % refs.length) + refs.length) % refs.length;
  const ref = refs[state.lightboxIndex];
  const video = $("lbVideo");
  video.pause();
  video.hidden = true;
  video.removeAttribute("src");
  $("lbImage").hidden = false;
  $("lbImage").src = ref.url;
  $("lbImage").alt = ref.title;
  $("lbTitle").textContent = ref.title;
  $("lightbox").hidden = false;
  document.body.classList.add("lightbox-open");
}

function showPlaybackTools(show, note = "") {
  const tools = $("lbPlaybackTools");
  if (!tools) return;
  tools.hidden = !show;
  if ($("lbPlayNote")) $("lbPlayNote").textContent = note || "";
}

function openVideo(url, title, note = "") {
  const video = $("lbVideo");
  $("lbImage").hidden = true;
  $("lbImage").removeAttribute("src");
  video.hidden = false;
  video.src = url;
  video.playbackRate = Number(($("lbSpeed") && $("lbSpeed").value) || 1);
  video.play().catch(() => { /* codec not browser-playable; OPEN / prepare still work */ });
  $("lbTitle").textContent = title;
  showPlaybackTools(true, note);
  $("lightbox").hidden = false;
  document.body.classList.add("lightbox-open");
}

async function playRecording(file, title) {
  const res = await post("/api/recordings/playback", { file });
  if (!res.ok) {
    openVideo(`/media/${file}`, title, res.error || "Playback unavailable.");
    return;
  }
  state.playback = { file, title };
  if (res.proxy_ready) {
    openVideo(res.url, title, "Browser proxy ready.");
    return;
  }
  openVideo(res.url, title, "Preparing a browser-friendly copy…");
  const prepared = await post("/api/recordings/prepare", { file });
  if (prepared.ok && prepared.url) {
    openVideo(prepared.url, title, "Browser proxy ready.");
  } else if (prepared.mjpeg_url) {
    showPlaybackTools(true, prepared.error || "Streaming replay.");
    $("lbImage").hidden = false;
    $("lbImage").src = prepared.mjpeg_url;
    $("lbVideo").hidden = true;
    $("lbVideo").removeAttribute("src");
    $("lbTitle").textContent = title;
    $("lightbox").hidden = false;
    document.body.classList.add("lightbox-open");
  } else {
    showPlaybackTools(true, prepared.error || "Open in the system player if this will not play.");
  }
}

function closeLightbox() {
  const video = $("lbVideo");
  video.pause();
  video.removeAttribute("src");
  showPlaybackTools(false);
  state.playback = null;
  $("lightbox").hidden = true;
  document.body.classList.remove("lightbox-open");
}

function stepLightbox(delta) {
  if ($("lightbox").hidden) return;
  openLightbox(state.lightboxIndex + delta);
}

$("lbClose").addEventListener("click", closeLightbox);
$("lbPrev").addEventListener("click", () => stepLightbox(-1));
$("lbNext").addEventListener("click", () => stepLightbox(1));
$("lightbox").addEventListener("click", (ev) => {
  if (ev.target === $("lightbox")) closeLightbox();
});
document.addEventListener("keydown", (ev) => {
  if ($("lightbox").hidden) return;
  if (ev.key === "Escape") closeLightbox();
  if (ev.key === "ArrowLeft") stepLightbox(-1);
  if (ev.key === "ArrowRight") stepLightbox(1);
});
$("guideImageWrap").addEventListener("click", () => {
  const idx = Number($("guideImage").dataset.chartIndex);
  if (!Number.isNaN(idx)) openLightbox(idx);
});

// --- modes + learning deck -------------------------------------------------------

function applyMode(mode) {
  state.mode = mode === "learning" ? "learning" : "training";
  document.body.classList.toggle("mode-learning", state.mode === "learning");
  document.body.classList.toggle("mode-training", state.mode !== "learning");
  $("learningDeck").hidden = state.mode !== "learning";
  if ($("practiceStage")) $("practiceStage").hidden = state.mode === "learning";
  $("trainingModeBtn").classList.toggle("sel", state.mode === "training");
  $("learningModeBtn").classList.toggle("sel", state.mode === "learning");
  if (state.mode === "learning") {
    closeWorkDrawer();
    closePracticePanels();
    if (state.running) mirrorOff();
    refreshLearning();
  }
  if (state.mode === "training") maybeAutoMirror();
}

function openWorkDrawer() {
  const drawer = $("workDrawer");
  if (!drawer) return;
  drawer.hidden = false;
  $("pickWorkBtn").classList.add("open");
}

function closeWorkDrawer() {
  const drawer = $("workDrawer");
  if (!drawer) return;
  drawer.hidden = true;
  if ($("pickWorkBtn")) $("pickWorkBtn").classList.remove("open");
}

function closePracticePanels() {
  for (const sid of ["trainStrip", "recordStrip"]) {
    const el = $(sid);
    if (el) el.hidden = true;
  }
  for (const bid of ["trainBtn", "recordBtn"]) {
    const el = $(bid);
    if (el) el.classList.remove("open");
  }
}

// Training mode means training: the webcam comes up by itself unless the
// spoken trainer holds the camera. Recording tees from the live mirror and
// must NOT force the Wireguy stage off. ?autostart=0 disables.
async function maybeAutoMirror() {
  if (state.mode !== "training" || state.running || state.autoMirrorBlocked) return;
  if (state.autoMirrorInFlight) return;
  state.autoMirrorInFlight = true;
  try {
    const s = await (await fetch("/api/control/status")).json();
    const busy = s.voice && s.voice.active && s.voice.kind === "training";
    if (!busy && state.mode === "training" && !state.running) await mirrorOn();
  } catch (err) {
    /* camera can be retried on the next mode switch */
  } finally {
    state.autoMirrorInFlight = false;
  }
}

// Interactive machine: the ear wakes with the cockpit so you can speak and be
// spoken to without hunting for WAKE. ?autostart=0 disables this too.
async function maybeAutoEar() {
  if (state.autoMirrorBlocked || state.autoEarInFlight) return;
  state.autoEarInFlight = true;
  try {
    const s = await (await fetch("/api/control/status")).json();
    if (s.ear && s.ear.running) return;
    const res = await post("/api/control/wake");
    if (!res.ok && res.error) {
      console.warn("Chirox ear did not wake:", res.error);
    }
    setTimeout(refreshControl, 1200);
  } catch (err) {
    /* Ollama/ear can be woken manually with WAKE */
  } finally {
    state.autoEarInFlight = false;
  }
}

async function setMode(mode) {
  const data = await post("/api/mode", { mode });
  applyMode(data.mode || mode);
}

function updateActivity(activity) {
  if (!activity) return;
  if (activity.mode && activity.mode !== state.mode) applyMode(activity.mode);
  $("piperText").textContent = activity.last_spoken || "No speech yet.";
  $("whisperText").textContent = activity.last_heard || "Nothing heard yet.";
  const reading = activity.reading || {};
  $("readingTitle").textContent = activity.reading_title || "No book active";
  $("readingProgress").textContent = reading.total_chunks
    ? `${reading.chunk_index || 1}/${reading.total_chunks}` : "--";
  $("readingChunk").textContent = reading.text || "Choose a book below to read along while Chirox speaks.";
}

function appendChat(who, text) {
  const line = document.createElement("div");
  line.className = "chat-line";
  line.innerHTML = `<strong>${who}</strong><span></span>`;
  line.querySelector("span").textContent = text;
  $("chatLog").append(line);
  $("chatLog").scrollTop = $("chatLog").scrollHeight;
}

function fillForm(formId, data) {
  const form = $(formId);
  for (const field of form.querySelectorAll("input, textarea")) {
    field.value = data && data[field.name] !== undefined ? data[field.name] : (field.type === "number" ? "0" : "");
  }
}

function collectForm(formId) {
  const out = {};
  for (const field of $(formId).querySelectorAll("input, textarea")) {
    out[field.name] = field.value;
  }
  return out;
}

function showMandarinFocus(focus) {
  if (!focus) return;
  $("hanziChar").textContent = focus.character;
  $("hanziPinyin").textContent = focus.pinyin;
  $("hanziMeaning").textContent = focus.meaning;
  $("hanziQuestion").textContent = focus.question;
}

function renderLearningBooks(items) {
  const box = $("learningBooks");
  box.innerHTML = "";
  for (const item of items || []) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "book-chip";
    btn.textContent = item.bookmark > 0 ? `${item.label} · ${item.bookmark}` : item.label;
    btn.addEventListener("click", async () => {
      btn.disabled = true;
      await post("/api/library/read", { label: item.label });
      setTimeout(() => { btn.disabled = false; refreshLearning(); refreshControl(); }, 1000);
    });
    box.append(btn);
  }
}

function renderRecordDays(days) {
  const box = $("recordDays");
  box.innerHTML = "";
  for (const day of days || []) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "day-chip";
    btn.textContent = `Day ${day.day_number}${day.has_daily || day.has_mandarin ? " *" : ""}`;
    btn.addEventListener("click", () => loadRecordDay(day.day_number));
    box.append(btn);
  }
}

function renderRecordDay(data) {
  state.recordDay = data.day_number;
  $("recordDay").value = data.day_number;
  fillForm("dailyForm", data.daily || {});
  fillForm("mandarinForm", data.mandarin || {});
  showMandarinFocus(data.mandarin_focus);
  const focus = data.mandarin_focus || {};
  const charInput = document.querySelector("#mandarinForm [name='character_focus']");
  if (charInput && !charInput.value) charInput.value = focus.character || "";
}

async function loadRecordDay(dayNumber) {
  const data = await (await fetch(`/api/learning/day/${dayNumber}`)).json();
  renderRecordDay(data);
}

async function saveLearningRecord(kind) {
  const isDaily = kind === "daily";
  const formId = isDaily ? "dailyForm" : "mandarinForm";
  const url = isDaily ? "/api/learning/daily" : "/api/learning/mandarin";
  const res = await post(url, {
    day_number: Number($("recordDay").value || state.recordDay || 1),
    data: collectForm(formId),
  });
  $("recordNote2").textContent = res.ok
    ? `Sealed ${res.type} at seq ${res.seq}.`
    : `Save failed: ${res.error || "unknown error"}`;
  await refreshLearning();
}

async function refreshLearning() {
  try {
    const data = await (await fetch("/api/learning")).json();
    updateActivity(data.activity);
    renderLearningBooks(data.library);
    renderRecordDays(data.days);
    showMandarinFocus(data.mandarin_focus);
    if (!state.recordDay && data.today) state.recordDay = data.today.day_number;
    if (data.record && Number($("recordDay").value || 0) <= 1) renderRecordDay(data.record);
    refreshMemory();
  } catch (err) {
    $("readingChunk").textContent = "Learning Mode data unavailable.";
  }
}

// --- the Master's memory --------------------------------------------------------------

async function refreshMemory() {
  try {
    const data = await (await fetch("/api/memory?last=20")).json();
    const box = $("memoryList");
    box.innerHTML = "";
    if (!data.items || !data.items.length) {
      box.textContent = "No conversations sealed yet.";
      return;
    }
    for (const item of data.items) {
      const row = document.createElement("div");
      row.className = "memory-row" + (item.forgotten ? " forgotten" : "");
      const body = document.createElement("div");
      body.className = "memory-body";
      const meta = document.createElement("div");
      meta.className = "memory-meta";
      meta.textContent = `${item.at}${item.forgotten ? " · withdrawn" : ""}`;
      const q = document.createElement("p");
      q.textContent = `You: ${item.question}`;
      const a = document.createElement("p");
      a.textContent = `Chirox: ${item.answer}`;
      body.append(meta, q, a);
      row.append(body);
      if (!item.forgotten) {
        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = "chip";
        btn.textContent = "FORGET";
        btn.title = "Withdraw this exchange from recall (recorded, never silent)";
        btn.addEventListener("click", async () => {
          const reason = prompt("Why withdraw this exchange? (the reason is sealed)");
          if (!reason || !reason.trim()) return;
          const res = await post("/api/memory/forget", { seq: item.seq, reason: reason.trim() });
          if (!res.ok) alert(res.error || "Could not seal the forgetting.");
          refreshMemory();
        });
        row.append(btn);
      }
      box.append(row);
    }
  } catch (err) {
    $("memoryList").textContent = "Memory unavailable.";
  }
}

// --- practice bar + ear --------------------------------------------------------------

const strips = { trainBtn: "trainStrip", recordBtn: "recordStrip" };

function toggleStrip(btnId) {
  const strip = $(strips[btnId]);
  if (!strip) return;
  const nowHidden = !strip.hidden;
  closePracticePanels();
  strip.hidden = nowHidden;
  if (!nowHidden) $(btnId).classList.add("open");
}

$("trainingModeBtn").addEventListener("click", () => setMode("training"));
$("learningModeBtn").addEventListener("click", () => setMode("learning"));

$("pickWorkBtn").addEventListener("click", () => {
  const drawer = $("workDrawer");
  if (drawer.hidden) openWorkDrawer();
  else closeWorkDrawer();
});
$("closeDrawerBtn").addEventListener("click", closeWorkDrawer);

if ($("autoDetectBtn")) {
  $("autoDetectBtn").addEventListener("click", () => {
    setTrackedStance("auto", "Detecting…");
  });
}

// WAKE: one press brings Ollama up (if it is down) and sets the ear listening.
$("earBtn").addEventListener("click", async () => {
  const btn = $("earBtn");
  if (btn.classList.contains("on")) {
    await post("/api/control/ear/stop");
    setTimeout(refreshControl, 1200);
    return;
  }
  btn.disabled = true;
  btn.textContent = "WAKING…";
  try {
    const res = await post("/api/control/wake");
    if (!res.ok && res.error) alert(res.error);
  } finally {
    btn.disabled = false;
    btn.textContent = "WAKE";
    setTimeout(refreshControl, 1200);
  }
});

$("silenceButton").addEventListener("click", async () => {
  await post("/api/control/silence");
  refreshControl();
});

if ($("lbBack5")) {
  $("lbBack5").addEventListener("click", () => {
    const v = $("lbVideo");
    if (!v.hidden) v.currentTime = Math.max(0, v.currentTime - 5);
  });
}
if ($("lbFwd5")) {
  $("lbFwd5").addEventListener("click", () => {
    const v = $("lbVideo");
    if (!v.hidden) v.currentTime = Math.min(v.duration || v.currentTime + 5, v.currentTime + 5);
  });
}
if ($("lbSpeed")) {
  $("lbSpeed").addEventListener("change", () => {
    const v = $("lbVideo");
    if (!v.hidden) v.playbackRate = Number($("lbSpeed").value) || 1;
  });
}

$("masterAskBtn").addEventListener("click", async () => {
  const q = $("masterQuestion").value.trim();
  if (!q) return;
  appendChat("You", q);
  $("masterQuestion").value = "";
  appendChat("Chirox", "Thinking from the record...");
  const res = await post("/api/master/debrief", { question: q });
  const lines = document.querySelectorAll(".chat-line span");
  lines[lines.length - 1].textContent = res.text || "The Master could not be reached.";
  if (res.ok && res.text) await post("/api/say", { text: res.text });
  refreshControl();
  refreshMemory();
});

$("masterReflectBtn").addEventListener("click", async () => {
  appendChat("You", "Look back over my path with me.");
  appendChat("Chirox", "Looking back through the record...");
  const res = await post("/api/master/debrief", { reflect: true });
  const lines = document.querySelectorAll(".chat-line span");
  lines[lines.length - 1].textContent = res.text || "The Master could not be reached.";
  if (res.ok && res.text) await post("/api/say", { text: res.text });
  refreshControl();
  refreshMemory();
});

$("memoryRefreshBtn").addEventListener("click", refreshMemory);

$("loadDayBtn").addEventListener("click", () => loadRecordDay(Number($("recordDay").value || 1)));
$("saveDailyBtn").addEventListener("click", () => saveLearningRecord("daily"));
$("saveMandarinBtn").addEventListener("click", () => saveLearningRecord("mandarin"));

for (const btnId of Object.keys(strips)) {
  $(btnId).addEventListener("click", () => {
    const btn = $(btnId);
    // an active organ: clicking its lit button stops it instead of opening the panel
    if (btn.classList.contains("on")) {
      if (btnId === "recordBtn") post("/api/record/stop").then(refreshControl);
      else post("/api/control/silence").then(refreshControl);
      return;
    }
    toggleStrip(btnId);
  });
}

// chip helpers: single-select within a class, multi-select for drills
function singleSelect(cls) {
  document.querySelectorAll(`.${cls}`).forEach((chip) => {
    chip.addEventListener("click", () => {
      document.querySelectorAll(`.${cls}`).forEach((c) => c.classList.remove("sel"));
      chip.classList.add("sel");
    });
  });
}
singleSelect("time-chip");
singleSelect("len-chip");

function recordExerciseId(key, kind) {
  if (kind === "reps") return key;
  if (key.endsWith("_stance") || key.includes("_")) return key;
  return `${key}_stance`;
}

function renderRecordCatalog(drills) {
  const box = $("recordList");
  if (!box) return;
  box.innerHTML = "";
  if (!state.selectedRecordKey && drills.length) {
    state.selectedRecordKey = drills[0].key;
  }
  for (const d of drills) {
    const chip = document.createElement("button");
    chip.type = "button";
    chip.className = "chip ex-chip";
    chip.dataset.key = d.key;
    chip.dataset.ex = recordExerciseId(d.key, d.kind);
    chip.dataset.stance = d.kind === "hold" ? d.key : "";
    chip.textContent = d.kind === "reps" ? `${d.label} ×` : d.label;
    if (d.key === state.selectedRecordKey) chip.classList.add("sel");
    chip.addEventListener("click", () => {
      box.querySelectorAll(".ex-chip").forEach((c) => c.classList.remove("sel"));
      chip.classList.add("sel");
      state.selectedRecordKey = d.key;
      showGuide(d.key);
      if (d.kind === "hold") setTrackedStance(d.key, d.label);
    });
    box.append(chip);
  }
}

async function loadRoutineCatalog() {
  const box = $("routineList");
  if (!box) return;
  try {
    const data = await (await fetch("/api/routine/catalog")).json();
    box.innerHTML = "";
    for (const r of data.routines || []) {
      const chip = document.createElement("button");
      chip.type = "button";
      chip.className = "chip go";
      chip.textContent = `BEGIN · ${r.label}`;
      chip.title = r.source_note || r.label;
      chip.addEventListener("click", async () => {
        const res = await post("/api/routine/start", { routine_key: r.key });
        if (!res.ok && res.error) {
          alert(res.error);
          return;
        }
        state.routineActive = true;
        $("hudPhase").textContent = `${r.label} · starting…`;
        $("routineNextBtn").hidden = false;
        $("routineStopBtn").hidden = false;
        closeWorkDrawer();
        if (!state.running) await maybeAutoMirror();
      });
      box.append(chip);
    }
    if (!box.children.length) box.textContent = "No named routines yet.";
  } catch (err) {
    box.textContent = "Routines unavailable.";
  }
}

async function loadDrillCatalog() {
  try {
    const data = await (await fetch("/api/train/catalog")).json();
    const box = $("drillList");
    box.innerHTML = "";
    for (const d of data.drills) {
      if (!state.guides.drills.has(d.key)) state.guides.drills.set(d.key, d);
      const chip = document.createElement("button");
      chip.type = "button";
      chip.className = "chip drill-chip";
      chip.dataset.key = d.key;
      chip.textContent = d.kind === "reps" ? `${d.label} ×` : d.label;
      chip.title = d.kind === "reps" ? "Counted reps" : "Timed hold";
      chip.addEventListener("click", () => {
        chip.classList.toggle("sel");
        showGuide(d.key);
        if (d.kind === "hold") setTrackedStance(d.key, d.label);
      });
      box.append(chip);
    }
    renderRecordCatalog(data.drills || []);
    if (state.stance !== "auto") showGuide(state.stance);
  } catch (err) {
    $("drillList").textContent = "Catalog unavailable.";
    if ($("recordList")) $("recordList").textContent = "Catalog unavailable.";
  }
}

if ($("routineNextBtn")) {
  $("routineNextBtn").addEventListener("click", async () => {
    const res = await post("/api/routine/next", {});
    if (res.phase_label) {
      $("hudPhase").textContent = `${res.label} · ${res.phase_index + 1}/${res.phase_count}: ${res.phase_label}`;
    }
  });
}
if ($("routineStopBtn")) {
  $("routineStopBtn").addEventListener("click", async () => {
    const res = await post("/api/routine/stop", {
      routine_key: "eight_brocades_ste",
      seal: true,
      source: state.sources.front,
    });
    state.routineActive = false;
    $("routineNextBtn").hidden = true;
    $("routineStopBtn").hidden = true;
    if (res.ok && res.sealed) {
      const t = (res.summary && res.summary.totals) || {};
      $("hudPhase").textContent = `Sealed forever · ${t.phases_completed || 0} phases · ${t.reps_total || 0} reps`;
      refreshTimeline();
    } else if (res.error) {
      $("hudPhase").textContent = res.error;
    }
  });
}

// --- organ launches ---------------------------------------------------------------

$("trainGo").addEventListener("click", async () => {
  const stances = [...document.querySelectorAll(".drill-chip.sel")].map((c) => c.dataset.key);
  const seconds = Number(document.querySelector(".time-chip.sel").dataset.sec);
  if (stances.length) showGuide(stances[0]);
  if (state.running) await mirrorOff();  // the trainer needs the camera
  const res = await post("/api/train/start", {
    stances: stances.length ? stances : null, seconds, drills: 3, source: state.sources.front,
  });
  $("trainNote").textContent = res.ok
    ? "He is calling the drills — listen."
    : `Could not start: ${res.error}`;
  refreshControl();
});

$("recordGo").addEventListener("click", async () => {
  const ex = document.querySelector(".ex-chip.sel");
  if (!ex) {
    $("recordNote").textContent = "Pick an exercise from the catalog first.";
    return;
  }
  const minutes = Number(document.querySelector(".len-chip.sel").dataset.min);
  // Keep Wireguy on: recording tees frames from the live session. If the
  // mirror is idle, wake it so you can see yourself while it saves.
  if (ex.dataset.stance) state.stance = ex.dataset.stance;
  if (!state.running) await mirrorOn();
  const res = await post("/api/record/start", {
    exercise: ex.dataset.ex,
    source: state.sources.front,
    seconds: minutes * 60,
    stance: ex.dataset.stance || null,
  });
  $("recordNote").textContent = res.ok
    ? `Recording ${ex.textContent} for ${minutes} min — Wireguy stays live. It seals when done.`
    : `Could not start: ${res.error}`;
  closePracticePanels();
  refreshControl();
});

$("readBtn").addEventListener("click", () => {
  refreshLibrary();
  refreshLearning();
});

// --- library ------------------------------------------------------------------------

async function refreshLibrary() {
  try {
    const data = await (await fetch("/api/library")).json();
    const box = $("libraryList");
    box.innerHTML = "";
    for (const item of data.items) {
      const chip = document.createElement("button");
      chip.type = "button";
      chip.className = "chip";
      const mark = item.bookmark > 0 ? ` ·${item.bookmark}` : "";
      chip.textContent = item.label + mark;
      chip.title = item.kind === "book" ? "Read this book aloud" : "Read this document aloud";
      chip.addEventListener("click", async () => {
        chip.disabled = true;
        await post("/api/library/read", { label: item.label });
        setTimeout(() => { chip.disabled = false; refreshControl(); }, 800);
      });
      box.append(chip);
    }
  } catch (err) {
    $("libraryList").textContent = "Library unavailable.";
  }
}

// --- status + timeline -----------------------------------------------------------------

async function refreshControl() {
  try {
    const s = await (await fetch("/api/control/status")).json();
    $("earBtn").classList.toggle("on", s.ear.running);
    if ($("readBtn")) $("readBtn").classList.toggle("on", s.voice.active && s.voice.kind === "reading");
    $("trainBtn").classList.toggle("on", s.voice.active && s.voice.kind === "training");
    $("recordBtn").classList.toggle("on", Boolean(s.voice.recording));
    $("sysCodex").textContent = s.codex.ok ? `record intact (${s.codex.events})` : "RECORD BROKEN";
    updateActivity(s.activity);
    updateRecording(s.voice);
  } catch (err) { /* server briefly busy opening cameras - next poll catches up */ }
}

// --- recording: unmistakable state, a STOP that works, files you can find -------------

function updateRecording(voice) {
  const wasRecording = Boolean(state.recording);
  const info = (voice && voice.recording_info) || {};
  state.recording = Boolean(voice && voice.recording);
  state.recStartedMs = info.started ? Date.parse(info.started) : state.recStartedMs;
  $("recBanner").hidden = !state.recording;
  if (state.recording) {
    $("recWhat").textContent = (info.exercise || "").replace(/_/g, " ");
    tickRecElapsed();
  }
  if (wasRecording && !state.recording) {
    // a recording just finished (or was stopped): show it, bring the mirror back
    refreshRecordings();
    maybeAutoMirror();
  }
}

function tickRecElapsed() {
  if (!state.recording || !state.recStartedMs) return;
  const s = Math.max(0, Math.floor((Date.now() - state.recStartedMs) / 1000));
  $("recElapsed").textContent = `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
}
setInterval(tickRecElapsed, 1000);

$("recStopBtn").addEventListener("click", async () => {
  await post("/api/record/stop");
  setTimeout(refreshControl, 800);
});

async function refreshRecordings() {
  try {
    const data = await (await fetch("/api/recordings")).json();
    $("mediaFolder").textContent = data.folder || "";
    const box = $("recordingsList");
    box.innerHTML = "";
    if (!data.items || !data.items.length) {
      box.textContent = "No recordings yet. Press RECORD, train, and the video lands here.";
      return;
    }
    for (const r of data.items) {
      const row = document.createElement("div");
      row.className = "recording-row";
      const info = document.createElement("div");
      info.className = "recording-info";
      const name = document.createElement("strong");
      name.textContent = (r.exercise || "unknown").replace(/_/g, " ");
      const meta = document.createElement("span");
      const bits = [];
      if (r.day_number) bits.push(`day ${r.day_number}`);
      if (r.date) bits.push(r.date);
      if (r.duration_s) bits.push(`${Math.round(r.duration_s)}s`);
      bits.push(`${r.size_mb} MB`);
      if (r.proxy_ready) bits.push("browser ready");
      if (!r.sealed) bits.push("not sealed (stopped early)");
      meta.textContent = bits.join(" · ");
      const path = document.createElement("span");
      path.className = "recording-path";
      path.textContent = r.file;
      info.append(name, meta, path);
      const play = document.createElement("button");
      play.type = "button";
      play.className = "chip";
      play.textContent = "PLAY";
      play.title = "Play here in the cockpit";
      play.addEventListener("click", () => playRecording(r.file, `${name.textContent} — ${meta.textContent}`));
      const open = document.createElement("button");
      open.type = "button";
      open.className = "chip";
      open.textContent = "OPEN";
      open.title = "Open in the system video player";
      open.addEventListener("click", () => post("/api/recordings/open", { file: r.file }));
      row.append(info, play, open);
      box.append(row);
    }
  } catch (err) {
    $("recordingsList").textContent = "Recordings unavailable.";
  }
}

$("openFolderBtn").addEventListener("click", () => post("/api/recordings/folder"));

async function refreshTimeline() {
  try {
    const data = await (await fetch("/api/timeline?limit=10")).json();
    const box = $("timelineList");
    box.innerHTML = "";
    if (!data.events.length) {
      box.textContent = "Nothing recorded yet. The record begins when you do.";
      return;
    }
    for (const e of data.events) {
      const item = document.createElement("span");
      item.className = "t-item";
      item.textContent = `${e.date || ""} ${e.type}: ${e.what}`;
      item.title = e.detail || "";
      box.append(item);
    }
  } catch (err) {
    $("timelineList").textContent = "Timeline unavailable.";
  }
}

async function loadStatus() {
  const res = await fetch("/api/status");
  const data = await res.json();
  $("standing").textContent = `Day ${data.practice.day_number} · Week ${data.practice.week_number} · ${data.practice.phase || ""}`;
  if (data.camera_defaults) {
    for (const role of ROLES) {
      if (data.camera_defaults[role] !== undefined) state.sources[role] = data.camera_defaults[role];
    }
  }
}

window.addEventListener("beforeunload", () => {
  if (state.running) navigator.sendBeacon("/api/session/stop", "{}");
});

const params = new URLSearchParams(window.location.search);
state.autoMirrorBlocked = params.get("autostart") === "0";

applyMode("training");
fetch("/api/mode")
  .then((r) => r.json())
  .then((activity) => updateActivity(activity))
  .catch(() => {});

loadStatus()
  .catch(() => { $("standing").textContent = "Status unavailable"; })
  .finally(() => {
    maybeAutoMirror();
    maybeAutoEar();
  });
refreshControl();
refreshLibrary();
refreshTimeline();
refreshRecordings();
loadGuides();
loadDrillCatalog();
loadRoutineCatalog();
setInterval(refreshControl, 5000);
setInterval(() => { if (state.mode === "learning") refreshLearning(); }, 2500);
setInterval(refreshTimeline, 30000);
