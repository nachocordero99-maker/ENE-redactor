from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx
import os
import urllib.parse
import json
from bs4 import BeautifulSoup

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

SYSTEM_PROMPT = """Sos el editor jefe digital de Diario ENE, medio regional con base en Bariloche y foco en Río Negro y la Patagonia.
ESTILO ENE: título directo, urgencia funcional, lenguaje claro, cero adjetivos grandilocuentes, pensado para el lector patagónico.
Evitar: "en el marco de", "con el objetivo de", "se llevó a cabo", párrafos de longitud idéntica.
Negrita: nombres propios, datos numéricos, keywords SEO. Cursiva: marcas, términos técnicos. Máx 15% del texto.
RESPONDÉ SOLO con JSON válido (sin markdown)."""

class FetchRequest(BaseModel):
    urls: list[str]
    seccion: str = ""
    tono: str = "informativo"
    extras: dict = {}

# =========================
# SCRAPER DE ARTÍCULOS
# =========================

async def fetch_article_text(url: str) -> str:
    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            r = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
            soup = BeautifulSoup(r.text, "html.parser")

            for tag in soup(["nav","header","footer","script","style","aside"]):
                tag.decompose()

            body = soup.find("article") or soup.body
            text = body.get_text(separator=" ", strip=True) if body else ""

            return " ".join(text.split())[:3000]

    except Exception as e:
        return f"(error: {e})"


async def fetch_listing(source: str) -> list[dict]:
    headers = {"User-Agent": "Mozilla/5.0 (compatible; DiarioENE/1.0)"}
    articles = []

    async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:

        # Strategy 1: NEXT DATA
        try:
            r = await client.get("https://prensa.rionegro.gov.ar/", headers=headers)
            soup = BeautifulSoup(r.text, "html.parser")
            script = soup.find("script", id="__NEXT_DATA__")

            if script and script.string:
                data = json.loads(script.string)

                def extract(obj):
                    if isinstance(obj, dict):
                        for k, v in obj.items():
                            if k in ["articles", "news"] and isinstance(v, list):
                                for item in v:
                                    if item.get("title"):
                                        articles.append({
                                            "url": f"https://prensa.rionegro.gov.ar/articulo/{item.get('id','')}/{item.get('slug','')}",
                                            "title": item.get("title"),
                                            "sec": "Río Negro",
                                            "img": None,
                                            "source": "Prensa Río Negro"
                                        })
                            else:
                                extract(v)
                    elif isinstance(obj, list):
                        for i in obj:
                            extract(i)

                extract(data)

                if articles:
                    return articles[:16]

        except Exception as e:
            print("NEXT error", e)

        # Strategy 2: ARCHIVO
        try:
            r = await client.get("https://prensa.rionegro.gov.ar/archivo", headers=headers)
            soup = BeautifulSoup(r.text, "html.parser")

            for a in soup.find_all("a", href=lambda h: h and "/articulo/" in h):
                title = a.get_text(strip=True)

                if len(title) < 20:
                    continue

                url = a["href"]
                if not url.startswith("http"):
                    url = f"https://prensa.rionegro.gov.ar{url}"

                articles.append({
                    "url": url,
                    "title": title,
                    "sec": "Río Negro",
                    "img": None,
                    "source": "Prensa Río Negro"
                })

                if len(articles) >= 16:
                    break

            if articles:
                return articles

        except Exception as e:
            print("ARCHIVO error", e)

    return articles


# =========================
# ENDPOINTS
# =========================

@app.get("/")
def root():
    return {"status": "ENE Redactor API ok"}


@app.get("/noticias")
async def get_noticias():
    articles = await fetch_listing("prensa")
    return {"articles": articles, "total": len(articles)}


@app.post("/generar")
async def generar(req: FetchRequest):
    if not ANTHROPIC_API_KEY:
        raise HTTPException(500, "Falta API KEY")

    texts = []

    for url in req.urls:
        text = await fetch_article_text(url)
        texts.append(f"URL: {url}\n\n{text}")

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
                "max_tokens": 2000,
                "system": SYSTEM_PROMPT,
                "messages": [{"role": "user", "content": " ".join(texts)}]
            },
        )

    return resp.json()


@app.get("/debug")
async def debug():
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.get("https://prensa.rionegro.gov.ar/")
        return {
            "status": r.status_code,
            "ok": "__NEXT_DATA__" in r.text
        }
