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

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")

# ─────────────────────────────────────────
# PROMPT COMPLETO ENE (el original de tu mamá)
# ─────────────────────────────────────────
SYSTEM_PROMPT = """Actuá como editor jefe digital patagónico y estratega SEO de Diario ENE, medio regional con base en Bariloche y foco en Río Negro y la Patagonia.

ESTILO DIARIO ENE:
- Título directo, sin vueltas
- Urgencia funcional, no exagerada
- Foco en lo que pasa y por qué importa
- Lenguaje claro, sobrio, cero adjetivos grandilocuentes
- Pensado para el lector patagónico, no para gacetilla

Evitar siempre: "en el marco de", "con el objetivo de", "se llevó a cabo", estructuras simétricas, párrafos de longitud idéntica.
Negrita: nombres propios relevantes, datos numéricos, keywords SEO. Cursiva: marcas, términos técnicos. Máx 15% del texto.

RESPONDÉ SOLO con JSON válido (sin markdown):
{
  "seccion": "",
  "kw_principal": "",
  "kw_secundarias": ["","","","",""],
  "kw_longtail": ["","",""],
  "tipo_guia": false,
  "etiquetas": ["","","",""],
  "volanta": "",
  "titulo": "",
  "copete": "",
  "desarrollo": "",
  "bloque_guia": null,
  "interlinking": [{"frase":"","destino":""}],
  "micro_seo": "",
  "rrss": {"instagram":"","twitter":"","facebook":""},
  "titulos": [
    {"tipo":"Informativo puro","texto":""},
    {"tipo":"Informativo puro","texto":""},
    {"tipo":"Impacto periodístico","texto":""},
    {"tipo":"Impacto periodístico","texto":""},
    {"tipo":"Explicativo / Contexto","texto":""},
    {"tipo":"Explicativo / Contexto","texto":""},
    {"tipo":"Híbrido estratégico","texto":""}
  ],
  "titulo_recomendado_index": 0,
  "titulo_recomendado_razon": "",
  "meta_title": "",
  "meta_description": "",
  "slug": "",
  "revision": {"variacion_ritmo":true,"dato_local":true,"sin_genericos":true,"observaciones":""},
  "portada": "",
  "horario": ""
}

Reglas de contenido:
VOLANTA: máx 3 palabras (topónimos no cuentan)
TÍTULO: máx 80 caracteres
COPETE: máx 200 caracteres, una oración, sin subordinadas, sin adjetivos
DESARROLLO: 500-800 palabras, subtítulos cada 4-5 párrafos, variá longitud de párrafos
META TITLE: máx 60 car. META DESC: máx 155 car."""

# ─────────────────────────────────────────
# HTML DE LA HERRAMIENTA
# ─────────────────────────────────────────
HTML = r"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Redactor ENE</title>
<link href="https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1&family=DM+Sans:wght@300;400;500;600&family=DM+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
:root{
  --ink:#04080f;--ink2:#2a3a4a;--ink3:#5a7a9a;
  --paper:#f5faff;--paper2:#e8f4fc;--paper3:#d8edf8;
  --blue:#3ab8e8;--blue2:#0a7ab8;--blue3:#061830;
  --border:#d0e4f0;--ok:#2a7a4b;--r:4px;
}
*{box-sizing:border-box;margin:0;padding:0;}
body{font-family:'DM Sans',sans-serif;background:var(--paper);color:var(--ink);min-height:100vh;}

/* HEADER */
header{background:var(--ink);border-bottom:3px solid var(--blue);padding:10px 24px;display:flex;align-items:center;justify-content:space-between;position:sticky;top:0;z-index:100;}
.logo{display:flex;flex-direction:column;line-height:1;}
.logo-d{font-size:9px;font-style:italic;font-weight:300;color:var(--blue);letter-spacing:2px;}
.logo-e{font-family:'Instrument Serif',serif;font-size:24px;color:#fff;letter-spacing:-0.5px;}
.logo-e em{color:var(--blue);font-style:italic;}
#hst{font-size:11px;color:#1a4a6a;}

/* TABS PRINCIPALES */
.main-tabs{display:flex;gap:2px;padding:20px 24px 0;max-width:1200px;margin:0 auto;}
.main-tab{padding:9px 20px;font-size:12px;font-weight:500;border:1px solid var(--border);background:var(--paper2);color:var(--ink3);border-radius:var(--r) var(--r) 0 0;border-bottom:none;cursor:pointer;transition:all .15s;}
.main-tab.on{background:#fff;color:var(--ink);border-bottom:1px solid #fff;margin-bottom:-1px;z-index:1;}

/* PANEL */
.wrap{max-width:1200px;margin:0 auto;padding:0 24px 48px;}
.panel{display:none;background:#fff;border:1px solid var(--border);border-radius:0 var(--r) var(--r) var(--r);padding:24px;}
.panel.on{display:block;}

/* ── PANEL A: PORTALES ── */
.src-bar{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:20px;}
.src-chip{display:flex;align-items:center;gap:6px;padding:6px 14px;border:1px solid var(--border);border-radius:20px;font-size:12px;cursor:pointer;background:var(--paper);user-select:none;transition:all .15s;}
.src-chip input{display:none;}
.src-chip.on{background:var(--ink);color:#fff;border-color:var(--ink);}
.btn{padding:9px 18px;background:var(--blue2);color:#fff;border:none;border-radius:var(--r);font-size:12px;font-weight:600;cursor:pointer;font-family:'DM Sans',sans-serif;transition:background .15s;}
.btn:hover{background:var(--blue);}
.btn:disabled{background:#bbb;cursor:not-allowed;}
.btn-sec{padding:9px 14px;background:transparent;border:1px solid var(--border);border-radius:var(--r);font-size:12px;color:var(--ink3);cursor:pointer;font-family:'DM Sans',sans-serif;}
.btn-sec:hover{border-color:var(--ink);color:var(--ink);}

.cards-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:12px;}
.card{border:1px solid var(--border);border-radius:var(--r);cursor:pointer;background:#fff;overflow:hidden;position:relative;transition:border-color .15s;}
.card:hover{border-color:var(--blue2);}
.card.sel{border:2px solid var(--blue2);box-shadow:0 0 0 3px rgba(58,184,232,.12);}
.card-chk{position:absolute;top:8px;right:8px;width:22px;height:22px;background:var(--blue2);color:#fff;border-radius:50%;font-size:12px;font-weight:700;display:none;align-items:center;justify-content:center;}
.card.sel .card-chk{display:flex;}
.card-body{padding:12px 14px;}
.card-sec{font-size:9px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;color:var(--ink3);margin-bottom:5px;}
.card-title{font-size:13px;font-weight:500;line-height:1.45;color:var(--ink);}
.card-src{font-size:10px;color:var(--ink3);margin-top:5px;}

.sel-footer{margin-top:18px;padding:12px 16px;background:var(--paper2);border:1px solid var(--border);border-radius:var(--r);display:flex;align-items:center;justify-content:space-between;gap:12px;}
.sel-info{font-size:13px;color:var(--ink2);}
.sel-info b{color:var(--blue2);}

.skl{background:linear-gradient(90deg,var(--paper2) 25%,var(--paper3) 50%,var(--paper2) 75%);background-size:200% 100%;animation:sk 1.2s infinite;border-radius:var(--r);height:90px;}
@keyframes sk{0%{background-position:200% 0}100%{background-position:-200% 0}}

/* ── PANEL B: GENERAR NOTA ── */
.gen-layout{display:grid;grid-template-columns:300px 1fr;gap:24px;}

/* Sub-tabs dentro de Generar */
.sub-tabs{display:flex;gap:4px;margin-bottom:16px;}
.sub-tab{padding:7px 16px;font-size:12px;font-weight:500;border:1px solid var(--border);background:var(--paper2);color:var(--ink3);border-radius:var(--r);cursor:pointer;transition:all .15s;}
.sub-tab.on{background:var(--ink);color:#fff;border-color:var(--ink);}
.sub-panel{display:none;}
.sub-panel.on{display:block;}

textarea{width:100%;min-height:160px;padding:14px;font-family:'DM Sans',sans-serif;font-size:13px;line-height:1.7;color:var(--ink);background:#fff;border:1px solid var(--border);border-radius:var(--r);outline:none;resize:vertical;margin-bottom:12px;}
textarea:focus{border-color:var(--blue2);}
textarea::placeholder{color:#bbb;}
input[type=text]{width:100%;padding:10px 14px;font-family:'DM Sans',sans-serif;font-size:13px;color:var(--ink);background:#fff;border:1px solid var(--border);border-radius:var(--r);outline:none;margin-bottom:12px;}
input[type=text]:focus{border-color:var(--blue2);}

.slbl{font-size:9px;font-weight:700;letter-spacing:2px;text-transform:uppercase;color:var(--ink3);margin-bottom:8px;display:flex;align-items:center;gap:6px;}
.slbl::after{content:'';flex:1;height:1px;background:var(--border);}

.prev-list{display:flex;flex-direction:column;gap:6px;margin-bottom:16px;}
.prev-item{padding:8px 10px;background:var(--paper);border:1px solid var(--border);border-radius:var(--r);font-size:11px;color:var(--ink2);line-height:1.4;}
.prev-item small{display:block;font-size:9px;color:var(--ink3);text-transform:uppercase;letter-spacing:1px;margin-bottom:2px;}

.opts{background:var(--paper);border:1px solid var(--border);border-radius:var(--r);overflow:hidden;margin-bottom:12px;}
.opt{padding:9px 12px;border-bottom:1px solid var(--paper3);}
.opt:last-child{border-bottom:none;}
.opt label{display:block;font-size:9px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;color:var(--ink3);margin-bottom:5px;}
select{width:100%;padding:7px 10px;font-family:'DM Sans',sans-serif;font-size:12px;color:var(--ink);background:#fff;border:1px solid var(--border);border-radius:var(--r);outline:none;appearance:none;}

.chips{display:flex;flex-wrap:wrap;gap:5px;margin-bottom:12px;}
.chip{display:flex;align-items:center;gap:4px;padding:5px 11px;border:1px solid var(--border);border-radius:20px;font-size:11px;cursor:pointer;background:#fff;user-select:none;}
.chip input{display:none;}
.chip.on{background:var(--ink);color:#fff;border-color:var(--ink);}

.btn-gen{display:block;width:100%;padding:13px;background:var(--blue2);color:#fff;font-family:'DM Sans',sans-serif;font-size:13px;font-weight:600;border:none;cursor:pointer;border-radius:var(--r);}
.btn-gen:hover{background:var(--blue);}
.btn-gen:disabled{background:#bbb;cursor:not-allowed;}
.spin{display:none;width:13px;height:13px;border:2px solid rgba(255,255,255,.3);border-top-color:#fff;border-radius:50%;animation:spin .7s linear infinite;vertical-align:middle;margin-right:6px;}
.loading .spin{display:inline-block;}
@keyframes spin{to{transform:rotate(360deg)}}
.err{background:#fde8e3;border:1px solid #f5b8b0;border-radius:var(--r);padding:10px 14px;font-size:12px;color:#c83030;margin-top:10px;display:none;}
.err.on{display:block;}

/* OUTPUT */
.out{min-height:400px;}
.empty{text-align:center;padding:60px 20px;color:var(--ink3);}
.empty-icon{font-size:32px;opacity:.2;margin-bottom:10px;}
.results{display:none;}
.results.on{display:block;animation:fi .3s ease;}
@keyframes fi{from{opacity:0;transform:translateY(5px)}to{opacity:1;transform:translateY(0)}}

.sec{border:1px solid var(--border);border-radius:var(--r);margin-bottom:12px;overflow:hidden;}
.sec-hd{display:flex;align-items:center;justify-content:space-between;padding:8px 14px;background:var(--paper2);border-bottom:1px solid var(--border);}
.sec-row{display:flex;align-items:center;gap:7px;}
.bdg{font-size:8px;font-weight:700;letter-spacing:2px;text-transform:uppercase;padding:2px 6px;border-radius:2px;}
.b1{background:#e8f4ec;color:#2a7a4b;}
.b2{background:#e4f0fc;color:var(--blue2);}
.b3{background:#e8edf8;color:#2a4a9a;}
.b4{background:#fdf6e3;color:#b8962e;}
.b5{background:#f0e8f8;color:#6a2a9a;}
.bx{background:#e4f4f8;color:#1a6a8a;}
.sec-nm{font-size:11px;font-weight:600;color:var(--ink2);}
.cp{font-size:10px;padding:4px 10px;background:transparent;border:1px solid var(--border);border-radius:20px;cursor:pointer;color:var(--ink3);font-family:'DM Sans',sans-serif;}
.cp:hover{border-color:var(--ink2);color:var(--ink);}
.cp.ok{background:var(--ok);color:#fff;border-color:var(--ok);}
.sec-body{padding:16px 18px;font-size:13px;line-height:1.8;color:var(--ink);white-space:pre-wrap;}

.kw-bl{padding:12px 16px;}
.kwr{margin-bottom:10px;}
.kwl{font-size:9px;font-weight:700;letter-spacing:2px;text-transform:uppercase;color:var(--ink3);margin-bottom:5px;}
.kwcs{display:flex;flex-wrap:wrap;gap:5px;}
.kwc{font-size:11px;padding:3px 9px;border-radius:2px;border:1px solid var(--border);color:var(--ink2);background:var(--paper);}
.kwc.pr{background:var(--ink);color:#fff;border-color:var(--ink);font-weight:500;}

.tl{padding:12px 16px;}
.ti{display:flex;gap:8px;padding:9px 0;border-bottom:1px solid var(--paper3);align-items:flex-start;}
.ti:last-child{border-bottom:none;}
.tt{font-size:9px;font-weight:700;letter-spacing:1px;text-transform:uppercase;color:var(--ink3);min-width:90px;padding-top:2px;}
.tx{font-size:12px;color:var(--ink);flex:1;line-height:1.5;}
.ti.rec .tx{font-weight:600;color:var(--blue2);}
.rtag{font-size:8px;background:var(--blue2);color:#fff;padding:2px 6px;border-radius:2px;white-space:nowrap;}

.mr{display:grid;grid-template-columns:110px 1fr;border-bottom:1px solid var(--paper3);}
.mr:last-child{border-bottom:none;}
.mk{font-size:9px;font-weight:700;letter-spacing:1px;text-transform:uppercase;color:var(--ink3);padding:10px 14px;background:var(--paper2);border-right:1px solid var(--paper3);}
.mv{padding:10px 14px;font-size:12px;font-family:'DM Mono',monospace;color:var(--ink);}

.er{display:grid;grid-template-columns:1fr 1fr;}
.ec{padding:12px 16px;border-right:1px solid var(--border);}
.ec:last-child{border-right:none;}
.ek{font-size:9px;font-weight:700;letter-spacing:2px;text-transform:uppercase;color:var(--ink3);margin-bottom:4px;}
.ev{font-size:13px;font-weight:500;}

.slbl2{font-size:9px;font-weight:700;letter-spacing:2px;text-transform:uppercase;color:var(--ink3);margin:14px 0 8px;display:flex;align-items:center;gap:6px;}
.slbl2::after{content:'';flex:1;height:1px;background:var(--border);}

@media(max-width:900px){.gen-layout{grid-template-columns:1fr}.er{grid-template-columns:1fr}}
</style>
</head>
<body>

<header>
  <div class="logo"><div class="logo-d">diario</div><div class="logo-e"><em>E</em>NE</div></div>
  <span id="hst">Listo</span>
</header>

<div class="main-tabs">
  <div class="main-tab on" id="mt0" onclick="goMain(0)">📰 Noticias del día</div>
  <div class="main-tab" id="mt1" onclick="goMain(1)">✍️ Redactar nota ENE</div>
</div>

<div class="wrap">

  <!-- ══ PANEL A: PORTALES ══ -->
  <div class="panel on" id="pa">
    <p style="font-size:13px;color:var(--ink2);margin-bottom:16px;">Seleccioná las fuentes y cargá las noticias del día. Elegí las que querés redactar y pasalas al redactor.</p>
    <div class="src-bar">
      <label class="src-chip on" id="sc-prensa"><input type="checkbox" value="prensa" checked onchange="toggleSrc(this,'sc-prensa')">📰 Prensa Río Negro</label>
      <label class="src-chip" id="sc-bariloche"><input type="checkbox" value="bariloche" onchange="toggleSrc(this,'sc-bariloche')">🏔 Bariloche Informa</label>
      <label class="src-chip" id="sc-policia"><input type="checkbox" value="policia" onchange="toggleSrc(this,'sc-policia')">🚔 Policía RN</label>
      <button class="btn" id="btn-load" onclick="loadNews()">Cargar noticias del día →</button>
    </div>
    <div id="cards-grid" class="cards-grid"></div>
    <div id="sel-footer" class="sel-footer" style="display:none">
      <span class="sel-info">Seleccionadas: <b id="sel-n">0</b> nota(s)</span>
      <div style="display:flex;gap:8px">
        <button class="btn-sec" onclick="clearSel()">Limpiar</button>
        <button class="btn" id="btn-pass" disabled onclick="passToRedactor()">Redactar estas notas →</button>
      </div>
    </div>
  </div>

  <!-- ══ PANEL B: REDACTOR ══ -->
  <div class="panel" id="pb">
    <div class="gen-layout">

      <!-- SIDEBAR -->
      <div>
        <div class="sub-tabs">
          <div class="sub-tab on" id="st0" onclick="goSub(0)">📋 Pegar texto</div>
          <div class="sub-tab" id="st1" onclick="goSub(1)">🔗 Desde URL</div>
          <div class="sub-tab" id="st2" onclick="goSub(2)">📌 Del portal</div>
        </div>

        <!-- Sub: Texto -->
        <div class="sub-panel on" id="sp0">
          <div class="slbl">Gacetilla o comunicado</div>
          <textarea id="texto-input" placeholder="Pegá acá el texto de la gacetilla, comunicado oficial o mensaje de WhatsApp..."></textarea>
          <button class="btn" onclick="usarTexto()" style="width:100%">Usar este texto →</button>
        </div>

        <!-- Sub: URL -->
        <div class="sub-panel" id="sp1">
          <div class="slbl">URL del artículo</div>
          <input type="text" id="url-input" placeholder="https://prensa.rionegro.gov.ar/articulo/...">
          <button class="btn" id="btn-url" onclick="fetchUrl()" style="width:100%">
            <span class="spin" id="spin-url"></span>
            <span id="btn-url-lbl">Traer artículo →</span>
          </button>
          <div id="url-preview" style="margin-top:10px;font-size:12px;color:var(--ink3);display:none;"></div>
        </div>

        <!-- Sub: Del portal -->
        <div class="sub-panel" id="sp2">
          <div class="slbl">Notas del portal</div>
          <div id="portal-prev" class="prev-list">
            <p style="font-size:12px;color:var(--ink3);">Cargá noticias en el panel "Noticias del día" y pasalas acá con el botón "Redactar estas notas".</p>
          </div>
        </div>

        <div style="margin-top:16px">
          <div class="slbl">Fuente seleccionada</div>
          <div id="source-preview" class="prev-list">
            <p style="font-size:12px;color:var(--ink3);">Ninguna fuente cargada todavía.</p>
          </div>
        </div>

        <div class="slbl">Opciones</div>
        <div class="opts">
          <div class="opt">
            <label>Sección</label>
            <select id="sec-ov">
              <option value="">Detectar automático</option>
              <option>Sociedad</option><option>Política</option><option>Economía</option>
              <option>Policiales / Judiciales</option><option>Turismo</option>
              <option>Cultura / Espectáculos</option><option>Deportes</option>
              <option>Medio Ambiente</option><option>Tecnología</option><option>Salud</option>
            </select>
          </div>
          <div class="opt">
            <label>Tono</label>
            <select id="tone">
              <option value="informativo">Informativo (ENE default)</option>
              <option value="urgente">Urgente / breaking</option>
              <option value="análisis">Análisis / contexto</option>
              <option value="servicio">Guía práctica</option>
            </select>
          </div>
        </div>

        <div class="chips">
          <label class="chip on" id="ch-rrss"><input type="checkbox" checked onchange="tChip(this,'ch-rrss')">Posts RRSS</label>
          <label class="chip on" id="ch-seo"><input type="checkbox" checked onchange="tChip(this,'ch-seo')">Micro SEO</label>
          <label class="chip on" id="ch-rev"><input type="checkbox" checked onchange="tChip(this,'ch-rev')">Anti-IA</label>
        </div>

        <button class="btn-gen" id="btn-gen" onclick="generate()">
          <span class="spin" id="spin"></span>
          <span id="btn-lbl">Generar nota completa →</span>
        </button>
        <div class="err" id="err"></div>
        <button class="btn-sec" onclick="goMain(0)" style="width:100%;margin-top:10px;text-align:center;">← Volver a noticias</button>
      </div>

      <!-- OUTPUT -->
      <div class="out">
        <div class="empty" id="empty">
          <div class="empty-icon">✦</div>
          <p style="font-size:13px;">Cargá una fuente y hacé clic en<br><strong>Generar nota completa</strong></p>
        </div>
        <div class="results" id="results">
          <div class="slbl2">Fase 1 — Clasificación</div>
          <div class="sec"><div class="sec-hd"><div class="sec-row"><span class="bdg b1">F1</span><span class="sec-nm">Sección · Keywords · Etiquetas</span></div><button class="cp" onclick="doCopy('kw-out',this)">⎘ Copiar</button></div><div class="kw-bl" id="kw-out"></div></div>
          <div class="slbl2">Fase 2 — Nota completa</div>
          <div class="sec"><div class="sec-hd"><div class="sec-row"><span class="bdg b2">F2</span><span class="sec-nm">Volanta · Título · Copete · Desarrollo</span></div><button class="cp" onclick="doCopy('nota-out',this)">⎘ Copiar</button></div><div class="sec-body" id="nota-out"></div></div>
          <div class="sec" id="rrss-sec" style="display:none"><div class="sec-hd"><div class="sec-row"><span class="bdg bx">RRSS</span><span class="sec-nm">Posts redes sociales</span></div><button class="cp" onclick="doCopy('rrss-out',this)">⎘ Copiar</button></div><div class="sec-body" id="rrss-out"></div></div>
          <div class="sec" id="seo-sec" style="display:none"><div class="sec-hd"><div class="sec-row"><span class="bdg b2">SEO</span><span class="sec-nm">Micro-bloque SEO / Discover</span></div><button class="cp" onclick="doCopy('seo-out',this)">⎘ Copiar</button></div><div class="sec-body" id="seo-out"></div></div>
          <div class="slbl2">Fase 3 — Títulos</div>
          <div class="sec"><div class="sec-hd"><div class="sec-row"><span class="bdg b3">F3</span><span class="sec-nm">7 títulos estratégicos</span></div><button class="cp" onclick="doCopy('tit-out',this)">⎘ Copiar</button></div><div class="tl" id="tit-out"></div></div>
          <div class="slbl2">Fase 4 — Metadatos SEO</div>
          <div class="sec"><div class="sec-hd"><div class="sec-row"><span class="bdg b4">F4</span><span class="sec-nm">Meta title · Description · Slug</span></div><button class="cp" onclick="doCopy('meta-out',this)">⎘ Copiar</button></div><div class="mg" id="meta-out"></div></div>
          <div class="sec" id="rev-sec" style="display:none"><div class="sec-hd"><div class="sec-row"><span class="bdg b5">F5</span><span class="sec-nm">Revisión anti-IA</span></div></div><div class="sec-body" id="rev-out"></div></div>
          <div class="slbl2">Fase 6 — Estrategia editorial</div>
          <div class="sec"><div class="sec-hd"><div class="sec-row"><span class="bdg b1">F6</span><span class="sec-nm">Portada · Horario</span></div></div><div class="er" id="ed-out"></div></div>
        </div>
      </div>
    </div>
  </div>

</div>

<script>
// ── ESTADO ──
let portalArticles = [], portalSelected = new Set();
let sourceArticles = [], busy = false;
const $ = id => document.getElementById(id);
const esc = s => String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');

// ── NAVEGACIÓN ──
function goMain(n){
  [0,1].forEach(i=>{ $('mt'+i).classList.toggle('on',i===n); $('pa').classList.toggle('on',n===0); $('pb').classList.toggle('on',n===1); });
  if(n===0){ $('pa').classList.add('on'); $('pb').classList.remove('on'); }
  else{ $('pb').classList.add('on'); $('pa').classList.remove('on'); }
}
function goSub(n){
  [0,1,2].forEach(i=>{ $('st'+i).classList.toggle('on',i===n); $('sp'+i).classList.toggle('on',i===n); });
}
function tChip(inp,id){ $(id).classList.toggle('on',inp.checked); }
function toggleSrc(inp,id){ $(id).classList.toggle('on',inp.checked); }

// ── PANEL A: PORTALES ──
async function loadNews(){
  const checks=[...$('pa').querySelectorAll('.src-chip input:checked')].map(i=>i.value);
  if(!checks.length){ alert('Seleccioná al menos una fuente.'); return; }
  const btn=$('btn-load'); btn.disabled=true; btn.textContent='Cargando…'; st('Cargando noticias…');
  portalArticles=[]; portalSelected.clear();
  $('cards-grid').innerHTML=Array(9).fill(0).map(()=>`<div class="skl"></div>`).join('');
  for(const src of checks){
    try{
      const r=await fetch(`/noticias/${src}`);
      const d=await r.json();
      portalArticles.push(...(d.articles||[]));
    }catch(e){ console.warn('Error',src,e); }
  }
  btn.disabled=false; btn.textContent='Actualizar →';
  st(portalArticles.length+' noticias cargadas');
  renderCards();
}

function renderCards(){
  const grid=$('cards-grid');
  if(!portalArticles.length){
    grid.innerHTML='<p style="color:var(--ink3);font-size:13px;grid-column:1/-1">No se encontraron noticias. Verificá que el backend esté activo.</p>';
    return;
  }
  grid.innerHTML=portalArticles.map((a,i)=>`
    <div class="card${portalSelected.has(i)?' sel':''}" onclick="toggleCard(${i})">
      <div class="card-chk">✓</div>
      <div class="card-body">
        <div class="card-sec">${esc(a.sec||'')}</div>
        <div class="card-title">${esc((a.title||'').slice(0,90))}${(a.title||'').length>90?'…':''}</div>
        <div class="card-src">${esc(a.source||'')}</div>
      </div>
    </div>`).join('');
  $('sel-footer').style.display='flex';
}

function toggleCard(i){
  portalSelected.has(i)?portalSelected.delete(i):portalSelected.add(i);
  $('sel-n').textContent=portalSelected.size;
  $('btn-pass').disabled=portalSelected.size===0;
  renderCards();
}
function clearSel(){ portalSelected.clear(); $('sel-n').textContent=0; $('btn-pass').disabled=true; renderCards(); }

function passToRedactor(){
  const arts=[...portalSelected].map(i=>portalArticles[i]);
  sourceArticles=arts.map(a=>({url:a.url,title:a.title,text:''}));
  $('portal-prev').innerHTML=arts.map(a=>`<div class="prev-item"><small>${esc(a.source)}</small>${esc(a.title.slice(0,80))}${a.title.length>80?'…':''}</div>`).join('');
  updateSourcePreview(arts.map(a=>a.title));
  goMain(1);
  goSub(2);
}

// ── PANEL B: REDACTOR ──
function updateSourcePreview(titles){
  $('source-preview').innerHTML=titles.map(t=>`<div class="prev-item">${esc(t.slice(0,80))}${t.length>80?'…':''}</div>`).join('');
}

function usarTexto(){
  const t=$('texto-input').value.trim();
  if(!t||t.length<20){ alert('Pegá un texto antes de continuar.'); return; }
  sourceArticles=[{url:'',title:'Texto manual',text:t}];
  updateSourcePreview([t.slice(0,80)+'…']);
}

async function fetchUrl(){
  const url=$('url-input').value.trim();
  if(!url.startsWith('http')){ alert('Ingresá una URL válida.'); return; }
  const btn=$('btn-url'); const lbl=$('btn-url-lbl'); const sp=$('spin-url');
  btn.disabled=true; sp.style.display='inline-block'; lbl.textContent='Obteniendo…';
  try{
    const r=await fetch(`/articulo?url=${encodeURIComponent(url)}`);
    const d=await r.json();
    sourceArticles=[{url,title:d.title||url,text:d.text||''}];
    $('url-preview').style.display='block';
    $('url-preview').textContent='✓ '+d.title;
    updateSourcePreview([d.title||url]);
  }catch(e){ alert('Error al obtener la URL.'); }
  finally{ btn.disabled=false; sp.style.display='none'; lbl.textContent='Traer artículo →'; }
}

async function generate(){
  if(busy||!sourceArticles.length){ alert('Cargá una fuente primero.'); return; }
  busy=true; setLoad(true); hideErr(); st('Generando nota con IA…');
  try{
    // Si vienen de portal, traer el texto completo
    const enriched=await Promise.all(sourceArticles.map(async a=>{
      if(a.text) return a;
      if(!a.url) return a;
      try{
        const r=await fetch(`/articulo?url=${encodeURIComponent(a.url)}`);
        const d=await r.json();
        return {...a, text:d.text||'', title:d.title||a.title};
      }catch(e){ return a; }
    }));

    const r=await fetch('/generar',{
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({
        articles: enriched,
        seccion: $('sec-ov').value,
        tono: $('tone').value,
        extras:{
          rrss: $('ch-rrss').querySelector('input').checked,
          micro_seo: $('ch-seo').querySelector('input').checked,
        }
      })
    });
    if(!r.ok) throw new Error(`Error ${r.status}: ${await r.text()}`);
    renderOut(await r.json());
    st('Nota generada ✓');
  }catch(e){ showErr(e.message||'Error.'); st('Error'); }
  finally{ busy=false; setLoad(false); }
}

function stripH(s){ return (s||'').replace(/<[^>]+>/g,'').replace(/&[a-z]+;/g,' ').trim(); }

function renderOut(d){
  $('empty').style.display='none';
  $('results').classList.add('on');

  // F1
  $('kw-out').innerHTML=`
    <div class="kwr"><div class="kwl">Sección</div><div class="kwcs"><span class="kwc pr">${esc(d.seccion)}</span></div></div>
    <div class="kwr"><div class="kwl">Keyword principal</div><div class="kwcs"><span class="kwc pr">${esc(d.kw_principal||'')}</span></div></div>
    <div class="kwr"><div class="kwl">Secundarias</div><div class="kwcs">${(d.kw_secundarias||[]).map(k=>`<span class="kwc">${esc(k)}</span>`).join('')}</div></div>
    ${(d.kw_longtail||[]).length?`<div class="kwr"><div class="kwl">Long tail</div><div class="kwcs">${d.kw_longtail.map(k=>`<span class="kwc">${esc(k)}</span>`).join('')}</div></div>`:''}
    <div class="kwr"><div class="kwl">Etiquetas</div><div class="kwcs">${(d.etiquetas||[]).map(k=>`<span class="kwc">${esc(k)}</span>`).join('')}</div></div>
    <div class="kwr"><div class="kwl">Tipo guía</div><div class="kwcs"><span class="kwc ${d.tipo_guia?'pr':''}">${d.tipo_guia?'Sí':'No'}</span></div></div>`;

  // F2
  $('nota-out').textContent=[
    `VOLANTA\n${d.volanta||''}`,
    `\nTÍTULO\n${d.titulo||''}`,
    `\nCOPETE\n${d.copete||''}`,
    `\nDESARROLLO\n${stripH(d.desarrollo)}`,
    d.bloque_guia?`\nBLOQUE GUÍA\n${stripH(d.bloque_guia)}`:'',
    (d.interlinking||[]).length?`\nINTERLINKING\n${d.interlinking.map(l=>`  → "${l.frase}" → ${l.destino}`).join('\n')}`:''
  ].filter(Boolean).join('');

  // RRSS
  const hasRrss=$('ch-rrss').querySelector('input').checked;
  const hasSeo=$('ch-seo').querySelector('input').checked;
  const hasRev=$('ch-rev').querySelector('input').checked;
  if(hasRrss&&d.rrss&&(d.rrss.instagram||d.rrss.twitter)){
    $('rrss-sec').style.display='block';
    $('rrss-out').textContent=`📸 INSTAGRAM\n${d.rrss.instagram||''}\n\n𝕏 X / TWITTER\n${d.rrss.twitter||''}\n\n📘 FACEBOOK\n${d.rrss.facebook||''}`;
  }
  if(hasSeo&&d.micro_seo){ $('seo-sec').style.display='block'; $('seo-out').textContent=d.micro_seo; }

  // F3
  const ri=d.titulo_recomendado_index??0;
  $('tit-out').innerHTML=(d.titulos||[]).map((t,i)=>`
    <div class="ti${i===ri?' rec':''}">
      <span class="tt">${esc(t.tipo)}</span>
      <span class="tx">${esc(t.texto)}</span>
      ${i===ri?'<span class="rtag">✓ REC</span>':''}
    </div>`).join('')+(d.titulo_recomendado_razon?`<div style="padding:8px 0;font-size:11px;color:var(--ink3);border-top:1px solid var(--paper3);margin-top:3px"><strong style="color:var(--blue2)">¿Por qué?</strong> ${esc(d.titulo_recomendado_razon)}</div>`:'');

  // F4
  $('meta-out').innerHTML=`
    <div class="mr"><div class="mk">Meta title</div><div class="mv">${esc(d.meta_title||'')} <span style="color:#aaa;font-size:10px">(${(d.meta_title||'').length} car.)</span></div></div>
    <div class="mr"><div class="mk">Description</div><div class="mv">${esc(d.meta_description||'')} <span style="color:#aaa;font-size:10px">(${(d.meta_description||'').length} car.)</span></div></div>
    <div class="mr"><div class="mk">Slug</div><div class="mv">${esc(d.slug||'')}</div></div>`;

  // F5
  if(hasRev&&d.revision){
    $('rev-sec').style.display='block';
    const rv=d.revision;
    $('rev-out').textContent=[`${rv.variacion_ritmo?'✓':'✗'} Variación de ritmo`,`${rv.dato_local?'✓':'✗'} Dato local específico`,`${rv.sin_genericos?'✓':'✗'} Sin expresiones genéricas`,rv.observaciones?`\nObservaciones: ${rv.observaciones}`:''].filter(Boolean).join('\n');
  }

  // F6
  $('ed-out').innerHTML=`<div class="ec"><div class="ek">Portada</div><div class="ev">${esc(d.portada||'—')}</div></div><div class="ec"><div class="ek">Horario sugerido</div><div class="ev">${esc(d.horario||'—')}</div></div>`;
  $('results').scrollIntoView({behavior:'smooth',block:'start'});
}

async function doCopy(id,btn){
  try{ await navigator.clipboard.writeText($(id)?.innerText||''); }catch(e){}
  btn.textContent='✓'; btn.classList.add('ok');
  setTimeout(()=>{ btn.textContent='⎘ Copiar'; btn.classList.remove('ok'); },2000);
}
function setLoad(v){ const b=$('btn-gen'); b.disabled=v; b.classList.toggle('loading',v); $('btn-lbl').textContent=v?'Generando…':'Generar nota completa →'; $('spin').style.display=v?'inline-block':'none'; }
function st(t){ $('hst').textContent=t; }
function showErr(m){ const e=$('err'); e.textContent='⚠ '+m; e.classList.add('on'); }
function hideErr(){ $('err').classList.remove('on'); }
</script>
</body>
</html>"""

# ─────────────────────────────────────────
# SCRAPER DE PORTALES
# ─────────────────────────────────────────
SOURCES = {
    "prensa":    {"name":"Prensa Río Negro",   "url":"https://prensa.rionegro.gov.ar/busqueda/articulo?q=",  "base":"https://prensa.rionegro.gov.ar",  "link_pattern":"/articulo/"},
    "bariloche": {"name":"Bariloche Informa",  "url":"https://barilocheinforma.gob.ar",                      "base":"https://barilocheinforma.gob.ar", "link_pattern":None},
    "policia":   {"name":"Policía Río Negro",  "url":"https://policia.rionegro.gov.ar",                      "base":"https://policia.rionegro.gov.ar", "link_pattern":None},
}
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "es-AR,es;q=0.9",
    "Referer": "https://prensa.rionegro.gov.ar/",
}

async def scrape_source(source_key: str):
    src = SOURCES[source_key]
    articles = []
    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True, verify=False) as client:
            r = await client.get(src["url"], headers=HEADERS)
            soup = BeautifulSoup(r.text, "html.parser")
            seen = set()
            pattern = src["link_pattern"]
            links = soup.find_all("a", href=lambda h: h and (pattern in h if pattern else True))
            for a in links:
                href = a.get("href","")
                url = href if href.startswith("http") else src["base"] + href
                if url in seen or len(url) < 20: continue
                seen.add(url)
                heading = a.find(["h2","h3","h4","h5"])
                title = (heading or a).get_text(strip=True).replace("\n"," ").strip()
                if not title or len(title) < 20 or len(title) > 200: continue
                parent = a.find_parent(["article","div","li"])
                sec = "—"
                if parent:
                    h6 = parent.find("h6")
                    if h6: sec = re.sub(r'\d+\s+de\s+\w+\s+de\s+\d{4}','',h6.get_text(strip=True)).strip()
                articles.append({"url":url,"title":title,"sec":sec,"source":src["name"]})
                if len(articles) >= 20: break
    except Exception as e:
        print(f"scrape error {source_key}: {e}")
    return articles

# ─────────────────────────────────────────
# MODELOS
# ─────────────────────────────────────────
class Article(BaseModel):
    url: str = ""
    title: str = ""
    text: str = ""

class GenerateRequest(BaseModel):
    articles: list[Article]
    seccion: str = ""
    tono: str = "informativo"
    extras: dict = {}

# ─────────────────────────────────────────
# ENDPOINTS
# ─────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
def root():
    return HTML

@app.get("/noticias/{source}")
async def get_noticias(source: str):
    if source not in SOURCES:
        return {"articles":[], "error":"Fuente no encontrada"}
    articles = await scrape_source(source)
    return {"articles":articles, "total":len(articles)}

@app.get("/articulo")
async def get_articulo(url: str):
    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True, verify=False) as client:
            r = await client.get(url, headers=HEADERS)
            soup = BeautifulSoup(r.text, "html.parser")
            h1 = soup.find("h1") or soup.find("h2")
            title = h1.get_text(strip=True) if h1 else ""
            for tag in soup(["nav","header","footer","script","style","aside"]):
                tag.decompose()
            body = soup.find("article") or soup.find(class_=lambda c: c and "content" in " ".join(c or [])) or soup.body
            text = body.get_text(separator=" ", strip=True) if body else ""
            return {"title":title, "text":" ".join(text.split())[:3000]}
    except Exception as e:
        return {"title":"", "text":f"(error: {e})"}

@app.post("/generar")
async def generar(req: GenerateRequest):
    if not OPENAI_API_KEY:
        raise HTTPException(500, "OPENAI_API_KEY no configurada en Render")

    parts = []
    for a in req.articles:
        parts.append(f"TÍTULO: {a.title}\nURL: {a.url}\n\n{a.text or '(sin texto)'}")

    user_msg = f"Procesá estas fuentes y generá la nota ENE completa:\n\n{'---'.join(parts)}"
    if req.seccion:
        user_msg += f"\n\nSECCIÓN FORZADA: {req.seccion}"
    if req.tono != "informativo":
        user_msg += f"\n\nTONO: {req.tono}"
    if not req.extras.get("rrss"):
        user_msg += "\n\nDejar rrss vacío."
    if not req.extras.get("micro_seo"):
        user_msg += "\n\nDejar micro_seo vacío."

    async with httpx.AsyncClient(timeout=90) as client:
        resp = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": "gpt-4o-mini",
                "temperature": 0.7,
                "max_tokens": 4000,
                "response_format": {"type": "json_object"},
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_msg}
                ]
            }
        )

    if resp.status_code != 200:
        raise HTTPException(500, f"Error OpenAI: {resp.text}")

    data = resp.json()
    raw = data["choices"][0]["message"]["content"]
    try:
        return json.loads(raw)
    except Exception:
        raise HTTPException(500, "No se pudo parsear la respuesta de GPT")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
