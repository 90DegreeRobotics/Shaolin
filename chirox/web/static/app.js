// Chirox control deck — one page, a row of toggles, three camera boxes.
// No terminal, no typing: every organ is a button; questions go by voice.

const ROLES = ["front", "side", "extra"];

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
  pair: ["front", "side"],      // hub truth: two live streams, third swaps in
  stance: "horse",
  sources: { front: 0, side: 2, extra: 1 },
  opacity: 0.9,
  startedAt: null,
  timer: null,
};

const bones = [
  ["left_shoulder", "right_shoulder"],
  ["left_hip", "right_hip"],
  ["left_shoulder", "left_elbow"],
  ["left_elbow", "left_wrist"],
  ["right_shoulder", "right_elbow"],
  ["right_elbow", "right_wrist"],
  ["left_shoulder", "left_hip"],
  ["right_shoulder", "right_hip"],
  ["left_hip", "left_knee"],
  ["left_knee", "left_ankle"],
  ["right_hip", "right_knee"],
  ["right_knee", "right_ankle"],
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

function pointOf(landmarks, name) {
  return landmarks.find((lm) => lm.name === name);
}

function toCanvasPoint(canvas, lm) {
  const mirrored = $("mirrorToggle").checked;
  const x = mirrored ? (1 - lm.x) * canvas.width : lm.x * canvas.width;
  return { x, y: lm.y * canvas.height, visibility: lm.visibility };
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
  for (const lm of landmarks) {
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

function updateView(role, payload) {
  const view = views[role];
  view.frameCount = payload.frame_index || view.frameCount + 1;
  if (!payload.reading) {
    view.lastState = "no_body";
    view.conf.textContent = "no body";
    view.msg.textContent = "No body detected. Step fully into frame.";
    view.assess.textContent = "";
    return;
  }
  const reading = payload.reading;
  view.conf.textContent = `conf ${Number(reading.confidence || 0).toFixed(2)}`;
  view.assess.textContent = reading.assessment || "";
  if (reading.uncertain || payload.state === "uncertain") {
    view.lastState = "uncertain";
    view.uncertain += 1;
    view.msg.textContent = "Uncertain - reframe before trusting numbers.";
  } else {
    view.lastState = "measured";
    view.msg.textContent = "";
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

function renderPayload(role, payload, jpeg) {
  drawFrame(views[role], payload, jpeg);
  updateView(role, payload);
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
  view.msg.textContent = role === "extra" && !state.pair.includes("extra")
    ? "Standby - the hub carries two live streams (measured)."
    : "Ready.";
}

function startTimer() {
  state.startedAt = Date.now();
  clearInterval(state.timer);
  state.timer = setInterval(() => {
    $("runtime").textContent = `${((Date.now() - state.startedAt) / 1000).toFixed(0)}s`;
  }, 500);
}

async function mirrorOn() {
  ROLES.forEach(resetView);
  const [a, b] = state.pair;
  await post("/api/session/start", { source: state.sources[a], stance: state.stance, role: a });
  await post("/api/session/start", { source: state.sources[b], stance: state.stance, role: b });
  openSocket(a);
  openSocket(b);
  state.running = true;
  $("mirrorBtn").classList.add("on");
  startTimer();
  updateGlobalTruth();
}

async function mirrorOff() {
  ROLES.forEach(closeSocket);
  await post("/api/session/stop").catch(() => {});
  state.running = false;
  $("mirrorBtn").classList.remove("on");
  clearInterval(state.timer);
  ROLES.forEach(resetView);
  setTruth("no-body", "Idle");
}

async function swapThird() {
  const leaving = state.pair.includes("side") ? "side" : "extra";
  const joining = leaving === "side" ? "extra" : "side";
  if (state.running) {
    closeSocket(leaving);
    await post("/api/session/stop-role", { role: leaving });
    await post("/api/session/start", {
      source: state.sources[joining], stance: state.stance, role: joining,
    });
    openSocket(joining);
  }
  state.pair = ["front", joining];
  $("swapBtn").textContent = `Swap live with ${joining === "extra" ? "Side" : "Extra"}`;
  resetView(leaving);
}

// --- toggles -----------------------------------------------------------------------

const strips = { trainBtn: "trainStrip", readBtn: "readStrip", recordBtn: "recordStrip", masterBtn: "masterStrip" };

function toggleStrip(btnId) {
  const strip = $(strips[btnId]);
  const nowHidden = !strip.hidden;
  for (const sid of Object.values(strips)) $(sid).hidden = true;
  for (const bid of Object.keys(strips)) $(bid).classList.remove("open");
  strip.hidden = nowHidden;
  if (!nowHidden) $(btnId).classList.add("open");
}

$("mirrorBtn").addEventListener("click", () => (state.running ? mirrorOff() : mirrorOn()));

$("earBtn").addEventListener("click", async () => {
  const on = $("earBtn").classList.contains("on");
  await post(on ? "/api/control/ear/stop" : "/api/control/ear/start");
  setTimeout(refreshControl, 1200);
});

$("silenceButton").addEventListener("click", async () => {
  await post("/api/control/silence");
  refreshControl();
});

for (const btnId of Object.keys(strips)) {
  $(btnId).addEventListener("click", (ev) => {
    const btn = $(btnId);
    // an active organ: clicking its lit toggle stops it instead of opening the strip
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
singleSelect("ex-chip");
singleSelect("len-chip");
singleSelect("cam-chip");

async function loadDrillCatalog() {
  try {
    const data = await (await fetch("/api/train/catalog")).json();
    const box = $("drillList");
    box.innerHTML = "";
    for (const d of data.drills) {
      const chip = document.createElement("button");
      chip.type = "button";
      chip.className = "chip drill-chip";
      chip.dataset.key = d.key;
      chip.textContent = d.kind === "reps" ? `${d.label} ×` : d.label;
      chip.title = `${d.kind === "reps" ? "Counted reps" : "Timed hold"} — best from the ${d.view} camera`;
      chip.addEventListener("click", () => chip.classList.toggle("sel"));
      box.append(chip);
    }
  } catch (err) {
    $("drillList").textContent = "Catalog unavailable.";
  }
}

document.querySelectorAll(".st-chip").forEach((chip) => {
  chip.addEventListener("click", async () => {
    document.querySelectorAll(".st-chip").forEach((c) => c.classList.remove("sel"));
    chip.classList.add("sel");
    state.stance = chip.dataset.st;
    if (state.running) {  // apply the new stance to the live mirror
      await mirrorOff();
      await mirrorOn();
    }
  });
});

$("swapBtn").addEventListener("click", swapThird);

// --- organ launches ---------------------------------------------------------------

$("trainGo").addEventListener("click", async () => {
  const stances = [...document.querySelectorAll(".drill-chip.sel")].map((c) => c.dataset.key);
  const seconds = Number(document.querySelector(".time-chip.sel").dataset.sec);
  if (state.running) await mirrorOff();  // the trainer needs the camera
  const res = await post("/api/train/start", {
    stances: stances.length ? stances : null, seconds, drills: 3, source: state.sources.front,
  });
  $("trainNote").textContent = res.ok
    ? "He is calling the drills - listen."
    : `Could not start: ${res.error}`;
  refreshControl();
});

$("recordGo").addEventListener("click", async () => {
  const ex = document.querySelector(".ex-chip.sel");
  const minutes = Number(document.querySelector(".len-chip.sel").dataset.min);
  const camRole = document.querySelector(".cam-chip.sel").dataset.role;
  if (state.running) await mirrorOff();  // the recorder needs the camera
  const res = await post("/api/record/start", {
    exercise: ex.dataset.ex,
    source: state.sources[camRole],
    seconds: minutes * 60,
    stance: ex.dataset.stance || null,
  });
  $("recordNote").textContent = res.ok
    ? `Recording ${ex.textContent} for ${minutes} min - train. It seals itself when done.`
    : `Could not start: ${res.error}`;
  refreshControl();
});

$("masterGo").addEventListener("click", async () => {
  $("masterText").textContent = "The Master is reading the record…";
  $("masterGo").disabled = true;
  try {
    const res = await post("/api/master/debrief", {});
    $("masterText").textContent = res.text;
    if (res.ok) await post("/api/say", { text: res.text });
  } catch (err) {
    $("masterText").textContent = "The Master could not be reached.";
  } finally {
    $("masterGo").disabled = false;
  }
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
    $("readBtn").classList.toggle("on", s.voice.active && s.voice.kind === "reading");
    $("trainBtn").classList.toggle("on", s.voice.active && s.voice.kind === "training");
    $("recordBtn").classList.toggle("on", Boolean(s.voice.recording));
    $("sysCodex").textContent = s.codex.ok ? `record intact (${s.codex.events})` : "RECORD BROKEN";
  } catch (err) { /* server briefly busy opening cameras - next poll catches up */ }
}

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

loadStatus()
  .catch(() => { $("standing").textContent = "Status unavailable"; })
  .finally(() => {
    const params = new URLSearchParams(window.location.search);
    if (["dual", "all", "1"].includes(params.get("autostart"))) mirrorOn();
  });
refreshControl();
refreshLibrary();
refreshTimeline();
loadDrillCatalog();
setInterval(refreshControl, 5000);
setInterval(refreshTimeline, 30000);
