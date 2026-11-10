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
  if (tl.imgs.length) {
    const per = tl.total / tl.imgs.length;
    const i = Math.min(tl.imgs.length - 1, Math.floor(tt / per));
    const local = tt - i * per;
    g.fillStyle = '#000'; g.fillRect(0, 0, W, H);
    drawCover(g, tl.imgs[i], 1 + 0.08 * (local / per));
    if (i > 0 && local < 0.5) {
      g.globalAlpha = 1 - local / 0.5;
      drawCover(g, tl.imgs[i - 1], 1.08);
      g.globalAlpha = 1;
    }
  } else {
    const bg = g.createLinearGradient(0, 0, W, H);
    bg.addColorStop(0, '#1b2a6b'); bg.addColorStop(1, '#6a1b5a');
    g.fillStyle = bg; g.fillRect(0, 0, W, H);
  }
  const sh = g.createLinearGradient(0, H * 0.5, 0, H);
  sh.addColorStop(0, 'rgba(0,0,0,0)'); sh.addColorStop(1, 'rgba(0,0,0,.65)');
  g.fillStyle = sh; g.fillRect(0, H * 0.5, W, H * 0.5);

  g.textAlign = 'center'; g.textBaseline = 'middle';

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
  const segTexts = splitText(text);
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

    // Fix: Process sentences sequentially with a small delay to avoid rate-limiting / blocking
    const segs = []; let at = 0;
    for (let i = 0; i < segTexts.length; i++) {
      say('⏳ កំពុងបង្កើតសំឡេង ' + (i + 1) + ' / ' + segTexts.length + ' ...', true);
      const blob = await ttsBlob(segTexts[i]);
      const buf = await actx.decodeAudioData(await blob.arrayBuffer());
      segs.push({ text: segTexts[i], buf, start: at, end: at + buf.duration + GAP });
      at += buf.duration + GAP;
      // Add a slight 200ms breathing room gap between requests to prevent server throttling
      await new Promise(r => setTimeout(r, 200));
    }
    const tl = { segs, imgs, total: at, title: $('title').value.trim() };

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
