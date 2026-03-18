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

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

SITE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "es-AR,es;q=0.9",
    "Referer": "https://prensa.rionegro.gov.ar/",
}

SYSTEM_PROMPT = """Sos el editor jefe digital de Diario ENE, medio regional con base en Bariloche y foco en Río Negro y la Patagonia.
ESTILO ENE: título directo, urgencia funcional, lenguaje claro, cero adjetivos grandilocuentes, pensado para el lector patagónico.
Evitar: "en el marco de", "con el objetivo de", "se llevó a cabo", párrafos de longitud idéntica.
Negrita: nombres propios, datos numéricos, keywords SEO. Cursiva: marcas, términos técnicos. Máx 15% del texto.
RESPONDÉ SOLO con JSON válido (sin markdown):
{"seccion":"","kw_principal":"","kw_secundarias":["","","","",""],"kw_longtail":["","",""],"tipo_guia":false,"etiquetas":["","","",""],"volanta":"","titulo":"","copete":"","desarrollo":"","bloque_guia":null,"interlinking":[{"frase":"","destino":""}],"micro_seo":"","rrss":{"instagram":"","twitter":"","facebook":""},"newsletter":"","titulos":[{"tipo":"Informativo puro","texto":""},{"tipo":"Informativo puro","texto":""},{"tipo":"Impacto periodístico","texto":""},{"tipo":"Impacto periodístico","texto":""},{"tipo":"Explicativo / Contexto","texto":""},{"tipo":"Explicativo / Contexto","texto":""},{"tipo":"Híbrido estratégico","texto":""}],"titulo_recomendado_index":0,"titulo_recomendado_razon":"","meta_title":"","meta_description":"","slug":"","revision":{"variacion_ritmo":true,"dato_local":true,"sin_genericos":true,"observaciones":""},"portada":"","horario":""}"""

HTML = r"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Redactor ENE</title>
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700;900&family=IBM+Plex+Sans:wght@300;400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
:root{--ink:#0f0f0f;--ink2:#3a3a3a;--ink3:#6b6b6b;--paper:#f8f6f1;--paper2:#f0ede6;--paper3:#e8e4db;--accent:#c8391a;--accent2:#e85d3a;--gold:#b8962e;--border:#d4cfc5;--ok:#2a7a4b;--r:4px;}
*{box-sizing:border-box;margin:0;padding:0;}
body{font-family:'IBM Plex Sans',sans-serif;background:var(--paper);color:var(--ink);min-height:100vh;}
header{background:var(--ink);border-bottom:3px solid var(--accent);padding:12px 24px;display:flex;align-items:center;justify-content:space-between;position:sticky;top:0;z-index:100;}
.logo{font-family:'Playfair Display',serif;font-size:22px;font-weight:900;color:#fff;}
.logo-tag{font-size:10px;font-weight:600;letter-spacing:2px;text-transform:uppercase;color:#e85d3a;margin-left:10px;}
#hst{font-size:11px;color:#777;}
.steps{display:flex;gap:2px;padding:20px 24px 0;max-width:1200px;margin:0 auto;}
.step{padding:8px 18px;font-size:12px;font-weight:500;border:1px solid var(--border);background:var(--paper2);color:var(--ink3);border-radius:3px 3px 0 0;border-bottom:none;cursor:pointer;}
.step.on{background:#fff;color:var(--ink);border-bottom:1px solid #fff;margin-bottom:-1px;z-index:1;}
.step.done{color:var(--ok);}
.wrap{max-width:1200px;margin:0 auto;padding:0 24px 48px;}
.panel{display:none;background:#fff;border:1px solid var(--border);border-radius:0 3px 3px 3px;padding:24px;}
.panel.on{display:block;}
.intro{font-size:13px;color:var(--ink2);margin-bottom:16px;line-height:1.6;}
.top-row{display:flex;align-items:center;gap:10px;margin-bottom:20px;flex-wrap:wrap;}
.top-row label{font-size:11px;font-weight:600;letter-spacing:1px;text-transform:uppercase;color:var(--ink3);}
textarea{width:100%;min-height:180px;padding:14px;font-family:'IBM Plex Sans',sans-serif;font-size:13px;line-height:1.7;color:var(--ink);background:#fff;border:1px solid var(--border);border-radius:var(--r);outline:none;resize:vertical;margin-bottom:12px;}
textarea:focus{border-color:var(--accent);}
textarea::placeholder{color:#bbb;}
.btn{padding:9px 18px;background:var(--accent);color:#fff;border:none;border-radius:var(--r);font-size:12px;font-weight:600;cursor:pointer;font-family:'IBM Plex Sans',sans-serif;}
.btn:hover{background:#a82e15;}
.btn:disabled{background:#bbb;cursor:not-allowed;}
.btn-sec{padding:9px 14px;background:transparent;border:1px solid var(--border);border-radius:var(--r);font-size:12px;color:var(--ink3);cursor:pointer;font-family:'IBM Plex Sans',sans-serif;}
.btn-sec:hover{border-color:var(--ink2);color:var(--ink);}
.cards-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:12px;}
.card{border:1px solid var(--border);border-radius:var(--r);cursor:pointer;background:#fff;overflow:hidden;position:relative;transition:border-color .15s;}
.card:hover{border-color:var(--ink2);}
.card.sel{border:2px solid var(--accent);box-shadow:0 0 0 3px #c8391a15;}
.card-chk{position:absolute;top:8px;right:8px;width:22px;height:22px;background:var(--accent);color:#fff;border-radius:50%;font-size:13px;font-weight:700;display:none;align-items:center;justify-content:center;}
.card.sel .card-chk{display:flex;}
.card-body{padding:12px 14px;}
.card-sec{font-size:9px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;color:var(--ink3);margin-bottom:5px;}
.card-title{font-size:13px;font-weight:600;line-height:1.45;color:var(--ink);}
.sel-footer{margin-top:18px;padding:12px 16px;background:var(--paper2);border:1px solid var(--border);border-radius:var(--r);display:flex;align-items:center;justify-content:space-between;gap:12px;}
.sel-info{font-size:13px;color:var(--ink2);}
.sel-info b{color:var(--accent);}
.skl{background:linear-gradient(90deg,var(--paper2) 25%,var(--paper3) 50%,var(--paper2) 75%);background-size:200% 100%;animation:sk 1.2s infinite;border-radius:var(--r);}
@keyframes sk{0%{background-position:200% 0}100%{background-position:-200% 0}}
.gen-layout{display:grid;grid-template-columns:280px 1fr;gap:24px;}
.slbl{font-size:9px;font-weight:700;letter-spacing:2px;text-transform:uppercase;color:var(--ink3);margin-bottom:8px;display:flex;align-items:center;gap:6px;}
.slbl::after{content:'';flex:1;height:1px;background:var(--border);}
.prev-list{display:flex;flex-direction:column;gap:6px;margin-bottom:16px;}
.prev-item{padding:8px 10px;background:var(--paper);border:1px solid var(--border);border-radius:var(--r);font-size:11px;color:var(--ink2);line-height:1.4;}
.prev-item small{display:block;font-size:9px;color:var(--ink3);text-transform:uppercase;letter-spacing:1px;margin-bottom:2px;}
.opts{background:var(--paper);border:1px solid var(--border);border-radius:var(--r);overflow:hidden;margin-bottom:12px;}
.opt{padding:9px 12px;border-bottom:1px solid var(--paper3);}
.opt:last-child{border-bottom:none;}
.opt label{display:block;font-size:9px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;color:var(--ink3);margin-bottom:5px;}
select{width:100%;padding:7px 10px;font-family:'IBM Plex Sans',sans-serif;font-size:12px;color:var(--ink);background:#fff;border:1px solid var(--border);border-radius:var(--r);outline:none;appearance:none;}
.chips{display:flex;flex-wrap:wrap;gap:5px;margin-bottom:12px;}
.chip{display:flex;align-items:center;gap:4px;padding:5px 11px;border:1px solid var(--border);border-radius:20px;font-size:11px;cursor:pointer;background:#fff;user-select:none;}
.chip input{display:none;}
.chip.on{background:var(--ink);color:#fff;border-color:var(--ink);}
.spin{display:none;width:13px;height:13px;border:2px solid rgba(255,255,255,.3);border-top-color:#fff;border-radius:50%;animation:spin .7s linear infinite;vertical-align:middle;margin-right:6px;}
.loading .spin{display:inline-block;}
@keyframes spin{to{transform:rotate(360deg)}}
.err{background:#fde8e3;border:1px solid var(--accent2);border-radius:var(--r);padding:10px 14px;font-size:12px;color:var(--accent);margin-top:10px;display:none;}
.err.on{display:block;}
.out{min-height:400px;}
.empty{text-align:center;padding:60px 20px;color:var(--ink3);}
.results{display:none;}
.results.on{display:block;animation:fi .3s ease;}
@keyframes fi{from{opacity:0;transform:translateY(5px)}to{opacity:1;transform:translateY(0)}}
.sec{border:1px solid var(--border);border-radius:var(--r);margin-bottom:12px;overflow:hidden;}
.sec-hd{display:flex;align-items:center;justify-content:space-between;padding:8px 14px;background:var(--paper);border-bottom:1px solid var(--border);}
.sec-row{display:flex;align-items:center;gap:7px;}
.bdg{font-size:8px;font-weight:700;letter-spacing:2px;text-transform:uppercase;padding:2px 6px;border-radius:2px;}
.b1{background:#e8f4ec;color:#2a7a4b;}.b2{background:#fde8e3;color:#c8391a;}
.b3{background:#e8edf8;color:#2a4a9a;}.b4{background:#fdf6e3;color:#b8962e;}
.b5{background:#f0e8f8;color:#6a2a9a;}.bx{background:#e8f4f8;color:#1a6a8a;}
.sec-nm{font-size:11px;font-weight:600;color:var(--ink2);}
.cp{font-size:10px;padding:4px 10px;background:transparent;border:1px solid var(--border);border-radius:20px;cursor:pointer;color:var(--ink3);font-family:'IBM Plex Sans',sans-serif;}
.cp:hover{border-color:var(--ink2);color:var(--ink);}
.cp.ok{background:#2a7a4b;color:#fff;border-color:#2a7a4b;}
.sec-body{padding:16px 18px;font-size:13px;line-height:1.8;color:var(--ink);white-space:pre-wrap;}
.kw-bl{padding:12px 16px;}.kwr{margin-bottom:10px;}
.kwl{font-size:9px;font-weight:700;letter-spacing:2px;text-transform:uppercase;color:var(--ink3);margin-bottom:5px;}
.kwcs{display:flex;flex-wrap:wrap;gap:5px;}
.kwc{font-size:11px;padding:3px 9px;border-radius:2px;border:1px solid var(--border);color:var(--ink2);background:var(--paper);}
.kwc.pr{background:var(--ink);color:#fff;border-color:var(--ink);font-weight:500;}
.tl{padding:12px 16px;}
.ti{display:flex;gap:8px;padding:9px 0;border-bottom:1px solid var(--paper3);align-items:flex-start;}
.ti:last-child{border-bottom:none;}
.tt{font-size:9px;font-weight:700;letter-spacing:1px;text-transform:uppercase;color:var(--ink3);min-width:90px;padding-top:2px;}
.tx{font-size:12px;color:var(--ink);flex:1;line-height:1.5;}
.ti.rec .tx{font-weight:600;color:#c8391a;}
.rtag{font-size:8px;background:#c8391a;color:#fff;padding:2px 6px;border-radius:2px;white-space:nowrap;}
.mr{display:grid;grid-template-columns:110px 1fr;border-bottom:1px solid var(--paper3);}
.mr:last-child{border-bottom:none;}
.mk{font-size:9px;font-weight:700;letter-spacing:1px;text-transform:uppercase;color:var(--ink3);padding:10px 14px;background:var(--paper);border-right:1px solid var(--paper3);}
.mv{padding:10px 14px;font-size:12px;font-family:'IBM Plex Mono',monospace;color:var(--ink);}
.er{display:grid;grid-template-columns:1fr 1fr;}
.ec{padding:12px 16px;border-right:1px solid var(--paper3);}
.ec:last-child{border-right:none;}
.ek{font-size:9px;font-weight:700;letter-spacing:2px;text-transform:uppercase;color:var(--ink3);margin-bottom:4px;}
.ev{font-size:13px;font-weight:500;color:var(--ink);}
.slbl2{font-size:9px;font-weight:700;letter-spacing:2px;text-transform:uppercase;color:var(--ink3);margin:14px 0 8px;display:flex;align-items:center;gap:6px;}
.slbl2::after{content:'';flex:1;height:1px;background:var(--border);}
.tab-row{display:flex;gap:4px;margin-bottom:16px;}
.tab{padding:7px 16px;font-size:12px;font-weight:500;border:1px solid var(--border);background:var(--paper2);color:var(--ink3);border-radius:var(--r);cursor:pointer;}
.tab.on{background:var(--ink);color:#fff;border-color:var(--ink);}
.tab-pnl{display:none;}.tab-pnl.on{display:block;}
@media(max-width:800px){.gen-layout{grid-template-columns:1fr}.er{grid-template-columns:1fr}.ec{border-right:none;border-bottom:1px solid var(--paper3)}.ec:last-child{border-bottom:none}}
</style>
</head>
<body>
<header>
  <div><span class="logo">ENE</span><span class="logo-tag">Redactor IA</span></div>
  <span id="hst">Listo</span>
</header>
<div class="steps">
  <div class="step on" id="s0" onclick="goStep(0)">① Fuente</div>
  <div class="step" id="s1" onclick="goStep(1)">② Generar nota ENE</div>
</div>
<div class="wrap">

  <!-- STEP 0 -->
  <div class="panel on" id="p0">
    <div class="tab-row">
      <div class="tab on" id="tab-texto" onclick="goTab('texto')">📋 Pegar texto</div>
      <div class="tab" id="tab-url" onclick="goTab('url')">🔗 Desde URL</div>
    </div>

    <!-- Tab: pegar texto -->
    <div class="tab-pnl on" id="pnl-texto">
      <p class="intro">Pegá la gacetilla, comunicado o texto de WhatsApp.</p>
      <textarea id="texto-input" placeholder="Pegá acá el texto de la gacetilla o comunicado oficial..."></textarea>
      <div style="display:flex;justify-content:flex-end">
        <button class="btn" onclick="usarTexto()">Usar este texto →</button>
      </div>
    </div>

    <!-- Tab: URL -->
    <div class="tab-pnl" id="pnl-url">
      <p class="intro">Pegá una o varias URLs de prensa.rionegro.gov.ar (una por línea) y el sistema trae el texto automáticamente.</p>
      <textarea id="url-input" placeholder="https://prensa.rionegro.gov.ar/articulo/58335/...&#10;https://prensa.rionegro.gov.ar/articulo/58334/..." style="min-height:120px;"></textarea>
      <div style="display:flex;justify-content:flex-end;gap:8px;align-items:center">
        <span id="url-status" style="font-size:12px;color:var(--ink3);"></span>
        <button class="btn" id="btn-fetch-url" onclick="fetchUrls()">Traer artículos →</button>
      </div>
      <div id="url-cards" class="cards-grid" style="margin-top:16px;"></div>
      <div id="url-sel-footer" class="sel-footer" style="display:none;margin-top:12px;">
        <span class="sel-info">Seleccionadas: <b id="url-sel-n">0</b></span>
        <button class="btn" id="btn-url-next" disabled onclick="usarUrls()">Continuar →</button>
      </div>
    </div>
  </div>

  <!-- STEP 1 -->
  <div class="panel" id="p1">
    <div class="gen-layout">
      <div>
        <div class="slbl">Fuente</div>
        <div class="prev-list" id="prev-list"></div>
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
          <label class="chip" id="ch-nl"><input type="checkbox" onchange="tChip(this,'ch-nl')">Newsletter</label>
          <label class="chip on" id="ch-seo"><input type="checkbox" checked onchange="tChip(this,'ch-seo')">Micro SEO</label>
          <label class="chip on" id="ch-rev"><input type="checkbox" checked onchange="tChip(this,'ch-rev')">Anti-IA</label>
        </div>
        <button class="btn" id="btn-gen" onclick="generate()" style="width:100%;padding:13px;font-size:13px;">
          <span class="spin" id="spin"></span>
          <span id="btn-lbl">Generar nota completa →</span>
        </button>
        <div class="err" id="err"></div>
        <button class="btn-sec" onclick="goStep(0)" style="width:100%;margin-top:10px;text-align:center;">← Volver</button>
      </div>
      <div class="out">
        <div class="empty" id="empty" style="text-align:center;padding:60px 20px;color:var(--ink3);">
          <div style="font-size:32px;opacity:.2;margin-bottom:10px;">✦</div>
          <p>Configurá las opciones y hacé clic en<br><strong>Generar nota completa</strong></p>
        </div>
        <div class="results" id="results">
          <div class="slbl2">Fase 1 — Clasificación</div>
          <div class="sec"><div class="sec-hd"><div class="sec-row"><span class="bdg b1">F1</span><span class="sec-nm">Sección · Keywords · Etiquetas</span></div><button class="cp" onclick="doCopy('kw-out',this)">⎘ Copiar</button></div><div class="kw-bl" id="kw-out"></div></div>
          <div class="slbl2">Fase 2 — Nota completa</div>
          <div class="sec"><div class="sec-hd"><div class="sec-row"><span class="bdg b2">F2</span><span class="sec-nm">Volanta · Título · Copete · Desarrollo</span></div><button class="cp" onclick="doCopy('nota-out',this)">⎘ Copiar</button></div><div class="sec-body" id="nota-out"></div></div>
          <div class="sec" id="rrss-sec" style="display:none"><div class="sec-hd"><div class="sec-row"><span class="bdg bx">EXTRA</span><span class="sec-nm">Posts redes sociales</span></div><button class="cp" onclick="doCopy('rrss-out',this)">⎘ Copiar</button></div><div class="sec-body" id="rrss-out"></div></div>
          <div class="sec" id="nl-sec" style="display:none"><div class="sec-hd"><div class="sec-row"><span class="bdg bx">EXTRA</span><span class="sec-nm">Newsletter</span></div><button class="cp" onclick="doCopy('nl-out',this)">⎘ Copiar</button></div><div class="sec-body" id="nl-out"></div></div>
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
const API = "";  // mismo servidor
let sourceArticles = [], urlSelected = new Set(), busy = false;
const $ = id => document.getElementById(id);
const esc = s => String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');

function goStep(n){
  [0,1].forEach(i=>{ $('s'+i).className='step'+(i===n?' on':i<n?' done':''); $('p'+i).className='panel'+(i===n?' on':''); });
}
function goTab(t){
  ['texto','url'].forEach(x=>{ $('tab-'+x).className='tab'+(x===t?' on':''); $('pnl-'+x).className='tab-pnl'+(x===t?' on':''); });
}
function tChip(inp,id){ $(id).classList.toggle('on',inp.checked); }

// --- TAB TEXTO ---
function usarTexto(){
  const t = $('texto-input').value.trim();
  if(!t||t.length<20){ alert('Pegá un texto antes de continuar.'); return; }
  sourceArticles = [{url:'', title:'Texto pegado', text: t}];
  $('prev-list').innerHTML=`<div class="prev-item"><small>Texto manual</small>${esc(t.slice(0,120))}${t.length>120?'…':''}</div>`;
  goStep(1);
}

// --- TAB URL ---
async function fetchUrls(){
  const raw = $('url-input').value.trim();
  if(!raw){ alert('Pegá al menos una URL.'); return; }
  const urls = raw.split('\n').map(u=>u.trim()).filter(u=>u.startsWith('http'));
  if(!urls.length){ alert('No encontré URLs válidas.'); return; }
  const btn=$('btn-fetch-url'); btn.disabled=true; btn.textContent='Obteniendo…';
  $('url-status').textContent=''; urlSelected.clear(); sourceArticles=[];
  $('url-cards').innerHTML=Array(urls.length).fill(0).map(()=>`<div class="skl" style="height:70px"></div>`).join('');
  const results = await Promise.all(urls.map(async url=>{
    try{
      const r=await fetch(`/articulo?url=${encodeURIComponent(url)}`);
      const d=await r.json();
      return {url, title: d.title||url, text: d.text||'', sec: d.sec||'Río Negro'};
    }catch(e){ return {url, title:url, text:'', sec:''}; }
  }));
  sourceArticles = results;
  btn.disabled=false; btn.textContent='Traer artículos →';
  $('url-status').textContent=results.length+' artículo(s) encontrado(s)';
  renderUrlCards();
}

function renderUrlCards(){
  const grid=$('url-cards');
  grid.innerHTML=sourceArticles.map((a,i)=>`
    <div class="card${urlSelected.has(i)?' sel':''}" onclick="toggleUrl(${i})">
      <div class="card-chk">✓</div>
      <div class="card-body">
        <div class="card-sec">${esc(a.sec)}</div>
        <div class="card-title">${esc(a.title.slice(0,100))}${a.title.length>100?'…':''}</div>
      </div>
    </div>`).join('');
  $('url-sel-footer').style.display='flex';
}

function toggleUrl(i){
  urlSelected.has(i)?urlSelected.delete(i):urlSelected.add(i);
  $('url-sel-n').textContent=urlSelected.size;
  $('btn-url-next').disabled=urlSelected.size===0;
  renderUrlCards();
}

function usarUrls(){
  const sel=[...urlSelected].map(i=>sourceArticles[i]);
  $('prev-list').innerHTML=sel.map(a=>`<div class="prev-item"><small>${esc(a.sec||'URL')}</small>${esc(a.title.slice(0,80))}${a.title.length>80?'…':''}</div>`).join('');
  sourceArticles=sel;
  goStep(1);
}

// --- GENERAR ---
async function generate(){
  if(busy||!sourceArticles.length) return;
  busy=true; setLoad(true); hideErr(); st('Generando nota con IA…');
  try{
    const r=await fetch('/generar',{
      method:'POST', headers:{'Content-Type':'application/json'},
      body:JSON.stringify({
        articles: sourceArticles,
        seccion: $('sec-ov').value,
        tono: $('tone').value,
        extras:{
          rrss: $('ch-rrss').querySelector('input').checked,
          newsletter: $('ch-nl').querySelector('input').checked,
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
  $('empty').style.display='none'; $('results').classList.add('on');
  $('kw-out').innerHTML=`
    <div class="kwr"><div class="kwl">Sección</div><div class="kwcs"><span class="kwc pr">${esc(d.seccion)}</span></div></div>
    <div class="kwr"><div class="kwl">Keyword principal</div><div class="kwcs"><span class="kwc pr">${esc(d.kw_principal)}</span></div></div>
    <div class="kwr"><div class="kwl">Secundarias</div><div class="kwcs">${(d.kw_secundarias||[]).map(k=>`<span class="kwc">${esc(k)}</span>`).join('')}</div></div>
    ${(d.kw_longtail||[]).length?`<div class="kwr"><div class="kwl">Long tail</div><div class="kwcs">${d.kw_longtail.map(k=>`<span class="kwc">${esc(k)}</span>`).join('')}</div></div>`:''}
    <div class="kwr"><div class="kwl">Etiquetas</div><div class="kwcs">${(d.etiquetas||[]).map(k=>`<span class="kwc">${esc(k)}</span>`).join('')}</div></div>
    <div class="kwr"><div class="kwl">Tipo guía</div><div class="kwcs"><span class="kwc ${d.tipo_guia?'pr':''}">${d.tipo_guia?'Sí':'No'}</span></div></div>`;
  $('nota-out').textContent=[
    `VOLANTA\n${d.volanta||''}`,`\nTÍTULO\n${d.titulo||''}`,`\nCOPETE\n${d.copete||''}`,
    `\nDESARROLLO\n${stripH(d.desarrollo)}`,
    d.bloque_guia?`\nBLOQUE GUÍA\n${stripH(d.bloque_guia)}`:'',
    (d.interlinking||[]).length?`\nINTERLINKING\n${d.interlinking.map(l=>`  → "${l.frase}" → ${l.destino}`).join('\n')}`:''
  ].filter(Boolean).join('');
  const hasRrss=$('ch-rrss').querySelector('input').checked;
  const hasNl=$('ch-nl').querySelector('input').checked;
  const hasSeo=$('ch-seo').querySelector('input').checked;
  const hasRev=$('ch-rev').querySelector('input').checked;
  if(hasRrss&&d.rrss){$('rrss-sec').style.display='block';$('rrss-out').textContent=`📸 INSTAGRAM\n${d.rrss.instagram||''}\n\n𝕏 X\n${d.rrss.twitter||''}\n\n📘 FACEBOOK\n${d.rrss.facebook||''}`;}
  if(hasNl&&d.newsletter){$('nl-sec').style.display='block';$('nl-out').textContent=d.newsletter;}
  if(hasSeo&&d.micro_seo){$('seo-sec').style.display='block';$('seo-out').textContent=d.micro_seo;}
  const ri=d.titulo_recomendado_index??0;
  $('tit-out').innerHTML=(d.titulos||[]).map((t,i)=>`<div class="ti${i===ri?' rec':''}"><span class="tt">${esc(t.tipo)}</span><span class="tx">${esc(t.texto)}</span>${i===ri?'<span class="rtag">✓ REC</span>':''}</div>`).join('')
    +(d.titulo_recomendado_razon?`<div style="padding:8px 0;font-size:11px;color:var(--ink3);border-top:1px solid var(--paper3);margin-top:3px"><strong style="color:#c8391a">¿Por qué?</strong> ${esc(d.titulo_recomendado_razon)}</div>`:'');
  $('meta-out').innerHTML=`<div class="mr"><div class="mk">Meta title</div><div class="mv">${esc(d.meta_title||'')} <span style="color:var(--ink3);font-size:10px">(${(d.meta_title||'').length} car.)</span></div></div><div class="mr"><div class="mk">Description</div><div class="mv">${esc(d.meta_description||'')} <span style="color:var(--ink3);font-size:10px">(${(d.meta_description||'').length} car.)</span></div></div><div class="mr"><div class="mk">Slug</div><div class="mv">${esc(d.slug||'')}</div></div>`;
  if(hasRev&&d.revision){$('rev-sec').style.display='block';const rv=d.revision;$('rev-out').textContent=[`${rv.variacion_ritmo?'✓':'✗'} Variación de ritmo`,`${rv.dato_local?'✓':'✗'} Dato local específico`,`${rv.sin_genericos?'✓':'✗'} Sin expresiones genéricas`,rv.observaciones?`\nObservaciones: ${rv.observaciones}`:''].filter(Boolean).join('\n');}
  $('ed-out').innerHTML=`<div class="ec"><div class="ek">Portada</div><div class="ev">${esc(d.portada||'—')}</div></div><div class="ec"><div class="ek">Horario sugerido</div><div class="ev">${esc(d.horario||'—')}</div></div>`;
  $('results').scrollIntoView({behavior:'smooth',block:'start'});
}
async function doCopy(id,btn){
  try{await navigator.clipboard.writeText($(id)?.innerText||'');}catch(e){}
  btn.textContent='✓'; btn.classList.add('ok');
  setTimeout(()=>{btn.textContent='⎘ Copiar';btn.classList.remove('ok');},2000);
}
function setLoad(v){const b=$('btn-gen');b.disabled=v;b.classList.toggle('loading',v);$('btn-lbl').textContent=v?'Generando…':'Generar nota completa →';$('spin').style.display=v?'inline-block':'none';}
function st(t){$('hst').textContent=t;}
function showErr(m){const e=$('err');e.textContent='⚠ '+m;e.classList.add('on');}
function hideErr(){$('err').classList.remove('on');}
</script>
</body>
</html>"""

class Article(BaseModel):
    url: str = ""
    title: str = ""
    text: str = ""

class GenerateRequest(BaseModel):
    articles: list[Article]
    seccion: str = ""
    tono: str = "informativo"
    extras: dict = {}

@app.get("/", response_class=HTMLResponse)
def root():
    return HTML

@app.get("/articulo")
async def get_articulo(url: str = Query(...)):
    async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
        try:
            r = await client.get(url, headers=SITE_HEADERS)
            soup = BeautifulSoup(r.text, "html.parser")
            # Get title
            h1 = soup.find("h1") or soup.find("h2")
            title = h1.get_text(strip=True) if h1 else ""
            # Get section
            sec_el = soup.find(class_=lambda c: c and any(x in " ".join(c) for x in ["categ","section","tag"]))
            sec = sec_el.get_text(strip=True) if sec_el else "Río Negro"
            # Get body text
            for tag in soup(["nav","header","footer","script","style","aside"]):
                tag.decompose()
            body = soup.find("article") or soup.find(class_=lambda c: c and "content" in " ".join(c or [])) or soup.body
            text = body.get_text(separator=" ", strip=True) if body else ""
            return {"title": title, "sec": sec, "text": " ".join(text.split())[:3000]}
        except Exception as e:
            return {"title": url, "sec": "Río Negro", "text": f"(error: {e})"}

@app.post("/generar")
async def generar(req: GenerateRequest):
    if not ANTHROPIC_API_KEY:
        raise HTTPException(500, "ANTHROPIC_API_KEY no configurada")
    parts = []
    for a in req.articles:
        parts.append(f"TÍTULO: {a.title}\nURL: {a.url}\n\n{a.text or '(sin texto)'}")
    user_msg = f"Procesá estas fuentes y generá la nota ENE:\n\n{'---'.join(parts)}"
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
            headers={"x-api-key": ANTHROPIC_API_KEY, "anthropic-version": "2023-06-01", "content-type": "application/json"},
            json={"model":"claude-sonnet-4-20250514","max_tokens":4000,"system":SYSTEM_PROMPT,"messages":[{"role":"user","content":user_msg}]},
        )
    if resp.status_code != 200:
        raise HTTPException(500, f"Error API: {resp.text}")
    data = resp.json()
    raw = "".join(b.get("text","") for b in data.get("content",[])).replace("```json","").replace("```","").strip()
    try:
        return json.loads(raw)
    except Exception:
        raise HTTPException(500, "No se pudo parsear la respuesta")
