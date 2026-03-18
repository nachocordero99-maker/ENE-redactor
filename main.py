from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import httpx
import os
import json
from bs4 import BeautifulSoup

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

# --- INTERFAZ VISUAL (HTML) ---
HTML_UI = r"""
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Redactor ENE</title>
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700;900&family=IBM+Plex+Sans:wght@300;400;500;600&display=swap" rel="stylesheet">
<style>
:root{--ink:#0f0f0f;--ink2:#3a3a3a;--paper:#f8f6f1;--paper2:#f0ede6;--accent:#c8391a;--border:#d4cfc5;--ok:#2a7a4b;--r:4px;}
*{box-sizing:border-box;margin:0;padding:0;}
body{font-family:'IBM Plex Sans',sans-serif;background:var(--paper);color:var(--ink);padding-bottom:50px;}
header{background:var(--ink);border-bottom:3px solid var(--accent);padding:15px 25px;color:#fff;display:flex;justify-content:space-between;align-items:center;}
.logo{font-family:'Playfair Display',serif;font-size:24px;font-weight:900;}
.wrap{max-width:1100px;margin:30px auto;padding:0 20px;}
.panel{background:#fff;border:1px solid var(--border);padding:25px;border-radius:var(--r);box-shadow:0 2px 10px rgba(0,0,0,0.05);}
textarea{width:100%;min-height:150px;padding:15px;border:1px solid var(--border);border-radius:var(--r);font-family:inherit;margin-bottom:15px;resize:vertical;}
.btn{background:var(--accent);color:#fff;border:none;padding:12px 25px;border-radius:var(--r);cursor:pointer;font-weight:600;transition:0.2s;}
.btn:hover{opacity:0.9;}
.btn:disabled{background:#ccc;}
.results{margin-top:30px;display:none;}
.sec{border:1px solid var(--border);margin-bottom:20px;background:#fff;}
.sec-hd{background:var(--paper2);padding:10px 15px;font-weight:700;border-bottom:1px solid var(--border);display:flex;justify-content:space-between;}
.sec-body{padding:20px;white-space:pre-wrap;line-height:1.6;}
.loading{display:none;margin:20px 0;font-weight:600;color:var(--accent);}
</style>
</head>
<body>
<header><div class="logo">ENE <span style="font-size:12px;color:var(--accent)">REDACTOR IA</span></div><div id="status">Conectado</div></header>
<div class="wrap">
    <div class="panel">
        <h3 style="margin-bottom:15px">Fuente de información</h3>
        <textarea id="input-text" placeholder="Pegá acá la gacetilla, informe o notas..."></textarea>
        <div style="display:flex; gap:10px">
            <button class="btn" onclick="generate()" id="btn-gen">Generar Nota ENE</button>
        </div>
        <div class="loading" id="loader">Generando con Gemini 1.5 Flash... esto puede tardar 20-30 segundos.</div>
    </div>

    <div class="results" id="results">
        <div class="sec">
            <div class="sec-hd"><span>CONTENIDO REDACTADO</span><button onclick="copy('nota-out')">Copiar</button></div>
            <div class="sec-body" id="nota-out"></div>
        </div>
        <div class="sec">
            <div class="sec-hd"><span>TÍTULOS ESTRATÉGICOS</span></div>
            <div class="sec-body" id="titulos-out"></div>
        </div>
        <div class="sec">
            <div class="sec-hd"><span>METADATOS SEO</span></div>
            <div class="sec-body" id="seo-out"></div>
        </div>
    </div>
</div>

<script>
async function generate() {
    const text = document.getElementById('input-text').value;
    if(!text) return alert("Pegá algún texto primero");
    
    const btn = document.getElementById('btn-gen');
    const loader = document.getElementById('loader');
    const resDiv = document.getElementById('results');
    
    btn.disabled = true;
    loader.style.display = "block";
    resDiv.style.display = "none";

    try {
        const response = await fetch('/generar', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                articles: [{title: "Entrada manual", text: text}],
                seccion: "",
                tono: "informativo",
                extras: {}
            })
        });
        
        const d = await response.json();
        
        document.getElementById('nota-out').innerHTML = `<b>${d.volanta}</b>\n<h2>${d.titulo}</h2>\n\n<i>${d.copete}</i>\n\n${d.desarrollo}`;
        
        document.getElementById('titulos-out').innerHTML = d.titulos.map(t => `• [${t.tipo}] ${t.texto}`).join('\n');
        
        document.getElementById('seo-out').innerHTML = `<b>Slug:</b> ${d.slug}\n<b>Meta Title:</b> ${d.meta_title}\n<b>Meta Description:</b> ${d.meta_description}`;
        
        resDiv.style.display = "block";
    } catch (e) {
        alert("Error al generar: " + e);
    } finally {
        btn.disabled = false;
        loader.style.display = "none";
    }
}

function copy(id) {
    const el = document.getElementById(id);
    navigator.clipboard.writeText(el.innerText);
    alert("Copiado al portapapeles");
}
</script>
</body>
</html>
"""

# --- LÓGICA DEL SERVIDOR ---
SYSTEM_PROMPT = """Actuá como editor jefe digital patagónico y estratega SEO de Diario ENE. 
ESTILO ENE: Títulos directos, lenguaje claro, sin adjetivos grandilocuentes.
Generar JSON puro con: seccion, kw_principal, kw_secundarias, volanta, titulo, copete, desarrollo, titulos[], slug, meta_title, meta_description."""

class Article(BaseModel):
    title: str = ""
    text: str = ""

class GenerateRequest(BaseModel):
    articles: list[Article]
    seccion: str = ""
    tono: str = "informativo"
    extras: dict = {}

@app.get("/", response_class=HTMLResponse)
def root():
    return HTML_UI

@app.get("/articulo")
async def get_articulo(url: str = Query(...)):
    async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
        try:
            r = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
            soup = BeautifulSoup(r.text, "html.parser")
            h1 = soup.find("h1")
            title = h1.get_text(strip=True) if h1 else "Sin título"
            body = soup.find("article") or soup.body
            text = body.get_text(separator=" ", strip=True) if body else ""
            return {"title": title, "text": text[:4000]}
        except Exception as e:
            return {"error": str(e)}

@app.post("/generar")
async def generar(req: GenerateRequest):
    if not GEMINI_API_KEY:
        raise HTTPException(500, "Falta GEMINI_API_KEY en Render")

    user_msg = f"Fuentes:\n" + "\n".join([f"- {a.text}" for a in req.articles])
    
    url_gemini = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    
    payload = {
        "contents": [{"parts": [{"text": f"{SYSTEM_PROMPT}\n\nENTRADA:\n{user_msg}"}]}],
        "generationConfig": {"response_mime_type": "application/json", "temperature": 0.7}
    }

    async with httpx.AsyncClient(timeout=90) as client:
        resp = await client.post(url_gemini, json=payload)
        if resp.status_code != 200:
            raise HTTPException(500, f"Error API: {resp.text}")
        
        raw_json = resp.json()['candidates'][0]['content']['parts'][0]['text']
        return json.loads(raw_json)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
