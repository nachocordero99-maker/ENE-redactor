from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import httpx
import os
import json
import re
from bs4 import BeautifulSoup

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

HTML_UI = r"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Redactor ENE</title>
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700;900&family=IBM+Plex+Sans:wght@300;400;500;600&display=swap" rel="stylesheet">
<style>
:root{--ink:#0f0f0f;--ink2:#3a3a3a;--paper:#f8f6f1;--paper2:#f0ede6;--accent:#c8391a;--border:#d4cfc5;--ok:#2a7a4b;--r:4px;--gold:#b8962e;}
*{box-sizing:border-box;margin:0;padding:0;}
body{font-family:'IBM Plex Sans',sans-serif;background:var(--paper);color:var(--ink);padding-bottom:50px;}
header{background:var(--ink);border-bottom:3px solid var(--accent);padding:14px 24px;color:#fff;display:flex;justify-content:space-between;align-items:center;}
.logo{font-family:'Playfair Display',serif;font-size:22px;font-weight:900;}
.logo-tag{font-size:10px;color:#e85d3a;letter-spacing:2px;text-transform:uppercase;margin-left:8px;}
#hst{font-size:11px;color:#777;}
.wrap{max-width:1100px;margin:28px auto;padding:0 20px;}
.input-card{background:#fff;border:1px solid var(--border);padding:24px;border-radius:var(--r);}
.input-card h3{font-size:13px;font-weight:600;letter-spacing:1px;text-transform:uppercase;color:var(--ink2);margin-bottom:12px;}
textarea{width:100%;min-height:200px;padding:14px;border:1px solid var(--border);border-radius:var(--r);font-family:inherit;margin-bottom:14px;resize:vertical;font-size:13px;line-height:1.7;outline:none;}
textarea:focus{border-color:var(--accent);}
.btn-row{display:flex;align-items:center;gap:12px;}
.btn{background:var(--accent);color:#fff;border:none;padding:12px 28px;border-radius:var(--r);cursor:pointer;font-weight:600;font-size:13px;font-family:inherit;}
.btn:hover{background:#a02d14;}
.btn:disabled{background:#ccc;cursor:not-allowed;}
.spin{display:none;width:14px;height:14px;border:2px solid rgba(255,255,255,.3);border-top-color:#fff;border-radius:50%;animation:spin .7s linear infinite;vertical-align:middle;margin-right:6px;}
.loading .spin{display:inline-block;}
@keyframes spin{to{transform:rotate(360deg)}}
#hst-msg{font-size:13px;color:var(--ink2);}
.results{margin-top:24px;}
.sec{border:1px solid var(--border);margin-bottom:16px;background:#fff;border-radius:var(--r);overflow:hidden;}
.sec-hd{display:flex;align-items:center;justify-content:space-between;padding:10px 16px;background:var(--paper2);border-bottom:1px solid var(--border);}
.sec-hd-left{display:flex;align-items:center;gap:8px;}
.bdg{font-size:8px;font-weight:700;letter-spacing:2px;text-transform:uppercase;padding:2px 7px;border-radius:2px;}
.b1{background:#e8f4ec;color:#2a7a4b;}
.b2{background:#fde8e3;color:#c8391a;}
.b3{background:#e8edf8;color:#2a4a9a;}
.b4{background:#fdf6e3;color:#b8962e;}
.bx{background:#e8f4f8;color:#1a6a8a;}
.sec-nm{font-size:11px;font-weight:600;color:var(--ink2);}
.cp{font-size:10px;padding:4px 10px;background:transparent;border:1px solid var(--border);border-radius:20px;cursor:pointer;color:var(--ink2);font-family:inherit;}
.cp:hover{border-color:var(--ink);color:var(--ink);}
.cp.ok{background:var(--ok);color:#fff;border-color:var(--ok);}
.sec-body{padding:18px 20px;white-space:pre-wrap;line-height:1.8;font-size:13px;}
.nota-render{padding:18px 20px;line-height:1.8;font-size:14px;}
.nota-render h1{font-family:'Playfair Display',serif;font-size:22px;margin:8px 0 12px;}
.nota-render .volanta{font-size:11px;font-weight:700;letter-spacing:2px;text-transform:uppercase;color:var(--accent);}
.nota-render .copete{font-style:italic;color:var(--ink2);margin-bottom:16px;font-size:14px;border-left:3px solid var(--accent);padding-left:12px;}
.nota-render h3{margin:18px 0 8px;font-size:15px;}
.kwcs{display:flex;flex-wrap:wrap;gap:6px;padding:14px 18px;}
.kwc{font-size:11px;padding:3px 10px;border-radius:2px;border:1px solid var(--border);color:var(--ink2);background:var(--paper);}
.kwc.pr{background:var(--ink);color:#fff;border-color:var(--ink);font-weight:500;}
.tl{padding:14px 18px;}
.ti{display:flex;gap:8px;padding:8px 0;border-bottom:1px solid var(--paper2);align-items:flex-start;}
.ti:last-child{border-bottom:none;}
.tt{font-size:9px;font-weight:700;letter-spacing:1px;text-transform:uppercase;color:var(--ink2);min-width:95px;padding-top:2px;}
.tx{font-size:13px;color:var(--ink);flex:1;line-height:1.5;}
.ti.rec .tx{font-weight:600;color:var(--accent);}
.rtag{font-size:8px;background:var(--accent);color:#fff;padding:2px 6px;border-radius:2px;white-space:nowrap;}
.mr{display:grid;grid-template-columns:120px 1fr;border-bottom:1px solid var(--paper2);}
.mr:last-child{border-bottom:none;}
.mk{font-size:10px;font-weight:600;letter-spacing:1px;text-transform:uppercase;color:var(--ink2);padding:10px 16px;background:var(--paper2);border-right:1px solid var(--border);}
.mv{padding:10px 16px;font-size:13px;color:var(--ink);}
.er{display:grid;grid-template-columns:1fr 1fr;}
.ec{padding:14px 18px;border-right:1px solid var(--border);}
.ec:last-child{border-right:none;}
.ek{font-size:10px;font-weight:600;letter-spacing:1px;text-transform:uppercase;color:var(--ink2);margin-bottom:4px;}
.ev{font-size:14px;font-weight:500;}
@media(max-width:700px){.er{grid-template-columns:1fr}.ec{border-right:none;border-bottom:1px solid var(--border)}.ec:last-child{border-bottom:none}}
</style>
</head>
<body>
<header>
  <div><span class="logo">ENE</span><span class="logo-tag">Redactor IA</span></div>
  <span id="hst">Listo</span>
</header>
<div class="wrap">
  <div class="input-card">
    <h3>Fuente — gacetilla, comunicado o texto de WhatsApp</h3>
    <textarea id="input-text" placeholder="Pegá acá el texto completo de la gacetilla o comunicado oficial..."></textarea>
    <div class="btn-row">
      <button class="btn" onclick="generate()" id="btn-gen">
        <span class="spin" id="spin"></span>
        <span id="btn-lbl">Generar nota completa →</span>
      </button>
      <span id="hst-msg"></span>
    </div>
  </div>
  <div class="results" id="results" style="display:none"></div>
</div>
<script>
const esc = s => String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
let busy = false;

async function generate(){
  if(busy) return;
  const text = document.getElementById('input-text').value.trim();
  if(!text || text.length < 20){ alert('Pegá un texto más largo antes de generar.'); return; }
  busy=true;
  const btn=document.getElementById('btn-gen');
  btn.disabled=true; btn.classList.add('loading');
  document.getElementById('btn-lbl').textContent='Generando…';
  document.getElementById('spin').style.display='inline-block';
  document.getElementById('hst-msg').textContent='Redactando nota con IA…';
  document.getElementById('hst').textContent='Generando…';
  document.getElementById('results').style.display='none';

  try{
    const r = await fetch('/generar',{
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({articles:[{title:'Entrada directa', text}], seccion:'', tono:'informativo', extras:{}})
    });
    if(!r.ok){
      const err = await r.text();
      throw new Error(err);
    }
    const d = await r.json();
    renderOut(d);
    document.getElementById('hst').textContent='Nota generada ✓';
    document.getElementById('hst-msg').textContent='';
  }catch(e){
    alert('Error: ' + e.message);
    document.getElementById('hst').textContent='Error';
    document.getElementById('hst-msg').textContent='';
  }finally{
    busy=false;
    btn.disabled=false; btn.classList.remove('loading');
    document.getElementById('btn-lbl').textContent='Generar nota completa →';
    document.getElementById('spin').style.display='none';
  }
}

function renderOut(d){
  const res = document.getElementById('results');
  const titulos = Array.isArray(d.titulos)?d.titulos:[];
  const ri = d.titulo_recomendado_index??0;
  const stripH = s=>(s||'').replace(/<[^>]+>/g,'').replace(/&[a-z]+;/g,' ').trim();

  res.innerHTML = `
    <!-- F1 -->
    <div class="sec">
      <div class="sec-hd"><div class="sec-hd-left"><span class="bdg b1">F1</span><span class="sec-nm">Clasificación · Keywords · Etiquetas</span></div><button class="cp" onclick="doCopy('kw-out',this)">⎘ Copiar</button></div>
      <div class="kwcs" id="kw-out">
        <span class="kwc pr">${esc(d.seccion)}</span>
        <span class="kwc pr">${esc(d.kw_principal||'')}</span>
        ${(d.kw_secundarias||[]).map(k=>`<span class="kwc">${esc(k)}</span>`).join('')}
        ${(d.etiquetas||[]).map(k=>`<span class="kwc">${esc(k)}</span>`).join('')}
      </div>
    </div>

    <!-- F2 -->
    <div class="sec">
      <div class="sec-hd"><div class="sec-hd-left"><span class="bdg b2">F2</span><span class="sec-nm">Nota completa</span></div><button class="cp" onclick="doCopy('nota-copy',this)">⎘ Copiar</button></div>
      <div class="nota-render">
        <div class="volanta">${esc(d.volanta||'')}</div>
        <h1>${esc(d.titulo||'')}</h1>
        <div class="copete">${esc(d.copete||'')}</div>
        <div>${(d.desarrollo||'').replace(/\n/g,'<br>')}</div>
        ${d.bloque_guia?`<div style="margin-top:16px;padding:16px;background:var(--paper2);border-radius:var(--r)">${(d.bloque_guia||'').replace(/\n/g,'<br>')}</div>`:''}
      </div>
      <div id="nota-copy" style="display:none">VOLANTA: ${stripH(d.volanta||'')}

TÍTULO: ${stripH(d.titulo||'')}

COPETE: ${stripH(d.copete||'')}

DESARROLLO:
${stripH(d.desarrollo||'')}${d.bloque_guia?'\n\nBLOQUE GUÍA:\n'+stripH(d.bloque_guia):''}${(d.interlinking||[]).length?'\n\nINTERLINKING:\n'+d.interlinking.map(l=>`→ "${l.frase}" → ${l.destino}`).join('\n'):''}</div>
    </div>

    <!-- RRSS -->
    ${d.rrss&&(d.rrss.instagram||d.rrss.twitter)?`
    <div class="sec">
      <div class="sec-hd"><div class="sec-hd-left"><span class="bdg bx">RRSS</span><span class="sec-nm">Posts redes sociales</span></div><button class="cp" onclick="doCopy('rrss-out',this)">⎘ Copiar</button></div>
      <div class="sec-body" id="rrss-out">📸 INSTAGRAM\n${d.rrss.instagram||''}\n\n𝕏 X\n${d.rrss.twitter||''}\n\n📘 FACEBOOK\n${d.rrss.facebook||''}</div>
    </div>`:''}

    <!-- SEO -->
    ${d.micro_seo?`
    <div class="sec">
      <div class="sec-hd"><div class="sec-hd-left"><span class="bdg b2">SEO</span><span class="sec-nm">Micro-bloque SEO / Discover</span></div><button class="cp" onclick="doCopy('seo-out',this)">⎘ Copiar</button></div>
      <div class="sec-body" id="seo-out">${esc(d.micro_seo)}</div>
    </div>`:''}

    <!-- F3 -->
    <div class="sec">
      <div class="sec-hd"><div class="sec-hd-left"><span class="bdg b3">F3</span><span class="sec-nm">7 títulos estratégicos</span></div><button class="cp" onclick="doCopy('tit-out',this)">⎘ Copiar</button></div>
      <div class="tl" id="tit-out">
        ${titulos.map((t,i)=>`<div class="ti${i===ri?' rec':''}"><span class="tt">${esc(t.tipo||'')}</span><span class="tx">${esc(t.texto||'')}</span>${i===ri?'<span class="rtag">✓ REC</span>':''}</div>`).join('')}
        ${d.titulo_recomendado_razon?`<div style="padding:8px 0;font-size:11px;color:var(--ink2);border-top:1px solid var(--paper2);margin-top:4px"><strong style="color:var(--accent)">¿Por qué?</strong> ${esc(d.titulo_recomendado_razon)}</div>`:''}
      </div>
    </div>

    <!-- F4 -->
    <div class="sec">
      <div class="sec-hd"><div class="sec-hd-left"><span class="bdg b4">F4</span><span class="sec-nm">Metadatos SEO</span></div><button class="cp" onclick="doCopy('meta-out',this)">⎘ Copiar</button></div>
      <div class="mg" id="meta-out">
        <div class="mr"><div class="mk">Meta title</div><div class="mv">${esc(d.meta_title||'')} <span style="color:#999;font-size:11px">(${(d.meta_title||'').length} car.)</span></div></div>
        <div class="mr"><div class="mk">Description</div><div class="mv">${esc(d.meta_description||'')} <span style="color:#999;font-size:11px">(${(d.meta_description||'').length} car.)</span></div></div>
        <div class="mr"><div class="mk">Slug</div><div class="mv">${esc(d.slug||'')}</div></div>
      </div>
    </div>

    <!-- F6 -->
    <div class="sec">
      <div class="sec-hd"><div class="sec-hd-left"><span class="bdg b1">F6</span><span class="sec-nm">Estrategia editorial</span></div></div>
      <div class="er">
        <div class="ec"><div class="ek">Portada</div><div class="ev">${esc(d.portada||'—')}</div></div>
        <div class="ec"><div class="ek">Horario sugerido</div><div class="ev">${esc(d.horario||'—')}</div></div>
      </div>
    </div>
  `;
  res.style.display='block';
  res.scrollIntoView({behavior:'smooth',block:'start'});
}

async function doCopy(id, btn){
  const el = document.getElementById(id);
  if(!el) return;
  try{ await navigator.clipboard.writeText(el.innerText||el.textContent); }catch(e){}
  btn.textContent='✓ Copiado'; btn.classList.add('ok');
  setTimeout(()=>{ btn.textContent='⎘ Copiar'; btn.classList.remove('ok'); }, 2000);
}
</script>
</body>
</html>"""

SYSTEM_PROMPT = """Actuá como editor jefe digital patagónico y estratega SEO de Diario ENE, medio regional con base en Bariloche y foco en Río Negro y la Patagonia.

ESTILO ENE: título directo, urgencia funcional, lenguaje claro, cero adjetivos grandilocuentes, pensado para el lector patagónico.
Evitar: "en el marco de", "con el objetivo de", "se llevó a cabo", párrafos de longitud idéntica.
Negrita: nombres propios, datos numéricos, keywords SEO. Cursiva: marcas, términos técnicos. Máx 15%.

RESPONDÉ SOLO con JSON válido sin markdown:
{"seccion":"","kw_principal":"","kw_secundarias":["","","","",""],"kw_longtail":["","",""],"tipo_guia":false,"etiquetas":["","","",""],"volanta":"","titulo":"","copete":"","desarrollo":"","bloque_guia":null,"interlinking":[{"frase":"","destino":""}],"micro_seo":"","rrss":{"instagram":"","twitter":"","facebook":""},"titulos":[{"tipo":"Informativo puro","texto":""},{"tipo":"Informativo puro","texto":""},{"tipo":"Impacto periodístico","texto":""},{"tipo":"Impacto periodístico","texto":""},{"tipo":"Explicativo / Contexto","texto":""},{"tipo":"Explicativo / Contexto","texto":""},{"tipo":"Híbrido estratégico","texto":""}],"titulo_recomendado_index":0,"titulo_recomendado_razon":"","meta_title":"","meta_description":"","slug":"","portada":"","horario":""}"""

class Article(BaseModel):
    title: str = ""
    text: str = ""
    url: str = ""

class GenerateRequest(BaseModel):
    articles: list[Article]
    seccion: str = ""
    tono: str = "informativo"
    extras: dict = {}

@app.get("/", response_class=HTMLResponse)
def root():
    return HTML_UI

@app.post("/generar")
async def generar(req: GenerateRequest):
    if not GEMINI_API_KEY:
        raise HTTPException(500, "Falta GEMINI_API_KEY en variables de entorno de Render")

    contexto = "\n---\n".join([f"Título: {a.title}\n{a.text}" for a in req.articles])
    user_msg = f"Procesá esta fuente y generá la nota ENE completa:\n\n{contexto}"
    if req.seccion:
        user_msg += f"\n\nSECCIÓN FORZADA: {req.seccion}"
    if req.tono != "informativo":
        user_msg += f"\n\nTONO: {req.tono}"

    url_gemini = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"

    payload = {
        "contents": [{"parts": [{"text": f"{SYSTEM_PROMPT}\n\n{user_msg}"}]}],
        "generationConfig": {
            "response_mime_type": "application/json",
            "temperature": 0.7,
            "max_output_tokens": 4000
        }
    }

    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(url_gemini, json=payload)

    if resp.status_code != 200:
        raise HTTPException(500, f"Error Gemini API: {resp.text}")

    data = resp.json()

    # Extraer texto de la respuesta
    try:
        raw = data['candidates'][0]['content']['parts'][0]['text']
    except (KeyError, IndexError) as e:
        raise HTTPException(500, f"Respuesta inesperada de Gemini: {data}")

    # Limpiar markdown si lo hay
    raw = raw.strip()
    raw = re.sub(r'^```json\s*', '', raw)
    raw = re.sub(r'^```\s*', '', raw)
    raw = re.sub(r'\s*```$', '', raw)
    raw = raw.strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        raise HTTPException(500, f"JSON inválido de Gemini: {str(e)} | Raw: {raw[:500]}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
