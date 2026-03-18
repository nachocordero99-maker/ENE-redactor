from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx
import os
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

SYSTEM_PROMPT = """Sos el editor jefe digital de Diario ENE."""

class FetchRequest(BaseModel):
    urls: list[str]
    seccion: str = ""
    tono: str = "informativo"
    extras: dict = {}

# =========================
# EXTRAER TEXTO ARTÍCULO
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

# =========================
# SCRAPER NOTICIAS (NEXT DATA)
# =========================
async def fetch_listing(source: str) -> list[dict]:
    headers = {"User-Agent": "Mozilla/5.0"}
    articles = []

    async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
        try:
            r = await client.get("https://prensa.rionegro.gov.ar/", headers=headers)
            soup = BeautifulSoup(r.text, "html.parser")

            script = soup.find("script", id="__NEXT_DATA__")

            if not script:
                print("NO NEXT DATA")
                return []

            data = json.loads(script.string)

            def find_articles(obj):
                results = []

                if isinstance(obj, dict):
                    if "titulo" in obj and "slug" in obj:
                        results.append(obj)

                    for v in obj.values():
                        results.extend(find_articles(v))

                elif isinstance(obj, list):
                    for item in obj:
                        results.extend(find_articles(item))

                return results

            raw_articles = find_articles(data)

            seen = set()

            for item in raw_articles:
                slug = item.get("slug")
                title = item.get("titulo")

                if not slug or not title:
                    continue

                url = f"https://prensa.rionegro.gov.ar/articulo/{slug}"

                if url in seen:
                    continue
                seen.add(url)

                if len(title) < 10:
                    continue

                articles.append({
                    "url": url,
                    "title": title.strip(),
                    "sec": "Río Negro",
                    "img": None,
                    "source": "Prensa Río Negro"
                })

                if len(articles) >= 20:
                    break

        except Exception as e:
            print("SCRAPER error:", e)

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
            "has_next_data": "__NEXT_DATA__" in r.text
        }
