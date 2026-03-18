from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx
import os
import urllib.parse
import json
import re
from datetime import datetime
from bs4 import BeautifulSoup

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

SYSTEM_PROMPT = """Sos el editor jefe digital de Diario ENE, medio regional con base en Bariloche y foco en Río Negro y la Patagonia.
ESTILO ENE: título directo, urgencia funcional, lenguaje claro, cero adjetivos grandilocuentes, pensado para el lector patagónico.
Evitar: "en el marco de", "con el objetivo de", "se llevó a cabo", párrafos de longitud idéntica.
Negrita: nombres propios, datos numéricos, keywords SEO. Cursiva: marcas, términos técnicos. Máx 15% del texto.
RESPONDÉ SOLO con JSON válido (sin markdown):
{"seccion":"","kw_principal":"","kw_secundarias":["","","","",""],"kw_longtail":["","",""],"tipo_guia":false,"etiquetas":["","","",""],"volanta":"","titulo":"","copete":"","desarrollo":"","bloque_guia":null,"interlinking":[{"frase":"","destino":""}],"micro_seo":"","rrss":{"instagram":"","twitter":"","facebook":""},"newsletter":"","titulos":[{"tipo":"Informativo puro","texto":""},{"tipo":"Informativo puro","texto":""},{"tipo":"Impacto periodístico","texto":""},{"tipo":"Impacto periodístico","texto":""},{"tipo":"Explicativo / Contexto","texto":""},{"tipo":"Explicativo / Contexto","texto":""},{"tipo":"Híbrido estratégico","texto":""}],"titulo_recomendado_index":0,"titulo_recomendado_razon":"","meta_title":"","meta_description":"","slug":"","revision":{"variacion_ritmo":true,"dato_local":true,"sin_genericos":true,"observaciones":""},"portada":"","horario":""}"""

class FetchRequest(BaseModel):
    urls: list[str]
    seccion: str = ""
    tono: str = "informativo"
    extras: dict = {}

async def fetch_article_text(url: str) -> str:
    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            r = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
            soup = BeautifulSoup(r.text, "html.parser")
            for tag in soup(["nav","header","footer","script","style","aside"]):
                tag.decompose()
            body = soup.find("article") or soup.find(class_=lambda c: c and "content" in c) or soup.body
            text = body.get_text(separator=" ", strip=True) if body else ""
            return " ".join(text.split())[:3000]
    except Exception as e:
        return f"(error: {e})"

async def fetch_listing(source: str) -> list[dict]:
    today = datetime.now().strftime("%Y-%m-%d")
    url = f"https://prensa.rionegro.gov.ar/busqueda/articulo?q=&t=&d={today}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "es-AR,es;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Cache-Control": "no-cache",
    }
    articles = []

    async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
        try:
            r = await client.get(url, headers=headers)
            soup = BeautifulSoup(r.text, "html.parser")
            seen = set()

            for a in soup.find_all("a", href=lambda h: h and "/articulo/" in str(h)):
                href = a.get("href", "")
                full_url = href if href.startswith("http") else f"https://prensa.rionegro.gov.ar{href}"
                if full_url in seen:
                    continue
                seen.add(full_url)

                heading = a.find(["h2","h3","h4","h5"])
                title = (heading or a).get_text(strip=True).replace("\n", " ").strip()
                if not title or len(title) < 15:
                    continue

                parent = a.find_parent(["article","div","li","section"])
                sec = "Río Negro"
                if parent:
                    h6 = parent.find("h6")
                    if h6:
                        sec = re.sub(r'\d+\s+de\s+\w+\s+de\s+\d{4}', '', h6.get_text(strip=True)).strip()

                img = None
                if parent:
                    img_el = parent.find("img")
                    if img_el:
                        raw = img_el.get("src") or img_el.get("data-src") or ""
                        if "_next/image" in raw:
                            parsed = urllib.parse.urlparse(raw)
                            params = urllib.parse.parse_qs(parsed.query)
                            img = urllib.parse.unquote(params.get("url", [""])[0])
                        elif raw.startswith("http") and "data:image" not in raw:
                            img = raw

                articles.append({
                    "url": full_url,
                    "title": title,
                    "sec": sec,
                    "img": img,
                    "source": "Prensa Río Negro"
                })
                if len(articles) >= 20:
                    break

        except Exception as e:
            print(f"fetch_listing error: {e}")

    return articles

@app.get("/")
def root():
    return {"status": "ENE Redactor API ok"}

@app.get("/debug")
async def debug():
    today = datetime.now().strftime("%Y-%m-%d")
    url = f"https://prensa.rionegro.gov.ar/busqueda/articulo?q=&t=&d={today}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "es-AR,es;q=0.9",
    }
    async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
        r = await client.get(url, headers=headers)
        html = r.text
        return {
            "status": r.status_code,
            "url_fetched": str(r.url),
            "today": today,
            "has_articulo_links": "/articulo/" in html,
            "articulo_count": html.count("/articulo/"),
            "html_length": len(html),
            "html_sample": html[1500:3500]
        }

@app.get("/noticias")
async def get_noticias(fuente: str = "prensa"):
    articles = await fetch_listing(fuente)
    return {"articles": articles, "total": len(articles)}

@app.post("/generar")
async def generar(req: FetchRequest):
    if not ANTHROPIC_API_KEY:
        raise HTTPException(500, "ANTHROPIC_API_KEY no configurada")
    texts = []
    for url in req.urls:
        text = await fetch_article_text(url)
        texts.append(f"URL: {url}\n\n{text}")
    user_msg = f"Procesá estas fuentes y generá la nota ENE:\n\n{'---'.join(texts)}"
    if req.seccion:
        user_msg += f"\n\nSECCIÓN FORZADA: {req.seccion}"
    if req.tono != "informativo":
        user_msg += f"\n\nTONO: {req.tono}"
    if not req.extras.get("rrss"):
        user_msg += "\n\nDejar rrss vacío."
    if not req.extras.get("newsletter"):
        user_msg += "\n\nDejar newsletter vacío."
    if not req.extras.get("micro_seo"):
        user_msg += "\n\nDejar micro_seo vacío."
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            },
            json={
                "model": "claude-sonnet-4-20250514",
                "max_tokens": 4000,
                "system": SYSTEM_PROMPT,
                "messages": [{"role": "user", "content": user_msg}]
            },
        )
    if resp.status_code != 200:
        raise HTTPException(500, f"Error API: {resp.text}")
    data = resp.json()
    raw = "".join(b.get("text","") for b in data.get("content",[])).replace("```json","").replace("```","").strip()
    try:
        return json.loads(raw)
    except Exception:
        raise HTTPException(500, "No se pudo parsear la respuesta")
