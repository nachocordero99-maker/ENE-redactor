from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
import httpx
import re
from bs4 import BeautifulSoup

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "es-AR,es;q=0.9",
}

SOURCES = {
    "prensa": {
        "name": "Prensa Río Negro",
        "url": "https://prensa.rionegro.gov.ar/busqueda/articulo?q=",
        "base": "https://prensa.rionegro.gov.ar",
        "selector_links": "a[href*='/articulo/']",
        "selector_title": "h2,h3,h4,h5",
        "selector_sec": "h6",
    },
    "bariloche": {
        "name": "Bariloche Informa",
        "url": "https://barilocheinforma.gob.ar",
        "base": "https://barilocheinforma.gob.ar",
        "selector_links": "a",
        "selector_title": "h2,h3,h4",
        "selector_sec": None,
    },
    "policia": {
        "name": "Policía Río Negro",
        "url": "https://policia.rionegro.gov.ar",
        "base": "https://policia.rionegro.gov.ar",
        "selector_links": "a",
        "selector_title": "h2,h3,h4",
        "selector_sec": None,
    },
}

async def scrape(source_key: str):
    src = SOURCES[source_key]
    articles = []
    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True, verify=False) as client:
            r = await client.get(src["url"], headers=HEADERS)
            soup = BeautifulSoup(r.text, "html.parser")
            seen = set()
            for a in soup.select(src["selector_links"]):
                href = a.get("href", "")
                if not href or href == "#":
                    continue
                url = href if href.startswith("http") else src["base"] + href
                if url in seen or len(url) < 20:
                    continue
                seen.add(url)
                heading = a.select_one(src["selector_title"]) if src["selector_title"] else None
                title = (heading or a).get_text(strip=True).replace("\n", " ").strip()
                if not title or len(title) < 20 or len(title) > 200:
                    continue
                sec = "—"
                if src["selector_sec"]:
                    parent = a.find_parent(["article", "div", "li"])
                    if parent:
                        sec_el = parent.select_one(src["selector_sec"])
                        if sec_el:
                            sec = re.sub(r'\d+\s+de\s+\w+\s+de\s+\d{4}', '', sec_el.get_text(strip=True)).strip()
                articles.append({"url": url, "title": title, "sec": sec})
                if len(articles) >= 20:
                    break
    except Exception as e:
        articles = [{"url": "", "title": f"Error: {e}", "sec": "—"}]
    return articles

HTML = r"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>ENE — Noticias del día</title>
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700;900&family=IBM+Plex+Sans:wght@300;400;500;600&display=swap" rel="stylesheet">
<style>
:root{--ink:#0f0f0f;--ink2:#3a3a3a;--ink3:#6b6b6b;--paper:#f8f6f1;--paper2:#f0ede6;--paper3:#e8e4db;--accent:#c8391a;--border:#d4cfc5;--ok:#2a7a4b;--r:4px;}
*{box-sizing:border-box;margin:0;padding:0;}
body{font-family:'IBM Plex Sans',sans-serif;background:var(--paper);color:var(--ink);min-height:100vh;padding-bottom:40px;}
header{background:var(--ink);border-bottom:3px solid var(--accent);padding:12px 24px;display:flex;align-items:center;justify-content:space-between;position:sticky;top:0;z-index:100;}
.logo{font-family:'Playfair Display',serif;font-size:22px;font-weight:900;color:#fff;}
.logo-tag{font-size:10px;color:#e85d3a;letter-spacing:2px;text-transform:uppercase;margin-left:8px;}
#hst{font-size:11px;color:#777;}
.wrap{max-width:1100px;margin:0 auto;padding:24px 20px;}
.src-bar{display:flex;gap:8px;margin-bottom:24px;flex-wrap:wrap;align-items:center;}
.src-chip{display:flex;align-items:center;gap:6px;padding:7px 16px;border:1px solid var(--border);border-radius:20px;font-size:12px;cursor:pointer;background:var(--paper);user-select:none;transition:all .15s;}
.src-chip input{display:none;}
.src-chip.on{background:var(--ink);color:#fff;border-color:var(--ink);}
.btn{padding:9px 20px;background:var(--accent);color:#fff;border:none;border-radius:var(--r);font-size:12px;font-weight:600;cursor:pointer;font-family:'IBM Plex Sans',sans-serif;}
.btn:hover{background:#a82e15;}
.btn:disabled{background:#bbb;cursor:not-allowed;}
.source-block{margin-bottom:28px;}
.source-title{font-size:10px;font-weight:700;letter-spacing:2px;text-transform:uppercase;color:var(--ink3);margin-bottom:10px;display:flex;align-items:center;gap:8px;}
.source-title::after{content:'';flex:1;height:1px;background:var(--border);}
.source-err{font-size:13px;color:var(--accent);padding:12px;background:#fde8e3;border-radius:var(--r);border:1px solid #f5c4b3;}
.cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:10px;}
.card{border:1px solid var(--border);border-radius:var(--r);background:#fff;padding:14px;cursor:pointer;transition:border-color .15s;position:relative;}
.card:hover{border-color:var(--ink2);}
.card.sel{border:2px solid var(--accent);background:#fff8f6;}
.card-chk{position:absolute;top:10px;right:10px;width:20px;height:20px;background:var(--accent);color:#fff;border-radius:50%;font-size:12px;font-weight:700;display:none;align-items:center;justify-content:center;}
.card.sel .card-chk{display:flex;}
.card-sec{font-size:9px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;color:var(--ink3);margin-bottom:5px;}
.card-title{font-size:13px;font-weight:600;line-height:1.45;color:var(--ink);}
.card-url{font-size:10px;color:var(--ink3);margin-top:6px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.skl{background:linear-gradient(90deg,var(--paper2) 25%,var(--paper3) 50%,var(--paper2) 75%);background-size:200% 100%;animation:sk 1.2s infinite;border-radius:var(--r);height:80px;}
@keyframes sk{0%{background-position:200% 0}100%{background-position:-200% 0}}
.sel-bar{position:sticky;bottom:0;background:#fff;border-top:2px solid var(--accent);padding:12px 24px;display:none;align-items:center;justify-content:space-between;z-index:50;}
.sel-bar.vis{display:flex;}
.sel-info{font-size:13px;color:var(--ink2);}
.sel-info b{color:var(--accent);}
</style>
</head>
<body>
<header>
  <div><span class="logo">ENE</span><span class="logo-tag">Noticias del día</span></div>
  <span id="hst">Listo</span>
</header>
<div class="wrap">
  <div class="src-bar">
    <label class="src-chip on" id="sc-prensa"><input type="checkbox" value="prensa" checked onchange="toggleSrc(this,'sc-prensa')">📰 Prensa Río Negro</label>
    <label class="src-chip" id="sc-bariloche"><input type="checkbox" value="bariloche" onchange="toggleSrc(this,'sc-bariloche')">🏔 Bariloche Informa</label>
    <label class="src-chip" id="sc-policia"><input type="checkbox" value="policia" onchange="toggleSrc(this,'sc-policia')">🚔 Policía RN</label>
    <button class="btn" id="btn-load" onclick="loadAll()">Cargar noticias →</button>
  </div>
  <div id="content"></div>
</div>
<div class="sel-bar" id="sel-bar">
  <span class="sel-info">Seleccionadas: <b id="sel-n">0</b> nota(s)</span>
  <div style="display:flex;gap:8px">
    <button class="btn" style="background:var(--ink3)" onclick="clearSel()">Limpiar</button>
    <button class="btn" id="btn-redactar" onclick="redactar()">Redactar nota ENE →</button>
  </div>
</div>
<script>
let selected = new Map(); // url -> {title, sec}
const $ = id => document.getElementById(id);
const esc = s => String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');

function toggleSrc(inp, id){ $(id).classList.toggle('on', inp.checked); }

async function loadAll(){
  const checks = [...document.querySelectorAll('.src-chip input:checked')].map(i=>i.value);
  if(!checks.length){ alert('Seleccioná al menos una fuente.'); return; }
  const btn=$('btn-load'); btn.disabled=true; btn.textContent='Cargando…';
  $('hst').textContent='Cargando noticias…';
  selected.clear(); updateSelBar();

  const content=$('content');
  content.innerHTML = checks.map(src=>`
    <div class="source-block" id="block-${src}">
      <div class="source-title">${src}</div>
      <div class="cards">${Array(6).fill(0).map(()=>`<div class="skl"></div>`).join('')}</div>
    </div>`).join('');

  await Promise.all(checks.map(src => loadSource(src)));

  btn.disabled=false; btn.textContent='Actualizar →';
  $('hst').textContent='Noticias cargadas';
}

async function loadSource(src){
  const block = $('block-'+src);
  if(!block) return;
  try{
    const r = await fetch(`/noticias/${src}`);
    const d = await r.json();
    const srcNames = {prensa:'Prensa Río Negro', bariloche:'Bariloche Informa', policia:'Policía RN'};
    block.querySelector('.source-title').textContent = srcNames[src] || src;
    if(!d.articles || !d.articles.length){
      block.querySelector('.cards').innerHTML = `<div class="source-err">No se encontraron noticias — el sitio puede estar bloqueando requests de servidor.</div>`;
      return;
    }
    block.querySelector('.cards').innerHTML = d.articles.map((a,i)=>`
      <div class="card" id="c-${src}-${i}" onclick="toggleCard('${src}',${i},'${encodeURIComponent(a.url)}','${encodeURIComponent(a.title)}','${encodeURIComponent(a.sec)}')">
        <div class="card-chk">✓</div>
        <div class="card-sec">${esc(a.sec)}</div>
        <div class="card-title">${esc(a.title.slice(0,100))}${a.title.length>100?'…':''}</div>
        <div class="card-url">${esc(a.url)}</div>
      </div>`).join('');
  }catch(e){
    block.querySelector('.cards').innerHTML = `<div class="source-err">Error: ${e.message}</div>`;
  }
}

function toggleCard(src, i, encUrl, encTitle, encSec){
  const key = `${src}-${i}`;
  const card = $(`c-${src}-${i}`);
  if(selected.has(key)){
    selected.delete(key);
    card.classList.remove('sel');
  } else {
    selected.set(key, {url: decodeURIComponent(encUrl), title: decodeURIComponent(encTitle), sec: decodeURIComponent(encSec)});
    card.classList.add('sel');
  }
  updateSelBar();
}

function clearSel(){
  selected.clear();
  document.querySelectorAll('.card.sel').forEach(c=>c.classList.remove('sel'));
  updateSelBar();
}

function updateSelBar(){
  $('sel-n').textContent = selected.size;
  $('sel-bar').classList.toggle('vis', selected.size > 0);
}

function redactar(){
  const items = [...selected.values()];
  const params = new URLSearchParams();
  items.forEach((a,i) => {
    params.set(`url${i}`, a.url);
    params.set(`title${i}`, a.title);
  });
  params.set('count', items.length);
  // Por ahora muestra las seleccionadas — cuando agreguen el generador se conecta acá
  alert(`Seleccionadas ${items.length} nota(s):\n\n${items.map(a=>a.title).join('\n')}`);
}
</script>
</body>
</html>"""

@app.get("/", response_class=HTMLResponse)
def root():
    return HTML

@app.get("/noticias/{source}")
async def get_noticias(source: str):
    if source not in SOURCES:
        return {"articles": [], "error": "Fuente no encontrada"}
    articles = await scrape(source)
    return {"articles": articles, "total": len(articles), "source": source}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(__import__('os').environ.get("PORT", 8000)))
