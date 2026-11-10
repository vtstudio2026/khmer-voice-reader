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

PAGE = """<!DOCTYPE html>
<html lang="km">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Khmer Voice Reader</title>
<link href="https://fonts.googleapis.com/css2?family=Kantumruy+Pro:wght@400;600&display=swap" rel="stylesheet">
<style>
  * { box-sizing: border-box; }
  body { font-family: 'Kantumruy Pro', sans-serif; background: #f3f5fa; margin: 0; padding: 16px; color: #1c2333; }
  .card { max-width: 640px; margin: 0 auto; background: #fff; border-radius: 16px; padding: 20px; box-shadow: 0 4px 18px rgba(0,0,0,.08); }
  h1 { font-size: 22px; margin: 0 0 4px; }
  p.sub { margin: 0 0 16px; color: #5b6478; font-size: 14px; }
  textarea { width: 100%; min-height: 180px; font: inherit; font-size: 16px; padding: 12px; border: 1px solid #cfd5e3; border-radius: 12px; resize: vertical; }
  .count { text-align: right; font-size: 12px; color: #7a8399; margin-top: 4px; }
  .voices { display: flex; gap: 10px; margin: 14px 0; }
  .voices label { flex: 1; border: 2px solid #cfd5e3; border-radius: 12px; padding: 12px; text-align: center; cursor: pointer; font-weight: 600; }
  .voices input { display: none; }
  .voices input:checked + span { color: #2456e6; }
  .voices label:has(input:checked) { border-color: #2456e6; background: #eef3ff; }
  .row { margin: 12px 0; font-size: 14px; }
  .row input[type=range] { width: 100%; }
  button { width: 100%; font: inherit; font-size: 18px; font-weight: 600; padding: 14px; border: 0; border-radius: 12px; background: #2456e6; color: #fff; cursor: pointer; }
  button:disabled { background: #9db1ee; cursor: wait; }
  #msg { margin-top: 12px; font-size: 14px; color: #c0392b; min-height: 20px; }
  #result { display: none; margin-top: 12px; }
  audio { width: 100%; }
  a.dl { display: block; text-align: center; margin-top: 10px; padding: 12px; border-radius: 12px; background: #17a05d; color: #fff; text-decoration: none; font-weight: 600; }
</style>
</head>
<body>
<div class="card">
  <h1>🎙️ កម្មវិធីអានអត្ថបទខ្មែរ</h1>
  <p class="sub">បញ្ចូលអត្ថបទ ជ្រើសសំឡេង រួចចុច "អាន"។ ឥតគិតថ្លៃ។</p>

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

  <button id="go">🔊 អាន</button>
  <div id="msg"></div>

  <div id="result">
    <audio id="player" controls></audio>
    <a id="dl" class="dl" download="khmer-voice.mp3">⬇ ទាញយក MP3</a>
  </div>
</div>

<script>
const $ = id => document.getElementById(id);
$('text').oninput = () => $('n').textContent = $('text').value.length;
$('speed').oninput = () => $('sv').textContent = $('speed').value;
$('pitch').oninput = () => $('pv').textContent = $('pitch').value;

let lastUrl = null;
$('go').onclick = async () => {
  const text = $('text').value.trim();
  $('msg').textContent = '';
  if (!text) { $('msg').textContent = 'សូមបញ្ចូលអត្ថបទជាមុនសិន។'; return; }
  $('go').disabled = true;
  $('go').textContent = '⏳ កំពុងបង្កើតសំឡេង...';
  try {
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
    const blob = await res.blob();
    if (lastUrl) URL.revokeObjectURL(lastUrl);
    lastUrl = URL.createObjectURL(blob);
    $('player').src = lastUrl;
    $('dl').href = lastUrl;
    $('result').style.display = 'block';
    $('player').play().catch(() => {});
  } catch (e) {
    $('msg').textContent = e.message;
  } finally {
    $('go').disabled = false;
    $('go').textContent = '🔊 អាន';
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
