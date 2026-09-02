# -*- coding: utf-8 -*-
"""タグ付け結果から「世界の道端で実際に何が見えるか」の地図を作る。

前回の flora_atlas.html とは別の成果物:
  flora_atlas = 48種を先に決めて、その分布域を描いた教材
  こちら       = **世界からランダムに引いた実測**。分布域は仮定していない

出せるもの:
  - タグごとの出現率（世界の道端を1回引いたときに見える確率）
  - タグごとの分布（実際に写っていた地点）
  - **地域の絞り込み力**。出現率が高くても全大陸に散らばる種
    （マツ属）は場所を絞れない。逆に出現率が低くても一箇所に
    集中する種は、見えたときの情報量が大きい。
"""
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent))

from paths import DATA, DIST  # noqa: E402
from regions import region_of  # noqa: E402

TAGS = DATA / "tags.json"
INDEX = DATA / "random_index.json"
LAND = DATA / "land_path.txt"
OUT = DIST / "tag_atlas.html"

VIEW_W, VIEW_H = 2000.0, 1000.0
LAT_TOP, LAT_BOTTOM = 84.0, -56.0

# 上位いくつまで地図に出すか。少なすぎる種は点が散らばるだけで
# 傾向が読めないので、最低この枚数は要る。
MIN_COUNT = 3


def project(lat, lon):
    x = (lon + 180.0) / 360.0 * VIEW_W
    y = (LAT_TOP - lat) / (LAT_TOP - LAT_BOTTOM) * VIEW_H
    return round(x, 1), round(y, 1)


def entropy(counts, total_regions):
    """地域分布のばらつき。低いほど一箇所に集中＝絞り込みに使える。

    **分母は「そのタグが出た地域数」ではなく「全体の地域数」**。
    自分が出た地域数で割ると、2地域にしか出ないタグでも均等なら
    100になってしまい、豪州に集中するユーカリ属が85、
    中国＋数カ国のポプラ属が92 という逆転が起きた（実際に踏んだ）。

    1に近い = 全世界に散らばる（マツ属）
    0に近い = 一箇所に集中（ユーカリ属）
    """
    n = sum(counts.values())
    if n == 0 or total_regions <= 1:
        return 0.0
    h = -sum((v / n) * math.log(v / n) for v in counts.values() if v)
    return min(1.0, h / math.log(total_regions))


def main():
    tags = json.loads(TAGS.read_text(encoding="utf-8"))
    idx = {x["img_id"]: x for x in json.loads(INDEX.read_text(encoding="utf-8"))}
    land = LAND.read_text(encoding="utf-8")

    judged = len(tags)
    empty = sum(1 for v in tags.values() if not v)

    # タグごとに点と地域を集める
    pts = defaultdict(list)
    regions = defaultdict(Counter)
    for img_id, names in tags.items():
        it = idx.get(img_id)
        if not it:
            continue
        for name in names:
            x, y = project(it["lat"], it["lon"])
            pts[name].append({"x": x, "y": y,
                              "lat": round(it["lat"], 3),
                              "lon": round(it["lon"], 3)})
            regions[name][region_of(it["lat"], it["lon"])] += 1

    # 「植物なし」の点も出す（世界のどこで識別できなかったか）
    none_pts = []
    for img_id, names in tags.items():
        if names:
            continue
        it = idx.get(img_id)
        if it:
            x, y = project(it["lat"], it["lon"])
            none_pts.append({"x": x, "y": y})

    # 拡散の分母に使う「世界にいくつ地域があるか」。
    # 実際にデータが出た地域の総数を使う（理論上の地域数ではなく）。
    all_regions = set()
    for reg in regions.values():
        all_regions |= set(reg)
    n_regions = len(all_regions)

    data = []
    for name, ps in sorted(pts.items(), key=lambda kv: -len(kv[1])):
        if len(ps) < MIN_COUNT:
            continue
        reg = regions[name]
        data.append({
            "name": name,
            "n": len(ps),
            "rate": round(len(ps) / judged * 100, 2),
            "spread": round(entropy(reg, n_regions), 3),
            "regions": [{"r": r, "n": c} for r, c in reg.most_common(6)],
            "pts": ps,
        })

    payload = json.dumps({
        "tags": data, "judged": judged, "empty": empty,
        "collected": len(idx), "none_pts": none_pts,
    }, ensure_ascii=False)

    html = TEMPLATE.replace("__LAND__", land).replace("__DATA__", payload)
    OUT.write_text(html, encoding="utf-8")
    print(f"書き出し: {OUT}  ({len(html.encode()) / 1048576:.1f} MB)")
    print(f"  判定 {judged}枚 / 収集 {len(idx)}枚 / タグ {len(data)}種類")


TEMPLATE = r"""<!doctype html><html lang="ja"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>世界の道端の植物</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Spectral:wght@500;600&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
:root{
  --bg:#e8e5dd; --panel:#faf9f6; --panel-2:#efece5; --ink:#1c1b19;
  --ink-soft:#55524c; --ink-faint:#8a8780; --rule:#d8d5cd; --accent:#c0563c;
  --ocean:#e4e1d9; --land:#d6d5cd; --edge:#b3b2a9;
  --shadow:0 4px 18px rgba(0,0,0,.13);
}
:root:not([data-theme="light"]){}
@media (prefers-color-scheme:dark){
  :root:not([data-theme="light"]){
    --bg:#14181a; --panel:#181d20; --panel-2:#20262a; --ink:#e8e5dd;
    --ink-soft:#b0aca4; --ink-faint:#807c74; --rule:#2e353a; --accent:#e0714f;
    --ocean:#0c1114; --land:#2b322f; --edge:#434b47;
    --shadow:0 4px 18px rgba(0,0,0,.4);
  }
}
:root[data-theme="dark"]{
  --bg:#14181a; --panel:#181d20; --panel-2:#20262a; --ink:#e8e5dd;
  --ink-soft:#b0aca4; --ink-faint:#807c74; --rule:#2e353a; --accent:#e0714f;
  --ocean:#0c1114; --land:#2b322f; --edge:#434b47;
  --shadow:0 4px 18px rgba(0,0,0,.4);
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
  font-family:"IBM Plex Sans","Hiragino Kaku Gothic ProN","Yu Gothic",system-ui,sans-serif;
  line-height:1.65}
h1,h2,h3{font-family:Spectral,"Hiragino Mincho ProN",Georgia,serif;font-weight:600;margin:0}
.mono{font-family:"IBM Plex Mono",ui-monospace,monospace;font-variant-numeric:tabular-nums}
header{padding:1rem 1.2rem .8rem;border-bottom:1px solid var(--rule);background:var(--panel)}
h1{font-size:1.25rem}
.sub{margin:.4rem 0 0;font-size:.85rem;color:var(--ink-soft);max-width:78ch}
.sub strong{color:var(--ink)}
.wrap{display:grid;grid-template-columns:1fr 340px;gap:0;height:calc(100vh - 118px)}
@media(max-width:900px){.wrap{grid-template-columns:1fr;height:auto}}
.mapwrap{position:relative;overflow:hidden;background:var(--ocean)}
svg.map{display:block;width:100%;height:100%}
.land{fill:var(--land);stroke:var(--edge);stroke-width:.6}
.pt{opacity:.85;cursor:pointer}
.pt.dim{opacity:.06}
.npt{fill:var(--ink-faint);opacity:.16}
.side{border-left:1px solid var(--rule);background:var(--panel);overflow-y:auto;padding:.8rem}
@media(max-width:900px){.side{border-left:0;border-top:1px solid var(--rule);max-height:60vh}}
.stat{font-size:.8rem;color:var(--ink-soft);margin-bottom:.7rem;padding-bottom:.7rem;
  border-bottom:1px solid var(--rule)}
.stat b{color:var(--ink);font-size:1.05rem}
.row{display:grid;grid-template-columns:1fr 54px 46px;gap:.4rem;align-items:center;
  padding:.28rem .35rem;border-radius:5px;cursor:pointer;font-size:.82rem}
.row:hover{background:var(--panel-2)}
.row.on{background:var(--accent);color:#fff}
.row.on .n,.row.on .sp{color:rgba(255,255,255,.85)}
.sw{width:9px;height:9px;border-radius:50%;display:inline-block;margin-right:.4rem;flex:none}
.nm{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.n{text-align:right;color:var(--ink-soft);font-size:.76rem}
.sp{text-align:right;color:var(--ink-faint);font-size:.7rem}
.hd{display:grid;grid-template-columns:1fr 54px 46px;gap:.4rem;font-size:.66rem;
  color:var(--ink-faint);padding:0 .35rem .3rem;letter-spacing:.04em}
.det{margin-top:.7rem;padding-top:.7rem;border-top:1px solid var(--rule);font-size:.8rem}
.det h3{font-size:1rem;margin-bottom:.15rem}
.det .meta{color:var(--ink-faint);font-size:.72rem;margin-bottom:.5rem}
.bar{display:grid;grid-template-columns:1fr 34px;gap:.4rem;align-items:center;
  font-size:.76rem;padding:.1rem 0}
.bar .t{position:relative;height:8px;background:var(--panel-2);border-radius:4px;
  border:1px solid var(--rule);overflow:hidden}
.bar .t i{position:absolute;left:0;top:0;bottom:0;background:var(--accent);opacity:.5}
.bar .l{color:var(--ink-soft);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.note{font-size:.72rem;color:var(--ink-faint);margin-top:.5rem;line-height:1.55}
.empty{color:var(--ink-faint);font-size:.82rem;text-align:center;padding:1.2rem 0}
.ctl{position:absolute;right:.6rem;top:.6rem;display:flex;flex-direction:column;gap:.25rem}
.ctl button{width:28px;height:28px;border:1px solid var(--rule);background:var(--panel);
  color:var(--ink-soft);border-radius:5px;cursor:pointer;font:inherit;font-size:.9rem}
.ctl button:hover{border-color:var(--accent);color:var(--accent)}
@media(prefers-reduced-motion:reduce){*{transition:none!important}}
</style></head><body>
<header>
<h1>世界の道端の植物</h1>
<p class="sub">Mapillary の車載写真を<strong>世界の陸地からランダムに</strong>引き、
写っている植物にタグを付けた実測。48種を先に決めた地図とは違い、
<strong>分布域を仮定していない</strong>。左の点は実際に写っていた地点。
灰色の点は「識別できる植物が無かった」地点。</p>
</header>
<div class="wrap">
<div class="mapwrap">
<svg class="map" id="map" viewBox="0 0 2000 1000" role="img" aria-label="タグの分布地図">
<g id="cam">
<path class="land" d="__LAND__"/>
<g id="npts"></g>
<g id="pts"></g>
</g></svg>
<div class="ctl">
<button id="zin" title="拡大">＋</button>
<button id="zout" title="縮小">−</button>
<button id="zrst" title="リセット">⟲</button>
</div>
</div>
<div class="side">
<div class="stat" id="stat"></div>
<div class="hd"><span>タグ</span><span style="text-align:right">枚数</span><span style="text-align:right">拡散</span></div>
<div id="list"></div>
<div class="det" id="det"><p class="empty">タグを選ぶと分布が出ます</p></div>
</div>
</div>
<script>
const D = __DATA__;
// tab10。近い順位のタグが同系色にならないよう間を空けて配る
const PAL = ['#4E79A7','#F28E2B','#59A14F','#E15759','#B07AA1',
             '#76B7B2','#EDC948','#FF9DA7','#9C755F','#BAB0AC'];
const color = i => PAL[(i * 3) % PAL.length];

const statEl = document.getElementById('stat');
statEl.innerHTML =
  '<b>' + D.judged.toLocaleString() + '</b> 枚を判定 '
  + '<span class="mono">/ ' + D.collected.toLocaleString() + '枚収集</span><br>'
  + '識別できる植物なし <b>' + Math.round(D.empty / D.judged * 100) + '%</b>'
  + '<span class="mono"> (' + D.empty.toLocaleString() + '枚)</span>';

/* 「植物なし」の点。世界のどこで識別できなかったかを薄く敷く */
const nptsG = document.getElementById('npts');
const nf = document.createDocumentFragment();
D.none_pts.forEach(p => {
  const c = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
  c.setAttribute('cx', p.x); c.setAttribute('cy', p.y);
  c.setAttribute('r', 1.6); c.setAttribute('class', 'npt');
  nf.appendChild(c);
});
nptsG.appendChild(nf);

const ptsG = document.getElementById('pts');
const listEl = document.getElementById('list');
const detEl = document.getElementById('det');
let sel = null;

D.tags.forEach((t, i) => {
  const col = color(i);
  t.color = col;
  const f = document.createDocumentFragment();
  t.pts.forEach(p => {
    const c = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
    c.setAttribute('cx', p.x); c.setAttribute('cy', p.y);
    c.setAttribute('r', 3.4); c.setAttribute('fill', col);
    c.setAttribute('class', 'pt'); c.dataset.t = t.name;
    c.setAttribute('role', 'button');
    c.setAttribute('aria-label', t.name + ' ' + p.lat + ',' + p.lon);
    f.appendChild(c);
  });
  ptsG.appendChild(f);

  const row = document.createElement('div');
  row.className = 'row'; row.dataset.t = t.name;
  row.innerHTML = '<span class="nm"><span class="sw" style="background:' + col + '"></span>'
    + t.name + '</span>'
    + '<span class="n mono">' + t.n + '</span>'
    + '<span class="sp mono">' + (t.spread * 100).toFixed(0) + '</span>';
  row.onclick = () => select(t.name === sel ? null : t.name);
  listEl.appendChild(row);
});

function select(name) {
  sel = name;
  [...ptsG.children].forEach(c =>
    c.classList.toggle('dim', !!name && c.dataset.t !== name));
  [...listEl.children].forEach(r =>
    r.classList.toggle('on', r.dataset.t === name));
  const t = D.tags.find(x => x.name === name);
  if (!t) { detEl.innerHTML = '<p class="empty">タグを選ぶと分布が出ます</p>'; return; }
  const max = Math.max(...t.regions.map(r => r.n));
  detEl.innerHTML =
    '<h3><span class="sw" style="background:' + t.color + '"></span>' + t.name + '</h3>'
    + '<div class="meta mono">' + t.n + '枚 / 出現率 ' + t.rate + '%'
    + ' / 拡散 ' + (t.spread * 100).toFixed(0) + '</div>'
    + t.regions.map(r =>
        '<div class="bar"><span class="l">' + r.r + '</span>'
        + '<span class="t"><i style="width:' + (r.n / max * 100) + '%"></i></span>'
        + '<span class="n mono">' + r.n + '</span></div>').join('')
    + '<p class="note"><strong>拡散</strong>は地域分布のばらつき（0〜100）。'
    + '低いほど一箇所に集中していて<strong>場所の絞り込みに使える</strong>。'
    + '高いと世界中にあるので、見えても場所が絞れない。</p>';
}
document.getElementById('pts').addEventListener('click', e => {
  if (e.target.classList.contains('pt')) select(e.target.dataset.t);
});

/* ---- パン・ズーム ---- */
let cam = {k:1, x:0, y:0};
const camG = document.getElementById('cam');
const mapEl = document.getElementById('map');
function applyCam() {
  camG.setAttribute('transform',
    'translate(' + cam.x + ',' + cam.y + ') scale(' + cam.k + ')');
  // 点は拡大しても同じ見た目の大きさに保つ
  document.documentElement.style.setProperty('--r', 3.4 / cam.k);
  [...ptsG.children].forEach(c => c.setAttribute('r', 3.4 / cam.k));
  [...nptsG.children].forEach(c => c.setAttribute('r', 1.6 / cam.k));
}
function zoomAt(f, cx, cy) {
  const k2 = Math.min(12, Math.max(1, cam.k * f));
  const r = k2 / cam.k;
  cam.x = cx - (cx - cam.x) * r;
  cam.y = cy - (cy - cam.y) * r;
  cam.k = k2;
  if (cam.k === 1) { cam.x = 0; cam.y = 0; }
  applyCam();
}
mapEl.addEventListener('wheel', e => {
  e.preventDefault();
  const r = mapEl.getBoundingClientRect();
  const sx = (e.clientX - r.left) / r.width * 2000;
  const sy = (e.clientY - r.top) / r.height * 1000;
  zoomAt(e.deltaY < 0 ? 1.2 : 1 / 1.2, sx, sy);
}, {passive:false});
let drag = null;
mapEl.addEventListener('pointerdown', e => {
  drag = {x:e.clientX, y:e.clientY, cx:cam.x, cy:cam.y};
  mapEl.setPointerCapture(e.pointerId);
});
mapEl.addEventListener('pointermove', e => {
  if (!drag) return;
  const r = mapEl.getBoundingClientRect();
  cam.x = drag.cx + (e.clientX - drag.x) / r.width * 2000;
  cam.y = drag.cy + (e.clientY - drag.y) / r.height * 1000;
  applyCam();
});
mapEl.addEventListener('pointerup', () => { drag = null; });
document.getElementById('zin').onclick = () => zoomAt(1.4, 1000, 500);
document.getElementById('zout').onclick = () => zoomAt(1/1.4, 1000, 500);
document.getElementById('zrst').onclick = () => { cam = {k:1,x:0,y:0}; applyCam(); };
</script></body></html>"""


if __name__ == "__main__":
    main()
