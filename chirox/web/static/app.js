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
  stance: "horse",
  sources: { front: 0 },
  opacity: 0.9,
  startedAt: null,
  timer: null,
  guides: { drills: new Map(), references: [] },
  mode: "training",
  recordDay: null,
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
  view.msg.textContent = "Ready.";
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
  await post("/api/session/start", { source: state.sources.front, stance: state.stance, role: "front" });
  openSocket("front");
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
      btn.addEventListener("click", () => showGuide(d.key));
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
  $("guideName").textContent = drill.label || key;
  $("guideInstruction").textContent = drill.instruction || "Move deliberately and keep the whole body in frame.";
  $("guideKind").textContent = drill.kind === "reps" ? "Counted reps" : "Timed hold";
  $("guideCamera").textContent = drill.camera_instruction || `Best camera: ${drill.view || "front"}.`;
  $("guideTruth").textContent = drill.guide_image ? drill.guide_image.title : (drill.guide_title || "Measured by Chirox vision.");
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
    showGuide(state.stance);
  } catch (err) {
    $("guideInstruction").textContent = "Exercise guide unavailable.";
  }
}

// --- lightbox: the charts at human scale ---------------------------------------------

function openLightbox(index) {
  const refs = state.guides.references;
  if (!refs.length) return;
  state.lightboxIndex = ((index % refs.length) + refs.length) % refs.length;
  const ref = refs[state.lightboxIndex];
  $("lbImage").src = ref.url;
  $("lbImage").alt = ref.title;
  $("lbTitle").textContent = ref.title;
  $("lightbox").hidden = false;
  document.body.classList.add("lightbox-open");
}

function closeLightbox() {
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
  $("trainingModeBtn").classList.toggle("sel", state.mode === "training");
  $("learningModeBtn").classList.toggle("sel", state.mode === "learning");
  if (state.mode === "learning" && state.running) mirrorOff();
  if (state.mode === "learning") refreshLearning();
  if (state.mode === "training") maybeAutoMirror();
}

// Training mode means training: the webcam comes up by itself unless another
// organ (trainer, recorder) holds the camera. ?autostart=0 disables.
async function maybeAutoMirror() {
  if (state.mode !== "training" || state.running || state.autoMirrorBlocked) return;
  if (state.autoMirrorInFlight) return;
  state.autoMirrorInFlight = true;
  try {
    const s = await (await fetch("/api/control/status")).json();
    const busy = (s.voice && s.voice.active && s.voice.kind === "training") ||
                 (s.voice && s.voice.recording);
    if (!busy && state.mode === "training" && !state.running) await mirrorOn();
  } catch (err) {
    /* camera can be retried on the next mode switch */
  } finally {
    state.autoMirrorInFlight = false;
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

$("trainingModeBtn").addEventListener("click", () => setMode("training"));
$("learningModeBtn").addEventListener("click", () => setMode("learning"));

$("mirrorBtn").addEventListener("click", () => (state.running ? mirrorOff() : mirrorOn()));

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
      state.guides.drills.set(d.key, d);
      const chip = document.createElement("button");
      chip.type = "button";
      chip.className = "chip drill-chip";
      chip.dataset.key = d.key;
      chip.textContent = d.kind === "reps" ? `${d.label} ×` : d.label;
      chip.title = `${d.kind === "reps" ? "Counted reps" : "Timed hold"} — best from the ${d.view} camera`;
      chip.addEventListener("click", () => {
        chip.classList.toggle("sel");
        showGuide(d.key);
      });
      box.append(chip);
    }
    showGuide(state.stance);
  } catch (err) {
    $("drillList").textContent = "Catalog unavailable.";
  }
}

document.querySelectorAll(".st-chip").forEach((chip) => {
  chip.addEventListener("click", async () => {
    document.querySelectorAll(".st-chip").forEach((c) => c.classList.remove("sel"));
    chip.classList.add("sel");
    state.stance = chip.dataset.st;
    showGuide(state.stance);
    if (state.running) {  // apply the new stance to the live mirror
      await mirrorOff();
      await mirrorOn();
    }
  });
});

document.querySelectorAll(".ex-chip").forEach((chip) => {
  chip.addEventListener("click", () => {
    const key = chip.dataset.stance || (chip.dataset.ex || "").replace(/_stance$/, "");
    showGuide(key);
  });
});

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
    ? "He is calling the drills - listen."
    : `Could not start: ${res.error}`;
  refreshControl();
});

$("recordGo").addEventListener("click", async () => {
  const ex = document.querySelector(".ex-chip.sel");
  const minutes = Number(document.querySelector(".len-chip.sel").dataset.min);
  const camRole = "front";
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
    updateActivity(s.activity);
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

const params = new URLSearchParams(window.location.search);
state.autoMirrorBlocked = params.get("autostart") === "0";

applyMode("training");
fetch("/api/mode")
  .then((r) => r.json())
  .then((activity) => updateActivity(activity))
  .catch(() => {});

loadStatus()
  .catch(() => { $("standing").textContent = "Status unavailable"; })
  .finally(() => { maybeAutoMirror(); });
refreshControl();
refreshLibrary();
refreshTimeline();
loadGuides();
loadDrillCatalog();
setInterval(refreshControl, 5000);
setInterval(() => { if (state.mode === "learning") refreshLearning(); }, 2500);
setInterval(refreshTimeline, 30000);
