#!/usr/bin/env python3
"""
Meta Ads Agent — Apple-style Web Interface
Ruben's Agency
"""

import anthropic
import json
import os
import sys
import uuid
import threading
import webbrowser
from datetime import datetime

try:
    from flask import Flask, request, jsonify, Response
except ImportError:
    print("\n⚠️  Falta Flask. Instálalo con:\n   pip3 install flask\n")
    sys.exit(1)

app = Flask(__name__)
sessions: dict = {}  # session_id → {messages, state, doc}

# ─────────────────────────────────────────────────────────
# SYSTEM PROMPT
# ─────────────────────────────────────────────────────────

SYSTEM_PROMPT = """Eres el estratega senior de Meta Ads de la agencia de Ruben.
Tu trabajo es guiar a Ruben a través de su metodología para construir una estrategia completa de Meta Ads para un cliente.

## CLIENTES TÍPICOS DE RUBEN
- Coaches y consultores de negocios, ventas y liderazgo en México
  Facturan $5,000–$30,000 USD/mes. 80% de sus clientes llegan por referidos.
  Necesitan un sistema predecible de adquisición. Ya intentaron orgánico y agencias genéricas sin resultados.
- Software a la medida (B2B)
- Campamento para niños

## METODOLOGÍA (síguela en este orden):

### FASE 1 — OFERTA
Entiende qué vende, precio, formato y qué resultados concretos genera para sus clientes.
Cuando tengas suficiente info, llama a `save_offer`.

### FASE 2 — NICHO / ICP
Entiende quién es el cliente ideal: demografía, situación actual, dolores profundos, deseos, qué ha intentado.
Cuando tengas suficiente info, llama a `save_icp`.

### FASE 3 — INVESTIGACIÓN PROFUNDA
Genera 5-7 ángulos de venta con nombre, dolor que activan, mensaje central, hipótesis y 2-3 hooks cada uno.
Un ángulo es una perspectiva única para conectar con un dolor o deseo específico del ICP.
Los mejores ángulos son específicos, creíbles y directamente ligados a un dolor real.
Llama a `save_angles` con todos los ángulos y mensajes ganadores.

### FASE 4 — ESTRATEGIA META ADS
Pregunta el presupuesto mensual y el objetivo de campaña (leads, llamadas, ventas directas).
Construye la estructura completa: campaña → conjuntos → anuncios.
Por cada conjunto: hipótesis clara, audiencia, presupuesto diario, copy completo (hook + desarrollo + CTA) y brief creativo.
Llama a `save_strategy` con todo.

### FASE 5 — DOCUMENTO FINAL
Llama a `compile_doc` para generar el documento final.

## REGLAS
- Máximo 2 preguntas a la vez, nunca un formulario largo
- Sé directo, habla como colega estratega, no como asistente genérico
- Usa los datos reales del cliente, jamás ejemplos genéricos
- Llama a los tools sin anunciarlo, continúa la conversación naturalmente
- Si el usuario da respuestas vagas, pide especificidad con ejemplos concretos
- Al terminar cada fase haz una síntesis breve antes de pasar a la siguiente

Empieza preguntando con qué cliente van a trabajar hoy."""

# ─────────────────────────────────────────────────────────
# TOOLS
# ─────────────────────────────────────────────────────────

TOOLS = [
    {
        "name": "save_offer",
        "description": "Guarda la oferta estructurada cuando esté completa.",
        "input_schema": {
            "type": "object",
            "properties": {
                "nombre_cliente":          {"type": "string"},
                "que_vende":               {"type": "string"},
                "precio":                  {"type": "string"},
                "formato_o_duracion":      {"type": "string"},
                "propuesta_de_valor":      {"type": "string"},
                "promesa_principal":       {"type": "string"},
                "mecanismo_unico":         {"type": "string"},
                "resultados_comprobables": {"type": "array", "items": {"type": "string"}},
                "testimonios_clave":       {"type": "array", "items": {"type": "string"}},
            },
            "required": ["nombre_cliente", "que_vende", "precio", "propuesta_de_valor", "promesa_principal"],
        },
    },
    {
        "name": "save_icp",
        "description": "Guarda el perfil del cliente ideal cuando esté completo.",
        "input_schema": {
            "type": "object",
            "properties": {
                "descripcion_demografica": {"type": "string"},
                "situacion_actual":        {"type": "string"},
                "dolores_principales":     {"type": "array", "items": {"type": "string"}},
                "dolor_mas_profundo":      {"type": "string"},
                "deseo_principal":         {"type": "string"},
                "resultado_sonado":        {"type": "string"},
                "lo_que_ha_intentado":     {"type": "array", "items": {"type": "string"}},
                "por_que_no_funciono":     {"type": "string"},
                "objeciones_principales":  {"type": "array", "items": {"type": "string"}},
                "momento_de_compra":       {"type": "string"},
            },
            "required": ["descripcion_demografica", "dolores_principales", "deseo_principal", "resultado_sonado"],
        },
    },
    {
        "name": "save_angles",
        "description": "Guarda los ángulos de venta, hooks y mensajes ganadores.",
        "input_schema": {
            "type": "object",
            "properties": {
                "angulos": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "nombre":           {"type": "string"},
                            "dolor_que_activa": {"type": "string"},
                            "mensaje_central":  {"type": "string"},
                            "hipotesis":        {"type": "string"},
                            "hooks":            {"type": "array", "items": {"type": "string"}},
                        },
                    },
                },
                "mensajes_ganadores":     {"type": "array", "items": {"type": "string"}},
                "palabras_clave_del_icp": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["angulos", "mensajes_ganadores"],
        },
    },
    {
        "name": "save_strategy",
        "description": "Guarda la estrategia completa de Meta Ads.",
        "input_schema": {
            "type": "object",
            "properties": {
                "objetivo_campana":        {"type": "string"},
                "presupuesto_mensual":     {"type": "string"},
                "presupuesto_diario_total":{"type": "string"},
                "conjuntos": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "nombre":            {"type": "string"},
                            "hipotesis":         {"type": "string"},
                            "angulo":            {"type": "string"},
                            "audiencia":         {"type": "string"},
                            "presupuesto_diario":{"type": "string"},
                            "copy": {
                                "type": "object",
                                "properties": {
                                    "hook":       {"type": "string"},
                                    "desarrollo": {"type": "string"},
                                    "cta":        {"type": "string"},
                                },
                            },
                            "brief_creativo": {
                                "type": "object",
                                "properties": {
                                    "formato":            {"type": "string"},
                                    "descripcion_video":  {"type": "string"},
                                    "descripcion_imagen": {"type": "string"},
                                },
                            },
                        },
                    },
                },
                "kpis":              {"type": "array", "items": {"type": "string"}},
                "criterios_escalar": {"type": "string"},
                "criterios_matar":   {"type": "string"},
                "proximos_pasos":    {"type": "array", "items": {"type": "string"}},
            },
            "required": ["objetivo_campana", "presupuesto_mensual", "conjuntos", "kpis"],
        },
    },
    {
        "name": "compile_doc",
        "description": "Compila todo en el documento final de estrategia.",
        "input_schema": {
            "type": "object",
            "properties": {
                "titulo":            {"type": "string"},
                "resumen_ejecutivo": {"type": "string"},
            },
            "required": ["titulo", "resumen_ejecutivo"],
        },
    },
]

# ─────────────────────────────────────────────────────────
# TOOL EXECUTION
# ─────────────────────────────────────────────────────────

def execute_tool(name: str, inputs: dict, state: dict) -> str:
    if name == "save_offer":
        state["oferta"] = inputs
        state["cliente"] = inputs.get("nombre_cliente", "cliente")

    elif name == "save_icp":
        state["icp"] = inputs

    elif name == "save_angles":
        state["investigacion"] = inputs

    elif name == "save_strategy":
        state["estrategia"] = inputs

    elif name == "compile_doc":
        md = build_markdown(inputs, state)
        slug = state.get("cliente", "cliente").lower().replace(" ", "_")[:20]
        filename = f"estrategia_{slug}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        state["doc"] = {"content": md, "filename": filename}

    return json.dumps({"ok": True}, ensure_ascii=False)


# ─────────────────────────────────────────────────────────
# MARKDOWN BUILDER
# ─────────────────────────────────────────────────────────

def build_markdown(meta: dict, state: dict) -> str:
    fecha = datetime.now().strftime("%d/%m/%Y")
    md = f"# {meta['titulo']}\n*{fecha} — Ruben's Agency*\n\n---\n\n"
    md += f"## RESUMEN EJECUTIVO\n\n{meta['resumen_ejecutivo']}\n\n---\n\n"

    if state.get("oferta"):
        o = state["oferta"]
        md += "## 1. OFERTA\n\n"
        for key, label in [("nombre_cliente","Cliente"),("que_vende","Qué vende"),("precio","Precio"),("formato_o_duracion","Formato")]:
            if o.get(key): md += f"**{label}:** {o[key]}\n"
        md += "\n"
        for key, label in [("propuesta_de_valor","Propuesta de valor"),("promesa_principal","Promesa principal"),("mecanismo_unico","Mecanismo único")]:
            if o.get(key): md += f"**{label}:**\n{o[key]}\n\n"
        for key, label in [("resultados_comprobables","Resultados comprobables"),("testimonios_clave","Testimonios clave")]:
            if o.get(key):
                md += f"**{label}:**\n" + "".join(f"- {r}\n" for r in o[key]) + "\n"
        md += "---\n\n"

    if state.get("icp"):
        i = state["icp"]
        md += "## 2. CLIENTE IDEAL (ICP)\n\n"
        if i.get("descripcion_demografica"): md += f"**Perfil:** {i['descripcion_demografica']}\n\n"
        if i.get("situacion_actual"): md += f"**Situación actual:**\n{i['situacion_actual']}\n\n"
        if i.get("dolores_principales"):
            md += "**Dolores principales:**\n" + "".join(f"- {d}\n" for d in i["dolores_principales"]) + "\n"
        if i.get("dolor_mas_profundo"): md += f"**Dolor más profundo:**\n{i['dolor_mas_profundo']}\n\n"
        if i.get("deseo_principal"): md += f"**Deseo principal:** {i['deseo_principal']}\n"
        if i.get("resultado_sonado"): md += f"**Resultado soñado:** {i['resultado_sonado']}\n\n"
        if i.get("lo_que_ha_intentado"):
            md += "**Lo que ha intentado:**\n" + "".join(f"- {t}\n" for t in i["lo_que_ha_intentado"]) + "\n"
        if i.get("por_que_no_funciono"): md += f"**Por qué no funcionó:**\n{i['por_que_no_funciono']}\n\n"
        if i.get("objeciones_principales"):
            md += "**Objeciones principales:**\n" + "".join(f"- {ob}\n" for ob in i["objeciones_principales"]) + "\n"
        md += "---\n\n"

    if state.get("investigacion"):
        inv = state["investigacion"]
        md += "## 3. ÁNGULOS DE VENTA Y MENSAJES\n\n"
        for idx, a in enumerate(inv.get("angulos", []), 1):
            md += f"### Ángulo {idx}: {a.get('nombre','')}\n\n"
            md += f"**Dolor que activa:** {a.get('dolor_que_activa','')}\n"
            md += f"**Mensaje central:** {a.get('mensaje_central','')}\n"
            md += f"**Hipótesis:** {a.get('hipotesis','')}\n\n"
            if a.get("hooks"):
                md += "**Hooks:**\n" + "".join(f"- {h}\n" for h in a["hooks"]) + "\n"
        if inv.get("mensajes_ganadores"):
            md += "**Mensajes ganadores:**\n" + "".join(f"- {m}\n" for m in inv["mensajes_ganadores"]) + "\n"
        md += "---\n\n"

    if state.get("estrategia"):
        est = state["estrategia"]
        md += "## 4. ESTRATEGIA META ADS\n\n"
        md += f"**Objetivo:** {est.get('objetivo_campana','')}\n"
        md += f"**Presupuesto mensual:** {est.get('presupuesto_mensual','')}\n"
        md += f"**Presupuesto diario total:** {est.get('presupuesto_diario_total','')}\n\n"
        for idx, c in enumerate(est.get("conjuntos", []), 1):
            copy = c.get("copy", {})
            brief = c.get("brief_creativo", {})
            md += f"### Conjunto {idx}: {c.get('nombre','')}\n\n"
            md += f"**Hipótesis:** {c.get('hipotesis','')}\n"
            md += f"**Ángulo:** {c.get('angulo','')}\n"
            md += f"**Audiencia:** {c.get('audiencia','')}\n"
            md += f"**Presupuesto diario:** {c.get('presupuesto_diario','')}\n\n"
            md += "**COPY:**\n"
            md += f"- **Hook:** {copy.get('hook','')}\n"
            md += f"- **Desarrollo:** {copy.get('desarrollo','')}\n"
            md += f"- **CTA:** {copy.get('cta','')}\n\n"
            md += "**BRIEF CREATIVO:**\n"
            md += f"- **Formato:** {brief.get('formato','')}\n"
            md += f"- **Video:** {brief.get('descripcion_video','')}\n"
            md += f"- **Imagen:** {brief.get('descripcion_imagen','')}\n\n"
        if est.get("kpis"):
            md += "**KPIs:**\n" + "".join(f"- {k}\n" for k in est["kpis"]) + "\n"
        md += f"**Escalar cuando:** {est.get('criterios_escalar','')}\n"
        md += f"**Matar cuando:** {est.get('criterios_matar','')}\n\n"
        if est.get("proximos_pasos"):
            md += "**Próximos pasos:**\n" + "".join(f"- {p}\n" for p in est["proximos_pasos"]) + "\n"

    return md


# ─────────────────────────────────────────────────────────
# AGENT LOOP
# ─────────────────────────────────────────────────────────

def run_agent_turn(sid: str, api_key: str) -> dict:
    sess = sessions[sid]
    client = anthropic.Anthropic(api_key=api_key)
    agent_text = ""
    phases_completed = []

    while True:
        response = client.messages.create(
            model="claude-opus-4-7",
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=sess["messages"],
        )

        # Serialize content blocks to plain dicts
        content_list = []
        for block in response.content:
            if block.type == "text":
                content_list.append({"type": "text", "text": block.text})
                agent_text += block.text
            elif block.type == "tool_use":
                content_list.append({
                    "type": "tool_use",
                    "id": block.id,
                    "name": block.name,
                    "input": block.input,
                })
        sess["messages"].append({"role": "assistant", "content": content_list})

        if response.stop_reason == "end_turn":
            break

        if response.stop_reason == "tool_use":
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    result_str = execute_tool(block.name, block.input, sess["state"])
                    phases_completed.append(block.name)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result_str,
                    })
            sess["messages"].append({"role": "user", "content": tool_results})
            continue

        break

    return {
        "text": agent_text,
        "phases_completed": phases_completed,
        "doc_ready": bool(sess["state"].get("doc")),
    }


# ─────────────────────────────────────────────────────────
# FLASK ROUTES
# ─────────────────────────────────────────────────────────

@app.route("/")
def index():
    return HTML

@app.route("/start", methods=["POST"])
def start():
    data = request.json or {}
    api_key = data.get("api_key", "")
    sid = str(uuid.uuid4())
    sessions[sid] = {
        "messages": [{"role": "user", "content": "Hola, listo para trabajar."}],
        "state": {"oferta": None, "icp": None, "investigacion": None, "estrategia": None, "doc": None, "cliente": ""},
    }
    try:
        result = run_agent_turn(sid, api_key)
        return jsonify({"session_id": sid, **result})
    except anthropic.AuthenticationError:
        del sessions[sid]
        return jsonify({"error": "API Key inválida. Verifica que sea correcta."}), 401
    except Exception as e:
        del sessions[sid]
        return jsonify({"error": str(e)}), 500

@app.route("/chat", methods=["POST"])
def chat():
    data = request.json or {}
    sid = data.get("session_id")
    msg = data.get("message", "")
    api_key = data.get("api_key", "")

    if sid not in sessions:
        return jsonify({"error": "Sesión no encontrada. Recarga la página."}), 404

    sessions[sid]["messages"].append({"role": "user", "content": msg})
    try:
        result = run_agent_turn(sid, api_key)
        return jsonify(result)
    except anthropic.AuthenticationError:
        return jsonify({"error": "API Key inválida."}), 401
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/download/<sid>")
def download(sid):
    if sid not in sessions or not sessions[sid]["state"].get("doc"):
        return "Not found", 404
    doc = sessions[sid]["state"]["doc"]
    return Response(
        doc["content"],
        mimetype="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="{doc["filename"]}"'},
    )


# ─────────────────────────────────────────────────────────
# HTML — APPLE DESIGN
# ─────────────────────────────────────────────────────────

HTML = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Meta Ads Agent</title>
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
html,body{height:100%;overflow:hidden}

:root{
  --bg:#f5f5f7;
  --surface:#ffffff;
  --t1:#1d1d1f;
  --t2:#6e6e73;
  --t3:#aeaeb2;
  --accent:#0071e3;
  --accent-h:#0077ed;
  --accent-a:#006edb;
  --red:#ff3b30;
  --border:rgba(0,0,0,0.08);
  --sh:0 2px 12px rgba(0,0,0,0.07),0 1px 3px rgba(0,0,0,0.05);
  --sh-md:0 8px 30px rgba(0,0,0,0.1),0 2px 6px rgba(0,0,0,0.06);
  --r:18px;--r-sm:12px;
  --font:system-ui,-apple-system,BlinkMacSystemFont,'Helvetica Neue',Arial,sans-serif;
}

body{
  font-family:var(--font);
  background:var(--bg);
  color:var(--t1);
  display:flex;flex-direction:column;
  height:100vh;
  -webkit-font-smoothing:antialiased;
  -moz-osx-font-smoothing:grayscale;
}

/* ── Header ── */
.hdr{
  flex-shrink:0;height:60px;
  background:rgba(255,255,255,0.82);
  backdrop-filter:blur(24px) saturate(180%);
  -webkit-backdrop-filter:blur(24px) saturate(180%);
  border-bottom:1px solid var(--border);
  display:flex;align-items:center;padding:0 24px;gap:12px;z-index:100;
}
.brand{display:flex;align-items:center;gap:10px;flex:1;cursor:default}
.brand-icon{
  width:32px;height:32px;border-radius:9px;
  background:var(--accent);display:flex;align-items:center;justify-content:center;
  box-shadow:0 2px 8px rgba(0,113,227,0.35);
}
.brand-name{font-size:15px;font-weight:600;letter-spacing:-.3px;color:var(--t1)}
.brand-badge{
  font-size:10px;font-weight:600;letter-spacing:.4px;text-transform:uppercase;
  background:rgba(0,113,227,0.1);color:var(--accent);
  padding:3px 8px;border-radius:980px;
}
.hdr-actions{display:flex;align-items:center;gap:8px}
.btn{
  display:inline-flex;align-items:center;gap:6px;
  padding:7px 16px;border-radius:980px;border:none;cursor:pointer;
  font-family:var(--font);font-size:13px;font-weight:500;
  transition:all .15s ease;letter-spacing:-.1px;
  -webkit-user-select:none;user-select:none;
}
.btn-primary{background:var(--accent);color:#fff}
.btn-primary:hover{background:var(--accent-h)}
.btn-primary:active{background:var(--accent-a);transform:scale(.98)}
.btn-ghost{background:rgba(0,0,0,0.06);color:var(--t1)}
.btn-ghost:hover{background:rgba(0,0,0,0.09)}
.btn-icon{
  width:34px;height:34px;border-radius:50%;border:none;
  background:rgba(0,0,0,0.06);cursor:pointer;
  display:flex;align-items:center;justify-content:center;
  transition:background .15s;color:var(--t2);
}
.btn-icon:hover{background:rgba(0,0,0,0.1)}

/* ── Phase bar ── */
.phases{
  flex-shrink:0;
  display:flex;align-items:center;justify-content:center;
  gap:6px;padding:10px 24px 8px;
  background:var(--bg);
}
.ph{
  display:flex;align-items:center;gap:5px;
  padding:5px 13px;border-radius:980px;
  font-size:11.5px;font-weight:500;letter-spacing:-.1px;
  color:var(--t3);background:rgba(0,0,0,0.04);
  transition:all .35s ease;white-space:nowrap;
}
.ph.active{background:var(--accent);color:#fff;box-shadow:0 2px 10px rgba(0,113,227,.3)}
.ph.done{background:rgba(52,199,89,.12);color:#34c759}
.ph.done::before{content:'✓  '}
.ph-sep{color:var(--t3);font-size:10px;opacity:.5}

/* ── Chat ── */
.chat{flex:1;overflow-y:auto;padding:24px 0 8px;scroll-behavior:smooth}
.chat::-webkit-scrollbar{width:0}

.msgs{max-width:740px;margin:0 auto;padding:0 24px;display:flex;flex-direction:column;gap:14px}

.msg{display:flex;gap:10px;animation:fadeUp .28s ease}
.msg.user{flex-direction:row-reverse}
@keyframes fadeUp{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:translateY(0)}}

.av{
  width:28px;height:28px;border-radius:50%;
  flex-shrink:0;margin-top:4px;
  display:flex;align-items:center;justify-content:center;
  font-size:12px;font-weight:700;letter-spacing:-.3px;
}
.av.agent{background:var(--accent);color:#fff;box-shadow:0 2px 6px rgba(0,113,227,.3)}
.av.user{background:var(--t1);color:#fff;font-size:11px}

.bbl{
  max-width:78%;padding:11px 15px;
  font-size:14.5px;line-height:1.6;
  box-shadow:var(--sh);
}
.msg.agent .bbl{
  background:var(--surface);color:var(--t1);
  border-radius:var(--r) var(--r) var(--r) 5px;
}
.msg.user .bbl{
  background:var(--t1);color:#fff;
  border-radius:var(--r) var(--r) 5px var(--r);
}
.bbl p{margin-bottom:7px}.bbl p:last-child{margin-bottom:0}
.bbl strong{font-weight:600}
.bbl ul,.bbl ol{padding-left:18px;margin:5px 0}
.bbl li{margin-bottom:3px}
.bbl h3{font-size:13.5px;font-weight:600;margin:10px 0 5px;letter-spacing:-.2px}
.bbl h2{font-size:15px;font-weight:700;margin:12px 0 6px;letter-spacing:-.3px}
.bbl hr{border:none;border-top:1px solid rgba(0,0,0,.07);margin:10px 0}
.bbl code{background:rgba(0,0,0,.06);padding:2px 6px;border-radius:5px;font-size:13px}
.msg.user .bbl code{background:rgba(255,255,255,.15)}
.msg.user .bbl a{color:rgba(255,255,255,.8)}
.msg.agent .bbl a{color:var(--accent)}

/* ── Typing ── */
.typing-wrap{display:flex;align-items:center;gap:4px;padding:10px 2px}
.dot{width:6px;height:6px;background:var(--t3);border-radius:50%;animation:bounce 1.3s infinite}
.dot:nth-child(2){animation-delay:.18s}
.dot:nth-child(3){animation-delay:.36s}
@keyframes bounce{0%,80%,100%{transform:translateY(0);opacity:.4}40%{transform:translateY(-5px);opacity:1}}

/* ── Download card ── */
.dl-card{
  background:linear-gradient(135deg,#0071e3 0%,#007aff 100%);
  color:#fff;border-radius:var(--r);padding:22px 24px;
  margin:4px 0;
  box-shadow:0 8px 28px rgba(0,113,227,.3);
  animation:fadeUp .35s ease;
}
.dl-card h3{font-size:16px;font-weight:600;margin-bottom:5px;letter-spacing:-.2px}
.dl-card p{font-size:13px;opacity:.85;margin-bottom:18px;line-height:1.5}
.btn-dl{
  background:rgba(255,255,255,.18);color:#fff;
  border:1px solid rgba(255,255,255,.28);
  padding:9px 20px;border-radius:980px;
  font-size:13.5px;font-weight:500;cursor:pointer;
  transition:background .15s;font-family:var(--font);
}
.btn-dl:hover{background:rgba(255,255,255,.28)}

/* ── Empty state ── */
.empty{
  display:flex;flex-direction:column;align-items:center;
  justify-content:center;height:100%;gap:12px;
}
.empty-icon{
  width:64px;height:64px;border-radius:18px;
  background:var(--accent);display:flex;align-items:center;justify-content:center;
  opacity:.15;
}
.empty p{font-size:14px;color:var(--t3);letter-spacing:-.1px}

/* ── Input bar ── */
.ibar{
  flex-shrink:0;padding:14px 24px 20px;
  background:rgba(255,255,255,.85);
  backdrop-filter:blur(24px) saturate(180%);
  -webkit-backdrop-filter:blur(24px) saturate(180%);
  border-top:1px solid var(--border);
}
.ibar-inner{
  max-width:740px;margin:0 auto;
  display:flex;gap:10px;align-items:flex-end;
  background:var(--surface);
  border:1px solid var(--border);border-radius:16px;
  padding:10px 10px 10px 16px;
  box-shadow:var(--sh);
  transition:border-color .15s,box-shadow .15s;
}
.ibar-inner:focus-within{
  border-color:var(--accent);
  box-shadow:0 0 0 3.5px rgba(0,113,227,.12),var(--sh);
}
textarea{
  flex:1;border:none;outline:none;resize:none;
  font-family:var(--font);font-size:15px;line-height:1.5;
  color:var(--t1);background:transparent;max-height:130px;
  scrollbar-width:none;
}
textarea::placeholder{color:var(--t3)}
textarea::-webkit-scrollbar{display:none}
textarea:disabled{opacity:.45;cursor:not-allowed}
.send{
  width:36px;height:36px;flex-shrink:0;
  background:var(--accent);border:none;border-radius:50%;
  cursor:pointer;display:flex;align-items:center;justify-content:center;
  transition:all .15s;color:#fff;
  box-shadow:0 2px 8px rgba(0,113,227,.3);
}
.send:hover:not(:disabled){background:var(--accent-h);transform:scale(1.05)}
.send:active:not(:disabled){transform:scale(.96)}
.send:disabled{background:var(--t3);box-shadow:none;cursor:not-allowed}

/* ── Modal ── */
.overlay{
  position:fixed;inset:0;
  background:rgba(0,0,0,.35);
  backdrop-filter:blur(6px);
  -webkit-backdrop-filter:blur(6px);
  display:flex;align-items:center;justify-content:center;
  z-index:200;animation:fadeIn .2s ease;
}
.overlay.hidden{display:none}
@keyframes fadeIn{from{opacity:0}to{opacity:1}}
.modal{
  background:var(--surface);border-radius:22px;
  padding:30px;width:420px;
  box-shadow:0 24px 60px rgba(0,0,0,.15),0 4px 12px rgba(0,0,0,.08);
  animation:scaleIn .25s cubic-bezier(.34,1.2,.64,1);
}
@keyframes scaleIn{from{opacity:0;transform:scale(.94)}to{opacity:1;transform:scale(1)}}
.modal h2{font-size:21px;font-weight:700;letter-spacing:-.4px;margin-bottom:6px}
.modal-sub{font-size:14px;color:var(--t2);line-height:1.55;margin-bottom:24px}
.field label{display:block;font-size:12.5px;font-weight:500;color:var(--t2);margin-bottom:7px;letter-spacing:-.1px}
.field input{
  width:100%;padding:12px 14px;
  border:1px solid var(--border);border-radius:var(--r-sm);
  font-family:var(--font);font-size:14.5px;outline:none;
  color:var(--t1);background:#fff;
  transition:border-color .15s,box-shadow .15s;
}
.field input:focus{border-color:var(--accent);box-shadow:0 0 0 3.5px rgba(0,113,227,.12)}
.field-hint{font-size:12px;color:var(--t3);margin-top:7px}
.field-hint a{color:var(--accent);text-decoration:none}
.field-hint a:hover{text-decoration:underline}
.modal-acts{display:flex;gap:10px;margin-top:26px;justify-content:flex-end}

/* ── Toast ── */
.toast{
  position:fixed;bottom:90px;left:50%;transform:translateX(-50%);
  background:var(--t1);color:#fff;
  padding:10px 20px;border-radius:980px;
  font-size:13.5px;font-weight:500;letter-spacing:-.1px;
  box-shadow:var(--sh-md);z-index:300;
  animation:fadeUp .25s ease;white-space:nowrap;
}
.toast.hidden{display:none}
</style>
</head>
<body>

<!-- Header -->
<header class="hdr">
  <div class="brand">
    <div class="brand-icon">
      <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
        <path d="M3 13.5L6.5 6l4 7 2.5-4.5L16 13.5" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
      </svg>
    </div>
    <span class="brand-name">Meta Ads Agent</span>
    <span class="brand-badge">Beta</span>
  </div>
  <div class="hdr-actions">
    <button class="btn btn-ghost" onclick="newSession()">
      <svg width="13" height="13" viewBox="0 0 13 13" fill="none">
        <path d="M11 6.5A4.5 4.5 0 1 1 6.5 2M11 2v4H7" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>
      </svg>
      Nueva sesión
    </button>
    <button class="btn-icon" onclick="openSettings()" title="Configuración">
      <svg width="15" height="15" viewBox="0 0 15 15" fill="none">
        <circle cx="7.5" cy="7.5" r="2.5" stroke="currentColor" stroke-width="1.4"/>
        <path d="M7.5 1v1.5M7.5 12.5V14M14 7.5h-1.5M2.5 7.5H1M12.07 2.93l-1.06 1.06M4 11l-1.06 1.07M12.07 12.07l-1.06-1.06M4 4 2.94 2.93" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/>
      </svg>
    </button>
  </div>
</header>

<!-- Phase bar -->
<div class="phases">
  <div class="ph active" id="ph-oferta">Oferta</div>
  <span class="ph-sep">›</span>
  <div class="ph" id="ph-icp">ICP</div>
  <span class="ph-sep">›</span>
  <div class="ph" id="ph-angulos">Ángulos</div>
  <span class="ph-sep">›</span>
  <div class="ph" id="ph-estrategia">Estrategia</div>
  <span class="ph-sep">›</span>
  <div class="ph" id="ph-doc">Documento</div>
</div>

<!-- Chat -->
<main class="chat" id="chat">
  <div class="msgs" id="msgs">
    <div class="empty" id="empty">
      <div class="empty-icon">
        <svg width="32" height="32" viewBox="0 0 32 32" fill="none">
          <path d="M4 24l6-14 7 11 4-6 7 9" stroke="#fff" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
      </div>
      <p>Ingresa tu API Key para comenzar</p>
    </div>
  </div>
</main>

<!-- Input bar -->
<footer class="ibar">
  <div class="ibar-inner">
    <textarea id="inp" placeholder="Escribe tu respuesta..." rows="1"
      onkeydown="onKey(event)" oninput="resize(this)" disabled></textarea>
    <button class="send" id="sbtn" onclick="send()" disabled>
      <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
        <path d="M7 12V2M2 7l5-5 5 5" stroke="#fff" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"/>
      </svg>
    </button>
  </div>
</footer>

<!-- Settings modal -->
<div class="overlay hidden" id="ov">
  <div class="modal">
    <h2>Configuración</h2>
    <p class="modal-sub">Ingresa tu Anthropic API Key para activar el agente. Tu key se guarda solo en este navegador.</p>
    <div class="field">
      <label>Anthropic API Key</label>
      <input type="password" id="key-inp" placeholder="sk-ant-..." autocomplete="off" onkeydown="if(event.key==='Enter')saveKey()"/>
      <div class="field-hint">Obtén tu key en <a href="https://console.anthropic.com" target="_blank">console.anthropic.com</a> — cuesta ~$0.01 por sesión.</div>
    </div>
    <div class="modal-acts">
      <button class="btn btn-ghost" onclick="closeSettings()">Cancelar</button>
      <button class="btn btn-primary" onclick="saveKey()">Guardar y comenzar</button>
    </div>
  </div>
</div>

<div class="toast hidden" id="toast"></div>

<script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
<script>
marked.setOptions({breaks:true,gfm:true});

let sid=null, apiKey=localStorage.getItem('ma_key')||'', busy=false;

const PHASE_ORDER=['ph-oferta','ph-icp','ph-angulos','ph-estrategia','ph-doc'];
const PHASE_MAP={save_offer:'ph-oferta',save_icp:'ph-icp',save_angles:'ph-angulos',save_strategy:'ph-estrategia',compile_doc:'ph-doc'};

// ── Boot ──────────────────────────────────────────────
window.onload=()=>{ apiKey ? startSession() : openSettings(); };

// ── Session ───────────────────────────────────────────
async function startSession(){
  clearChat();setInputEnabled(false);showTyping();
  try{
    const r=await post('/start',{api_key:apiKey});
    hideTyping();
    if(r.error){toast(r.error);showEmpty();return;}
    sid=r.session_id;
    addMsg('agent',r.text);
    markPhases(r.phases_completed||[]);
    if(r.doc_ready)showDl();
    setInputEnabled(true);
    document.getElementById('inp').focus();
  }catch(e){hideTyping();toast('Error de conexión');showEmpty();}
}

async function send(){
  if(busy||!sid)return;
  const el=document.getElementById('inp');
  const txt=el.value.trim();if(!txt)return;
  el.value='';resize(el);
  addMsg('user',txt);setBusy(true);showTyping();
  try{
    const r=await post('/chat',{session_id:sid,message:txt,api_key:apiKey});
    hideTyping();
    if(r.error){toast(r.error);setBusy(false);return;}
    addMsg('agent',r.text);
    markPhases(r.phases_completed||[]);
    if(r.doc_ready)showDl();
  }catch(e){hideTyping();toast('Error de conexión');}
  setBusy(false);
}

function newSession(){
  sid=null;busy=false;
  document.querySelectorAll('.ph').forEach((el,i)=>{
    el.className='ph'+(i===0?' active':'');
  });
  startSession();
}

// ── Rendering ─────────────────────────────────────────
function addMsg(role,text){
  const el=document.getElementById('empty');if(el)el.remove();
  const c=document.getElementById('msgs');
  const d=document.createElement('div');d.className=`msg ${role}`;
  const initials=role==='agent'?'MA':'Tú';
  d.innerHTML=`<div class="av ${role}">${initials}</div><div class="bbl">${marked.parse(text||'')}</div>`;
  c.appendChild(d);scrollBot();
}

function showTyping(){
  const c=document.getElementById('msgs');
  const d=document.createElement('div');d.className='msg agent';d.id='typing';
  d.innerHTML=`<div class="av agent">MA</div><div class="bbl"><div class="typing-wrap"><div class="dot"></div><div class="dot"></div><div class="dot"></div></div></div>`;
  c.appendChild(d);scrollBot();
}
function hideTyping(){const t=document.getElementById('typing');if(t)t.remove();}

function showDl(){
  const c=document.getElementById('msgs');
  const w=document.createElement('div');
  w.innerHTML=`<div class="dl-card"><h3>📄 Estrategia completa lista</h3><p>Tu documento fue generado con la investigación, ángulos, copies y estructura de campaña completa.</p><button class="btn-dl" onclick="dlDoc()">⬇&nbsp; Descargar documento .md</button></div>`;
  c.appendChild(w);scrollBot();
}

function dlDoc(){if(sid)window.location.href=`/download/${sid}`;}

function markPhases(completed){
  completed.forEach(name=>{
    const id=PHASE_MAP[name];if(!id)return;
    const el=document.getElementById(id);if(!el)return;
    el.className='ph done';
    const idx=PHASE_ORDER.indexOf(id);
    if(idx>=0&&idx+1<PHASE_ORDER.length){
      const next=document.getElementById(PHASE_ORDER[idx+1]);
      if(next&&!next.classList.contains('done'))next.className='ph active';
    }
  });
}

function clearChat(){
  document.getElementById('msgs').innerHTML=`<div class="empty" id="empty"><div class="empty-icon"><svg width="32" height="32" viewBox="0 0 32 32" fill="none"><path d="M4 24l6-14 7 11 4-6 7 9" stroke="#fff" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/></svg></div><p>Iniciando sesión...</p></div>`;
}
function showEmpty(){
  document.getElementById('msgs').innerHTML=`<div class="empty" id="empty"><div class="empty-icon"><svg width="32" height="32" viewBox="0 0 32 32" fill="none"><path d="M4 24l6-14 7 11 4-6 7 9" stroke="#fff" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/></svg></div><p>Ingresa tu API Key para comenzar</p></div>`;
}
function scrollBot(){const c=document.getElementById('chat');c.scrollTop=c.scrollHeight;}

// ── UI helpers ────────────────────────────────────────
function setBusy(b){busy=b;setInputEnabled(!b);}
function setInputEnabled(on){
  document.getElementById('inp').disabled=!on;
  document.getElementById('sbtn').disabled=!on;
}
function resize(el){el.style.height='auto';el.style.height=Math.min(el.scrollHeight,130)+'px';}
function onKey(e){if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();send();}}
function toast(msg,ms=3500){
  const t=document.getElementById('toast');
  t.textContent=msg;t.classList.remove('hidden');
  clearTimeout(t._t);t._t=setTimeout(()=>t.classList.add('hidden'),ms);
}
async function post(url,body){
  const r=await fetch(url,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
  return r.json();
}

// ── Settings ──────────────────────────────────────────
function openSettings(){
  document.getElementById('key-inp').value=apiKey;
  document.getElementById('ov').classList.remove('hidden');
  setTimeout(()=>document.getElementById('key-inp').focus(),120);
}
function closeSettings(){document.getElementById('ov').classList.add('hidden');}
function saveKey(){
  const v=document.getElementById('key-inp').value.trim();
  if(!v){toast('Ingresa tu API Key');return;}
  apiKey=v;localStorage.setItem('ma_key',v);
  closeSettings();
  if(!sid)startSession();
}
document.getElementById('ov').addEventListener('click',e=>{if(e.target===document.getElementById('ov'))closeSettings();});
</script>
</body>
</html>"""


# ─────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    port = 5001
    print(f"\n{'─'*46}")
    print(f"  🎯  Meta Ads Agent — Ruben's Agency")
    print(f"{'─'*46}")
    print(f"  Abriendo en → http://localhost:{port}")
    print(f"  Ctrl+C para detener")
    print(f"{'─'*46}\n")
    threading.Timer(1.2, lambda: webbrowser.open(f"http://localhost:{port}")).start()
    app.run(port=port, debug=False, use_reloader=False)
