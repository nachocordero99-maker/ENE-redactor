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
# SCRAPER NOTICIAS (FIX REAL)
# =========================
async def fetch_listing(source: str) -> list[dict]:
    headers = {"User-Agent": "Mozilla/5.0"}
    articles = []

    async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
        try:
            r = await client.get("https://prensa.rionegro.gov.ar/archivo", headers=headers)
            soup = BeautifulSoup(r.text, "html.parser")

            seen = set()

            for a in soup.find_all("a", href=True):
                href = a["href"]

                if "/articulo/" not in href:
                    continue

                url = href if href.startswith("http") else f"https://prensa.rionegro.gov.ar{href}"

                if url in seen:
                    continue
                seen.add(url)

                title = ""

                heading = a.find(["h1","h2","h3","h4"])
                if heading:
                    title = heading.get_text(strip=True)

                if not title:
                    title = a.get_text(strip=True)

                if not title or len(title) < 15:
                    continue

                articles.append({
                    "url": url,
                    "title": title,
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
            "ok": "__NEXT_DATA__" in r.text
        }
