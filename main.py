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
textarea{width:100%;min-height:200px;padding:15px;border:1px solid var(--border);border-radius:var(--r);font-family:inherit;margin-bottom:15px;resize:vertical;font-size:14px;line-height:1.6;}
.btn{background:var(--accent);color:#fff;border:none;padding:14px 30px;border-radius:var(--r);cursor:pointer;font-weight:600;transition:0.2s;font-size:15px;}
.btn:hover{background:#a02d14;}
.btn:disabled{background:#ccc;cursor:not-allowed;}
.results{margin-top:30px;display:none;}
.sec{border:1px solid var(--border);margin-bottom:25px;background:#fff;border-radius:var(--r);overflow:hidden;}
.sec-hd{background:var(--paper2);padding:12px 18px;font-weight:700;border-bottom:1px solid var(--border);display:flex;justify-content:space-between;align-items:center;font-size:13px;letter-spacing:1px;text-transform:uppercase;}
.sec-body{padding:25px;white-space:pre-wrap;line-height:1.8;font-size:15px;}
.loading{display:none;margin:20px 0;font-weight:600;color:var(--accent);text-align:center;padding:20px;border:2px dashed var(--border);}
.copy-btn{background:transparent;border:1px solid var(--border);padding:5px 10px;cursor:pointer;font-size:11px;border-radius:3px;}
.copy-btn:hover{background:var(--paper);}
</style>
</head>
<body>
<header><div class="logo">ENE <span style="font-size:12px;color:var(--accent)">REDACTOR IA</span></div></header>
<div class="wrap">
    <div class="panel">
        <h3 style="margin-bottom:15px">Contenido base (Gacetilla o Notas)</h3>
        <textarea id="input-text" placeholder="Pegá acá toda la información que tengas para procesar..."></textarea>
        <button class="btn" onclick="generate()" id="btn-gen">Generar Nota Completa →</button>
        <div class="loading" id="loader">🚀 El Editor Jefe está redactando... por favor esperá.</div>
    </div>

    <div class="results" id="results">
        <div class="sec">
            <div class="sec-hd"><span>Nota Redactada</span><button class="copy-btn" onclick="copy('nota-out')">Copiar Nota</button></div>
            <div class="sec-body" id="nota-out"></div>
        </div>
        <div class="sec">
            <div class="sec-hd"><span>Títulos Sugeridos</span></div>
            <div class="sec-body" id="titulos-out"></div>
        </div>
        <div class="sec">
            <div class="sec-hd"><span>Estrategia SEO y Metadatos</span></div>
            <div class="sec-body" id="seo-out"></div>
        </div>
    </div>
</div>

<script>
async function generate() {
    const text = document.getElementById('input-text').value;
    if(!text || text.length < 10) return alert("Por favor, pegá un texto más largo.");
    
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
                articles: [{title: "Entrada Directa", text: text}],
                seccion: "",
                tono: "informativo",
                extras: {}
            })
        });
        
        if(!response.ok) throw new Error("Error en la respuesta del servidor");
        const d = await response.json();
        
        // Blindaje de datos para evitar el error de 'undefined'
        const titulosLista = Array.isArray(d.titulos) ? d.titulos : [];
        
        document.getElementById('nota-out').innerHTML = `<b>${d.volanta || ''}</b>\n<h1 style="font-family:'Playfair Display',serif; margin:10px 0;">${d.titulo || ''}</h1>\n\n<i>${d.copete || ''}</i>\n\n${d.desarrollo || ''}`;
        
        document.getElementById('titulos-out').innerHTML = titulosLista.length > 0 
            ? titulosLista.map(t => `<strong>[${t.tipo || 'Título'}]</strong> ${t.texto || ''}`).join('\n\n')
            : "No se generaron títulos adicionales.";
        
        document.getElementById('seo-out').innerHTML = `<strong>Slug:</strong> ${d.slug || ''}\n<strong>Meta Title:</strong> ${d.meta_title || ''}\n<strong>Meta Description:</strong> ${d.meta_description || ''}\n\n<strong>Sección sugerida:</strong> ${d.seccion || ''}`;
        
        resDiv.style.display = "block";
        resDiv.scrollIntoView({behavior: 'smooth'});
    } catch (e) {
        console.error(e);
        alert("Hubo un problema al generar la nota. Revisá los logs de Render.");
    } finally {
        btn.disabled = false;
        loader.style.display = "none";
    }
}

function copy(id) {
    const el = document.getElementById(id);
    const range = document.createRange();
    range.selectNode(el);
    window.getSelection().removeAllRanges();
    window.getSelection().addRange(range);
    document.execCommand("copy");
    window.getSelection().removeAllRanges();
    alert("¡Copiado!");
}
</script>
</body>
</html>
"""

# --- LÓGICA DEL SERVIDOR ---
SYSTEM_PROMPT = """Actuá como editor jefe digital patagónico de Diario ENE.
IMPORTANTE: Debes responder EXCLUSIVAMENTE con un objeto JSON válido.
Estructura obligatoria:
{
  "seccion": "string",
  "volanta": "string",
  "titulo": "string",
  "copete": "string",
  "desarrollo": "string (usa negritas para datos clave)",
  "titulos": [{"tipo": "string", "texto": "string"}],
  "slug": "string",
  "meta_title": "string",
  "meta_description": "string"
}"""

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

@app.post("/generar")
async def generar(req: GenerateRequest):
    if not GEMINI_API_KEY:
        raise HTTPException(500, "Falta GEMINI_API_KEY en variables de entorno")

    contexto = "\n".join([f"INFO: {a.text}" for a in req.articles])
    
    url_gemini = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    
    payload = {
        "contents": [{"parts": [{"text": f"{SYSTEM_PROMPT}\n\nDATOS PARA REDACTAR:\n{contexto}"}]}],
        "generationConfig": {
            "response_mime_type": "application/json",
            "temperature": 0.7,
            "max_output_tokens": 4000
        }
    }

    async with httpx.AsyncClient(timeout=120) as client:
        try:
            resp = await client.post(url_gemini, json=payload)
            if resp.status_code != 200:
                raise HTTPException(500, f"Error Gemini: {resp.text}")
            
            data = resp.json()
            raw_json = data['candidates'][0]['content']['parts'][0]['text']
            return json.loads(raw_json)
        except Exception as e:
            raise HTTPException(500, f"Error procesando JSON: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
