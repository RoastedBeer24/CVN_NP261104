/* 블루 아워 — 비주얼 노벨 엔진 */
(function () {
  "use strict";

  const S = window.SCENARIO;
  const META = S.meta;
  const CMDS = S.cmds;
  const LABELS = S.labels;
  const KEY = "bluehour_";
  const SLOT_PAGES = 4, SLOTS_PER_PAGE = 8;

  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));
  const el = (tag, cls, html) => { const e = document.createElement(tag); if (cls) e.className = cls; if (html != null) e.innerHTML = html; return e; };
  const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

  /* ───────── 저장소 ───────── */
  const store = {
    get(k, d) { try { const v = localStorage.getItem(KEY + k); return v == null ? d : JSON.parse(v); } catch (e) { return d; } },
    set(k, v) { try { localStorage.setItem(KEY + k, JSON.stringify(v)); return true; } catch (e) { return false; } },
    del(k) { try { localStorage.removeItem(KEY + k); } catch (e) { /* noop */ } },
  };

  const DEFAULT_SETTINGS = { textSpeed: 45, autoWait: 1.5, bgmVol: 0.6, seVol: 0.8, fontSize: "m", boxAlpha: 0.78, skipUnread: false, adult: true };
  const G = Object.assign({ endings: {}, cgs: {}, read: "", agreed: false, lastName: null }, store.get("global", {}));
  G.settings = Object.assign({}, DEFAULT_SETTINGS, G.settings || {});

  // 읽음 표시 비트셋
  const readBits = new Uint8Array(Math.ceil(CMDS.length / 8) + 1);
  try { const bin = atob(G.read || ""); for (let i = 0; i < bin.length && i < readBits.length; i++) readBits[i] = bin.charCodeAt(i); } catch (e) { /* noop */ }
  const isRead = (i) => (readBits[i >> 3] >> (i & 7)) & 1;
  const markRead = (i) => { readBits[i >> 3] |= 1 << (i & 7); };
  let saveGlobalTimer = null;
  function saveGlobal(now) {
    clearTimeout(saveGlobalTimer);
    const doit = () => {
      let bin = ""; for (let i = 0; i < readBits.length; i++) bin += String.fromCharCode(readBits[i]);
      G.read = btoa(bin);
      store.set("global", G);
    };
    if (now) doit(); else saveGlobalTimer = setTimeout(doit, 800);
  }

  /* ───────── 상태 ───────── */
  let st = null;          // 게임 상태 (저장 대상)
  let mode = "title";     // title | game
  let waiting = null;     // 현재 대기 중인 것: 'say' | 'choice' | 'wait' | 'card' | 'ending'
  let typing = null;      // 타이핑 진행 정보
  let auto = false, skip = false;
  let timer = null;
  let backlog = [];
  let phoneBubbles = [];

  function freshState(name) {
    return { ptr: 0, vars: {}, bg: null, cg: null, sprites: {}, bgm: null, chapter: "", time: "", msg: false, dark: false, blur: false, name };
  }

  /* ───────── 텍스트 치환 ───────── */
  function fmt(s) {
    const n = st ? st.name : META.defaultName;
    return String(s).replace(/\{name\}/g, n.given).replace(/\{family\}/g, n.family);
  }

  /* ───────── 조건식 ───────── */
  const condCache = {};
  function evalCond(expr) {
    let fn = condCache[expr];
    if (!fn) {
      try { fn = condCache[expr] = compileCond(expr); } catch (e) { console.warn("조건식 오류", expr, e); return false; }
    }
    return !!fn(Object.assign({ truecount: trueCount() }, st.vars));
  }
  // eval 없이 동작하는 조건식 파서 (CSP 대응)
  // 문법: or := and ('||' and)* / and := not ('&&' not)* / not := '!' not | cmp
  //       cmp := add (op add)? / add := atom (('+'|'-') atom)* / atom := 숫자 | 변수 | '(' or ')'
  function compileCond(expr) {
    const toks = expr.match(/\s*(>=|<=|==|!=|&&|\|\||[<>!()+\-]|\d+|[A-Za-z_][A-Za-z0-9_]*)/g).map((t) => t.trim());
    if (toks.join("") !== expr.replace(/\s+/g, "")) throw new Error("알 수 없는 문자");
    let i = 0;
    const peek = () => toks[i];
    const eat = (t) => { if (toks[i] !== t) throw new Error("기대: " + t); i++; };
    function parseOr() { let a = parseAnd(); while (peek() === "||") { i++; const l = a, r = parseAnd(); a = (v) => l(v) || r(v); } return a; }
    function parseAnd() { let a = parseNot(); while (peek() === "&&") { i++; const l = a, r = parseNot(); a = (v) => l(v) && r(v); } return a; }
    function parseNot() { if (peek() === "!") { i++; const x = parseNot(); return (v) => !x(v); } return parseCmp(); }
    function parseCmp() {
      const l = parseAdd(); const op = peek();
      if ([">=", "<=", "==", "!=", ">", "<"].includes(op)) {
        i++; const r = parseAdd();
        return { ">=": (v) => l(v) >= r(v), "<=": (v) => l(v) <= r(v), "==": (v) => l(v) === r(v), "!=": (v) => l(v) !== r(v), ">": (v) => l(v) > r(v), "<": (v) => l(v) < r(v) }[op];
      }
      return l;
    }
    function parseAdd() { let a = parseAtom(); while (peek() === "+" || peek() === "-") { const op = toks[i++]; const l = a, r = parseAtom(); a = op === "+" ? (v) => l(v) + r(v) : (v) => l(v) - r(v); } return a; }
    function parseAtom() {
      const t = toks[i++];
      if (t === "(") { const x = parseOr(); eat(")"); return x; }
      if (t === "-") { const x = parseAtom(); return (v) => -x(v); }
      if (/^\d+$/.test(t)) { const n = +t; return () => n; }
      if (/^[A-Za-z_]/.test(t)) return (v) => +(v[t] || 0);
      throw new Error("예상치 못한 토큰: " + t);
    }
    const f = parseOr();
    if (i !== toks.length) throw new Error("남은 토큰");
    return f;
  }
  function applySet(ops) {
    (ops || []).forEach(([k, op, n]) => {
      const cur = st.vars[k] || 0;
      st.vars[k] = op === "+" ? cur + n : op === "-" ? cur - n : n;
    });
  }
  function trueCount() { return (META.hiddenRequires || []).filter((id) => G.endings[id]).length; }

  /* ───────── 이미지 로딩 (없으면 자리표시자) ───────── */
  const imgCache = {};
  function resolveImg(dir, id) {
    const key = dir + "/" + id;
    if (imgCache[key]) return imgCache[key];
    const exts = ["png", "webp", "jpg", "jpeg"];
    imgCache[key] = new Promise((resolve) => {
      let i = 0;
      const tryNext = () => {
        if (i >= exts.length) return resolve(null);
        const url = `assets/${dir}/${id}.${exts[i++]}`;
        const im = new Image();
        im.onload = () => resolve(url);
        im.onerror = tryNext;
        im.src = url;
      };
      tryNext();
    });
    return imgCache[key];
  }
  function hashHue(s) { let h = 0; for (const c of s) h = (h * 31 + c.charCodeAt(0)) % 360; return h; }
  function placeholderBg(id) {
    const b = META.bgs[id];
    const [a, c] = b ? b.colors : [`hsl(${hashHue(id)},30%,22%)`, `hsl(${(hashHue(id) + 40) % 360},30%,55%)`];
    return `linear-gradient(170deg, ${a} 0%, ${c} 100%)`;
  }

  /* ───────── 배경 ───────── */
  function setBg(id, tr) {
    const host = $("#bg");
    const layer = el("div", "bglayer ph-grain" + (tr === "cut" ? " cut" : ""));
    layer.style.backgroundImage = placeholderBg(id);
    if (id !== "black" && id !== "white") {
      const lab = el("div", "ph-label", "배경 · " + esc(id) + (META.bgs[id] ? " — " + esc(META.bgs[id].desc) : ""));
      layer.appendChild(lab);
    }
    host.appendChild(layer);
    resolveImg("bg", id).then((url) => {
      if (url) { layer.style.backgroundImage = `url("${url}")`; layer.classList.remove("ph-grain"); layer.innerHTML = ""; }
    });
    const old = $$(".bglayer", host).filter((l) => l !== layer);
    requestAnimationFrame(() => requestAnimationFrame(() => layer.classList.add("on")));
    setTimeout(() => old.forEach((o) => o.remove()), tr === "cut" ? 30 : 1000);
  }

  /* ───────── 캐릭터 ───────── */
  const POS = { left: 20, left2: 35, center: 50, right2: 65, right: 80 };
  function silhouette(ch, ex) {
    const c = META.characters[ch] || { name: ch, color: "#888" };
    const div = el("div", "ph");
    div.innerHTML = `<svg viewBox="0 0 200 500" preserveAspectRatio="xMidYMax meet"><defs><linearGradient id="g_${ch}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="${c.color}" stop-opacity=".95"/><stop offset="1" stop-color="${c.color}" stop-opacity=".55"/></linearGradient></defs>
      <ellipse cx="100" cy="92" rx="44" ry="52" fill="url(#g_${ch})"/>
      <path d="M100 150 C60 150 40 175 32 230 L18 500 L182 500 L168 230 C160 175 140 150 100 150Z" fill="url(#g_${ch})"/></svg>
      <div class="tag">${esc(c.name)} · ${esc(ex)}</div>`;
    return div;
  }
  function renderSprite(node, ch, ex) {
    node.dataset.ex = ex;
    node.innerHTML = "";
    node.appendChild(silhouette(ch, ex));
    const want = ex;
    resolveImg("ch", `${ch}_${ex}`).then((url) => url || resolveImg("ch", `${ch}_normal`)).then((url) => {
      if (!url || node.dataset.ex !== want) return;
      node.innerHTML = ""; const im = new Image(); im.src = url; im.alt = ""; node.appendChild(im);
    });
  }
  function showChar(ch, ex, pos, instant) {
    let node = $(`.sprite[data-ch="${ch}"]`);
    const fresh = !node;
    if (fresh) { node = el("div", "sprite"); node.dataset.ch = ch; $("#sprites").appendChild(node); }
    node.style.left = POS[pos || "center"] + "%";
    if (node.dataset.ex !== ex) renderSprite(node, ch, ex);
    if (fresh && !instant) requestAnimationFrame(() => requestAnimationFrame(() => node.classList.add("on")));
    else node.classList.add("on");
    st.sprites[ch] = { ex, pos: pos || "center" };
  }
  function hideChar(ch) {
    const targets = ch === "all" ? $$(".sprite") : $$(`.sprite[data-ch="${ch}"]`);
    targets.forEach((n) => { n.classList.remove("on"); n.dataset.dead = "1"; setTimeout(() => n.dataset.dead && n.remove(), 450); });
    if (ch === "all") st.sprites = {}; else delete st.sprites[ch];
  }
  function focusSpeaker(ch) {
    $$(".sprite").forEach((n) => n.classList.toggle("dim", !!ch && n.dataset.ch !== ch && Object.keys(st.sprites).length > 1));
  }

  /* ───────── CG ───────── */
  function setCg(id) {
    const cg = $("#cg");
    if (!id) { cg.classList.remove("on"); st.cg = null; return; }
    st.cg = id;
    cg.style.backgroundImage = `linear-gradient(160deg, #1b2747, #6d5a7a)`;
    cg.innerHTML = `<div class="ph-label">이벤트 CG · ${esc(id)}</div>`;
    resolveImg("cg", id).then((url) => { if (url && st.cg === id) { cg.style.backgroundImage = `url("${url}")`; cg.innerHTML = ""; } });
    cg.classList.add("on");
    if (!G.cgs[id]) { G.cgs[id] = 1; saveGlobal(); }
  }

  /* ───────── 사운드 ───────── */
  const bgmEl = new Audio(); bgmEl.loop = true;
  let bgmId = null;
  function playBgm(id) {
    if (id === "stop" || !id) { bgmEl.pause(); bgmId = null; if (st) st.bgm = null; return; }
    if (st && mode === "game") st.bgm = id;
    if (bgmId === id) return;
    bgmId = id;
    const exts = ["mp3", "ogg", "m4a"]; let i = 0;
    const tryNext = () => {
      if (i >= exts.length || bgmId !== id) return;
      bgmEl.src = `assets/bgm/${id}.${exts[i++]}`;
      bgmEl.volume = G.settings.bgmVol;
      bgmEl.play().catch(() => { /* 파일 없음 또는 자동재생 차단 */ });
    };
    bgmEl.onerror = tryNext;
    tryNext();
  }
  function playSe(id) {
    if (skip) return;
    const a = new Audio(); const exts = ["mp3", "ogg", "wav"]; let i = 0;
    a.volume = G.settings.seVol;
    a.onerror = () => { if (i < exts.length) { a.src = `assets/se/${id}.${exts[i++]}`; a.play().catch(() => {}); } };
    a.src = `assets/se/${id}.${exts[i++]}`; a.play().catch(() => {});
  }

  /* ───────── 효과 ───────── */
  function effect(id) {
    const stage = $("#stage");
    if (id === "shake") { stage.classList.remove("shake"); void stage.offsetWidth; stage.classList.add("shake"); }
    if (id === "flash") { const f = $("#flash"); f.classList.remove("go"); void f.offsetWidth; f.classList.add("go"); }
    if (id === "dark") { st.dark = true; $("#fx").classList.add("on"); }
    if (id === "light") { st.dark = false; $("#fx").classList.remove("on"); }
    if (id === "blur") { st.blur = true; $("#bg").classList.add("blur"); }
    if (id === "unblur") { st.blur = false; $("#bg").classList.remove("blur"); }
  }
  function setTimeCap(t) {
    st.time = t;
    const tc = $("#timecap");
    tc.textContent = t; tc.classList.toggle("on", !!t);
  }
  function setMsg(on) {
    st.msg = on;
    $("#phone").classList.toggle("hidden", !on);
    if (!on) { phoneBubbles = []; $(".phone-body").innerHTML = ""; }
  }

  /* ───────── 메인 루프 ───────── */
  function clearTimer() { if (timer) { clearTimeout(timer); timer = null; } }

  function run() {
    clearTimer();
    waiting = null;
    let guard = 0;
    while (mode === "game") {
      if (++guard > 5000) { console.error("무한 루프 의심", st.ptr); return; }
      const c = CMDS[st.ptr];
      if (!c) { toTitle(); return; }
      const idx = st.ptr;
      switch (c.t) {
        case "say": return doSay(c, idx);
        case "choice": return doChoice(c);
        case "chapter": st.chapter = c.text; st.ptr++; return doCard(c.text);
        case "time": setTimeCap(c.text); break;
        case "bg": setBg(c.id, skip ? "cut" : c.tr); st.bg = c.id; hideChar("all"); break;
        case "show": showChar(c.ch, c.ex, c.pos, skip); break;
        case "hide": hideChar(c.ch); break;
        case "cg": setCg(c.id); break;
        case "cgoff": setCg(null); break;
        case "bgm": playBgm(c.id); break;
        case "se": playSe(c.id); break;
        case "effect": effect(c.id); break;
        case "msg": setMsg(c.on); break;
        case "set": applySet(c.ops); break;
        case "wait":
          st.ptr++;
          if (skip) continue;
          waiting = "wait";
          timer = setTimeout(run, c.sec * 1000);
          return;
        case "if": if (evalCond(c.cond)) { jump(c.to); continue; } break;
        case "jump": jump(c.to); continue;
        case "route": {
          let best = null, bestV = -Infinity;
          for (const [k, lab] of Object.entries(c.map)) {
            const v = st.vars[k] || 0;
            if (v > bestV) { best = lab; bestV = v; }
          }
          jump(best && bestV >= c.min ? best : c.else);
          continue;
        }
        case "adult":
          if (!G.settings.adult) { st.ptr = c.end; continue; }
          break;
        case "adultend": break;
        case "ending": return doEnding(c.id);
        case "title": toTitle(); return;
        default: break;
      }
      st.ptr++;
    }
  }
  function jump(label) {
    if (!(label in LABELS)) { console.error("라벨 없음", label); toTitle(); return; }
    st.ptr = LABELS[label];
  }
  function next() {
    if (waiting !== "say") return;
    markRead(st.ptr); saveGlobal();
    st.ptr++;
    run();
  }

  /* ───────── 대사 ───────── */
  function speakerName(c) {
    if (!c.who) return "";
    if (c.who === "나") return st.name.given;
    return fmt(c.who);
  }
  function doSay(c, idx) {
    waiting = "say";
    const name = speakerName(c);
    const text = fmt(c.text);
    if (c.ch && c.ex && st.sprites[c.ch]) showChar(c.ch, c.ex, st.sprites[c.ch].pos, true);
    focusSpeaker(c.ch);
    backlog.push({ who: name, text });
    if (backlog.length > 400) backlog.shift();

    const read = isRead(idx);
    if (skip && !read && !G.settings.skipUnread) setSkip(false);

    if (st.msg && c.who) {
      // 메시지 모드 말풍선
      const me = c.who === "나";
      const b = el("div", "bubble " + (me ? "me" : "them"), (me ? "" : `<span class="who">${esc(name)}</span>`) + esc(text));
      const body = $(".phone-body");
      body.appendChild(b);
      phoneBubbles.push(b);
      while (body.children.length > 7) body.removeChild(body.firstChild);
      $("#textbox").classList.add("empty");
      typing = null;
      afterText(text.length);
      return;
    }
    $("#textbox").classList.remove("empty");
    const nb = $("#namebox");
    nb.textContent = name;
    const chColor = c.ch ? META.characters[c.ch].color : (c.who === "나" ? "#8fb0e3" : "#9aa6b8");
    nb.style.setProperty("--name-color", chColor);
    const tx = $("#text");
    tx.classList.toggle("narration", !c.who);
    $("#indicator").classList.remove("on");
    typeText(tx, text);
  }
  function typeText(node, text) {
    const speed = G.settings.textSpeed;
    if (skip || speed >= 130) { node.textContent = text; typing = null; afterText(text.length); return; }
    let i = 0;
    node.textContent = "";
    const step = 1000 / speed;
    typing = { node, text, finish() { clearTimer(); node.textContent = text; typing = null; afterText(text.length); } };
    const tick = () => {
      i += 1;
      node.textContent = text.slice(0, i);
      if (i >= text.length) { typing = null; afterText(text.length); return; }
      timer = setTimeout(tick, step);
    };
    timer = setTimeout(tick, step);
  }
  function afterText(len) {
    $("#indicator").classList.add("on");
    if (skip) { timer = setTimeout(next, 35); return; }
    if (auto) timer = setTimeout(next, G.settings.autoWait * 1000 + len * 45);
  }
  function advance() {
    if (mode !== "game") return;
    if (anyOverlay()) return;
    if ($("#stage").classList.contains("uihidden")) { $("#stage").classList.remove("uihidden"); return; }
    if (skip) { setSkip(false); return; }
    if (waiting === "card") { finishCard(); return; }
    if (typing) { typing.finish(); return; }
    if (waiting === "say") { clearTimer(); next(); }
  }

  /* ───────── 선택지 ───────── */
  function doChoice(c) {
    waiting = "choice";
    setSkip(false); setAuto(false);
    focusSpeaker(null);
    autoSave();
    const box = $("#choices");
    box.innerHTML = "";
    const opts = c.opts.filter((o) => !o.cond || evalCond(o.cond));
    opts.forEach((o, n) => {
      const b = el("button", null, esc(fmt(o.text)));
      b.style.animationDelay = n * 0.06 + "s";
      b.onclick = (e) => {
        e.stopPropagation();
        box.classList.add("hidden");
        backlog.push({ who: "", text: "▶ " + fmt(o.text), choice: true });
        applySet(o.set);
        if (o.to) jump(o.to); else st.ptr++;
        run();
      };
      box.appendChild(b);
    });
    box.classList.remove("hidden");
  }

  /* ───────── 장 카드 ───────── */
  function doCard(text) {
    waiting = "card";
    autoSave();
    const card = $("#chaptercard");
    $(".cc-text", card).textContent = text;
    card.classList.remove("hidden");
    timer = setTimeout(finishCard, skip ? 300 : 2400);
  }
  function finishCard() {
    clearTimer();
    $("#chaptercard").classList.add("hidden");
    run();
  }

  /* ───────── 엔딩 ───────── */
  function doEnding(id) {
    waiting = "ending";
    setSkip(false); setAuto(false);
    const e = META.endings.find((x) => x.id === id) || { kind: "", no: 0, title: id };
    const first = !G.endings[id];
    G.endings[id] = Date.now();
    saveGlobal(true);
    const card = $("#endcard");
    const k = $(".ec-kind", card); k.textContent = e.kind + " END"; k.className = "ec-kind " + e.kind;
    $(".ec-no", card).textContent = "ENDING " + String(e.no).padStart(2, "0") + (first ? " · NEW" : "");
    $(".ec-title", card).textContent = e.title;
    card.classList.remove("hidden");
    card.onclick = () => { card.classList.add("hidden"); toTitle(); };
  }

  /* ───────── 자동 / 스킵 ───────── */
  function setAuto(on) {
    auto = on;
    $('#quickmenu [data-act="auto"]').classList.toggle("active", on);
    updateModeFlag();
    if (on && waiting === "say" && !typing) { clearTimer(); timer = setTimeout(next, 500); }
  }
  function setSkip(on) {
    skip = on;
    $('#quickmenu [data-act="skip"]').classList.toggle("active", on);
    updateModeFlag();
    if (on) {
      if (waiting === "say") { if (typing) typing.finish(); else { clearTimer(); timer = setTimeout(next, 35); } }
      if (waiting === "card") finishCard();
    }
  }
  function updateModeFlag() { $("#modeflag").textContent = skip ? "SKIP ▶▶" : auto ? "AUTO ▶" : ""; }

  /* ───────── 세이브 / 로드 ───────── */
  function snapshot() {
    const last = backlog.slice(-1)[0];
    return {
      st: JSON.parse(JSON.stringify(st)),
      date: Date.now(),
      chapter: st.chapter,
      preview: last ? (last.who ? last.who + ": " : "") + last.text : "",
      bg: st.bg,
    };
  }
  function saveSlot(key) { const ok = store.set("save_" + key, snapshot()); toast(ok ? "저장했습니다" : "저장 실패 (저장 공간 부족)"); }
  function autoSave() { if (mode === "game" && st) store.set("save_auto", snapshot()); }
  function loadSlot(key) {
    const d = store.get("save_" + key, null);
    if (!d) { toast("저장된 데이터가 없습니다"); return false; }
    startFromState(d.st);
    return true;
  }
  function startFromState(s) {
    closeAll();
    st = Object.assign(freshState(s.name), s);
    mode = "game";
    setSkip(false); setAuto(false);
    backlog = [];
    showScreen("game");
    // 화면 복원
    $("#bg").innerHTML = ""; $("#sprites").innerHTML = "";
    if (st.bg) setBg(st.bg, "cut");
    const spr = st.sprites; st.sprites = {};
    Object.entries(spr).forEach(([ch, v]) => showChar(ch, v.ex, v.pos, true));
    setCg(st.cg); if (st.cg) $("#cg").classList.add("on");
    $("#fx").classList.toggle("on", !!st.dark);
    $("#bg").classList.toggle("blur", !!st.blur);
    setTimeCap(st.time || "");
    setMsg(!!st.msg);
    playBgm(st.bgm || "stop");
    $("#choices").classList.add("hidden");
    $("#chaptercard").classList.add("hidden");
    run();
  }

  /* ───────── 화면 전환 ───────── */
  function showScreen(name) {
    $("#title").classList.toggle("hidden", name !== "title");
    $("#stage").classList.toggle("hidden", name !== "game");
  }
  const OVERLAYS = ["#nameinput", "#saveload", "#settings", "#backlog", "#endings", "#gallery", "#confirm", "#agegate"];
  function anyOverlay() { return OVERLAYS.some((s) => !$(s).classList.contains("hidden")) || !$("#endcard").classList.contains("hidden"); }
  function closeAll() { OVERLAYS.forEach((s) => $(s).classList.add("hidden")); }
  function open(sel) { $(sel).classList.remove("hidden"); }

  function toTitle() {
    clearTimer();
    mode = "title";
    waiting = null; typing = null;
    setSkip(false); setAuto(false);
    closeAll();
    $("#endcard").classList.add("hidden");
    $("#choices").classList.add("hidden");
    showScreen("title");
    playBgm("main");
    refreshTitle();
  }
  function refreshTitle() {
    $("#btn-continue").disabled = !store.get("save_auto", null);
    const unlocked = (META.hiddenRequires || []).every((id) => G.endings[id]);
    $("#btn-epilogue").classList.toggle("hidden", !unlocked);
  }

  function newGame(label) {
    const n = G.lastName || META.defaultName;
    $("#in-family").value = n.family; $("#in-given").value = n.given;
    open("#nameinput");
    $("#nameinput").dataset.label = label || "start";
  }
  function beginGame() {
    const family = $("#in-family").value.trim() || META.defaultName.family;
    const given = $("#in-given").value.trim() || META.defaultName.given;
    G.lastName = { family, given }; saveGlobal(true);
    const s = freshState({ family, given });
    s.ptr = LABELS[$("#nameinput").dataset.label] || 0;
    startFromState(s);
  }

  /* ───────── 세이브/로드 화면 ───────── */
  let slMode = "save", slPage = 0;
  function openSaveLoad(m) {
    slMode = m;
    $("#sl-title").textContent = m === "save" ? "저장" : "불러오기";
    renderSaveLoad();
    open("#saveload");
  }
  function fmtDate(t) { const d = new Date(t); const p = (n) => String(n).padStart(2, "0"); return `${d.getFullYear()}.${p(d.getMonth() + 1)}.${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`; }
  function renderSaveLoad() {
    const tabs = $("#sl-tabs"); tabs.innerHTML = "";
    const pages = slMode === "load" ? ["자동/퀵", ...Array.from({ length: SLOT_PAGES }, (_, i) => `${i + 1}`)] : Array.from({ length: SLOT_PAGES }, (_, i) => `${i + 1}`);
    const offset = slMode === "load" ? 1 : 0;
    if (slMode === "save" && slPage < 1) slPage = 1;
    pages.forEach((p, i) => {
      const pageNo = i + (slMode === "load" ? 0 : 1);
      const b = el("button", pageNo === slPage ? "on" : "", p);
      b.onclick = () => { slPage = pageNo; renderSaveLoad(); };
      tabs.appendChild(b);
    });
    void offset;
    const grid = $("#sl-grid"); grid.innerHTML = "";
    const keys = slPage === 0 ? ["auto", "quick"] : Array.from({ length: SLOTS_PER_PAGE }, (_, i) => String((slPage - 1) * SLOTS_PER_PAGE + i + 1));
    keys.forEach((k) => {
      const d = store.get("save_" + k, null);
      const label = k === "auto" ? "자동" : k === "quick" ? "퀵" : "No." + k;
      const b = el("button", "slot" + (d ? "" : " empty"));
      const thumb = el("div", "thumb", `<span>${label}</span>`);
      if (d && d.bg) {
        thumb.style.backgroundImage = placeholderBg(d.bg);
        resolveImg("bg", d.bg).then((u) => { if (u) thumb.style.backgroundImage = `url("${u}")`; });
      }
      b.appendChild(thumb);
      b.appendChild(el("div", "meta", d
        ? `<b>${esc(d.chapter || "프롤로그")}</b><small>${fmtDate(d.date)}</small><i>${esc(d.preview || "")}</i>`
        : `<b>비어 있음</b>`));
      b.onclick = () => {
        if (slMode === "save") {
          const doSave = () => { saveSlot(k); renderSaveLoad(); };
          if (d) confirmBox("이 슬롯에 덮어쓸까요?", doSave); else doSave();
        } else if (d) {
          const doLoad = () => loadSlot(k);
          if (mode === "game") confirmBox("불러올까요? 진행 중인 내용은 사라집니다.", doLoad); else doLoad();
        }
      };
      grid.appendChild(b);
    });
  }

  /* ───────── 백로그 ───────── */
  function openLog() {
    const list = $("#log-list"); list.innerHTML = "";
    backlog.forEach((l) => list.appendChild(el("div", "log" + (l.choice ? " choice" : ""), (l.who ? `<b>${esc(l.who)}</b>` : "") + esc(l.text))));
    open("#backlog");
    list.scrollTop = list.scrollHeight;
  }

  /* ───────── 엔딩 목록 ───────── */
  function openEndings() {
    const list = $("#end-list"); list.innerHTML = "";
    let n = 0;
    META.endings.forEach((e) => {
      const seen = !!G.endings[e.id]; if (seen) n++;
      const hide = !seen && e.secret;
      list.appendChild(el("div", "end" + (seen ? "" : " locked"),
        `<span class="no">${String(e.no).padStart(2, "0")}</span><span class="kind ${seen ? e.kind : ""}">${hide ? "???" : e.kind}</span><span class="tt">${seen ? esc(e.title) : hide ? "？？？" : "— 아직 보지 못한 엔딩 —"}</span>`));
    });
    $("#end-count").textContent = `${n} / ${META.endings.length}`;
    open("#endings");
  }

  /* ───────── 갤러리 ───────── */
  function openGallery() {
    const grid = $("#gal-grid"); grid.innerHTML = "";
    const all = S.assets.cg || [];
    let n = 0;
    all.forEach((id) => {
      const got = !!G.cgs[id]; if (got) n++;
      const g = el("div", "gal" + (got ? "" : " locked"), got ? `<span>${esc(id)}</span>` : "?");
      if (got) {
        g.style.backgroundImage = "linear-gradient(160deg, #1b2747, #6d5a7a)";
        resolveImg("cg", id).then((u) => { if (u) g.style.backgroundImage = `url("${u}")`; });
        g.onclick = () => {
          const v = $("#gal-view");
          v.style.backgroundImage = g.style.backgroundImage;
          v.classList.remove("hidden");
          v.onclick = () => v.classList.add("hidden");
        };
      }
      grid.appendChild(g);
    });
    $("#gal-count").textContent = `${n} / ${all.length}`;
    open("#gallery");
  }

  /* ───────── 설정 ───────── */
  function applySettings() {
    const s = G.settings;
    document.body.classList.remove("fs-s", "fs-m", "fs-l");
    document.body.classList.add("fs-" + s.fontSize);
    document.documentElement.style.setProperty("--box-alpha", s.boxAlpha);
    bgmEl.volume = s.bgmVol;
  }
  function openSettings() {
    const s = G.settings;
    const fmtVal = { textSpeed: (v) => (v >= 130 ? "즉시" : v), autoWait: (v) => v + "초", bgmVol: (v) => Math.round(v * 100), seVol: (v) => Math.round(v * 100), boxAlpha: (v) => Math.round(v * 100) + "%", fontSize: () => "" };
    ["textSpeed", "autoWait", "bgmVol", "seVol", "boxAlpha", "fontSize"].forEach((k) => {
      const inp = $("#set-" + k);
      inp.value = s[k];
      const out = inp.parentElement.querySelector(".val");
      const upd = () => { out.textContent = fmtVal[k](inp.value); };
      upd();
      inp.oninput = inp.onchange = () => {
        s[k] = k === "fontSize" ? inp.value : parseFloat(inp.value);
        upd(); applySettings(); saveGlobal();
      };
    });
    ["skipUnread", "adult"].forEach((k) => {
      const inp = $("#set-" + k);
      inp.checked = !!s[k];
      inp.onchange = () => { s[k] = inp.checked; saveGlobal(); };
    });
    open("#settings");
  }

  /* ───────── 확인창 / 토스트 ───────── */
  let confirmCb = null;
  function confirmBox(msg, cb) { $("#confirm-msg").textContent = msg; confirmCb = cb; open("#confirm"); }
  let toastT = null;
  function toast(msg) { const t = $("#toast"); t.textContent = msg; t.classList.add("on"); clearTimeout(toastT); toastT = setTimeout(() => t.classList.remove("on"), 1600); }

  /* ───────── 입력 ───────── */
  function onAct(act, e) {
    if (e) e.stopPropagation();
    switch (act) {
      case "new": newGame("start"); break;
      case "continue": loadSlot("auto"); break;
      case "load": slPage = 0; openSaveLoad("load"); break;
      case "save": slPage = 1; openSaveLoad("save"); break;
      case "endings": openEndings(); break;
      case "gallery": openGallery(); break;
      case "settings": openSettings(); break;
      case "epilogue": newGame("hidden_start"); break;
      case "start": beginGame(); break;
      case "auto": setSkip(false); setAuto(!auto); break;
      case "skip": setAuto(false); setSkip(!skip); break;
      case "log": openLog(); break;
      case "qsave": if (waiting === "choice" || waiting === "say") saveSlot("quick"); break;
      case "qload": if (store.get("save_quick", null)) confirmBox("퀵 세이브를 불러올까요?", () => loadSlot("quick")); else toast("퀵 세이브가 없습니다"); break;
      case "hideui": $("#stage").classList.add("uihidden"); break;
      case "title": confirmBox("타이틀로 돌아갈까요?", () => { autoSave(); toTitle(); }); break;
      case "reset": confirmBox("세이브, 엔딩, 갤러리 등 모든 데이터를 지울까요?", () => {
        try { Object.keys(localStorage).filter((k) => k.startsWith(KEY)).forEach((k) => localStorage.removeItem(k)); } catch (er) { /* noop */ }
        location.reload();
      }); break;
      case "adult-on": case "adult-off":
        G.settings.adult = act === "adult-on"; G.agreed = true; saveGlobal(true);
        $("#agegate").classList.add("hidden"); break;
      default: break;
    }
  }

  function bind() {
    $$("[data-act]").forEach((b) => b.addEventListener("click", (e) => {
      const act = b.dataset.act;
      if (act === "close") { e.stopPropagation(); b.closest(".screen").classList.add("hidden"); return; }
      if (act === "yes") { e.stopPropagation(); $("#confirm").classList.add("hidden"); const cb = confirmCb; confirmCb = null; cb && cb(); return; }
      if (act === "no") { e.stopPropagation(); $("#confirm").classList.add("hidden"); confirmCb = null; return; }
      onAct(act, e);
    }));
    // 오버레이 바깥 클릭으로 닫기
    $$(".overlay").forEach((o) => o.addEventListener("click", (e) => {
      if (e.target === o && o.id !== "agegate" && o.id !== "nameinput") o.classList.add("hidden");
    }));
    $("#stage").addEventListener("click", (e) => {
      if (e.target.closest("#quickmenu") || e.target.closest("#choices")) return;
      advance();
    });
    $("#stage").addEventListener("contextmenu", (e) => { e.preventDefault(); if (mode === "game" && !anyOverlay()) $("#stage").classList.toggle("uihidden"); });
    $("#stage").addEventListener("wheel", (e) => {
      if (mode !== "game" || anyOverlay()) return;
      if (e.deltaY < 0) openLog(); else advance();
    }, { passive: true });
    $("#in-given").addEventListener("keydown", (e) => { if (e.key === "Enter") beginGame(); });

    let ctrlSkip = false;
    document.addEventListener("keydown", (e) => {
      if (e.target.tagName === "INPUT") return;
      if (e.key === "Escape") {
        const openOv = OVERLAYS.find((s) => !$(s).classList.contains("hidden") && s !== "#agegate");
        if (openOv) { $(openOv).classList.add("hidden"); return; }
        if (!$("#gal-view").classList.contains("hidden")) { $("#gal-view").classList.add("hidden"); return; }
        if (mode === "game") openSettings();
        return;
      }
      if (mode !== "game" || anyOverlay()) return;
      if (e.key === "Enter" || e.key === " ") { e.preventDefault(); advance(); }
      else if (e.key === "Control" && !ctrlSkip) { ctrlSkip = true; setSkip(true); }
      else if (e.key === "a" || e.key === "A") setAuto(!auto);
      else if (e.key === "s" || e.key === "S") onAct("save");
      else if (e.key === "l" || e.key === "L") onAct("load");
      else if (e.key === "h" || e.key === "H") $("#stage").classList.toggle("uihidden");
      else if (e.key === "ArrowUp" || e.key === "PageUp") openLog();
    });
    document.addEventListener("keyup", (e) => { if (e.key === "Control" && ctrlSkip) { ctrlSkip = false; setSkip(false); } });
    window.addEventListener("beforeunload", () => { saveGlobal(true); autoSave(); });
    document.addEventListener("visibilitychange", () => { if (document.hidden) { saveGlobal(true); autoSave(); } });
    // 첫 터치 시 BGM 재생 시도 (자동재생 정책)
    document.addEventListener("pointerdown", () => { if (bgmId && bgmEl.paused) bgmEl.play().catch(() => {}); }, { once: true });
  }

  /* ───────── 시작 ───────── */
  function init() {
    document.title = META.title;
    applySettings();
    bind();
    toTitle();
    if (!G.agreed) open("#agegate");
  }
  // 디버그/테스트용
  window.BH = { get state() { return st; }, jump: (l) => { jump(l); run(); }, G, cmds: CMDS };
  init();
})();
