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

# 遭遇率。「その地域を引いたとき画面にその植物が写っている確率」。
# 分布の有無だけでは「知識としては正しいが実戦で当たらないメタ」を
# 見分けられないので、頻度を併記する。無ければ出さない。
enc_path = SP / "encounter.json"
ENC = json.loads(enc_path.read_text(encoding="utf-8")) if enc_path.exists() else {}


def project(lat, lon):
    x = (lon + 180.0) / 360.0 * VIEW_W
    y = (LAT_TOP - lat) / (LAT_TOP - LAT_BOTTOM) * VIEW_H
    return round(x, 1), round(y, 1)


# 点は sample_points.py が分布域からサンプリングし、陸地判定で海を弾いたもの。
# **個々の点にその植物がある確認は無い**（分布の濃さの表示）。
PTS = json.loads((SP / "points.json").read_text(encoding="utf-8"))

# 確認済みの点。実際の車載写真にその植物が写っていることを目視で確認したもの。
# 表示用の点とは意味が違うので、地図上でも区別する。
vp_path = SP / "verified_photos.json"
VPHOTOS = json.loads(vp_path.read_text(encoding="utf-8")) if vp_path.exists() else {}

data = []
for s in SPECIES:
    pts = [{"x": project(la, lo)[0], "y": project(la, lo)[1],
            "lat": la, "lon": lo} for la, lo in PTS[s["id"]]]
    data.append({
        "id": s["id"], "ja": s["ja"], "en": s["en"], "sci": s["sci"],
        "group": s["group"], "color": s["color"], "regions": s["regions"],
        "tells": s["tells"], "trap": s["trap"], "pts": pts,
        "photos": PHOTOS.get(s["id"], []),
        "enc": ENC.get(s["id"]),
        "vpts": [{"x": project(v["lat"], v["lon"])[0],
                  "y": project(v["lat"], v["lon"])[1],
                  "lat": v["lat"], "lon": v["lon"],
                  "src": v["src"], "by": v.get("by", "")}
                 for v in VPHOTOS.get(s["id"], [])],
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
#tip .hint{font-size:.7rem; color:var(--accent); margin-top:.35rem}
#tip .by{font-size:.62rem; color:var(--ink-faint); margin-top:.25rem}
#tip .vchip{font-size:.6rem; background:var(--accent); color:#fff; border-radius:3px;
  padding:.05rem .3rem; margin-left:.35rem; font-weight:600; letter-spacing:.02em}
/* 確認済みの点は白い縁で目立たせる。表示用の点と意味が違うため */
.pt.vpt{stroke:#fff; stroke-width:2; paint-order:stroke}

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
.shotwrap{position:relative; line-height:0}
.bx{
  position:absolute; border:2px solid var(--accent); border-radius:3px;
  box-shadow:0 0 0 1px rgba(255,255,255,.85), inset 0 0 0 1px rgba(255,255,255,.85);
  pointer-events:none; transition:opacity .15s;
}
.bx i{
  position:absolute; left:-2px; bottom:100%; margin-bottom:2px; white-space:nowrap;
  font-style:normal; font-size:.62rem; line-height:1.4; font-weight:600;
  background:var(--accent); color:#fff; padding:.05rem .3rem; border-radius:3px;
}
/* 画像の上端に接する枠はラベルが画像の外に出てしまうので、枠の内側上部に置く */
.bx.top i{bottom:auto; top:2px; left:2px; margin:0}
.shotwrap.nobx .bx{opacity:0}
.bxtog{
  float:right; font:inherit; font-size:.62rem; letter-spacing:.04em; cursor:pointer;
  background:var(--accent); color:#fff; border:1px solid var(--accent);
  border-radius:3px; padding:.02rem .34rem;
}
.bxtog[aria-pressed="false"]{background:transparent; color:var(--ink-faint); border-color:var(--rule)}
.shotnote{font-size:.7rem; color:var(--ink-faint); margin:.4rem 0 0; line-height:1.5}
.shotnote strong{color:var(--ink-soft)}
.enc{margin-top:.7rem}
.enc h5{font-family:"IBM Plex Sans",sans-serif; font-size:.7rem; letter-spacing:.1em;
  text-transform:uppercase; color:var(--ink-faint); font-weight:600; margin:0 0 .4rem;
  display:flex; align-items:baseline; gap:.5rem}
.enchelp{text-transform:none; letter-spacing:0; font-size:.68rem; font-weight:400}
.encrow{display:grid; grid-template-columns:1fr 90px 34px 38px; gap:.4rem;
  align-items:center; font-size:.75rem; padding:.12rem 0}
.encrow.total{font-weight:600; border-bottom:1px solid var(--rule); padding-bottom:.3rem;
  margin-bottom:.2rem}
.encrow.few{opacity:.55}
.encname{color:var(--ink-soft); overflow:hidden; text-overflow:ellipsis; white-space:nowrap}
.encbar{position:relative; height:9px; background:var(--panel-2); border-radius:5px;
  border:1px solid var(--rule)}
/* 帯＝信頼区間。狭いほど確か */
.encbar i{position:absolute; top:0; bottom:0; background:var(--accent); opacity:.28;
  border-radius:5px}
/* 縦線＝点推定 */
.encbar b{position:absolute; top:-2px; bottom:-2px; width:2px; background:var(--accent);
  margin-left:-1px; border-radius:1px}
.encpct{text-align:right; color:var(--ink)}
.encn{text-align:right; color:var(--ink-faint); font-size:.68rem}
.encnote{font-size:.68rem; color:var(--ink-faint); margin:.35rem 0 0; line-height:1.5}
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
  <p class="sub">見えた植物から地域を絞り込むための地図。<strong>点は分布域から機械的に散らしたもので、その1点にその木がある確認は取っていません</strong>（＝分布の濃さを見るための表示）。色は種類そのものではなく、近くに生える種どうしを見分けるための10色。種名は点にカーソルを合わせると出ます。点をクリックするとその座標の地図が開きます。</p>
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
  /* 確認済みの点は、実際の車載写真にその植物が写っていることを目視した点。
     表示用の点（分布域からのサンプリング）とは意味が違うので、
     縁を付けて上に重ねる。ホバーでその地点の写真が出る。 */
  (s.vpts || []).forEach((p, i) => {
    const c = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
    c.setAttribute('cx', p.x); c.setAttribute('cy', p.y); c.setAttribute('r', 5);
    c.setAttribute('fill', s.color);
    c.setAttribute('class', 'pt vpt');
    c.setAttribute('tabindex', '0');
    c.setAttribute('role', 'button');
    c.setAttribute('aria-label', s.ja + '（写真で確認済み） / ' +
      p.lat.toFixed(1) + ', ' + p.lon.toFixed(1));
    c.dataset.sp = s.id;
    c.dataset.lat = p.lat; c.dataset.lon = p.lon;
    c.dataset.v = i;
    ptsG.appendChild(c);
  });
});

/* ---- ツールチップ ---- */
const tip = document.getElementById('tip'), mapEl = document.getElementById('map');
function showTip(el) {
  const s = byId[el.dataset.sp];
  // 確認済みの点なら**その地点の写真**、そうでなければ図鑑写真を出す
  const vi = el.dataset.v;
  const v = (vi !== undefined) ? s.vpts[+vi] : null;
  const shot = v || s.photos[0];
  tip.innerHTML =
    '<div class="n"><span class="sw" style="background:' + s.color + '"></span>' + s.ja +
    (v ? '<span class="vchip">写真で確認</span>' : '') + '</div>' +
    '<div class="r">' + (v ? 'この地点で実際に写っていた' : s.regions.join(' / ')) + '</div>' +
    '<div class="r mono">' + Number(el.dataset.lat).toFixed(2) + ', ' + Number(el.dataset.lon).toFixed(2) + '</div>' +
    (shot ? '<img src="' + shot.src + '" alt="">' : '') +
    (v && v.by ? '<div class="by mono">© ' + v.by + ' / Mapillary (CC BY-SA)</div>' : '') +
    '<div class="hint">クリックでこの座標の地図へ（ペグマンでSV）</div>';
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
/* 点のクリック = その座標のGoogleマップを別タブで開く。
   点は分布域からのサンプリングなので「その木がそこにある」保証は無い。
   実際に何が生えているかは本物のStreet Viewで自分の目で確かめる、という使い方。

   `map_action=pano` は**その座標にパノラマが無いと黒画面**になる。
   点は道路上ではなく分布域内のランダムな位置なので、ほとんどが該当してしまう
   （実際に試して全滅した）。地図を開いてペグマンを近くの道に落としてもらう方が
   確実で、「近くの道を探す」というGeoGuessrの実際の操作にも近い。 */
function panoUrl(lat, lon) {
  return 'https://www.google.com/maps/@' + lat + ',' + lon + ',13z/data=!5m1!1e4';
}
function openPano(el) {
  select(el.dataset.sp);
  window.open(panoUrl(el.dataset.lat, el.dataset.lon), '_blank', 'noopener');
}
ptsG.addEventListener('click', e => { if (e.target.classList.contains('pt')) openPano(e.target); });
ptsG.addEventListener('keydown', e => {
  if ((e.key === 'Enter' || e.key === ' ') && e.target.classList.contains('pt')) {
    e.preventDefault(); openPano(e.target);
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

/* 遭遇率 = その地域を引いたとき、画面にその植物が写っている確率。
   分布の有無だけだと「知識としては正しいが実戦で当たらないメタ」を
   見分けられない。標本が少ないうちは幅が広く出るので、
   点推定だけでなく信頼区間と件数も一緒に出す。 */
function encBar(r) {
  const pct = (r.seen_rate * 100).toFixed(0);
  const lo = r.seen_lo * 100, hi = r.seen_hi * 100;
  return '<div class="encrow' + (r.enough ? '' : ' few') + '">' +
    '<span class="encname">' + r.region + '</span>' +
    '<span class="encbar"><i style="left:' + lo + '%;width:' + (hi - lo) + '%"></i>' +
    '<b style="left:' + pct + '%"></b></span>' +
    '<span class="encpct mono">' + pct + '%</span>' +
    '<span class="encn mono">' + r.accepted + '/' + r.judged + '</span></div>';
}
function encHtml(s) {
  const e = s.enc;
  if (!e || !e.judged) return '';
  const rows = e.regions.filter(r => r.judged > 0).map(encBar).join('');
  const few = e.regions.some(r => r.judged > 0 && !r.enough);
  return '<div class="enc"><h5>遭遇率' +
    '<span class="enchelp">その地域の道端で実際に画面に写る割合</span></h5>' +
    '<div class="encrow total"><span class="encname">全体</span>' +
    '<span class="encbar"><i style="left:' + (e.seen_lo * 100) + '%;width:' +
    ((e.seen_hi - e.seen_lo) * 100) + '%"></i>' +
    '<b style="left:' + (e.seen_rate * 100) + '%"></b></span>' +
    '<span class="encpct mono">' + (e.seen_rate * 100).toFixed(0) + '%</span>' +
    '<span class="encn mono">' + e.accepted + '/' + e.judged + '</span></div>' +
    rows +
    (few ? '<p class="encnote">薄い行は標本が少なく、幅（帯）が広い＝まだ確かでない。</p>' : '') +
    '</div>';
}

function renderDetail(s) {
  if (!s) { detPane.innerHTML = '<p class="empty">地図の点か、一覧の種類を選ぶと表示されます。</p>'; return; }
  /* 写真の上に「どこを見るか」の枠を重ねる。
     枠は 0〜1 の相対座標なので、画像が伸縮しても位置がずれない。 */
  const shots = s.photos.length
    ? '<div class="shots">' + s.photos.map(p => {
        const boxes = (p.boxes || []).map(b =>
          '<span class="bx' + (b.box[1] < 0.08 ? ' top' : '') + '" style="left:' + (b.box[0] * 100).toFixed(2) +
          '%;top:' + (b.box[1] * 100).toFixed(2) +
          '%;width:' + (b.box[2] * 100).toFixed(2) +
          '%;height:' + (b.box[3] * 100).toFixed(2) + '%">' +
          '<i>' + b.label + '</i></span>').join('');
        return '<figure><div class="shotwrap">' +
          '<img src="' + p.src + '" alt="' + s.ja + 'の実例">' + boxes + '</div>' +
          '<figcaption>' + p.credit + '</figcaption></figure>';
      }).join('') + '</div>'
    : '<div class="noshot">この種は実写が未取得です</div>';
  detPane.innerHTML =
    '<div class="hd"><span class="sw" style="background:' + s.color + '"></span><h2>' + s.ja + '</h2></div>' +
    '<div class="sci mono">' + s.en + ' — ' + s.sci + '</div>' +
    '<section><h4>実例<button class="bxtog" id="bxtog" aria-pressed="true">枠</button></h4>' +
      shots + '<p class="shotnote">枠は<strong>この写真のどこを見るか</strong>。' +
      '実際の景色は地図の点をクリックし、ペグマンを近くの道に落として確かめる。</p></section>' +
    '<section><h4>示す地域</h4><div class="tags">' +
      s.regions.map(r => '<span class="tag">' + r + '</span>').join('') + '</div>' +
      encHtml(s) + '</section>' +
    '<section><h4>見分け方</h4><ul>' + s.tells.map(t => '<li>' + t + '</li>').join('') + '</ul></section>' +
    '<section><h4>罠・紛らわしい点</h4><div class="trap">' +
      s.trap.replace(/\\*\\*(.+?)\\*\\*/g, '<strong>$1</strong>') + '</div></section>';
  const tg = document.getElementById('bxtog');
  if (tg) tg.addEventListener('click', () => {
    const on = tg.getAttribute('aria-pressed') === 'true';
    tg.setAttribute('aria-pressed', String(!on));
    detPane.querySelectorAll('.shotwrap').forEach(w => w.classList.toggle('nobx', on));
  });
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
