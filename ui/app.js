// VoiceMod 2.0 — lógica de la interfaz
const $ = (s) => document.querySelector(s);
const $$ = (s) => [...document.querySelectorAll(s)];
let api, S = { voices: [], sounds: [], favs: [], current: "Normal", params: {}, cat: "Todas", running: false, binds: {}, actions: [] };

const MODULES = [
  { id: "tono", title: "Tono", img: "img/modulos/tono.jpg", keys: [["pitch", "Semitonos", -12, 12, 0.5, (v) => (v > 0 ? "+" : "") + v]] },
  { id: "mod", title: "Modulación", img: "img/modulos/mod.jpg", keys: [
    ["ring_freq", "Robot · frecuencia", 0, 1000, 5, (v) => v + " Hz"], ["ring_mix", "Robot · mezcla", 0, 1, 0.01, pct],
    ["tremolo_rate", "Trémolo · velocidad", 0, 20, 0.5, (v) => v + " Hz"], ["tremolo_depth", "Trémolo · profundidad", 0, 1, 0.01, pct]] },
  { id: "textura", title: "Textura", img: "img/modulos/textura.jpg", keys: [
    ["whisper", "Susurro", 0, 1, 0.01, pct], ["drive", "Distorsión", 0, 1, 0.01, pct],
    ["bits", "Resolución", 3, 16, 1, (v) => (v >= 16 ? "Off" : v + " bits")], ["downsample", "Reducción de muestreo", 1, 16, 1, (v) => (v <= 1 ? "Off" : "÷" + v)]] },
  { id: "filtros", title: "Ecualizador", img: "img/modulos/filtros.jpg", keys: [
    ["lowcut", "Cortar graves", 0, 2000, 10, (v) => (v < 20 ? "Off" : v + " Hz")], ["highcut", "Cortar agudos", 0, 16000, 100, (v) => (v < 20 ? "Off" : v + " Hz")]] },
  { id: "eco", title: "Eco", img: "img/modulos/eco.jpg", keys: [
    ["echo_time", "Tiempo", 0.01, 1, 0.01, (v) => Math.round(v * 1000) + " ms"], ["echo_fb", "Repeticiones", 0, 0.9, 0.01, pct], ["echo_mix", "Mezcla", 0, 1, 0.01, pct]] },
  { id: "reverb", title: "Reverberación", img: "img/modulos/reverb.jpg", keys: [["reverb_size", "Tamaño de la sala", 0.3, 0.97, 0.01, pct], ["reverb_mix", "Mezcla", 0, 1, 0.01, pct]] },
  { id: "salida", title: "Salida", img: "img/modulos/salida.jpg", keys: [["gate_db", "Puerta de ruido", -80, -20, 1, (v) => v + " dB"], ["volume", "Volumen", 0, 3, 0.01, pct]] },
];
function pct(v) { return Math.round(v * 100) + "%"; }
const PAGES = {
  voices: ["Voces", "Elige una voz y empieza a hablar"],
  sounds: ["Soundboard", "Lanza sonidos en directo a tu micrófono"],
  lab: ["Laboratorio de voz", "Crea tu propia voz con 18 parámetros en tiempo real"],
  settings: ["Ajustes y audio", "Dispositivos, atajos y ayuda"],
};
const PAD_COLORS = [["#8b5cf6", "#4c1d95"], ["#06b6d4", "#155e75"], ["#f43f5e", "#881337"], ["#f59e0b", "#92400e"], ["#22c55e", "#14532d"], ["#ec4899", "#831843"], ["#3b82f6", "#1e3a8a"], ["#14b8a6", "#134e4a"]];

// ---------- utilidades ----------
function toast(msg, err) {
  const t = document.createElement("div");
  t.className = "toast" + (err ? " err" : "");
  t.textContent = msg;
  $("#toasts").appendChild(t);
  setTimeout(() => t.remove(), 3200);
}
const voiceBy = (n) => S.voices.find((v) => v.name === n) || S.voices[0];
function artStyle(v) {
  return v.img ? `background-image:url('${v.img}')` : `background:linear-gradient(135deg,${v.c1},${v.c2})`;
}
function setThumb(el, v) {
  el.style.cssText = artStyle(v);
  el.textContent = v.img ? "" : v.emoji;
}

// ---------- navegación ----------
function go(page) {
  $$("#nav button").forEach((b) => b.classList.toggle("active", b.dataset.page === page));
  $$(".page").forEach((p) => p.classList.toggle("active", p.id === "page-" + page));
  $("#pageTitle").textContent = PAGES[page][0];
  $("#pageSub").textContent = PAGES[page][1];
  $("#searchBox").style.visibility = page === "voices" ? "visible" : "hidden";
}

// ---------- voces ----------
function renderCats() {
  const cats = ["Favoritas", ...S.categories];
  $("#cats").innerHTML = cats.map((c) => `<button class="chip ${c === S.cat ? "active" : ""}" data-cat="${c}">${c === "Favoritas" ? "★ " : ""}${c}</button>`).join("");
}
function renderVoices() {
  const q = $("#search").value.trim().toLowerCase();
  const list = S.voices.map((v, i) => ({ ...v, i })).filter((v) => {
    if (S.cat === "Favoritas" && !S.favs.includes(v.name)) return false;
    if (!["Todas", "Favoritas"].includes(S.cat) && v.cat !== S.cat) return false;
    return !q || (v.name + " " + v.desc + " " + v.cat).toLowerCase().includes(q);
  });
  $("#voiceGrid").innerHTML = list.length ? list.map((v) => `
    <div class="card ${v.name === S.current ? "selected" : ""}" data-voice="${v.name}">
      <div class="art" style="${artStyle(v)}">${v.img ? "" : v.emoji}</div>
      <button class="fav ${S.favs.includes(v.name) ? "on" : ""}" data-fav="${v.name}" title="Favorita"><svg><use href="#i-star"/></svg></button>
      <button class="hkbtn" data-hk="voice:${v.name}" title="Asignar atajo">⌨</button>
      ${S.binds["voice:" + v.name] ? `<span class="key user">${fmtCombo(S.binds["voice:" + v.name])}</span>` : ""}
      <div class="meta"><b>${v.name}</b><small>${v.desc}</small></div>
    </div>`).join("") : `<div class="empty">${S.cat === "Favoritas" ? "Marca voces con ★ para verlas aquí." : "No hay voces que coincidan."}</div>`;
  $("#nVoices").textContent = S.voices.length;
}
function showCurrent() {
  const v = voiceBy(S.current);
  $("#heroName").textContent = v.name;
  $("#heroDesc").textContent = v.desc + " · " + v.cat;
  $("#heroImg").style.cssText = artStyle(v);
  $("#dockName").textContent = v.name;
  setThumb($("#dockThumb"), v);
  setThumb($("#labThumb"), v);
  $("#labName").textContent = v.name;
  $("#labDelete").style.display = v.custom ? "" : "none";
  $$(".card").forEach((c) => c.classList.toggle("selected", c.dataset.voice === S.current));
}
async function selectVoice(name, silent) {
  const r = await api.voice(name);
  S.current = r.current; S.params = r.params;
  showCurrent(); syncSliders();
  if (!silent) toast("Voz: " + r.current);
}

// ---------- laboratorio ----------
function renderModules() {
  $("#modules").innerHTML = MODULES.map((m) => `
    <div class="module">
      <h4><span class="ico" style="background-image:url('${m.img}');background-size:cover"></span>${m.title}<button class="reset" data-reset="${m.id}">Restablecer</button></h4>
      ${m.keys.map(([k, label, lo, hi, st]) => `
        <div class="ctl"><div class="top"><span>${label}</span><output id="o-${k}"></output></div>
        <input type="range" class="range" data-k="${k}" min="${lo}" max="${hi}" step="${st}"></div>`).join("")}
    </div>`).join("");
}
const FMT = Object.fromEntries(MODULES.flatMap((m) => m.keys.map((k) => [k[0], k[5]])));
function paintRange(el) {
  const p = ((el.value - el.min) / (el.max - el.min)) * 100;
  el.style.background = `linear-gradient(90deg,#8b5cf6 0%,#06b6d4 ${p}%,var(--surface-3) ${p}%)`;
}
function syncSliders() {
  $$("#modules input[data-k]").forEach((el) => {
    const k = el.dataset.k;
    el.value = S.params[k];
    $("#o-" + k).textContent = FMT[k](+(+el.value).toFixed(2));
    paintRange(el);
  });
}

// ---------- soundboard ----------
function renderSounds() {
  $("#soundGrid").innerHTML = S.sounds.map((s, i) => {
    const [a, b] = PAD_COLORS[i % PAD_COLORS.length];
    const bg = s.img ? `url('${s.img}') center/cover` : `linear-gradient(145deg,${a},${b})`;
    return `<button class="pad" data-sound="${s.file}" style="--pad:${bg}">
      ${S.binds["sound:" + s.file] ? `<span class="key user">${fmtCombo(S.binds["sound:" + s.file])}</span>` : ""}
      <span class="hkbtn" data-hk="sound:${s.file}" title="Asignar atajo">⌨</span>
      <span class="emo">${s.img ? "" : s.emoji}</span><b>${s.name}</b>
      <span class="del" data-del="${s.file}" title="Eliminar"><svg><use href="#i-trash"/></svg></span></button>`;
  }).join("") + `<button class="pad add" id="padAdd"><svg style="width:28px;height:28px"><use href="#i-plus"/></svg><b>Añadir sonido</b></button>`;
  $("#nSounds").textContent = S.sounds.length;
}

// ---------- atajos (los pone el usuario) ----------
function fmtCombo(c) {
  return c.split("+").map((k) => k.trim().replace(/^\w/, (m) => m.toUpperCase())).join(" + ");
}
function kbdCombo(c) {
  return c.split("+").map((k) => `<kbd>${k.trim().replace(/^\w/, (m) => m.toUpperCase())}</kbd>`).join("");
}
function hkLabel(target) {
  const [kind, ...rest] = target.split(":"); const arg = rest.join(":");
  if (kind === "voice") return "🎭 Voz: " + arg;
  if (kind === "sound") return "🔊 Sonido: " + arg.replace(/\.wav$/i, "");
  return (S.actions.find((a) => a.id === arg) || { label: arg }).label;
}
function hkRow(target) {
  const c = S.binds[target];
  return `<div class="hk-row"><span class="lbl">${hkLabel(target)}</span>
    ${c ? `<span>${kbdCombo(c)}</span>` : `<span class="none">Sin asignar</span>`}
    <button class="btn" data-hkset="${target}">${c ? "Cambiar" : "Asignar"}</button>
    ${c ? `<button class="btn danger" data-hkclear="${target}">Quitar</button>` : ""}</div>`;
}
function renderHotkeys() {
  if (!S.hkAvailable) {
    $("#hkActions").innerHTML = `<div class="alert">Falta la librería «keyboard»: ejecuta <b>pip install keyboard</b> para usar atajos.</div>`;
    return;
  }
  $("#hkActions").innerHTML = S.actions.map((a) => hkRow("action:" + a.id)).join("");
  const others = Object.keys(S.binds).filter((k) => !k.startsWith("action:"));
  $("#hkOthers").innerHTML = others.length ? others.map(hkRow).join("") : `<div class="hk-empty">Ninguno. Pulsa ⌨ en una voz o en un sonido para asignarle una tecla.</div>`;
}
function refreshBinds(b) {
  S.binds = b; renderHotkeys(); renderVoices(); renderSounds();
}
async function assignHotkey(target) {
  if (!S.hkAvailable) return toast("Instala la librería keyboard para usar atajos", true);
  $("#hkFor").textContent = "Para: " + hkLabel(target);
  $("#hkModal").classList.add("show");
  let combo = null;
  try { combo = await api.capture_hotkey(); } finally { $("#hkModal").classList.remove("show"); }
  if (!combo) return toast("Cancelado");
  refreshBinds(await api.set_hotkey(target, combo));
  toast("Atajo " + fmtCombo(combo) + " → " + hkLabel(target));
}

// ---------- dispositivos ----------
function fill(sel, items, value) {
  sel.innerHTML = items.map((d) => `<option ${d.name === value ? "selected" : ""}>${d.name}</option>`).join("");
}
function renderDevices(d) {
  fill($("#selIn"), d.inputs, d.sel_in);
  fill($("#selOut"), d.outputs, d.sel_out);
  fill($("#selMon"), d.monitors, d.sel_mon);
  $("#cableAlert").innerHTML = d.has_cable
    ? `<div class="alert ok">✔ Cable virtual detectado. Ya puedes usar tu voz en Discord, juegos y OBS.</div>`
    : `<div class="alert">⚠ No se ha encontrado ningún cable virtual. Instala VB-Cable (gratis) para enviar tu voz a otras apps. Mientras tanto puedes probar las voces con «Escucharme».</div>`;
}

// ---------- motor ----------
async function power() {
  if (S.running) { await api.stop(); toast("Motor detenido"); return; }
  const r = await api.start($("#selApi").value, $("#selIn").value, $("#selOut").value, $("#selMon").value);
  if (r.ok) toast("¡En marcha! Tu voz sale por " + $("#selOut").value);
  else { toast("No se pudo abrir el audio: " + r.error, true); go("settings"); }
}
function setToggles(t) {
  $("#tEnabled").classList.toggle("on", t.enabled);
  $("#tMonitor").classList.toggle("on", t.monitor);
  $("#tMute").classList.toggle("on", t.muted);
  $("#sfxMic").checked = t.sfx_to_mic;
}

// ---------- visualizador y bucle de estado ----------
const BARS = 32;
$("#viz").innerHTML = "<i></i>".repeat(BARS);
const vizBars = $$("#viz i");
let polling = false;
async function poll() {
  if (polling) return;
  polling = true;
  try {
    const st = await api.state();
    if (st.running !== S.running) {
      S.running = st.running;
      $("#power").classList.toggle("on", st.running);
      $("#powerLbl").textContent = st.running ? "DETENER" : "INICIAR";
      $("#engDot").classList.toggle("on", st.running);
      $("#engTxt").textContent = st.running ? "Motor activo · 48 kHz" : "Motor detenido";
    }
    $("#mIn").style.width = st.inp * 100 + "%";
    $("#mOut").style.width = st.out * 100 + "%";
    st.spec.forEach((v, i) => (vizBars[i].style.height = 4 + v * 104 + "px"));
    setToggles(st.toggles);
    if (st.current !== S.current) { S.current = st.current; const r = await api.voice(st.current); S.params = r.params; showCurrent(); syncSliders(); }
    $("#tTest").classList.toggle("rec", st.test === "grabando");
    $("#testLbl").textContent = st.test === "grabando" ? "Grabando…" : st.test === "reproduciendo" ? "Reproduciendo" : "Probar voz";
    if (st.notice) toast(st.notice);
  } finally { polling = false; }
}

// ---------- eventos ----------
function bind() {
  $("#nav").onclick = (e) => { const b = e.target.closest("button"); if (b) go(b.dataset.page); };
  $("#cats").onclick = (e) => { const b = e.target.closest(".chip"); if (b) { S.cat = b.dataset.cat; renderCats(); renderVoices(); } };
  $("#search").oninput = renderVoices;
  $("#voiceGrid").onclick = async (e) => {
    const h = e.target.closest("[data-hk]");
    if (h) { e.stopPropagation(); return assignHotkey(h.dataset.hk); }
    const f = e.target.closest("[data-fav]");
    if (f) {
      const n = f.dataset.fav;
      S.favs = S.favs.includes(n) ? S.favs.filter((x) => x !== n) : [...S.favs, n];
      api.set_favs(S.favs); renderVoices(); return;
    }
    const c = e.target.closest(".card");
    if (c) selectVoice(c.dataset.voice);
  };
  $("#heroEdit").onclick = () => go("lab");
  $("#heroRandom").onclick = async () => { const r = await api.random_voice(); S.current = r.current; S.params = r.params; showCurrent(); syncSliders(); toast("🎲 " + r.current); };

  $("#modules").oninput = (e) => {
    const el = e.target; if (!el.dataset.k) return;
    const k = el.dataset.k, v = +el.value;
    S.params[k] = v; $("#o-" + k).textContent = FMT[k](+v.toFixed(2)); paintRange(el);
    api.param(k, v);
  };
  $("#modules").onclick = (e) => {
    const b = e.target.closest("[data-reset]"); if (!b) return;
    MODULES.find((m) => m.id === b.dataset.reset).keys.forEach(([k]) => { S.params[k] = S.defaults[k]; api.param(k, S.defaults[k]); });
    syncSliders();
  };
  $("#labReset").onclick = () => selectVoice(S.current, true).then(() => toast("Ajustes restaurados"));
  $("#labSave").onclick = () => { $("#modal").classList.add("show"); $("#modalInput").value = ""; setTimeout(() => $("#modalInput").focus(), 50); };
  $("#modalCancel").onclick = () => $("#modal").classList.remove("show");
  const doSave = async () => {
    const n = $("#modalInput").value.trim(); if (!n) return;
    const r = await api.save_custom(n);
    $("#modal").classList.remove("show");
    S.voices = r.voices; S.current = r.current; S.params = r.params;
    renderVoices(); showCurrent(); toast("Voz guardada: " + n);
  };
  $("#modalOk").onclick = doSave;
  $("#modalInput").onkeydown = (e) => { if (e.key === "Enter") doSave(); if (e.key === "Escape") $("#modalCancel").click(); };
  $("#labDelete").onclick = async () => {
    const r = await api.delete_custom(S.current);
    S.voices = r.voices; S.current = r.current; S.params = r.params;
    renderVoices(); showCurrent(); syncSliders(); toast("Voz eliminada");
  };

  $("#soundGrid").onclick = async (e) => {
    const h = e.target.closest("[data-hk]");
    if (h) { e.stopPropagation(); return assignHotkey(h.dataset.hk); }
    const d = e.target.closest("[data-del]");
    if (d) { e.stopPropagation(); S.sounds = await api.delete_sound(d.dataset.del); renderSounds(); return; }
    if (e.target.closest("#padAdd")) return $("#sbAdd").click();
    const p = e.target.closest(".pad"); if (!p) return;
    p.classList.add("hit"); setTimeout(() => p.classList.remove("hit"), 120);
    const r = await api.play(p.dataset.sound);
    if (!r.ok) toast(r.error, true);
  };
  $("#sbAdd").onclick = async () => { S.sounds = await api.add_sounds(); renderSounds(); };
  $("#sbFolder").onclick = () => api.open_folder();
  $("#sbStop").onclick = () => api.stop_sounds();
  $("#sfxVol").oninput = (e) => { $("#sfxVolOut").textContent = pct(+e.target.value); paintRange(e.target); api.sfx_volume(+e.target.value); };
  $("#sfxMic").onchange = (e) => api.toggle("sfx_to_mic", e.target.checked);

  $("#selApi").onchange = async () => renderDevices(await api.devices($("#selApi").value));
  $("#applyDevices").onclick = async () => { if (S.running) await api.stop(); S.running = true; power(); };
  $$(".link[data-url]").forEach((l) => (l.onclick = () => api.open_url(l.dataset.url)));

  $("#power").onclick = power;
  $("#page-settings").addEventListener("click", async (e) => {
    const set = e.target.closest("[data-hkset]"), clr = e.target.closest("[data-hkclear]");
    if (set) assignHotkey(set.dataset.hkset);
    if (clr) { refreshBinds(await api.clear_hotkey(clr.dataset.hkclear)); toast("Atajo quitado"); }
  });
  $("#tEnabled").onclick = async () => setToggles((await api.toggle("enabled", !$("#tEnabled").classList.contains("on"))).toggles);
  $("#tMute").onclick = async () => setToggles((await api.toggle("muted", !$("#tMute").classList.contains("on"))).toggles);
  $("#tMonitor").onclick = async () => {
    const r = await api.toggle("monitor", !$("#tMonitor").classList.contains("on"));
    if (!r.ok) toast(r.error, true); else setToggles(r.toggles);
  };
  $("#tTest").onclick = async () => {
    const r = await api.test_voice(4);
    toast(r.ok ? "🎙 Habla durante 4 segundos… luego te lo reproduzco con la voz actual" : r.error, !r.ok);
  };
}

// ---------- arranque ----------
async function boot() {
  const d = await api.init();
  Object.assign(S, d);
  S.categories = d.categories;
  S.binds = d.binds || {};
  const hk = await api.hotkeys();
  S.actions = hk.actions; S.hkAvailable = hk.available;
  fill($("#selApi"), d.apis.map((n) => ({ name: n })), d.api);
  renderDevices(d.devices);
  renderCats(); renderVoices(); renderModules(); syncSliders(); renderSounds(); showCurrent(); renderHotkeys();
  setToggles(d.toggles);
  $("#sfxVol").value = d.sfx_volume; $("#sfxVolOut").textContent = pct(d.sfx_volume); paintRange($("#sfxVol"));
  bind();
  setInterval(poll, 45);
  setTimeout(() => $("#splash").classList.add("hide"), 350);
}

window.addEventListener("pywebviewready", () => { api = window.pywebview.api; boot(); });
// Vista previa en navegador sin Python: datos de ejemplo
setTimeout(() => { if (!api && window.MockApi) { api = window.MockApi; boot(); } }, 800);
