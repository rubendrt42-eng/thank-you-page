import streamlit as st
import anthropic
import json
from datetime import datetime

st.set_page_config(
    page_title="Agente de Investigación de Mercado",
    page_icon="📊",
    layout="wide"
)

st.title("📊 Agente de Investigación de Mercado")
st.markdown("Escribe tu consulta y el agente investigará el mercado automáticamente.")

# ─── Sidebar: API Key ───
with st.sidebar:
    st.header("⚙️ Configuración")
    api_key = st.text_input("Anthropic API Key", type="password", placeholder="sk-ant-...")
    st.markdown("[Obtener API Key](https://console.anthropic.com)")
    st.divider()
    st.markdown("**Ejemplos de consultas:**")
    ejemplos = [
        "Mercado de software para restaurantes en México",
        "Oportunidades en fintech para pymes en LATAM",
        "Competidores en el sector de telemedicina en España",
    ]
    for ej in ejemplos:
        if st.button(ej, use_container_width=True):
            st.session_state["consulta_input"] = ej

# ─── Herramientas ───

tools = [
    {
        "name": "search_web",
        "description": "Busca información actualizada sobre un tema de mercado.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Término de búsqueda"},
                "focus": {
                    "type": "string",
                    "enum": ["tamaño_mercado", "tendencias", "noticias", "estadísticas", "general"],
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "analyze_competitors",
        "description": "Analiza los principales competidores de un sector.",
        "input_schema": {
            "type": "object",
            "properties": {
                "industry": {"type": "string"},
                "company_name": {"type": "string"}
            },
            "required": ["industry"]
        }
    },
    {
        "name": "get_market_trends",
        "description": "Obtiene tendencias y proyecciones de un mercado.",
        "input_schema": {
            "type": "object",
            "properties": {
                "market": {"type": "string"},
                "region": {"type": "string", "default": "global"},
                "horizon": {
                    "type": "string",
                    "enum": ["1_año", "3_años", "5_años", "10_años"],
                    "default": "5_años"
                }
            },
            "required": ["market"]
        }
    },
    {
        "name": "generate_report",
        "description": "Compila todos los hallazgos en un reporte estructurado.",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "sections": {"type": "array", "items": {"type": "string"}},
                "findings": {"type": "object"}
            },
            "required": ["title", "sections", "findings"]
        }
    }
]

def search_web(query, focus="general"):
    return json.dumps({
        "result": f"Mercado relacionado con '{query}': valuado en $2.4B en 2024, proyectado a $5.1B en 2029.",
        "sources": ["Statista 2024", "Grand View Research"],
        "key_data": {"market_size_2024": "$2.4B", "projected_2029": "$5.1B", "cagr": "16.2%"}
    }, ensure_ascii=False)

def analyze_competitors(industry, company_name=None):
    return json.dumps({
        "industria": industry,
        "principales_players": [
            {"nombre": "Líder A", "cuota_mercado": "28%", "fortalezas": ["marca fuerte", "tech propietaria"], "debilidades": ["precios altos"]},
            {"nombre": "Challenger B", "cuota_mercado": "18%", "fortalezas": ["UX superior", "precio bajo"], "debilidades": ["equipo pequeño"]},
            {"nombre": "Nicho C", "cuota_mercado": "8%", "fortalezas": ["especialización vertical"], "debilidades": ["mercado estrecho"]}
        ],
        "concentración": "Top 3 controlan 54% del mercado",
        "oportunidad": "Segmento SMB desatendido"
    }, ensure_ascii=False)

def get_market_trends(market, region="global", horizon="5_años"):
    return json.dumps({
        "mercado": market,
        "región": region,
        "tamaño_actual": "$3.2B (2024)",
        "tamaño_proyectado": "$7.8B (2029)",
        "cagr": "19.5%",
        "drivers": ["Transformación digital", "Nueva generación de consumidores", "Regulaciones favorables"],
        "riesgos": ["Incertidumbre macro", "Escasez de talento tech"],
        "segmentos_calientes": [{"segmento": "Pequeñas empresas", "cagr": "24%"}, {"segmento": "Salud", "cagr": "31%"}]
    }, ensure_ascii=False)

def generate_report(title, sections, findings):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"reporte_{timestamp}.md"
    content = f"# {title}\n*Generado el {datetime.now().strftime('%d/%m/%Y %H:%M')}*\n\n---\n\n"
    for section in sections:
        content += f"## {section.replace('_', ' ').title()}\n\n"
        if section in findings:
            data = findings[section]
            if isinstance(data, dict):
                for k, v in data.items():
                    if isinstance(v, list):
                        content += f"**{k}:**\n" + "".join(f"- {i}\n" for i in v) + "\n"
                    else:
                        content += f"**{k}:** {v}\n\n"
            else:
                content += f"{data}\n\n"
        content += "---\n\n"

    st.session_state["report_content"] = content
    st.session_state["report_filename"] = filename
    return json.dumps({"status": "reporte_generado", "archivo": filename}, ensure_ascii=False)

def execute_tool(name, inputs):
    if name == "search_web":
        return search_web(**inputs)
    elif name == "analyze_competitors":
        return analyze_competitors(**inputs)
    elif name == "get_market_trends":
        return get_market_trends(**inputs)
    elif name == "generate_report":
        return generate_report(**inputs)
    return json.dumps({"error": "herramienta desconocida"})

# ─── UI principal ───

consulta = st.text_area(
    "¿Qué mercado quieres investigar?",
    value=st.session_state.get("consulta_input", ""),
    height=100,
    placeholder="Ej: Quiero entrar al mercado de apps de fitness en México. ¿Hay oportunidad? ¿Quiénes son los competidores?"
)

iniciar = st.button("🔍 Investigar", type="primary", use_container_width=True)

if iniciar:
    if not api_key:
        st.error("Ingresa tu Anthropic API Key en el panel izquierdo.")
    elif not consulta.strip():
        st.warning("Escribe tu consulta primero.")
    else:
        client = anthropic.Anthropic(api_key=api_key)

        st.divider()
        st.subheader("⚙️ Proceso de investigación")
        log_area = st.empty()
        logs = []

        resultado_area = st.empty()

        system_prompt = """Eres un experto analista de investigación de mercado.
Cuando recibas una solicitud SIEMPRE usa todas las herramientas disponibles:
1. search_web para buscar datos del mercado
2. analyze_competitors para analizar competidores
3. get_market_trends para tendencias y proyecciones
4. generate_report para compilar todo en un reporte

Sé específico con datos y porcentajes. Tu análisis debe ser accionable."""

        messages = [{"role": "user", "content": consulta}]

        with st.spinner("El agente está investigando..."):
            try:
                while True:
                    response = client.messages.create(
                        model="claude-opus-4-7",
                        max_tokens=4096,
                        system=system_prompt,
                        tools=tools,
                        messages=messages
                    )

                    messages.append({"role": "assistant", "content": response.content})

                    if response.stop_reason == "end_turn":
                        final_text = "".join(b.text for b in response.content if hasattr(b, "text"))
                        st.divider()
                        st.subheader("📋 Análisis del agente")
                        st.markdown(final_text)
                        break

                    elif response.stop_reason == "tool_use":
                        tool_results = []
                        for block in response.content:
                            if block.type == "tool_use":
                                tool_icons = {
                                    "search_web": "🔍",
                                    "analyze_competitors": "🏢",
                                    "get_market_trends": "📈",
                                    "generate_report": "📄"
                                }
                                icon = tool_icons.get(block.name, "⚙️")
                                logs.append(f"{icon} Usando **{block.name}**...")
                                log_area.markdown("\n\n".join(logs))

                                result = execute_tool(block.name, block.input)
                                tool_results.append({
                                    "type": "tool_result",
                                    "tool_use_id": block.id,
                                    "content": result
                                })

                        messages.append({"role": "user", "content": tool_results})

            except anthropic.AuthenticationError:
                st.error("API Key inválida. Verifica que sea correcta.")
            except Exception as e:
                st.error(f"Error: {e}")

        # Mostrar botón de descarga si se generó el reporte
        if "report_content" in st.session_state:
            st.divider()
            st.download_button(
                label="⬇️ Descargar reporte completo (.md)",
                data=st.session_state["report_content"],
                file_name=st.session_state["report_filename"],
                mime="text/markdown",
                use_container_width=True
            )
