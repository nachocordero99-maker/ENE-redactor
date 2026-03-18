from fastapi import FastAPI, HTTPException, Query
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

# --- CONFIGURACIÓN ---
# Asegúrate de configurar esta variable en tu entorno de GitHub o servidor
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

SITE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "es-AR,es;q=0.9",
    "Referer": "https://prensa.rionegro.gov.ar/",
}

# --- NUEVO PROMPT ESTRATÉGICO DIARIO ENE ---
SYSTEM_PROMPT = """Actuá como editor jefe digital patagónico y estratega SEO de Diario ENE, medio regional con base en Bariloche y foco en Río Negro y la Patagonia. 
Tu tarea es crear un artículo periodístico optimizado al máximo nivel profesional.

ESTILO DIARIO ENE:
- Título directo, sin vueltas. Urgencia funcional.
- Lenguaje claro, sobrio, cero adjetivos grandilocuentes.
- Evitar: "en el marco de", "con el objetivo de", "se llevó a cabo".
- Redacción humana: Variá longitud de párrafos. Usá datos locales específicos.

RESPONDÉ EXCLUSIVAMENTE EN FORMATO JSON con la siguiente estructura (sin markdown):
{
  "seccion": "",
  "kw_principal": "",
  "kw_secundarias": [],
  "kw_longtail": [],
  "tipo_guia": false,
  "etiquetas": [],
  "volanta": "",
  "titulo": "",
  "copete": "",
  "desarrollo": "",
  "bloque_guia": null,
  "interlinking": [{"frase": "", "destino": ""}],
  "micro_seo": "",
  "titulos": [{"tipo": "Informativo puro", "texto": ""}, {"tipo": "Impacto periodístico", "texto": ""}, {"tipo": "Explicativo", "texto": ""}, {"tipo": "Híbrido", "texto": ""}],
  "titulo_recomendado_index": 0,
  "titulo_recomendado_razon": "",
  "meta_title": "",
  "meta_description": "",
  "slug": "",
  "revision": {"variacion_ritmo": true, "dato_local": true, "observaciones": ""},
  "portada": "",
  "horario": ""
}

INSTRUCCIONES DE RELLENO:
- Desarrollo: 500-800 palabras. Usar negritas para nombres propios y datos.
- Copete: Máx 200 caracteres, una sola oración.
- Interlinking: 2 a 4 oportunidades."""

# --- MODELOS DE DATOS ---
class Article(BaseModel):
    url: str = ""
    title: str = ""
    text: str = ""

class GenerateRequest(BaseModel):
    articles: list[Article]
    seccion: str = ""
    tono: str = "informativo"
    extras: dict = {}

# --- RUTAS ---
@app.get("/", response_class=HTMLResponse)
def root():
    # Aquí iría el HTML que ya tienes (puedes pegarlo aquí mismo o dejarlo como referencia)
    return "Servidor Redactor ENE Activo. Accede vía Web UI."

@app.get("/articulo")
async def get_articulo(url: str = Query(...)):
    async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
        try:
            r = await client.get(url, headers=SITE_HEADERS)
            soup = BeautifulSoup(r.text, "html.parser")
            h1 = soup.find("h1") or soup.find("h2")
            title = h1.get_text(strip=True) if h1 else ""
            sec_el = soup.find(class_=lambda c: c and any(x in " ".join(c) for x in ["categ","section","tag"]))
            sec = sec_el.get_text(strip=True) if sec_el else "Río Negro"
            for tag in soup(["nav","header","footer","script","style","aside"]):
                tag.decompose()
            body = soup.find("article") or soup.find(class_=lambda c: c and "content" in " ".join(c or [])) or soup.body
            text = body.get_text(separator=" ", strip=True) if body else ""
            return {"title": title, "sec": sec, "text": " ".join(text.split())[:4000]}
        except Exception as e:
            return {"title": url, "sec": "Río Negro", "text": f"(error: {e})"}

@app.post("/generar")
async def generar(req: GenerateRequest):
    if not GEMINI_API_KEY:
        raise HTTPException(500, "GEMINI_API_KEY no configurada")

    # Construcción del mensaje para el modelo
    parts = []
    for a in req.articles:
        parts.append(f"FUENTE: {a.title}\nCONTENIDO: {a.text}")
    
    user_msg = f"Procesá estas fuentes y generá la nota para Diario ENE:\n\n{'---'.join(parts)}"
    if req.seccion:
        user_msg += f"\n\nSECCIÓN PRIORITARIA: {req.seccion}"
    if req.tono != "informativo":
        user_msg += f"\n\nTONO SOLICITADO: {req.tono}"

    # Llamada a la API de Gemini
    url_gemini = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    
    payload = {
        "contents": [{
            "parts": [{"text": f"{SYSTEM_PROMPT}\n\nDATOS DE ENTRADA:\n{user_msg}"}]
        }],
        "generationConfig": {
            "response_mime_type": "application/json",
            "temperature": 0.7,
            "max_output_tokens": 8192,
        }
    }

    async with httpx.AsyncClient(timeout=90) as client:
        try:
            resp = await client.post(url_gemini, json=payload)
            if resp.status_code != 200:
                raise HTTPException(500, f"Error Gemini API: {resp.text}")
            
            data = resp.json()
            raw_text = data['candidates'][0]['content']['parts'][0]['text']
            
            # Limpieza de posibles residuos de texto antes del JSON
            return json.loads(raw_text)
            
        except (KeyError, IndexError) as e:
            raise HTTPException(500, "La IA devolvió un formato inesperado.")
        except json.JSONDecodeError:
            raise HTTPException(500, "Error al parsear el JSON de la IA.")
        except Exception as e:
            raise HTTPException(500, f"Error interno: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
