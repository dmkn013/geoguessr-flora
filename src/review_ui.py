# -*- coding: utf-8 -*-
"""候補写真を種ごとにブラウザで見て、クリックで採否を決めるページを作る。

    python src/review_ui.py            # dist/review.html を作る
    python src/review_ui.py --apply    # ブラウザで書き出した判定を取り込む

判定はブラウザの localStorage に貯まる。「判定を書き出す」ボタンで
decisions.json をダウンロードし、data/ に置いて --apply で反映する。

なぜHTMLか: 数百枚を「シートを見る→番号を打つ」で回すのは間違えやすい。
写真の隣に「写っていれば採用」の条件と罠を出し、クリック1回で決まる形にする。
"""
import base64
import json
import sys
from io import BytesIO
from pathlib import Path

from PIL import Image

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent))

from paths import DATA, DIST  # noqa: E402
from species import SPECIES  # noqa: E402
from verify_points import CAND, load_state, save_state  # noqa: E402

OUT = DIST / "review.html"
DEC = DATA / "decisions.json"
THUMB = (560, 420)


def enc(path):
    im = Image.open(path).convert("RGB")
    im.thumbnail(THUMB, Image.LANCZOS)
    b = BytesIO()
    im.save(b, "JPEG", quality=72, optimize=True)
    return "data:image/jpeg;base64," + base64.b64encode(b.getvalue()).decode()


def build():
    groups, total = [], 0
    for s in SPECIES:
        sid = s["id"]
        pend = CAND / sid / "_pending.json"
        if not pend.exists():
            continue
        items = json.loads(pend.read_text(encoding="utf-8"))
        st = load_state(sid)
        done = {i["img_id"] for i in st["accepted"]} | {i["img_id"] for i in st["rejected"]}
        cards = []
        for it in items:
            if it["img_id"] in done:
                continue
            f = CAND / sid / it["file"]
            if f.exists():
                cards.append({"img_id": it["img_id"], "lat": it["lat"],
                              "lon": it["lon"], "src": enc(f)})
        if cards:
            groups.append({"id": sid, "ja": s["ja"], "sci": s["sci"],
                           "tells": s["tells"], "trap": s["trap"],
                           "regions": s["regions"], "cards": cards})
            total += len(cards)
    html = TEMPLATE.replace("__DATA__", json.dumps({"groups": groups}, ensure_ascii=False))
    OUT.write_text(html, encoding="utf-8")
    print(f"書き出し: {OUT}  ({len(html.encode()) / 1048576:.1f} MB / "
          f"{total}枚 / {len(groups)}種)")
    if not total:
        print("未判定の候補が無い。先に verify_points.py を回す")


def apply():
    if not DEC.exists():
        print(f"{DEC} が無い。ブラウザで「判定を書き出す」を押し、data/ に置く")
        return
    dec = json.loads(DEC.read_text(encoding="utf-8"))
    byimg = {}
    for sid in {d["sid"] for d in dec}:
        pend = CAND / sid / "_pending.json"
        if pend.exists():
            for it in json.loads(pend.read_text(encoding="utf-8")):
                byimg[(sid, it["img_id"])] = it
    n_a = n_r = 0
    for sid in sorted({d["sid"] for d in dec}):
        st = load_state(sid)
        have = {i["img_id"] for i in st["accepted"]} | {i["img_id"] for i in st["rejected"]}
        for d in dec:
            if d["sid"] != sid or d["img_id"] in have:
                continue
            it = byimg.get((sid, d["img_id"]))
            if not it:
                continue
            if d["ok"]:
                st["accepted"].append(it)
                n_a += 1
            else:
                st["rejected"].append(it)
                n_r += 1
        save_state(sid, st)
    print(f"反映: 採用 {n_a} / 却下 {n_r}")
    print("次: python src/build_verified.py")


TEMPLATE = r"""<!doctype html><html lang="ja"><head><meta charset="utf-8">
<title>候補の判定</title><style>
:root{--bg:#f7f6f2;--panel:#fff;--ink:#1c1b19;--soft:#5b5852;--faint:#918d85;
      --rule:#e0ddd5;--ok:#3f7d4e;--ng:#b4483a}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
     font-family:"IBM Plex Sans","Hiragino Kaku Gothic ProN","Yu Gothic",system-ui,sans-serif}
header{position:sticky;top:0;z-index:5;background:var(--panel);border-bottom:1px solid var(--rule);
       padding:.7rem 1rem;display:flex;gap:1rem;align-items:center;flex-wrap:wrap}
h1{font-size:1rem;margin:0}
.prog{font-size:.82rem;color:var(--soft)}
button{font:inherit;cursor:pointer;border-radius:6px;border:1px solid var(--rule);
       background:var(--panel);padding:.3rem .7rem}
.exp{margin-left:auto;background:var(--ink);color:#fff;border-color:var(--ink)}
section{padding:1rem;border-bottom:1px solid var(--rule)}
.hd{display:flex;gap:.6rem;align-items:baseline;flex-wrap:wrap;margin-bottom:.2rem}
.hd h2{font-size:1.05rem;margin:0}
.sci{color:var(--faint);font-size:.8rem}
.tell{background:#fff;border-left:3px solid var(--ok);padding:.5rem .7rem;
      border-radius:0 6px 6px 0;font-size:.85rem;margin:.4rem 0 .2rem}
.trap{background:#fff;border-left:3px solid var(--ng);padding:.5rem .7rem;
      border-radius:0 6px 6px 0;font-size:.8rem;color:var(--soft);margin:.3rem 0 .7rem}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:.9rem}
figure{margin:0;background:var(--panel);border:1px solid var(--rule);
       border-radius:8px;overflow:hidden}
figure img{width:100%;display:block;cursor:zoom-in}
.meta{font-size:.72rem;color:var(--faint);padding:.3rem .5rem;font-variant-numeric:tabular-nums}
.btns{display:flex;gap:.4rem;padding:0 .5rem .5rem}
.btns button{flex:1}
.y{border-color:var(--ok);color:var(--ok)} .n{border-color:var(--ng);color:var(--ng)}
figure.ok{outline:3px solid var(--ok)} figure.ng{outline:3px solid var(--ng);opacity:.5}
figure.ok .y{background:var(--ok);color:#fff} figure.ng .n{background:var(--ng);color:#fff}
#zoom{position:fixed;inset:0;background:rgba(0,0,0,.92);display:none;align-items:center;
      justify-content:center;z-index:20;cursor:zoom-out}
#zoom img{max-width:98vw;max-height:98vh}
.done{color:var(--faint);font-size:.9rem;padding:1.5rem}
</style></head><body>
<header><h1>候補の判定</h1>
<span class="prog" id="prog"></span>
<span class="prog">写真クリックで拡大</span>
<button class="exp" id="exp">判定を書き出す</button></header>
<div id="root"></div>
<div id="zoom"><img id="zimg" alt=""></div>
<script>
const DATA = __DATA__;
const KEY = 'flora_decisions';
let dec = {};
try { dec = JSON.parse(localStorage.getItem(KEY) || '{}'); } catch (e) { dec = {}; }
const root = document.getElementById('root');
const total = () => DATA.groups.reduce((n, g) => n + g.cards.length, 0);
function prog() {
  document.getElementById('prog').textContent =
    Object.keys(dec).length + ' / ' + total() + ' 判定済み';
}
function save() {
  try { localStorage.setItem(KEY, JSON.stringify(dec)); } catch (e) {}
  prog();
}
function mark(sid, id, ok, fig) {
  dec[sid + '|' + id] = ok;
  fig.classList.toggle('ok', ok);
  fig.classList.toggle('ng', !ok);
  save();
}
DATA.groups.forEach(g => {
  const sec = document.createElement('section');
  sec.innerHTML =
    '<div class="hd"><h2>' + g.ja + '</h2><span class="sci">' + g.sci + ' — ' +
    g.regions.join(' / ') + '</span></div>' +
    '<div class="tell"><b>写っていれば採用:</b> ' + g.tells.join(' / ') + '</div>' +
    '<div class="trap"><b>罠:</b> ' +
    g.trap.replace(/\*\*(.+?)\*\*/g, '<b>$1</b>') + '</div>';
  const grid = document.createElement('div');
  grid.className = 'grid';
  g.cards.forEach(c => {
    const fig = document.createElement('figure');
    fig.innerHTML =
      '<img src="' + c.src + '" alt="">' +
      '<div class="meta">' + c.lat.toFixed(4) + ', ' + c.lon.toFixed(4) + '</div>' +
      '<div class="btns"><button class="y">写ってる</button>' +
      '<button class="n">写ってない</button></div>';
    const k = g.id + '|' + c.img_id;
    if (k in dec) { fig.classList.toggle('ok', dec[k]); fig.classList.toggle('ng', !dec[k]); }
    fig.querySelector('.y').onclick = () => mark(g.id, c.img_id, true, fig);
    fig.querySelector('.n').onclick = () => mark(g.id, c.img_id, false, fig);
    fig.querySelector('img').onclick = () => openZoom(c.src);
    grid.appendChild(fig);
  });
  sec.appendChild(grid);
  root.appendChild(sec);
});
if (!total()) root.innerHTML = '<p class="done">未判定の候補はありません。</p>';
prog();
const zoom = document.getElementById('zoom'), zimg = document.getElementById('zimg');
function openZoom(src) { zimg.src = src; zoom.style.display = 'flex'; }
zoom.onclick = () => { zoom.style.display = 'none'; };
document.addEventListener('keydown', e => {
  if (e.key === 'Escape') zoom.style.display = 'none';
});
document.getElementById('exp').onclick = () => {
  const out = Object.entries(dec).map(([k, v]) => {
    const i = k.indexOf('|');
    return { sid: k.slice(0, i), img_id: k.slice(i + 1), ok: v };
  });
  const blob = new Blob([JSON.stringify(out, null, 1)], { type: 'application/json' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'decisions.json';
  document.body.appendChild(a);
  a.click();
  a.remove();
};
</script></body></html>"""


if __name__ == "__main__":
    if "--apply" in sys.argv:
        apply()
    else:
        build()
