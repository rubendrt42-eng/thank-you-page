"""
Agente de Investigación de Mercado
Usa Claude para investigar mercados, competidores y tendencias.
"""

import anthropic
import json
from datetime import datetime

client = anthropic.Anthropic()

# ─────────────────────────────────────────────
# DEFINICIÓN DE HERRAMIENTAS
# ─────────────────────────────────────────────

tools = [
    {
        "name": "search_web",
        "description": (
            "Busca información actualizada sobre un tema de mercado. "
            "Útil para encontrar noticias, datos de la industria y estadísticas."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Término de búsqueda, ej: 'mercado de IA en Latinoamérica 2024'"
                },
                "focus": {
                    "type": "string",
                    "enum": ["tamaño_mercado", "tendencias", "noticias", "estadísticas", "general"],
                    "description": "Tipo de información que se busca"
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "analyze_competitors",
        "description": (
            "Analiza los principales competidores de un sector o empresa. "
            "Devuelve información sobre sus fortalezas, debilidades y posicionamiento."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "industry": {
                    "type": "string",
                    "description": "Industria o sector a analizar, ej: 'e-commerce de moda en México'"
                },
                "company_name": {
                    "type": "string",
                    "description": "Nombre de la empresa (opcional) para análisis competitivo específico"
                }
            },
            "required": ["industry"]
        }
    },
    {
        "name": "get_market_trends",
        "description": (
            "Obtiene las tendencias actuales y proyecciones futuras de un mercado. "
            "Incluye CAGR, tamaño del mercado y drivers de crecimiento."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "market": {
                    "type": "string",
                    "description": "Mercado a analizar, ej: 'fintech', 'salud digital', 'SaaS B2B'"
                },
                "region": {
                    "type": "string",
                    "description": "Región geográfica, ej: 'Latinoamérica', 'global', 'México'",
                    "default": "global"
                },
                "horizon": {
                    "type": "string",
                    "enum": ["1_año", "3_años", "5_años", "10_años"],
                    "description": "Horizonte temporal de las proyecciones",
                    "default": "5_años"
                }
            },
            "required": ["market"]
        }
    },
    {
        "name": "generate_report",
        "description": (
            "Genera un reporte estructurado de investigación de mercado "
            "con todos los hallazgos recopilados durante la investigación."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Título del reporte"
                },
                "sections": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Lista de secciones a incluir: resumen_ejecutivo, tamaño_mercado, competidores, tendencias, oportunidades, riesgos, recomendaciones"
                },
                "findings": {
                    "type": "object",
                    "description": "Diccionario con los hallazgos por sección"
                }
            },
            "required": ["title", "sections", "findings"]
        }
    }
]

# ─────────────────────────────────────────────
# IMPLEMENTACIÓN DE HERRAMIENTAS
# (simuladas — en producción conectarías APIs reales)
# ─────────────────────────────────────────────

def search_web(query: str, focus: str = "general") -> dict:
    """Simula búsqueda web. En producción: conectar a Serper, Tavily, Brave Search API."""
    print(f"  🔍 Buscando: '{query}' [{focus}]")

    # Datos simulados realistas por tipo de búsqueda
    simulated_results = {
        "tamaño_mercado": {
            "result": f"Mercado global relacionado con '{query}': valuado en $2.4B en 2024, proyectado a $5.1B en 2029.",
            "sources": ["Statista 2024", "Grand View Research", "IBISWorld"],
            "key_data": {"market_size_2024": "$2.4B", "projected_2029": "$5.1B", "cagr": "16.2%"}
        },
        "tendencias": {
            "result": f"Principales tendencias en '{query}': automatización con IA, personalización masiva, sostenibilidad.",
            "sources": ["McKinsey Global Institute", "Gartner 2024", "Forrester"],
            "key_data": {"top_trends": ["IA generativa", "sostenibilidad", "experiencia omnicanal"]}
        },
        "general": {
            "result": f"Información general sobre '{query}': sector en crecimiento con alta adopción tecnológica.",
            "sources": ["Reuters", "Bloomberg", "TechCrunch"],
            "key_data": {"growth_rate": "12% anual", "investment_2024": "$890M"}
        }
    }

    return simulated_results.get(focus, simulated_results["general"])


def analyze_competitors(industry: str, company_name: str = None) -> dict:
    """Simula análisis competitivo. En producción: conectar a Crunchbase, SimilarWeb, SEMrush."""
    print(f"  🏢 Analizando competidores en: '{industry}'")

    competitors = [
        {
            "nombre": "Líder del Mercado A",
            "cuota_mercado": "28%",
            "fortalezas": ["marca reconocida", "red de distribución amplia", "tecnología propietaria"],
            "debilidades": ["precios altos", "poca personalización", "lento en innovación"],
            "modelo_negocio": "B2B SaaS",
            "financiamiento": "$45M Series C"
        },
        {
            "nombre": "Challenger B",
            "cuota_mercado": "18%",
            "fortalezas": ["precio competitivo", "UX superior", "crecimiento rápido"],
            "debilidades": ["equipo pequeño", "presencia regional limitada"],
            "modelo_negocio": "Freemium + Enterprise",
            "financiamiento": "$12M Series A"
        },
        {
            "nombre": "Nicho Player C",
            "cuota_mercado": "8%",
            "fortalezas": ["especialización vertical", "alta retención (94%)"],
            "debilidades": ["mercado objetivo muy estrecho"],
            "modelo_negocio": "B2B vertical",
            "financiamiento": "Bootstrapped"
        }
    ]

    return {
        "industria": industry,
        "total_competidores_identificados": 12,
        "principales_players": competitors,
        "concentración_mercado": "Moderada — top 3 controlan 54% del mercado",
        "barreras_entrada": ["alto costo de adquisición de clientes", "regulaciones del sector", "efectos de red"],
        "oportunidad_diferenciación": "Segmento SMB desatendido con soluciones asequibles"
    }


def get_market_trends(market: str, region: str = "global", horizon: str = "5_años") -> dict:
    """Simula análisis de tendencias. En producción: conectar a Bloomberg, PitchBook, CB Insights."""
    print(f"  📈 Obteniendo tendencias de '{market}' en {region} a {horizon}")

    return {
        "mercado": market,
        "región": region,
        "horizonte": horizon,
        "tamaño_actual": "$3.2B (2024)",
        "tamaño_proyectado": "$7.8B (2029)",
        "cagr": "19.5%",
        "drivers_crecimiento": [
            "Adopción acelerada post-pandemia",
            "Inversión récord en transformación digital ($2.3T global)",
            "Regulaciones favorables en LATAM",
            "Nueva generación de consumidores digitales nativos"
        ],
        "inhibidores": [
            "Incertidumbre macroeconómica",
            "Escasez de talento tecnológico",
            "Fragmentación regulatoria entre países"
        ],
        "segmentos_mayor_crecimiento": [
            {"segmento": "Pequeñas empresas (1-50 empleados)", "cagr": "24%"},
            {"segmento": "Sector salud", "cagr": "31%"},
            {"segmento": "Educación", "cagr": "22%"}
        ],
        "tecnologías_disruptivas": ["IA Generativa", "Edge Computing", "Web3 aplicado"],
        "m_and_a_activity": "Alta — 47 adquisiciones en los últimos 18 meses"
    }


def generate_report(title: str, sections: list, findings: dict) -> dict:
    """Genera y guarda el reporte en un archivo."""
    print(f"  📄 Generando reporte: '{title}'")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"reporte_mercado_{timestamp}.md"
    filepath = f"/home/user/thank-you-page/{filename}"

    report_content = f"""# {title}
*Generado el {datetime.now().strftime("%d/%m/%Y a las %H:%M")}*
*Agente de Investigación de Mercado — Powered by Claude*

---

"""
    section_titles = {
        "resumen_ejecutivo": "## 📋 Resumen Ejecutivo",
        "tamaño_mercado": "## 📊 Tamaño y Estructura del Mercado",
        "competidores": "## 🏢 Análisis Competitivo",
        "tendencias": "## 📈 Tendencias y Proyecciones",
        "oportunidades": "## 💡 Oportunidades Identificadas",
        "riesgos": "## ⚠️ Riesgos y Desafíos",
        "recomendaciones": "## 🎯 Recomendaciones Estratégicas"
    }

    for section in sections:
        header = section_titles.get(section, f"## {section.replace('_', ' ').title()}")
        report_content += f"{header}\n\n"
        if section in findings:
            content = findings[section]
            if isinstance(content, dict):
                for k, v in content.items():
                    if isinstance(v, list):
                        report_content += f"**{k.replace('_', ' ').title()}:**\n"
                        for item in v:
                            report_content += f"- {item}\n"
                        report_content += "\n"
                    else:
                        report_content += f"**{k.replace('_', ' ').title()}:** {v}\n\n"
            else:
                report_content += f"{content}\n\n"
        report_content += "---\n\n"

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(report_content)

    return {
        "status": "reporte_generado",
        "archivo": filename,
        "ruta": filepath,
        "secciones_incluidas": sections,
        "palabras_aprox": len(report_content.split())
    }


# ─────────────────────────────────────────────
# DISPATCHER DE HERRAMIENTAS
# ─────────────────────────────────────────────

def execute_tool(tool_name: str, tool_input: dict) -> str:
    """Ejecuta la herramienta correspondiente y devuelve el resultado como string."""
    try:
        if tool_name == "search_web":
            result = search_web(**tool_input)
        elif tool_name == "analyze_competitors":
            result = analyze_competitors(**tool_input)
        elif tool_name == "get_market_trends":
            result = get_market_trends(**tool_input)
        elif tool_name == "generate_report":
            result = generate_report(**tool_input)
        else:
            result = {"error": f"Herramienta desconocida: {tool_name}"}

        return json.dumps(result, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


# ─────────────────────────────────────────────
# BUCLE AGÉNTICO PRINCIPAL
# ─────────────────────────────────────────────

def run_market_research_agent(user_query: str) -> str:
    """
    Ejecuta el agente de investigación de mercado.
    Devuelve la respuesta final del agente.
    """
    print(f"\n{'='*60}")
    print(f"AGENTE DE INVESTIGACIÓN DE MERCADO")
    print(f"{'='*60}")
    print(f"Consulta: {user_query}")
    print(f"{'='*60}\n")

    system_prompt = """Eres un experto analista de investigación de mercado con 15 años de experiencia.
Tu objetivo es proporcionar análisis profundos, precisos y accionables.

Cuando recibas una solicitud de investigación, SIEMPRE:
1. Busca información relevante del mercado con search_web
2. Analiza el panorama competitivo con analyze_competitors
3. Investiga tendencias y proyecciones con get_market_trends
4. Genera un reporte completo y estructurado con generate_report

Usa las herramientas de forma sistemática antes de dar tu respuesta final.
Sé específico con datos, porcentajes y fuentes cuando los tengas disponibles.
Tu reporte debe ser accionable para un emprendedor o directivo de empresa."""

    messages = [{"role": "user", "content": user_query}]
    tool_call_count = 0

    while True:
        response = client.messages.create(
            model="claude-opus-4-7",
            max_tokens=4096,
            system=system_prompt,
            tools=tools,
            messages=messages
        )

        # Agregar respuesta al historial
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason == "end_turn":
            # Extraer texto final
            final_text = ""
            for block in response.content:
                if hasattr(block, "text"):
                    final_text += block.text
            print(f"\n{'='*60}")
            print("RESPUESTA FINAL DEL AGENTE:")
            print(f"{'='*60}")
            print(final_text)
            return final_text

        elif response.stop_reason == "tool_use":
            tool_results = []

            for block in response.content:
                if block.type == "tool_use":
                    tool_call_count += 1
                    print(f"\n[Herramienta {tool_call_count}] → {block.name}")

                    result = execute_tool(block.name, block.input)

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result
                    })

            messages.append({"role": "user", "content": tool_results})

        else:
            print(f"Stop reason inesperado: {response.stop_reason}")
            break

    return "El agente terminó sin respuesta final."


# ─────────────────────────────────────────────
# PUNTO DE ENTRADA
# ─────────────────────────────────────────────

if __name__ == "__main__":
    # Ejemplo de investigación de mercado
    consulta = (
        "Necesito una investigación de mercado completa sobre el sector "
        "de software de gestión para restaurantes en México y Latinoamérica. "
        "Quiero entender el tamaño del mercado, los principales competidores, "
        "las tendencias actuales y si hay oportunidad para lanzar un nuevo producto."
    )

    resultado = run_market_research_agent(consulta)
