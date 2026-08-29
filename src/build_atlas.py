# -*- coding: utf-8 -*-
"""植生メタアトラスの HTML を生成する。

Artifact は外部ホストへ通信できないため、地図の輪郭・データ・画像はすべて埋め込む。
（Google Fonts だけは CSP で許可されているのでリンクで読む）
"""
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

from palette import assign  # noqa: E402
from species import SPECIES  # noqa: E402

# 38色を全部分けても見分けられないので、色は「隣接する種の区別」に絞る（10色）。
# 種の識別はホバー/クリックのラベルが担う。
_pal = assign(SPECIES)

sys.path.insert(0, str(Path(__file__).resolve().parent))
from paths import DATA, DIST  # noqa: E402
SP = DATA
LAND = (SP / "land_path.txt").read_text(encoding="utf-8")
OUT = DIST / "flora_atlas.html"

VIEW_W, VIEW_H = 2000.0, 1000.0
LAT_TOP, LAT_BOTTOM = 84.0, -56.0

# 画像はトークン取得後に differ で流し込む。無ければプレースホルダを出す。
photos_path = SP / "photos.json"
PHOTOS = json.loads(photos_path.read_text(encoding="utf-8")) if photos_path.exists() else {}


def project(lat, lon):
    x = (lon + 180.0) / 360.0 * VIEW_W
    y = (LAT_TOP - lat) / (LAT_TOP - LAT_BOTTOM) * VIEW_H
    return round(x, 1), round(y, 1)


# 点は sample_points.py が分布域からサンプリングし、陸地判定で海を弾いたもの。
PTS = json.loads((SP / "points.json").read_text(encoding="utf-8"))

data = []
for s in SPECIES:
    pts = [{"x": project(la, lo)[0], "y": project(la, lo)[1],
            "lat": la, "lon": lo} for la, lo in PTS[s["id"]]]
    data.append({
        "id": s["id"], "ja": s["ja"], "en": s["en"], "sci": s["sci"],
        "group": s["group"], "color": s["color"], "regions": s["regions"],
        "tells": s["tells"], "trap": s["trap"], "pts": pts,
        "photos": PHOTOS.get(s["id"], []),
    })

groups = []
for s in data:
    if s["group"] not in groups:
        groups.append(s["group"])

payload = json.dumps({"species": data, "groups": groups}, ensure_ascii=False)

HTML = """<title>植生メタアトラス</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Spectral:wght@500;600&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
/* 点の色は matplotlib の tab10 をそのまま使う。
   tab10 には緑・灰が含まれるので、陸と海はほぼ無彩色まで落として点を浮かせる。 */
:root{
  --ocean:#EFEDE7; --ocean-deep:#E4E1D9;
  --land:#D6D5CD; --land-edge:#B3B2A9;
  --ink:#1E2220; --ink-soft:#5F6663; --ink-faint:#8E9391;
  --panel:#F7F6F2; --panel-2:#FFFFFC;
  --rule:#CFCDC5; --accent:#B4622A; --focus:#2E6E8E;
  --shadow:0 2px 4px rgba(30,34,32,.06),0 8px 24px rgba(30,34,32,.10);
}
@media (prefers-color-scheme:dark){
  :root:not([data-theme="light"]){
    --ocean:#12181C; --ocean-deep:#0C1114;
    --land:#2B322F; --land-edge:#434B47;
    --ink:#E8EAE9; --ink-soft:#A3A9A6; --ink-faint:#727977;
    --panel:#171C1F; --panel-2:#1E2427;
    --rule:#2C3336; --accent:#E0925A; --focus:#68B4D6;
    --shadow:0 2px 4px rgba(0,0,0,.30),0 10px 30px rgba(0,0,0,.38);
  }
}
:root[data-theme="dark"]{
  --ocean:#12181C; --ocean-deep:#0C1114;
  --land:#2B322F; --land-edge:#434B47;
  --ink:#E8EAE9; --ink-soft:#A3A9A6; --ink-faint:#727977;
  --panel:#171C1F; --panel-2:#1E2427;
  --rule:#2C3336; --accent:#E0925A; --focus:#68B4D6;
  --shadow:0 2px 4px rgba(0,0,0,.30),0 10px 30px rgba(0,0,0,.38);
}

*{box-sizing:border-box}
body{
  margin:0; background:var(--ocean); color:var(--ink);
  font-family:"IBM Plex Sans","Hiragino Kaku Gothic ProN","Yu Gothic",system-ui,sans-serif;
  font-size:15px; line-height:1.6;
}
h1,h2,h3{font-family:Spectral,"Hiragino Mincho ProN",Georgia,serif; font-weight:600; text-wrap:balance; margin:0}
.mono{font-family:"IBM Plex Mono",ui-monospace,monospace; font-variant-numeric:tabular-nums}

header{
  display:flex; flex-wrap:wrap; align-items:baseline; gap:.4rem 1rem;
  padding:1.1rem clamp(1rem,3vw,2rem) .9rem; border-bottom:1px solid var(--rule);
}
header h1{font-size:clamp(1.25rem,2.4vw,1.7rem); letter-spacing:.01em}
header .sub{color:var(--ink-soft); font-size:.85rem; max-width:62ch}
header .count{margin-left:auto; color:var(--ink-faint); font-size:.78rem; letter-spacing:.06em; text-transform:uppercase}

.wrap{display:grid; grid-template-columns:minmax(0,1fr) 340px; gap:0; align-items:stretch}
@media (max-width:900px){ .wrap{grid-template-columns:minmax(0,1fr)} }

/* ---- 地図 ---- */
.mapcell{position:relative; background:var(--ocean-deep); min-width:0}
svg.map{display:block; width:100%; height:auto; aspect-ratio:2/1; touch-action:none; cursor:grab}
svg.map.dragging{cursor:grabbing}
.land{fill:var(--land); stroke:var(--land-edge); stroke-width:1.1; vector-effect:non-scaling-stroke}
.grat{stroke:var(--land-edge); stroke-width:.8; opacity:.42; fill:none; vector-effect:non-scaling-stroke}
.grat.eq{stroke:var(--accent); opacity:.5; stroke-dasharray:8 7}
.pt{r:var(--dotr,5px); stroke:var(--ocean-deep); stroke-width:1.1;
    cursor:pointer; transition:opacity .16s}
.pt:focus-visible{outline:none; stroke:var(--focus); stroke-width:3}
.dim .pt:not(.on){opacity:.13}
.dim .pt.on{stroke-width:2}

.zoomer{position:absolute; left:.65rem; bottom:.65rem; display:flex; gap:.3rem}
.zoomer button{
  width:30px; height:30px; border:1px solid var(--rule); background:var(--panel);
  color:var(--ink); border-radius:5px; font-size:15px; cursor:pointer; line-height:1;
}
.zoomer button:hover{border-color:var(--accent); color:var(--accent)}
.zoomer button:focus-visible{outline:2px solid var(--focus); outline-offset:1px}

#tip{
  position:absolute; pointer-events:none; z-index:5; max-width:290px; opacity:0;
  transform:translate(-50%,-112%); transition:opacity .1s;
  background:var(--panel-2); border:1px solid var(--rule); border-radius:8px;
  box-shadow:var(--shadow); padding:.55rem .7rem;
}
#tip.show{opacity:1}
#tip .n{font-family:Spectral,serif; font-size:1rem; font-weight:600; display:flex; align-items:center; gap:.45rem}
#tip .sw{width:11px; height:11px; border-radius:50%; flex:none}
#tip .r{color:var(--ink-soft); font-size:.78rem; margin-top:.2rem}
#tip img{width:100%; border-radius:5px; margin-top:.45rem; display:block}

/* ---- 右ペイン ---- */
.side{
  border-left:1px solid var(--rule); background:var(--panel);
  display:flex; flex-direction:column; max-height:calc(100vh - 88px); min-width:0;
}
@media (max-width:900px){ .side{border-left:none; border-top:1px solid var(--rule); max-height:none} }
.tabs{display:flex; border-bottom:1px solid var(--rule); flex:none}
.tabs button{
  flex:1; padding:.6rem .5rem; background:none; border:none; cursor:pointer;
  color:var(--ink-soft); font:inherit; font-size:.82rem; letter-spacing:.04em;
  border-bottom:2px solid transparent;
}
.tabs button[aria-selected="true"]{color:var(--ink); border-bottom-color:var(--accent)}
.tabs button:focus-visible{outline:2px solid var(--focus); outline-offset:-2px}
.pane{overflow-y:auto; padding:.9rem 1rem 1.6rem; flex:1; min-height:0}
.pane[hidden]{display:none}

.grp{margin:0 0 1rem}
.grp h3{font-size:.72rem; letter-spacing:.1em; text-transform:uppercase; color:var(--ink-faint);
        font-family:"IBM Plex Sans",sans-serif; font-weight:600; margin-bottom:.4rem}
.chip{
  display:flex; align-items:center; gap:.5rem; width:100%; text-align:left;
  padding:.3rem .45rem; border:1px solid transparent; border-radius:6px;
  background:none; color:var(--ink); font:inherit; font-size:.86rem; cursor:pointer;
}
.chip:hover{background:var(--panel-2); border-color:var(--rule)}
.chip:focus-visible{outline:2px solid var(--focus); outline-offset:1px}
.chip[aria-pressed="true"]{background:var(--panel-2); border-color:var(--accent)}
.chip .sw{width:12px; height:12px; border-radius:50%; flex:none; border:1px solid rgba(0,0,0,.25)}
.chip .cnt{margin-left:auto; color:var(--ink-faint); font-size:.72rem}

.detail .hd{display:flex; align-items:center; gap:.55rem; margin-bottom:.15rem}
.detail .hd .sw{width:15px; height:15px; border-radius:50%; flex:none; border:1px solid rgba(0,0,0,.25)}
.detail h2{font-size:1.22rem}
.detail .sci{color:var(--ink-faint); font-size:.8rem; margin-bottom:.9rem}
.detail section{margin-bottom:1.05rem}
.detail h4{
  font-family:"IBM Plex Sans",sans-serif; font-size:.7rem; letter-spacing:.1em;
  text-transform:uppercase; color:var(--ink-faint); font-weight:600; margin:0 0 .35rem;
}
.detail ul{margin:0; padding-left:1.05rem}
.detail li{margin-bottom:.2rem}
.tags{display:flex; flex-wrap:wrap; gap:.3rem}
.tag{border:1px solid var(--rule); border-radius:20px; padding:.1rem .55rem; font-size:.78rem; color:var(--ink-soft)}
.trap{border-left:3px solid var(--accent); padding:.5rem .7rem; background:var(--panel-2); border-radius:0 6px 6px 0; font-size:.87rem}
.trap strong{color:var(--accent)}
.shots{display:grid; gap:.4rem}
.shots figure{margin:0}
.shots img{width:100%; border-radius:6px; display:block; border:1px solid var(--rule)}
.shots figcaption{font-size:.68rem; color:var(--ink-faint); margin-top:.2rem}
.noshot{
  border:1px dashed var(--rule); border-radius:6px; padding:.8rem; text-align:center;
  color:var(--ink-faint); font-size:.8rem;
}
.empty{color:var(--ink-faint); font-size:.88rem; padding:1.2rem 0; text-align:center}
.clear{
  margin-top:.2rem; background:none; border:1px solid var(--rule); border-radius:6px;
  color:var(--ink-soft); font:inherit; font-size:.78rem; padding:.3rem .6rem; cursor:pointer;
}
.clear:hover{border-color:var(--accent); color:var(--accent)}
@media (prefers-reduced-motion:reduce){*{transition:none!important}}
</style>

<header>
  <h1>植生メタアトラス</h1>
  <p class="sub">見えた植物から地域を絞り込むための地図。点は代表的な生育地。<strong>色は種類そのものではなく、近くに生える種どうしを見分けるための10色</strong>。種名は点にカーソルを合わせると出ます。</p>
  <span class="count mono" id="hdcount"></span>
</header>

<div class="wrap">
  <div class="mapcell">
    <svg class="map" id="map" viewBox="0 0 2000 1000" role="img" aria-label="植生メタの世界地図">
      <g id="cam">
        <path class="land" d="__LAND__"/>
        <g id="grat"></g>
        <g id="pts"></g>
      </g>
    </svg>
    <div class="zoomer">
      <button type="button" id="zin" aria-label="拡大">+</button>
      <button type="button" id="zout" aria-label="縮小">−</button>
      <button type="button" id="zrst" aria-label="全体表示">⤾</button>
    </div>
    <div id="tip" role="tooltip"></div>
  </div>

  <aside class="side">
    <div class="tabs" role="tablist">
      <button type="button" role="tab" id="t-list" aria-selected="true" aria-controls="p-list">一覧</button>
      <button type="button" role="tab" id="t-det" aria-selected="false" aria-controls="p-det">詳細</button>
    </div>
    <div class="pane" id="p-list" role="tabpanel" aria-labelledby="t-list"></div>
    <div class="pane detail" id="p-det" role="tabpanel" aria-labelledby="t-det" hidden></div>
  </aside>
</div>

<script>
const DATA = __DATA__;
const S = DATA.species, GROUPS = DATA.groups;
const byId = Object.fromEntries(S.map(s => [s.id, s]));
let sel = null;

document.getElementById('hdcount').textContent =
  S.length + ' species · ' + S.reduce((a, s) => a + s.pts.length, 0) + ' points';

/* ---- 経緯線（赤道と回帰線だけ引く。緯度感覚が植生の手がかりそのものなので） ---- */
const LAT_TOP = 84, LAT_BOT = -56;
const yOf = lat => (LAT_TOP - lat) / (LAT_TOP - LAT_BOT) * 1000;
const grat = document.getElementById('grat');
[[0, 'eq', '赤道'], [23.44, '', '北回帰線'], [-23.44, '', '南回帰線'],
 [45, '', ''], [-45, '', ''], [66.56, '', '北極圏']].forEach(([lat, cls, label]) => {
  const y = yOf(lat);
  const l = document.createElementNS('http://www.w3.org/2000/svg', 'line');
  l.setAttribute('x1', 0); l.setAttribute('x2', 2000);
  l.setAttribute('y1', y); l.setAttribute('y2', y);
  l.setAttribute('class', 'grat ' + cls);
  grat.appendChild(l);
});

/* ---- 点 ---- */
const ptsG = document.getElementById('pts');
S.forEach(s => {
  s.pts.forEach(p => {
    const c = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
    c.setAttribute('cx', p.x); c.setAttribute('cy', p.y); c.setAttribute('r', 5);
    c.setAttribute('fill', s.color);
    c.setAttribute('class', 'pt');
    c.setAttribute('tabindex', '0');
    c.setAttribute('role', 'button');
    c.setAttribute('aria-label', s.ja + ' / ' + p.lat.toFixed(1) + ', ' + p.lon.toFixed(1));
    c.dataset.sp = s.id;
    c.dataset.lat = p.lat; c.dataset.lon = p.lon;
    ptsG.appendChild(c);
  });
});

/* ---- ツールチップ ---- */
const tip = document.getElementById('tip'), mapEl = document.getElementById('map');
function showTip(el) {
  const s = byId[el.dataset.sp];
  const shot = s.photos[0];
  tip.innerHTML =
    '<div class="n"><span class="sw" style="background:' + s.color + '"></span>' + s.ja + '</div>' +
    '<div class="r">' + s.regions.join(' / ') + '</div>' +
    '<div class="r mono">' + Number(el.dataset.lat).toFixed(2) + ', ' + Number(el.dataset.lon).toFixed(2) + '</div>' +
    (shot ? '<img src="' + shot.src + '" alt="">' : '');
  const r = el.getBoundingClientRect(), m = mapEl.parentElement.getBoundingClientRect();
  tip.style.left = (r.left - m.left + r.width / 2) + 'px';
  tip.style.top = (r.top - m.top) + 'px';
  tip.classList.add('show');
}
const hideTip = () => tip.classList.remove('show');
ptsG.addEventListener('pointerover', e => { if (e.target.classList.contains('pt')) showTip(e.target); });
ptsG.addEventListener('pointerout', hideTip);
ptsG.addEventListener('focusin', e => { if (e.target.classList.contains('pt')) showTip(e.target); });
ptsG.addEventListener('focusout', hideTip);
ptsG.addEventListener('click', e => { if (e.target.classList.contains('pt')) select(e.target.dataset.sp); });
ptsG.addEventListener('keydown', e => {
  if ((e.key === 'Enter' || e.key === ' ') && e.target.classList.contains('pt')) {
    e.preventDefault(); select(e.target.dataset.sp);
  }
});

/* ---- 一覧 ---- */
const listPane = document.getElementById('p-list');
GROUPS.forEach(g => {
  const box = document.createElement('div');
  box.className = 'grp';
  box.innerHTML = '<h3>' + g + '</h3>';
  S.filter(s => s.group === g).forEach(s => {
    const b = document.createElement('button');
    b.type = 'button'; b.className = 'chip'; b.dataset.sp = s.id;
    b.setAttribute('aria-pressed', 'false');
    b.innerHTML = '<span class="sw" style="background:' + s.color + '"></span>' +
      '<span>' + s.ja + '</span><span class="cnt mono">' + s.pts.length + '</span>';
    b.addEventListener('click', () => select(s.id === sel ? null : s.id));
    box.appendChild(b);
  });
  listPane.appendChild(box);
});
const clearBtn = document.createElement('button');
clearBtn.type = 'button'; clearBtn.className = 'clear'; clearBtn.textContent = '選択を解除';
clearBtn.addEventListener('click', () => select(null));
listPane.appendChild(clearBtn);

/* ---- 詳細 ---- */
const detPane = document.getElementById('p-det');
const tabList = document.getElementById('t-list'), tabDet = document.getElementById('t-det');
function setTab(which) {
  const det = which === 'det';
  tabDet.setAttribute('aria-selected', det); tabList.setAttribute('aria-selected', !det);
  detPane.hidden = !det; listPane.hidden = det;
}
tabList.addEventListener('click', () => setTab('list'));
tabDet.addEventListener('click', () => setTab('det'));

function renderDetail(s) {
  if (!s) { detPane.innerHTML = '<p class="empty">地図の点か、一覧の種類を選ぶと表示されます。</p>'; return; }
  const shots = s.photos.length
    ? '<div class="shots">' + s.photos.map(p =>
        '<figure><img src="' + p.src + '" alt="' + s.ja + 'の実例"><figcaption>' +
        p.credit + '</figcaption></figure>').join('') + '</div>'
    : '<div class="noshot">この種は実写が未取得です</div>';
  detPane.innerHTML =
    '<div class="hd"><span class="sw" style="background:' + s.color + '"></span><h2>' + s.ja + '</h2></div>' +
    '<div class="sci mono">' + s.en + ' — ' + s.sci + '</div>' +
    '<section><h4>実例</h4>' + shots + '</section>' +
    '<section><h4>示す地域</h4><div class="tags">' +
      s.regions.map(r => '<span class="tag">' + r + '</span>').join('') + '</div></section>' +
    '<section><h4>見分け方</h4><ul>' + s.tells.map(t => '<li>' + t + '</li>').join('') + '</ul></section>' +
    '<section><h4>罠・紛らわしい点</h4><div class="trap">' +
      s.trap.replace(/\\*\\*(.+?)\\*\\*/g, '<strong>$1</strong>') + '</div></section>';
}

function select(id) {
  sel = id;
  const g = document.getElementById('pts');
  g.parentElement.parentElement.classList.toggle('dim', !!id);
  [...g.children].forEach(c => c.classList.toggle('on', c.dataset.sp === id));
  listPane.querySelectorAll('.chip').forEach(b =>
    b.setAttribute('aria-pressed', String(b.dataset.sp === id)));
  renderDetail(id ? byId[id] : null);
  if (id) setTab('det');
}
renderDetail(null);

/* ---- パン・ズーム ---- */
let cam = { k: 1, x: 0, y: 0 };
const camG = document.getElementById('cam');
function applyCam() {
  camG.setAttribute('transform', 'translate(' + cam.x + ',' + cam.y + ') scale(' + cam.k + ')');
  // 点はズームしても見かけの大きさをほぼ保つ。2800点あるので個別に
  // setAttribute せず、CSS変数1つで全点を動かす。
  mapEl.style.setProperty('--dotr', (5 / Math.pow(cam.k, 0.72)) + 'px');
  hideTip();
}
function zoomAt(f, cx, cy) {
  const k2 = Math.min(12, Math.max(1, cam.k * f));
  const r = k2 / cam.k;
  cam.x = cx - (cx - cam.x) * r; cam.y = cy - (cy - cam.y) * r; cam.k = k2;
  if (cam.k === 1) { cam.x = 0; cam.y = 0; }
  applyCam();
}
function svgPt(ev) {
  const r = mapEl.getBoundingClientRect();
  return [(ev.clientX - r.left) / r.width * 2000, (ev.clientY - r.top) / r.height * 1000];
}
mapEl.addEventListener('wheel', e => {
  e.preventDefault();
  const [cx, cy] = svgPt(e);
  zoomAt(e.deltaY < 0 ? 1.22 : 1 / 1.22, cx, cy);
}, { passive: false });
let drag = null;
mapEl.addEventListener('pointerdown', e => {
  if (e.target.classList.contains('pt')) return;
  drag = { x: e.clientX, y: e.clientY, ox: cam.x, oy: cam.y };
  mapEl.setPointerCapture(e.pointerId); mapEl.classList.add('dragging');
});
mapEl.addEventListener('pointermove', e => {
  if (!drag) return;
  const r = mapEl.getBoundingClientRect();
  cam.x = drag.ox + (e.clientX - drag.x) / r.width * 2000;
  cam.y = drag.oy + (e.clientY - drag.y) / r.height * 1000;
  applyCam();
});
const endDrag = () => { drag = null; mapEl.classList.remove('dragging'); };
mapEl.addEventListener('pointerup', endDrag);
mapEl.addEventListener('pointercancel', endDrag);
document.getElementById('zin').addEventListener('click', () => zoomAt(1.4, 1000, 500));
document.getElementById('zout').addEventListener('click', () => zoomAt(1 / 1.4, 1000, 500));
document.getElementById('zrst').addEventListener('click', () => { cam = { k: 1, x: 0, y: 0 }; applyCam(); });
</script>
"""

html = HTML.replace("__LAND__", LAND).replace("__DATA__", payload)
OUT.write_text(html, encoding="utf-8")
kb = len(html.encode("utf-8")) / 1024
print(f"書き出し: {OUT}  ({kb:,.0f} KB)")
print(f"  種 {len(data)} / 点 {sum(len(s['pts']) for s in data)} / "
      f"写真あり {sum(1 for s in data if s['photos'])} 種")
