#!/usr/bin/env python3
"""
Agente de Estrategia Meta Ads
Ruben's Agency — Uso interno
"""

import anthropic
import json
import os
import sys
from datetime import datetime

CYAN  = "\033[96m"
GREEN = "\033[92m"
RESET = "\033[0m"
BOLD  = "\033[1m"
DIM   = "\033[2m"

client = anthropic.Anthropic()

# Acumula la info durante la sesión
session = {
    "cliente":        "",
    "oferta":         None,
    "icp":            None,
    "investigacion":  None,
    "estrategia":     None,
    "doc_path":       "",
}

# ─────────────────────────────────────────────────────────
# SYSTEM PROMPT
# ─────────────────────────────────────────────────────────

SYSTEM_PROMPT = """Eres el estratega senior de Meta Ads de la agencia de Ruben.
Tu trabajo es guiar a Ruben a través de su metodología para construir una estrategia completa de Meta Ads para un cliente.

## CLIENTES TÍPICOS DE RUBEN
- Coaches y consultores de negocios, ventas y liderazgo en México
  Facturan $5,000–$30,000 USD/mes, 80% de clientes llegan por referidos.
  Quieren un sistema predecible de adquisición. Ya intentaron contenido orgánico y agencias genéricas.
- Software a la medida (B2B)
- Campamento para niños

## TU METODOLOGÍA (síguela en este orden exacto):

### FASE 1 — OFERTA
Entiende completamente qué vende, a qué precio, qué resultados genera y si tiene testimonios.
Cuando tengas suficiente info llama a `save_offer`.

### FASE 2 — NICHO / ICP
Entiende quién es el cliente ideal: demografía, situación actual, dolores, deseos, qué ha intentado antes.
Cuando tengas suficiente info llama a `save_icp`.

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
Llama a `compile_doc`. Eso guarda el archivo y termina la sesión.

## REGLAS
- Máximo 2 preguntas a la vez, nunca un formulario largo
- Sé directo, habla como colega estratega, no como asistente genérico
- Usa los datos reales del cliente, jamás ejemplos genéricos
- Llama a los tools sin anunciarlo, continúa la conversación naturalmente
- Si el usuario da respuestas vagas, pide especificidad con ejemplos concretos
- Al terminar cada fase haz una síntesis de 2-3 líneas antes de pasar a la siguiente

Empieza preguntando con qué cliente van a trabajar hoy."""

# ─────────────────────────────────────────────────────────
# DEFINICIÓN DE TOOLS
# ─────────────────────────────────────────────────────────

tools = [
    {
        "name": "save_offer",
        "description": "Guarda la oferta estructurada cuando esté completa.",
        "input_schema": {
            "type": "object",
            "properties": {
                "nombre_cliente":         {"type": "string"},
                "que_vende":              {"type": "string"},
                "precio":                 {"type": "string"},
                "formato_o_duracion":     {"type": "string"},
                "propuesta_de_valor":     {"type": "string"},
                "promesa_principal":      {"type": "string"},
                "mecanismo_unico":        {"type": "string"},
                "resultados_comprobables":{"type": "array", "items": {"type": "string"}},
                "testimonios_clave":      {"type": "array", "items": {"type": "string"}}
            },
            "required": ["nombre_cliente", "que_vende", "precio", "propuesta_de_valor", "promesa_principal"]
        }
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
                "momento_de_compra":       {"type": "string"}
            },
            "required": ["descripcion_demografica", "dolores_principales", "deseo_principal", "resultado_sonado"]
        }
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
                            "hooks":            {"type": "array", "items": {"type": "string"}}
                        }
                    }
                },
                "mensajes_ganadores":    {"type": "array", "items": {"type": "string"}},
                "palabras_clave_del_icp":{"type": "array", "items": {"type": "string"}}
            },
            "required": ["angulos", "mensajes_ganadores"]
        }
    },
    {
        "name": "save_strategy",
        "description": "Guarda la estrategia completa de Meta Ads.",
        "input_schema": {
            "type": "object",
            "properties": {
                "objetivo_campana":      {"type": "string"},
                "presupuesto_mensual":   {"type": "string"},
                "presupuesto_diario_total":{"type": "string"},
                "conjuntos": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "nombre":           {"type": "string"},
                            "hipotesis":        {"type": "string"},
                            "angulo":           {"type": "string"},
                            "audiencia":        {"type": "string"},
                            "presupuesto_diario":{"type": "string"},
                            "copy": {
                                "type": "object",
                                "properties": {
                                    "hook":      {"type": "string"},
                                    "desarrollo":{"type": "string"},
                                    "cta":       {"type": "string"}
                                }
                            },
                            "brief_creativo": {
                                "type": "object",
                                "properties": {
                                    "formato":           {"type": "string"},
                                    "descripcion_video": {"type": "string"},
                                    "descripcion_imagen":{"type": "string"}
                                }
                            }
                        }
                    }
                },
                "kpis":              {"type": "array", "items": {"type": "string"}},
                "criterios_escalar": {"type": "string"},
                "criterios_matar":   {"type": "string"},
                "proximos_pasos":    {"type": "array", "items": {"type": "string"}}
            },
            "required": ["objetivo_campana", "presupuesto_mensual", "conjuntos", "kpis"]
        }
    },
    {
        "name": "compile_doc",
        "description": "Compila todo en el documento final y lo guarda en el escritorio.",
        "input_schema": {
            "type": "object",
            "properties": {
                "titulo":            {"type": "string"},
                "resumen_ejecutivo": {"type": "string"}
            },
            "required": ["titulo", "resumen_ejecutivo"]
        }
    }
]

# ─────────────────────────────────────────────────────────
# EJECUCIÓN DE TOOLS
# ─────────────────────────────────────────────────────────

def execute_tool(name: str, inputs: dict) -> str:
    if name == "save_offer":
        session["oferta"] = inputs
        session["cliente"] = inputs.get("nombre_cliente", "cliente")
        return json.dumps({"ok": True})

    elif name == "save_icp":
        session["icp"] = inputs
        return json.dumps({"ok": True})

    elif name == "save_angles":
        session["investigacion"] = inputs
        return json.dumps({"ok": True, "angulos": len(inputs.get("angulos", []))})

    elif name == "save_strategy":
        session["estrategia"] = inputs
        return json.dumps({"ok": True})

    elif name == "compile_doc":
        doc = build_markdown(inputs)
        timestamp  = datetime.now().strftime("%Y%m%d_%H%M%S")
        slug       = session["cliente"].lower().replace(" ", "_")[:20]
        filename   = f"estrategia_{slug}_{timestamp}.md"
        filepath   = os.path.join(os.path.expanduser("~/Desktop"), filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(doc)
        session["doc_path"] = filepath
        return json.dumps({"ok": True, "archivo": filepath})

    return json.dumps({"error": "tool desconocido"})


# ─────────────────────────────────────────────────────────
# CONSTRUCCIÓN DEL DOCUMENTO MARKDOWN
# ─────────────────────────────────────────────────────────

def build_markdown(meta: dict) -> str:
    fecha = datetime.now().strftime("%d/%m/%Y")
    md = f"# {meta['titulo']}\n*{fecha} — Ruben's Agency*\n\n---\n\n"
    md += f"## RESUMEN EJECUTIVO\n\n{meta['resumen_ejecutivo']}\n\n---\n\n"

    # 1. OFERTA
    if session["oferta"]:
        o = session["oferta"]
        md += "## 1. OFERTA\n\n"
        md += f"**Cliente:** {o.get('nombre_cliente','')}\n"
        md += f"**Qué vende:** {o.get('que_vende','')}\n"
        md += f"**Precio:** {o.get('precio','')}\n"
        md += f"**Formato:** {o.get('formato_o_duracion','')}\n\n"
        md += f"**Propuesta de valor:**\n{o.get('propuesta_de_valor','')}\n\n"
        md += f"**Promesa principal:**\n{o.get('promesa_principal','')}\n\n"
        md += f"**Mecanismo único:**\n{o.get('mecanismo_unico','')}\n\n"
        if o.get("resultados_comprobables"):
            md += "**Resultados comprobables:**\n"
            for r in o["resultados_comprobables"]:
                md += f"- {r}\n"
            md += "\n"
        if o.get("testimonios_clave"):
            md += "**Testimonios clave:**\n"
            for t in o["testimonios_clave"]:
                md += f"- {t}\n"
            md += "\n"
        md += "---\n\n"

    # 2. ICP
    if session["icp"]:
        i = session["icp"]
        md += "## 2. CLIENTE IDEAL (ICP)\n\n"
        md += f"**Perfil:** {i.get('descripcion_demografica','')}\n\n"
        md += f"**Situación actual:**\n{i.get('situacion_actual','')}\n\n"
        if i.get("dolores_principales"):
            md += "**Dolores principales:**\n"
            for d in i["dolores_principales"]:
                md += f"- {d}\n"
            md += "\n"
        md += f"**Dolor más profundo:**\n{i.get('dolor_mas_profundo','')}\n\n"
        md += f"**Deseo principal:** {i.get('deseo_principal','')}\n"
        md += f"**Resultado soñado:** {i.get('resultado_sonado','')}\n\n"
        if i.get("lo_que_ha_intentado"):
            md += "**Lo que ha intentado:**\n"
            for t in i["lo_que_ha_intentado"]:
                md += f"- {t}\n"
            md += "\n"
        md += f"**Por qué no funcionó:**\n{i.get('por_que_no_funciono','')}\n\n"
        if i.get("objeciones_principales"):
            md += "**Objeciones principales:**\n"
            for ob in i["objeciones_principales"]:
                md += f"- {ob}\n"
            md += "\n"
        md += "---\n\n"

    # 3. ÁNGULOS
    if session["investigacion"]:
        inv = session["investigacion"]
        md += "## 3. ÁNGULOS DE VENTA Y MENSAJES\n\n"
        for idx, a in enumerate(inv.get("angulos", []), 1):
            md += f"### Ángulo {idx}: {a.get('nombre','')}\n\n"
            md += f"**Dolor que activa:** {a.get('dolor_que_activa','')}\n"
            md += f"**Mensaje central:** {a.get('mensaje_central','')}\n"
            md += f"**Hipótesis:** {a.get('hipotesis','')}\n\n"
            if a.get("hooks"):
                md += "**Hooks:**\n"
                for h in a["hooks"]:
                    md += f"- {h}\n"
                md += "\n"
        if inv.get("mensajes_ganadores"):
            md += "**Mensajes ganadores:**\n"
            for m in inv["mensajes_ganadores"]:
                md += f"- {m}\n"
            md += "\n"
        md += "---\n\n"

    # 4. ESTRATEGIA META ADS
    if session["estrategia"]:
        est = session["estrategia"]
        md += "## 4. ESTRATEGIA META ADS\n\n"
        md += f"**Objetivo:** {est.get('objetivo_campana','')}\n"
        md += f"**Presupuesto mensual:** {est.get('presupuesto_mensual','')}\n"
        md += f"**Presupuesto diario total:** {est.get('presupuesto_diario_total','')}\n\n"
        for idx, c in enumerate(est.get("conjuntos", []), 1):
            copy  = c.get("copy", {})
            brief = c.get("brief_creativo", {})
            md += f"### Conjunto {idx}: {c.get('nombre','')}\n\n"
            md += f"**Hipótesis:** {c.get('hipotesis','')}\n"
            md += f"**Ángulo:** {c.get('angulo','')}\n"
            md += f"**Audiencia:** {c.get('audiencia','')}\n"
            md += f"**Presupuesto diario:** {c.get('presupuesto_diario','')}\n\n"
            md += "**COPY:**\n"
            md += f"- Hook: {copy.get('hook','')}\n"
            md += f"- Desarrollo: {copy.get('desarrollo','')}\n"
            md += f"- CTA: {copy.get('cta','')}\n\n"
            md += "**BRIEF CREATIVO:**\n"
            md += f"- Formato: {brief.get('formato','')}\n"
            md += f"- Video: {brief.get('descripcion_video','')}\n"
            md += f"- Imagen: {brief.get('descripcion_imagen','')}\n\n"
        if est.get("kpis"):
            md += "**KPIs:**\n"
            for k in est["kpis"]:
                md += f"- {k}\n"
            md += "\n"
        md += f"**Escalar cuando:** {est.get('criterios_escalar','')}\n"
        md += f"**Matar cuando:** {est.get('criterios_matar','')}\n\n"
        if est.get("proximos_pasos"):
            md += "**Próximos pasos:**\n"
            for p in est["proximos_pasos"]:
                md += f"- {p}\n"

    return md


# ─────────────────────────────────────────────────────────
# CHAT EN TERMINAL
# ─────────────────────────────────────────────────────────

def print_agent(text: str):
    print(f"\n{CYAN}{BOLD}Agente:{RESET} {text}\n")

def get_input() -> str:
    try:
        return input(f"{GREEN}{BOLD}Tú:{RESET} ").strip()
    except (KeyboardInterrupt, EOFError):
        print(f"\n{DIM}Sesión terminada.{RESET}\n")
        sys.exit(0)

def run():
    print(f"\n{BOLD}{'═'*52}{RESET}")
    print(f"{BOLD}  🎯  AGENTE META ADS — RUBEN'S AGENCY{RESET}")
    print(f"{BOLD}{'═'*52}{RESET}")
    print(f"{DIM}  Escribe 'salir' para terminar en cualquier momento{RESET}")
    print(f"{BOLD}{'═'*52}{RESET}\n")

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("⚠️  Falta ANTHROPIC_API_KEY")
        print("   Corre: export ANTHROPIC_API_KEY='sk-ant-...'")
        sys.exit(1)

    messages = [{"role": "user", "content": "Hola, listo para trabajar."}]

    while True:
        print(f"{DIM}  ...{RESET}", end="\r", flush=True)

        response = client.messages.create(
            model="claude-opus-4-7",
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            tools=tools,
            messages=messages,
        )
        messages.append({"role": "assistant", "content": response.content})

        # Siempre imprimir texto primero
        text = "".join(b.text for b in response.content if hasattr(b, "text"))
        if text:
            print_agent(text)

        # Ejecutar tools silenciosamente
        if response.stop_reason == "tool_use":
            results = []
            for block in response.content:
                if block.type == "tool_use":
                    result = execute_tool(block.name, block.input)
                    results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    })
            messages.append({"role": "user", "content": results})

            # Si ya compiló el doc, terminamos
            if session["doc_path"]:
                print(f"{BOLD}{'═'*52}{RESET}")
                print(f"  ✅ Documento guardado en:")
                print(f"  {session['doc_path']}")
                print(f"{BOLD}{'═'*52}{RESET}\n")
                break
            continue

        # Pedir input al usuario
        user_input = get_input()
        if user_input.lower() in ("salir", "exit", "quit"):
            break
        if not user_input:
            continue
        messages.append({"role": "user", "content": user_input})


if __name__ == "__main__":
    run()
