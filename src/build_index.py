# -*- coding: utf-8 -*-
"""トップページ（dist/index.html）を作る。

**どの点をタップしても、その地点の写真と写っている植物が出る**地図。
資料を3つ並べるのではなく、これ1枚を入口にする（ユーザー指定）。

サムネイルは緯度経度のタイルに分けてある（build_tiles.py）。
タップした点のタイルだけを取りに行くので、初回表示は地図だけで軽い。
"""
import json
import sys
from collections import Counter
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent))

from build_tagmap import project  # noqa: E402
from coverage import is_covered  # noqa: E402
from paths import DATA, DIST  # noqa: E402

def main():
    tags = json.loads((DATA / "tags.json").read_text(encoding="utf-8"))
    idx = {x["img_id"]: x for x in
           json.loads((DATA / "random_index.json").read_text(encoding="utf-8"))}

    # GeoGuessr のカバー国かどうか。非カバー国（中国本土・ミャンマー・
    # アフリカの多くなど）はゲームに出ないので、そこで見える植物を
    # 覚えても無駄になる（ユーザー判断）。
    where = json.loads((DATA / "country_of.json").read_text(encoding="utf-8"))         if (DATA / "country_of.json").exists() else {}

    pts = []
    skip_none = skip_uncov = 0
    for img_id, names in tags.items():
        it = idx.get(img_id)
        if not it:
            continue
        # 属を特定できなかった点は地図に出さない（ユーザー判断）。
        # 「植物が無い」のではなく「属を特定できない」だけだが、
        # 手がかりにならない点を打っても地図が濁るだけ。
        if not names:
            skip_none += 1
            continue
        if not is_covered(where.get(img_id) or ""):
            skip_uncov += 1
            continue
        x, y = project(it["lat"], it["lon"])
        pts.append([x, y, round(it["lat"], 3), round(it["lon"], 3),
                    img_id, names])

    c = Counter(n for p in pts for n in p[5])

    # 点の色。出現数の多い12タグに固有色を割り当て、それ以外は「その他」。
    # 全部を色分けしても53色は見分けられないので、地図で意味を持つ
    # 上位だけに絞る。
    top = [t for t, _ in c.most_common(12)]
    cidx = {t: i for i, t in enumerate(top)}
    for pt in pts:
        # 複数タグなら、より珍しい方（＝順位が下）を優先する。
        # ヤシ科とココヤシが両方付いた点は「ココヤシ」で塗る方が
        # 地図として情報量が多い。
        ranks = [cidx.get(n, 99) for n in pt[5]]
        best = max(ranks)
        pt.append(best if best < 12 else 12)       # 12 = その他

    payload = json.dumps({
        "pts": pts,
        "n": len(pts),
        "hit": sum(1 for p in pts if p[5]),
        "tags": c.most_common(),
        "legend": top,
    }, ensure_ascii=False, separators=(",", ":"))

    # 陸地のパスは既存の地図から流用する（同じ投影・同じ viewBox）
    src = (DIST / "tag_atlas.html").read_text(encoding="utf-8")
    i = src.index('<path class="land" d="') + len('<path class="land" d="')
    land = src[i:src.index('"', i)]

    html = TEMPLATE.replace("__LAND__", land).replace("__DATA__", payload)
    out = DIST / "index.html"
    out.write_text(html, encoding="utf-8")
    print(f"書き出し: {out}  ({len(html.encode())/1048576:.1f} MB)")
    print(f"  点 {len(pts)} / タグ {len(c)}種類")
    print(f"  除外: 属を特定できず {skip_none} / 非カバー国 {skip_uncov}")


TEMPLATE = r"""<!doctype html><html lang="ja"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no">
<title>世界の道端の植物</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Spectral:wght@500;600&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
:root{
  --bg:#f7f6f2; --panel:#fffdf9; --panel-2:#f0eee7; --ocean:#e8e6df; --land:#dcd9d0;
  --edge:#c8c5bb; --ink:#1c1b19; --ink-soft:#55524c; --ink-faint:#8a8780;
  --rule:#d8d5cd; --accent:#c0563c; --hit:#c0563c; --miss:#a9a69d;
}
@media (prefers-color-scheme:dark){
  :root:not([data-theme="light"]){
    --bg:#14161a; --panel:#1a1d21; --panel-2:#22262b; --ocean:#101317; --land:#272c31;
    --edge:#343a40; --ink:#e9e7e2; --ink-soft:#b0aca4; --ink-faint:#807c74;
    --rule:#2e353a; --accent:#e0714f; --hit:#e0714f; --miss:#5d6167;
  }
}
:root[data-theme="dark"]{
  --bg:#14161a; --panel:#1a1d21; --panel-2:#22262b; --ocean:#101317; --land:#272c31;
  --edge:#343a40; --ink:#e9e7e2; --ink-soft:#b0aca4; --ink-faint:#807c74;
  --rule:#2e353a; --accent:#e0714f; --hit:#e0714f; --miss:#5d6167;
}
*{box-sizing:border-box}
html,body{height:100%}
body{
  margin:0; background:var(--bg); color:var(--ink);
  font-family:"IBM Plex Sans",system-ui,sans-serif; font-size:15px;
  overflow:hidden;
}
header{
  padding:.5rem .9rem; border-bottom:1px solid var(--rule); background:var(--panel);
  display:flex; align-items:baseline; gap:.7rem; flex-wrap:wrap;
}
h1{font-family:Spectral,serif; font-size:1.05rem; margin:0; font-weight:600}
.count{font-family:"IBM Plex Mono",monospace; font-size:.74rem; color:var(--ink-faint)}
.mapwrap{position:relative; overflow:hidden; background:var(--ocean);
  height:calc(100% - 42px - 34px); display:grid; place-items:center}
svg.map{display:block; width:100%; height:100%; touch-action:none}
.land{fill:var(--land); stroke:var(--edge); stroke-width:.6}
.pt{cursor:pointer}
.pt.miss{fill:var(--miss); opacity:.34}
.pt.on{stroke:var(--ink); stroke-width:2.5px; paint-order:stroke; opacity:1}
/* 上位12タグの色（matplotlib tab10 + 2色）。
   カテゴリカル配色として実績のあるものを使う。 */
.c0{fill:#1f77b4} .c1{fill:#ff7f0e} .c2{fill:#2ca02c} .c3{fill:#d62728}
.c4{fill:#9467bd} .c5{fill:#8c564b} .c6{fill:#e377c2} .c7{fill:#17becf}
.c8{fill:#bcbd22} .c9{fill:#7f7f7f} .c10{fill:#aec7e8} .c11{fill:#ffbb78}
.c12{fill:#c49a6c}
.pt[class*="c"]{opacity:.88}

/* ---- 凡例 ---- */
.legend{
  position:absolute; left:.5rem; bottom:.5rem; z-index:5;
  background:color-mix(in srgb,var(--panel) 93%,transparent);
  border:1px solid var(--rule); border-radius:8px; padding:.35rem .5rem;
  font-size:.7rem; line-height:1.45; max-width:min(62vw,200px);
  cursor:pointer; user-select:none;
}
.legend > b{
  display:flex; align-items:center; gap:.3rem; font-size:.68rem;
  color:var(--ink-faint); font-weight:500; letter-spacing:.04em;
}
.legend > b::after{content:"▾"; font-size:.6rem}
.legend .items{display:none; margin-top:.25rem;
  max-height:min(46vh,300px); overflow-y:auto}
/* 狭い画面では畳んでおく。開いたままだと地図の1/3を隠す。 */
.legend.open .items{display:block}
.legend.open > b::after{content:"▴"}
@media (min-width:900px){
  .legend .items{display:block; margin-top:.25rem}
  .legend > b::after{content:""}
  .legend{cursor:default}
}
.legend .items div{display:flex; align-items:center; gap:.32rem; white-space:nowrap}
.legend i{width:9px; height:9px; border-radius:50%; flex:none; display:block}
.ctl{position:absolute; top:.5rem; right:.5rem; display:flex; flex-direction:column; gap:.3rem}
.ctl button{
  width:34px; height:34px; border:1px solid var(--rule); background:var(--panel);
  color:var(--ink-soft); border-radius:6px; cursor:pointer; font:inherit; font-size:1rem;
}
.ctl button:active{background:var(--panel-2)}

/* ---- タップしたときのカード ---- */
.card{
  position:absolute; left:.6rem; right:.6rem; bottom:.6rem; z-index:10;
  background:var(--panel); border:1px solid var(--rule); border-radius:10px;
  box-shadow:0 6px 24px rgba(0,0,0,.16); padding:.6rem .7rem;
  max-width:420px; margin-inline:auto;
  animation:cardIn .18s ease;
}
@keyframes cardIn{from{transform:translateY(18px);opacity:0}to{transform:none;opacity:1}}
@media (prefers-reduced-motion:reduce){ .card{animation:none} }
.shotbox{
  position:relative; overflow:hidden; border-radius:6px;
  background:var(--panel-2); touch-action:none; cursor:grab;
}
.shotbox img{
  width:100%; display:block; transform-origin:0 0;
  will-change:transform; user-select:none; -webkit-user-drag:none;
}
.shotbox.zoomed{cursor:grab}
.shotbox .zhint{
  position:absolute; right:.3rem; bottom:.3rem; z-index:2;
  background:color-mix(in srgb,var(--panel) 88%,transparent);
  border-radius:4px; padding:.1rem .35rem; font-size:.66rem;
  color:var(--ink-faint); font-family:"IBM Plex Mono",monospace;
  pointer-events:none; transition:opacity .2s;
}
.shotbox.zoomed .zhint{opacity:0}
.card .ld{height:150px; display:grid; place-items:center; border-radius:6px;
  background:var(--panel-2); color:var(--ink-faint); font-size:.8rem}
.card .tags{display:flex; flex-wrap:wrap; gap:.3rem; margin:.5rem 0 0}
.chip{
  font-size:.78rem; padding:.16rem .5rem; border-radius:999px;
  background:var(--accent); color:#fff; font-weight:500;
}
.chip.none{background:var(--panel-2); color:var(--ink-faint); font-weight:400}
.card .foot{
  display:flex; justify-content:space-between; align-items:baseline; gap:.6rem;
  margin-top:.45rem; font-size:.74rem; color:var(--ink-faint);
  font-family:"IBM Plex Mono",monospace;
}
.card .foot a{color:var(--accent); text-decoration:none; white-space:nowrap}
.card .x{
  position:absolute; top:.3rem; right:.35rem; width:28px; height:28px; border:0;
  background:transparent; color:var(--ink-faint); font-size:1.05rem; cursor:pointer;
  line-height:1;
}
.hintbar{
  position:absolute; left:0; right:0; bottom:.7rem; text-align:center;
  font-size:.76rem; color:var(--ink-faint); pointer-events:none;
  transition:opacity .2s;
}
.hintbar.hide{opacity:0}
.more{
  height:34px; padding:0 .9rem; border-top:1px solid var(--rule); background:var(--panel);
  font-size:.76rem; display:flex; gap:.9rem; align-items:center;
  overflow-x:auto; white-space:nowrap;
}
.more a{color:var(--accent); text-decoration:none}
@media (prefers-reduced-motion:reduce){*{transition:none!important}}
</style>
</head><body>
<header>
  <h1>世界の道端の植物</h1>
  <span class="count" id="cnt"></span>
</header>
<div class="mapwrap">
<svg class="map" id="map" viewBox="0 0 2000 1000" preserveAspectRatio="xMidYMid meet" role="img" aria-label="撮影地点の地図">
<g id="cam">
<path class="land" d="__LAND__"/>
<g id="pts"></g>
</g></svg>
<div class="ctl">
  <button id="zin" title="拡大" aria-label="拡大">＋</button>
  <button id="zout" title="縮小" aria-label="縮小">−</button>
  <button id="zrst" title="全体表示" aria-label="全体表示">⟲</button>
</div>
<div class="legend" id="legend"></div>
<p class="hintbar" id="hint">点をタップすると、その地点の写真が出ます</p>
<div class="card" id="card" hidden>
  <button class="x" id="cx" aria-label="閉じる">✕</button>
  <div id="cbody"></div>
</div>
</div>
<div class="more">
  <a href="analysis.html">分析レポート</a>
  <a href="tag_atlas.html">タグ別の分布</a>
  <a href="flora_atlas.html">48種の見分け方</a>
  <a href="https://github.com/dmkn013/geoguessr-flora">GitHub</a>
</div>
<script>
const D = __DATA__;
document.getElementById('cnt').textContent =
  D.n.toLocaleString() + '地点 / ' + D.tags.length + '分類群';

/* ---- 凡例 ---- */
const LEG = document.getElementById('legend');
LEG.innerHTML = '<b>特定できた植物</b><div class="items">' +
  D.legend.map((t, i) =>
    '<div><i class="lc' + i + '"></i>' + t + '</div>').join('') +
  '<div><i class="lc12"></i>その他</div></div>';
LEG.addEventListener('click', () => LEG.classList.toggle('open'));
// 凡例の色見本は CSS の fill を使えないので、同じ色を背景に入れる
{
  const cs = getComputedStyle(document.documentElement);
  const cols = ['#1f77b4','#ff7f0e','#2ca02c','#d62728','#9467bd','#8c564b',
                '#e377c2','#17becf','#bcbd22','#7f7f7f','#aec7e8','#ffbb78','#c49a6c'];
  cols.forEach((c, i) => LEG.querySelectorAll('.lc' + i)
    .forEach(e => e.style.background = c));
}

const ptsG = document.getElementById('pts');
const camG = document.getElementById('cam');
const mapEl = document.getElementById('map');
const card = document.getElementById('card');
const cbody = document.getElementById('cbody');
const hint = document.getElementById('hint');

/* ---- 点を描く ----
   1万点あるので DOM を作るのは1回だけ。以降は transform だけ動かす。
   「植物あり」を大きく濃く、「なし」を小さく薄くして、
   拡大しなくても分布の差が読めるようにする。 */
const frag = document.createDocumentFragment();
D.pts.forEach((p, i) => {
  const c = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
  c.setAttribute('cx', p[0]); c.setAttribute('cy', p[1]);
  c.setAttribute('r', 3.2);
  c.setAttribute('class', 'pt c' + p[6]);
  c.dataset.i = i;
  frag.appendChild(c);
});
ptsG.appendChild(frag);
const nodes = [...ptsG.children];

/* ---- カメラ ---- */
// 拡大の上限。点は10,001個あって密集地では重なるので、
// 街区レベルまで寄れないと個別にタップできない。
const MAXK = 200;
let cam = {k:1, x:0, y:0};
function applyCam() {
  camG.setAttribute('transform',
    'translate(' + cam.x + ',' + cam.y + ') scale(' + cam.k + ')');
  // 1/k だと画面上のピクセルは一定になるが、拡大するほど点どうしが
  // 離れるので相対的に小さく見え、タップもしづらい。
  // k^0.72 で割ると、拡大につれて画面上では少しずつ大きくなる。
  const sh = Math.pow(cam.k, 0.45);
  nodes.forEach(c => c.setAttribute('r', 3.2 / sh));
}
function zoomAt(f, cx, cy) {
  const k2 = Math.min(MAXK, Math.max(1, cam.k * f));
  const r = k2 / cam.k;
  cam.x = cx - (cx - cam.x) * r;
  cam.y = cy - (cy - cam.y) * r;
  cam.k = k2;
  if (cam.k === 1) { cam.x = 0; cam.y = 0; }
  applyCam();
}
function mapPoint(cx, cy) {
  // meet では viewBox 全体が収まるように縮小され、余った側に余白が出る。
  // その余白ぶん原点がずれるので、単純な比率換算では合わない。
  const r = mapEl.getBoundingClientRect();
  const s = Math.min(r.width / 2000, r.height / 1000);   // meet = min
  return {x: (cx - r.left - (r.width - 2000 * s) / 2) / s,
          y: (cy - r.top - (r.height - 1000 * s) / 2) / s};
}
mapEl.addEventListener('wheel', e => {
  e.preventDefault();
  const m = mapPoint(e.clientX, e.clientY);
  zoomAt(e.deltaY < 0 ? 1.2 : 1/1.2, m.x, m.y);
}, {passive:false});

/* ---- パンとピンチ ----
   ポインタを複数追う。1本ならドラッグ、2本なら指の間隔で拡大。
   setPointerCapture は1本目だけにする。2本目も取ると片方しか
   届かず、ピンチが検出できない。 */
const ptrs = new Map();
let drag = null, pinch = null, moved = 0;

mapEl.addEventListener('pointerdown', e => {
  ptrs.set(e.pointerId, e);
  if (ptrs.size === 1) {
    try { mapEl.setPointerCapture(e.pointerId); } catch (_) {}
    drag = {x:e.clientX, y:e.clientY, cx:cam.x, cy:cam.y};
    moved = 0;
  } else if (ptrs.size === 2) {
    drag = null;
    const [a, b] = [...ptrs.values()];
    pinch = {
      d: Math.hypot(a.clientX-b.clientX, a.clientY-b.clientY),
      mid: mapPoint((a.clientX+b.clientX)/2, (a.clientY+b.clientY)/2),
      k: cam.k, cx: cam.x, cy: cam.y
    };
  }
});
mapEl.addEventListener('pointermove', e => {
  if (!ptrs.has(e.pointerId)) return;
  ptrs.set(e.pointerId, e);
  if (ptrs.size >= 2 && pinch) {
    const [a, b] = [...ptrs.values()];
    const d = Math.hypot(a.clientX-b.clientX, a.clientY-b.clientY);
    if (pinch.d < 1) return;
    const k2 = Math.min(MAXK, Math.max(1, pinch.k * (d / pinch.d)));
    const m = pinch.mid, ratio = k2 / pinch.k;
    cam.k = k2;
    cam.x = m.x - (m.x - pinch.cx) * ratio;
    cam.y = m.y - (m.y - pinch.cy) * ratio;
    if (cam.k === 1) { cam.x = 0; cam.y = 0; }
    applyCam();
    moved = 99;               // ピンチ直後をタップと誤認しない
    return;
  }
  if (!drag) return;
  const r = mapEl.getBoundingClientRect();
  const sc = Math.min(r.width / 2000, r.height / 1000);
  moved += Math.abs(e.clientX - drag.x) + Math.abs(e.clientY - drag.y);
  cam.x = drag.cx + (e.clientX - drag.x) / sc;
  cam.y = drag.cy + (e.clientY - drag.y) / sc;
  applyCam();
});
function endPtr(e) {
  ptrs.delete(e.pointerId);
  if (ptrs.size < 2) pinch = null;
  if (ptrs.size === 1) {
    // 片方を離したら、残った指でドラッグを続けられるようにする
    const [a] = [...ptrs.values()];
    drag = {x:a.clientX, y:a.clientY, cx:cam.x, cy:cam.y};
  }
  if (ptrs.size === 0) drag = null;
}
mapEl.addEventListener('pointerup', endPtr);
mapEl.addEventListener('pointercancel', endPtr);

document.getElementById('zin').onclick = () => zoomAt(1.5, 1000, 500);
document.getElementById('zout').onclick = () => zoomAt(1/1.5, 1000, 500);
document.getElementById('zrst').onclick = () => { cam = {k:1,x:0,y:0}; applyCam(); };

/* ---- タップ → 写真とタグ ----
   写真は photos/<画像ID>.jpg に元画質のまま置いてある。
   base64 をタイルにまとめる方式もやったが、1枚見るのに数MB
   まとめて落とすことになり、キャッシュも効かなかった。
   個別の JPEG なら必要な1枚だけで済む（平均100KB）。

   「植物なし」の点にも写真がある。何が写っていて何が識別
   できなかったのかを確かめられる。 */
let want = null;

/* 写真の拡大。
   地図と同じく2本指のピンチと1本指のドラッグ。
   拡大していないときのドラッグはカードの操作を邪魔しないよう素通しする。
   等倍に戻すには縮小方向にピンチする。 */
function enableZoom(box, im) {
  let k = 1, tx = 0, ty = 0;
  const ptrs = new Map();
  let pinch = null, drag = null;

  const apply = () => {
    // 拡大時に画像が枠から離れないよう、移動量を内側に収める
    const w = box.clientWidth, h = box.clientHeight;
    const maxX = w * (k - 1), maxY = h * (k - 1);
    tx = Math.min(0, Math.max(-maxX, tx));
    ty = Math.min(0, Math.max(-maxY, ty));
    im.style.transform =
      'translate(' + tx + 'px,' + ty + 'px) scale(' + k + ')';
    box.classList.toggle('zoomed', k > 1.02);
  };
  const zoomAtLocal = (f, cx, cy) => {
    const k2 = Math.min(8, Math.max(1, k * f));
    const r = k2 / k;
    tx = cx - (cx - tx) * r;
    ty = cy - (cy - ty) * r;
    k = k2;
    if (k <= 1.001) { k = 1; tx = 0; ty = 0; }
    apply();
  };
  const local = (e) => {
    const r = box.getBoundingClientRect();
    return {x: e.clientX - r.left, y: e.clientY - r.top};
  };

  box.addEventListener('pointerdown', e => {
    ptrs.set(e.pointerId, e);
    if (ptrs.size === 1) {
      // 失敗しても以降の処理を止めない（NotFoundError を投げることがある）
      try { box.setPointerCapture(e.pointerId); } catch (_) {}
      drag = k > 1 ? {...local(e), tx, ty} : null;
    } else if (ptrs.size === 2) {
      drag = null;
      const [a, b] = [...ptrs.values()];
      const la = local(a), lb = local(b);
      pinch = {
        d: Math.hypot(a.clientX-b.clientX, a.clientY-b.clientY),
        cx: (la.x + lb.x) / 2, cy: (la.y + lb.y) / 2,
        k, tx, ty
      };
    }
  });
  box.addEventListener('pointermove', e => {
    if (!ptrs.has(e.pointerId)) return;
    ptrs.set(e.pointerId, e);
    if (ptrs.size >= 2 && pinch) {
      const [a, b] = [...ptrs.values()];
      const d = Math.hypot(a.clientX-b.clientX, a.clientY-b.clientY);
      if (pinch.d < 1) return;
      const k2 = Math.min(8, Math.max(1, pinch.k * (d / pinch.d)));
      const r = k2 / pinch.k;
      k = k2;
      tx = pinch.cx - (pinch.cx - pinch.tx) * r;
      ty = pinch.cy - (pinch.cy - pinch.ty) * r;
      if (k <= 1.001) { k = 1; tx = 0; ty = 0; }
      apply();
      return;
    }
    if (!drag) return;
    const p = local(e);
    tx = drag.tx + (p.x - drag.x);
    ty = drag.ty + (p.y - drag.y);
    apply();
  });
  const end = e => {
    ptrs.delete(e.pointerId);
    if (ptrs.size < 2) pinch = null;
    if (ptrs.size === 0) drag = null;
    else if (ptrs.size === 1 && k > 1) {
      const [a] = [...ptrs.values()];
      drag = {...local(a), tx, ty};
    }
  };
  box.addEventListener('pointerup', end);
  box.addEventListener('pointercancel', end);
  box.addEventListener('wheel', e => {
    e.preventDefault();
    const p = local(e);
    zoomAtLocal(e.deltaY < 0 ? 1.25 : 1/1.25, p.x, p.y);
  }, {passive:false});
}

function openCard(i) {
  const p = D.pts[i];
  const lat = p[2], lon = p[3], id = p[4], names = p[5];
  want = id;
  nodes.forEach(c => c.classList.remove('on'));
  nodes[i].classList.add('on');
  hint.classList.add('hide');

  const chips = names.map(n => '<span class="chip">' + n + '</span>').join('');
  const gmap = 'https://www.google.com/maps/@' + lat + ',' + lon + ',14z/data=!5m1!1e4';
  const foot = '<div class="foot"><span>' + lat.toFixed(3) + ', ' + lon.toFixed(3) +
    '</span><a href="' + gmap + '" target="_blank" rel="noopener">地図で開く</a></div>';
  const tail = '<div class="tags">' + chips + '</div>' + foot;

  cbody.innerHTML = '<div class="ld">読み込み中…</div>' + tail;
  card.hidden = false;

  const im = new Image();
  im.alt = 'この地点の車載写真';
  im.onload = () => {
    if (want !== id) return;              // 別の点に移っていたら捨てる
    cbody.innerHTML = '';
    const box = document.createElement('div');
    box.className = 'shotbox';
    box.appendChild(im);
    box.insertAdjacentHTML('beforeend',
      '<span class="zhint">2本指で拡大</span>');
    cbody.appendChild(box);
    cbody.insertAdjacentHTML('beforeend', tail);
    enableZoom(box, im);
  };
  im.onerror = () => {
    if (want !== id) return;
    cbody.innerHTML = '<div class="ld">写真を読み込めませんでした</div>' + tail;
  };
  im.src = 'photos/' + id + '.jpg';
}

function closeCard() {
  card.hidden = true;
  want = null;
  nodes.forEach(c => c.classList.remove('on'));
  hint.classList.remove('hide');
}
document.getElementById('cx').onclick = closeCard;

/* タップ判定。
   e.target に頼ると、点の描画サイズ（数px）に正確に触れないと反応せず、
   かなり拡大しないと写真が出せなかった。
   **タップ位置から一定範囲内で最も近い点**を探す。指の太さを考えて
   半径は画面上 22px 相当（指のタップ領域はおよそこのくらい）。 */
const HIT_PX = 22;

function nearestPoint(clientX, clientY) {
  const m = mapPoint(clientX, clientY);          // viewBox 座標
  const r = mapEl.getBoundingClientRect();
  const disp = Math.min(r.width / 2000, r.height / 1000) * cam.k;  // 1単位=何px
  const lim = HIT_PX / disp;                     // viewBox 単位のしきい値
  // カメラ変換を戻して、点の元座標での距離を測る
  const px = (m.x - cam.x) / cam.k, py = (m.y - cam.y) / cam.k;
  let best = -1, bestD = lim * lim;
  for (let i = 0; i < D.pts.length; i++) {
    const dx = D.pts[i][0] - px, dy = D.pts[i][1] - py;
    const d = dx * dx + dy * dy;
    if (d < bestD) { bestD = d; best = i; }
  }
  return best;
}

mapEl.addEventListener('click', e => {
  if (moved > 8) { moved = 0; return; }    // ドラッグの終わりをタップと誤認しない
  const i = nearestPoint(e.clientX, e.clientY);
  if (i >= 0) openCard(i);
  else closeCard();
});

/* 初期倍率。
   縦長の画面では 2:1 の地図が画面のごく一部になり、点が小さすぎて
   押せない。地図が画面を埋めるところから始める（世界全体は
   縮小ボタンかピンチで見られる）。 */
function fitInitial() {
  const r = mapEl.getBoundingClientRect();
  const meet = Math.min(r.width / 2000, r.height / 1000);
  const fill = Math.max(r.width / 2000, r.height / 1000);
  const k = Math.min(6, fill / meet);
  if (k > 1.05) { cam = {k, x: 1000 - 1000 * k, y: 500 - 500 * k}; }
  applyCam();
}
fitInitial();
// スクリプト実行時点ではレイアウトが未確定で、
// getBoundingClientRect が 0 を返すことがある（実際に初期倍率が
// 効かず地図が小さいままになった）。読み込み後にもう一度合わせる。
addEventListener('load', () => { if (cam.k === 1) fitInitial(); });
</script></body></html>"""


if __name__ == "__main__":
    main()
