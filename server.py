import asyncio
import io

import edge_tts
from flask import Flask, Response, jsonify, request, send_file

app = Flask(__name__)

VOICES = {
    "piseth": "km-KH-PisethNeural",
    "sreymom": "km-KH-SreymomNeural",
}
MAX_CHARS = 10000

PAGE = r"""<!DOCTYPE html>
<html lang="km">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Khmer Voice Reader</title>
<link href="https://fonts.googleapis.com/css2?family=Kantumruy+Pro:wght@400;600;700&display=swap" rel="stylesheet">
<style>
  * { box-sizing: border-box; }
  body { font-family: 'Kantumruy Pro', sans-serif; background: #f3f5fa; margin: 0; padding: 16px; color: #1c2333; }
  .card { max-width: 640px; margin: 0 auto 16px; background: #fff; border-radius: 16px; padding: 20px; box-shadow: 0 4px 18px rgba(0,0,0,.08); }
  h1 { font-size: 22px; margin: 0 0 4px; }
  h2 { font-size: 18px; margin: 0 0 4px; }
  p.sub { margin: 0 0 16px; color: #5b6478; font-size: 14px; }
  textarea, input[type=text] { width: 100%; font: inherit; font-size: 16px; padding: 12px; border: 1px solid #cfd5e3; border-radius: 12px; }
  textarea { min-height: 180px; resize: vertical; }
  .count { text-align: right; font-size: 12px; color: #7a8399; margin-top: 4px; }
  .voices { display: flex; gap: 10px; margin: 14px 0; }
  .voices label { flex: 1; border: 2px solid #cfd5e3; border-radius: 12px; padding: 12px; text-align: center; cursor: pointer; font-weight: 600; }
  .voices input { display: none; }
  .voices label:has(input:checked) { border-color: #2456e6; background: #eef3ff; color: #2456e6; }
  .row { margin: 12px 0; font-size: 14px; }
  .row input[type=range] { width: 100%; }
  button { width: 100%; font: inherit; font-size: 18px; font-weight: 600; padding: 14px; border: 0; border-radius: 12px; background: #2456e6; color: #fff; cursor: pointer; }
  button.reel { background: #d6336c; }
  button:disabled { opacity: .55; cursor: wait; }
  .msg { margin-top: 12px; font-size: 14px; color: #c0392b; min-height: 20px; }
  .info { color: #2456e6; }
  .result { display: none; margin-top: 12px; }
  audio, video { width: 100%; }
  a.dl { display: block; text-align: center; margin-top: 10px; padding: 12px; border-radius: 12px; background: #17a05d; color: #fff; text-decoration: none; font-weight: 600; }
  .pick { display: block; border: 2px dashed #cfd5e3; border-radius: 12px; padding: 16px; text-align: center; cursor: pointer; margin: 12px 0; font-size: 15px; }
  .pick input { display: none; }
  .stage { display: none; text-align: center; margin-top: 12px; }
  canvas { width: 220px; max-width: 60%; border-radius: 12px; background: #000; }
  video { max-width: 300px; display: block; margin: 0 auto; border-radius: 12px; background: #000; }
</style>
</head>
<body>

<div class="card">
  <h1>🎙️ កម្មវិធីអានអត្ថបទខ្មែរ</h1>
  <p class="sub">បញ្ចូលអត្ថបទ ជ្រើសសំឡេង រួចចុច "អាន" ឬ "បង្កើត Reel"។ ឥតគិតថ្លៃ។</p>

  <textarea id="text" maxlength="10000" placeholder="សរសេរ ឬ paste អត្ថបទខ្មែរនៅទីនេះ..."></textarea>
  <div class="count"><span id="n">0</span> / 10000</div>

  <div class="voices">
    <label><input type="radio" name="voice" value="piseth" checked><span>👨 Piseth (ប្រុស)</span></label>
    <label><input type="radio" name="voice" value="sreymom"><span>👩 Sreymom (ស្រី)</span></label>
  </div>

  <div class="row">ល្បឿន៖ <b id="sv">0</b>%
    <input type="range" id="speed" min="-50" max="50" step="5" value="0">
  </div>
  <div class="row">កម្ពស់សំឡេង៖ <b id="pv">0</b>Hz
    <input type="range" id="pitch" min="-20" max="20" step="1" value="0">
  </div>

  <button id="go">🔊 អាន (MP3)</button>
  <div id="msg" class="msg"></div>

  <div id="result" class="result">
    <audio id="player" controls></audio>
    <a id="dl" class="dl" download="khmer-voice.mp3">⬇ ទាញយក MP3</a>
  </div>
</div>

<div class="card">
  <h2>🎬 បង្កើត Reel (វីដេអូបញ្ឈរ 9:16)</h2>
  <p class="sub">ប្រើអត្ថបទ និងសំឡេងខាងលើ។ ដាក់រូបភាព ១ ឬច្រើនសន្លឹក វានឹងបង្ហាញតាមលំដាប់ ជាមួយអក្សររត់។<br>💡 ចង់ឲ្យរូបត្រូវនឹងសំឡេង៖ ចុះបន្ទាត់ទទេ (Enter ២ ដង) រវាងឈុតនីមួយៗ — ឈុតទី ១ = រូបទី ១, ឈុតទី ២ = រូបទី ២...</p>

  <input type="text" id="title" maxlength="60" placeholder="ចំណងជើង (មិនដាក់ក៏បាន)">

  <label class="pick">
    <input type="file" id="imgs" accept="image/*" multiple>
    <span id="pickTxt">🖼️ ចុចដើម្បីជ្រើសរូបភាព</span>
  </label>

  <button id="mk" class="reel">🎬 បង្កើត Reel</button>
  <div id="rmsg" class="msg"></div>

  <div id="stage" class="stage"><canvas id="cv" width="720" height="1280"></canvas></div>

  <div id="rresult" class="result">
    <video id="vid" controls playsinline></video>
    <a id="vdl" class="dl">⬇ ទាញយកវីដេអូ</a>
  </div>
</div>

<script>
const $ = id => document.getElementById(id);
$('text').oninput = () => $('n').textContent = $('text').value.length;
$('speed').oninput = () => $('sv').textContent = $('speed').value;
$('pitch').oninput = () => $('pv').textContent = $('pitch').value;
$('imgs').onchange = () => {
  const n = $('imgs').files.length;
  $('pickTxt').textContent = n ? '🖼️ បានជ្រើស ' + n + ' រូប' : '🖼️ ចុចដើម្បីជ្រើសរូបភាព';
};

function busy(on) { $('go').disabled = on; $('mk').disabled = on; }

async function ttsBlob(text) {
  const res = await fetch('/tts', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      text,
      voice: document.querySelector('input[name=voice]:checked').value,
      speed: +$('speed').value,
      pitch: +$('pitch').value
    })
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.error || 'មានបញ្ហា សូមសាកម្តងទៀត។');
  }
  return res.blob();
}

/* ---------- MP3 ---------- */
let lastUrl = null;
$('go').onclick = async () => {
  const text = $('text').value.trim();
  $('msg').className = 'msg'; $('msg').textContent = '';
  if (!text) { $('msg').textContent = 'សូមបញ្ចូលអត្ថបទជាមុនសិន។'; return; }
  busy(true);
  $('go').textContent = '⏳ កំពុងបង្កើតសំឡេង...';
  try {
    const blob = await ttsBlob(text);
    if (lastUrl) URL.revokeObjectURL(lastUrl);
    lastUrl = URL.createObjectURL(blob);
    $('player').src = lastUrl;
    $('dl').href = lastUrl;
    $('result').style.display = 'block';
    $('player').play().catch(() => {});
  } catch (e) {
    $('msg').textContent = e.message;
  } finally {
    busy(false);
    $('go').textContent = '🔊 អាន (MP3)';
  }
};

/* ---------- Reel ---------- */
const W = 720, H = 1280, MAX_SEG = 60, SEG_LEN = 90, GAP = 0.25;
const FONT = '"Kantumruy Pro", "Khmer OS", sans-serif';

function splitText(text) {
  const parts = text.split(/(?<=[។៕?!])|\n+/).map(s => s.trim()).filter(Boolean);
  const out = [];
  for (const p of parts) {
    if (p.length <= SEG_LEN) { out.push(p); continue; }
    let cur = '';
    for (const w of p.split(/\s+/)) {
      if (cur && (cur + ' ' + w).length > SEG_LEN) { out.push(cur); cur = w; }
      else cur = cur ? cur + ' ' + w : w;
    }
    if (cur) out.push(cur);
  }
  return out;
}

function tokens(text) {
  if (window.Intl && Intl.Segmenter) {
    return [...new Intl.Segmenter('km', { granularity: 'word' }).segment(text)].map(s => s.segment);
  }
  return text.split(/(\s+)/);
}

function wrapLines(g, text, maxW) {
  const lines = []; let cur = '';
  for (const tk of tokens(text)) {
    if (cur && g.measureText((cur + tk).trimEnd()).width > maxW) {
      lines.push(cur.trimEnd());
      cur = tk.trimStart();
    } else cur += tk;
  }
  if (cur.trim()) lines.push(cur.trimEnd());
  return lines;
}

function loadImage(file) {
  return new Promise((ok, bad) => {
    const im = new Image();
    im.onload = () => ok(im);
    im.onerror = () => bad(new Error('បើករូបភាពមិនបាន៖ ' + file.name));
    im.src = URL.createObjectURL(file);
  });
}

function roundRect(g, x, y, w, h, r) {
  g.beginPath();
  g.moveTo(x + r, y);
  g.arcTo(x + w, y, x + w, y + h, r);
  g.arcTo(x + w, y + h, x, y + h, r);
  g.arcTo(x, y + h, x, y, r);
  g.arcTo(x, y, x + w, y, r);
  g.closePath();
}

function drawCover(g, im, zoom) {
  const s = Math.max(W / im.width, H / im.height) * zoom;
  const w = im.width * s, h = im.height * s;
  g.drawImage(im, (W - w) / 2, (H - h) / 2, w, h);
}

function drawFrame(g, t, tl) {
  const tt = Math.max(0, Math.min(t, tl.total));
  // background: each image stays exactly as long as its own sentences are spoken
  if (tl.spans.length) {
    let k = tl.spans.findIndex(sp => tt < sp.end);
    if (k < 0) k = tl.spans.length - 1;
    const sp = tl.spans[k];
    const per = Math.max(0.001, sp.end - sp.start);
    const local = tt - sp.start;
    g.fillStyle = '#000'; g.fillRect(0, 0, W, H);
    drawCover(g, tl.imgs[sp.img], 1 + 0.08 * Math.min(1, local / per));
    if (k > 0 && local < 0.5) {
      g.globalAlpha = 1 - local / 0.5;
      drawCover(g, tl.imgs[tl.spans[k - 1].img], 1.08);
      g.globalAlpha = 1;
    }
  } else {
    const bg = g.createLinearGradient(0, 0, W, H);
    bg.addColorStop(0, '#1b2a6b'); bg.addColorStop(1, '#6a1b5a');
    g.fillStyle = bg; g.fillRect(0, 0, W, H);
  }
  // shade for readability
  const sh = g.createLinearGradient(0, H * 0.5, 0, H);
  sh.addColorStop(0, 'rgba(0,0,0,0)'); sh.addColorStop(1, 'rgba(0,0,0,.65)');
  g.fillStyle = sh; g.fillRect(0, H * 0.5, W, H * 0.5);

  g.textAlign = 'center'; g.textBaseline = 'middle';

  // title
  if (tl.title) {
    g.font = '700 46px ' + FONT;
    const lines = wrapLines(g, tl.title, W - 120).slice(0, 2);
    const lh = 68, bh = lines.length * lh + 36;
    let bw = 0; for (const l of lines) bw = Math.max(bw, g.measureText(l).width);
    bw += 64;
    g.fillStyle = 'rgba(214,51,108,.92)';
    roundRect(g, (W - bw) / 2, 110, bw, bh, 24); g.fill();
    g.fillStyle = '#fff';
    lines.forEach((l, k) => g.fillText(l, W / 2, 110 + 18 + lh / 2 + k * lh));
  }

  // subtitle
  const seg = tl.segs.find(s => tt >= s.start && tt < s.end);
  if (seg) {
    let size = 44;
    g.font = '600 ' + size + 'px ' + FONT;
    let lines = wrapLines(g, seg.text, W - 120);
    if (lines.length > 4) {
      size = 34;
      g.font = '600 ' + size + 'px ' + FONT;
      lines = wrapLines(g, seg.text, W - 120);
    }
    const lh = size * 1.55, bh = lines.length * lh + 40;
    const top = H - 250 - bh;
    g.fillStyle = 'rgba(0,0,0,.6)';
    roundRect(g, 40, top, W - 80, bh, 26); g.fill();
    g.fillStyle = '#fff';
    lines.forEach((l, k) => g.fillText(l, W / 2, top + 20 + lh / 2 + k * lh));
  }
}

function pickMime() {
  const list = [
    ['video/mp4;codecs=avc1.42E01E,mp4a.40.2', 'mp4'],
    ['video/mp4', 'mp4'],
    ['video/webm;codecs=vp9,opus', 'webm'],
    ['video/webm;codecs=vp8,opus', 'webm'],
    ['video/webm', 'webm']
  ];
  for (const [m, ext] of list) {
    if (window.MediaRecorder && MediaRecorder.isTypeSupported(m)) return [m, ext];
  }
  return null;
}

let lastVid = null;
$('mk').onclick = async () => {
  const say = (t, info) => { $('rmsg').className = info ? 'msg info' : 'msg'; $('rmsg').textContent = t; };
  const text = $('text').value.trim();
  say('');
  if (!text) { say('សូមបញ្ចូលអត្ថបទខាងលើជាមុនសិន។'); return; }
  const mime = pickMime();
  if (!mime) { say('Browser នេះមិនអាចថតវីដេអូបានទេ។ សូមប្រើ Chrome។'); return; }
  // scenes are separated by a blank line; each scene = one image
  const scenes = text.split(/\n\s*\n/).map(s => s.trim()).filter(Boolean);
  const segTexts = [], segScene = [];
  scenes.forEach((sc, si) => splitText(sc).forEach(t => { segTexts.push(t); segScene.push(si); }));
  if (segTexts.length > MAX_SEG) { say('អត្ថបទវែងពេកសម្រាប់ Reel (អតិបរមា ' + MAX_SEG + ' ប្រយោគ)។'); return; }

  const AC = window.AudioContext || window.webkitAudioContext;
  const actx = new AC();
  busy(true);
  $('rresult').style.display = 'none';
  let rec = null;
  try {
    await actx.resume();
    await document.fonts.load('600 44px "Kantumruy Pro"', 'កខគ');
    await document.fonts.load('700 46px "Kantumruy Pro"', 'កខគ');

    const imgs = [];
    for (const f of $('imgs').files) imgs.push(await loadImage(f));

    // 1) voice for every sentence
    const segs = []; let at = 0;
    for (let i = 0; i < segTexts.length; i++) {
      say('⏳ កំពុងបង្កើតសំឡេង ' + (i + 1) + ' / ' + segTexts.length + ' ...', true);
      const blob = await ttsBlob(segTexts[i]);
      const buf = await actx.decodeAudioData(await blob.arrayBuffer());
      segs.push({ text: segTexts[i], buf, start: at, end: at + buf.duration + GAP });
      at += buf.duration + GAP;
    }
    // which image goes with each sentence
    const n = imgs.length;
    segs.forEach((s, i) => {
      if (scenes.length > 1) {
        // marked scenes: scene 1 -> image 1, scene 2 -> image 2 ...
        s.img = Math.min(n - 1, segScene[i]);
      } else {
        // no marks: split by time, but never change image in the middle of a sentence
        const mid = (s.start + s.end) / 2;
        s.img = Math.min(n - 1, Math.floor(mid / at * n));
      }
    });
    const spans = [];
    if (n) for (const s of segs) {
      const last = spans[spans.length - 1];
      if (last && last.img === s.img) last.end = s.end;
      else spans.push({ img: s.img, start: s.start, end: s.end });
    }
    if (spans.length) spans[spans.length - 1].end = at + 1;
    if (n > 1 && scenes.length > 1 && scenes.length !== n) {
      say('⚠️ មាន ' + scenes.length + ' ឈុត តែមាន ' + n + ' រូប — រូបខ្លះអាចមិនត្រូវ។ កំពុងបន្ត...', true);
    }
    const tl = { segs, imgs, spans, total: at, title: $('title').value.trim() };

    // 2) record canvas + audio
    const cv = $('cv'), g = cv.getContext('2d');
    $('stage').style.display = 'block';
    drawFrame(g, 0, tl);

    const dest = actx.createMediaStreamDestination();
    const stream = cv.captureStream(30);
    stream.addTrack(dest.stream.getAudioTracks()[0]);
    rec = new MediaRecorder(stream, { mimeType: mime[0], videoBitsPerSecond: 5000000, audioBitsPerSecond: 128000 });
    const chunks = [];
    rec.ondataavailable = e => { if (e.data.size) chunks.push(e.data); };
    const done = new Promise(ok => rec.onstop = ok);

    const t0 = actx.currentTime + 0.4;
    for (const s of segs) {
      const src = actx.createBufferSource();
      src.buffer = s.buf;
      src.connect(dest);
      src.connect(actx.destination);
      src.start(t0 + s.start);
    }
    rec.start(1000);

    await new Promise(ok => {
      const tick = () => {
        const t = actx.currentTime - t0;
        drawFrame(g, t, tl);
        const pct = Math.max(0, Math.min(100, Math.round(t / tl.total * 100)));
        say('🎬 កំពុងថតវីដេអូ ' + pct + '% (សូមកុំបិទ ឬប្តូរ tab)', true);
        if (t >= tl.total + 0.3) ok(); else requestAnimationFrame(tick);
      };
      requestAnimationFrame(tick);
    });

    rec.stop();
    await done;

    const out = new Blob(chunks, { type: mime[0].split(';')[0] });
    if (lastVid) URL.revokeObjectURL(lastVid);
    lastVid = URL.createObjectURL(out);
    $('vid').src = lastVid;
    $('vdl').href = lastVid;
    $('vdl').download = 'khmer-reel.' + mime[1];
    $('vdl').textContent = '⬇ ទាញយកវីដេអូ (.' + mime[1] + ')';
    $('stage').style.display = 'none';
    $('rresult').style.display = 'block';
    say(mime[1] === 'mp4'
      ? '✅ រួចរាល់! ទាញយក រួច upload ជា Reel បាន។'
      : '✅ រួចរាល់ ប៉ុន្តែ browser នេះផ្តល់ជា .webm។ Facebook ត្រូវការ .mp4 សូមប្រើ Chrome ជំនាន់ថ្មី។', true);
  } catch (e) {
    if (rec && rec.state !== 'inactive') rec.stop();
    say(e.message || 'មានបញ្ហា សូមសាកម្តងទៀត។');
  } finally {
    actx.close().catch(() => {});
    busy(false);
  }
};
</script>
</body>
</html>
"""


async def synth(text, voice, rate, pitch):
    tts = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
    buf = io.BytesIO()
    async for chunk in tts.stream():
        if chunk["type"] == "audio":
            buf.write(chunk["data"])
    buf.seek(0)
    return buf


@app.get("/")
def index():
    return Response(PAGE, mimetype="text/html")


@app.post("/tts")
def tts():
    data = request.get_json(silent=True) or {}
    text = (data.get("text") or "").strip()
    if not text:
        return jsonify(error="សូមបញ្ចូលអត្ថបទជាមុនសិន។"), 400
    if len(text) > MAX_CHARS:
        return jsonify(error=f"អត្ថបទវែងពេក (អតិបរមា {MAX_CHARS} តួអក្សរ)។"), 400

    voice = VOICES.get(data.get("voice"), VOICES["piseth"])
    try:
        speed = max(-50, min(50, int(data.get("speed", 0))))
        pitch = max(-20, min(20, int(data.get("pitch", 0))))
    except (TypeError, ValueError):
        speed, pitch = 0, 0

    try:
        buf = asyncio.run(synth(text, voice, f"{speed:+d}%", f"{pitch:+d}Hz"))
    except Exception as e:
        return jsonify(error=f"បង្កើតសំឡេងមិនបាន សូមសាកម្តងទៀត។ ({e})"), 502

    if buf.getbuffer().nbytes == 0:
        return jsonify(error="មិនទទួលបានសំឡេង សូមសាកម្តងទៀត។"), 502

    return send_file(buf, mimetype="audio/mpeg", download_name="khmer-voice.mp3")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
