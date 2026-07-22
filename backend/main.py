import re
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from data import buscar_lugares, buscar_eventos, obtener_cantones, interpretar_consulta, normalizar

app = FastAPI(title="Mana API", description="Backend del portal turistico Manabia")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class PreguntaRequest(BaseModel):
    texto: str

@app.get("/")
@app.head("/")
def inicio():
    return JSONResponse(
        content={"mensaje": "Hola, soy Mana. El portal turistico del Norte de Manabi esta activo."},
        media_type="application/json; charset=utf-8"
    )

@app.get("/health")
@app.head("/health")
def health():
    return {"status": "ok"}

@app.get("/lugares")
def lugares(canton: str = "", categoria: str = "", consulta: str = ""):
    resultados = buscar_lugares(consulta=consulta, canton=canton, categoria=categoria)
    return {"total": len(resultados), "lugares": resultados}

@app.get("/eventos")
def eventos(canton: str = "", categoria: str = ""):
    resultados = buscar_eventos(canton=canton, categoria=categoria)
    return {"total": len(resultados), "eventos": resultados}

@app.get("/cantones")
@app.head("/cantones")
def cantones():
    return {"cantones": obtener_cantones()}

# ── RESPUESTAS FIJAS ──
RESPUESTAS_FIJAS = {
    "saludo": {
        "respuesta": "¡Hola! Soy **Mana** 🌊, tu guía digital del Norte de Manabí.\n\nPuedo ayudarte a encontrar:\n📍 Lugares turísticos, playas y naturaleza\n🏨 Hospedaje en los cinco cantones\n🍽️ Restaurantes y gastronomía típica\n🏄 Actividades y deportes\n📅 Eventos y festivales\n💰 Cajeros, bancos y servicios\n\n¿Qué estás buscando hoy?"
    },
    "gracias": {
        "respuesta": "¡Con mucho gusto! 😊 Estoy aquí para ayudarte a descubrir el norte de Manabí. ¿Hay algo más en lo que pueda ayudarte?"
    },
    "quien_eres": {
        "respuesta": "Soy **Mana** 🌊, la guía digital del Norte de Manabí.\n\nFui creada para ayudarte a descubrir los cinco cantones: **Pedernales, Jama, San Vicente, Sucre y Chone**.\n\nPuedes preguntarme sobre hospedaje, restaurantes, playas, eventos, cajeros, transporte y mucho más. ¿En qué puedo ayudarte?"
    },
    "clima": {
        "respuesta": "🌤️ **Clima del Norte de Manabí:**\n\n**Temporada seca** (junio - noviembre): Días soleados, pocas lluvias, ideal para playa y surf. Temperatura promedio 24-28°C.\n\n**Temporada de lluvias** (diciembre - mayo): Más calurosa y húmeda, mayor vegetación. Temperatura promedio 26-32°C.\n\n🐋 **Ballenas:** Junio a septiembre, especialmente en Bahía de Caráquez.\n\n🏄 **Surf:** Todo el año en Canoa, mejores olas en temporada seca.\n\n¿Quieres saber sobre algún cantón específico?"
    },
    "como_llegar": {
        "respuesta": "🚌 **Cómo llegar al Norte de Manabí:**\n\n**Desde Quito:**\n- Bus directo a Pedernales (~5 hrs), Bahía (~6 hrs) o Chone (~5 hrs)\n- Cooperativas: Flota Bolívar, Reina del Camino, CITM\n\n**Desde Guayaquil:**\n- Bus a Bahía (~4 hrs) o Pedernales (~5 hrs)\n\n**Desde Manta:**\n- Bus a Bahía (~2 hrs) o Canoa (~2.5 hrs)\n\n**Movilidad interna:**\n- Taxis y mototaxis en todos los cantones\n- Ferry entre Bahía y San Vicente (5 minutos)\n\n¿Necesitas info sobre transporte en algún cantón?"
    },
    "rutas": {
        "respuesta": "🗺️ **Rutas recomendadas:**\n\n**Fin de semana (2 días):**\n📍 Día 1: Bahía de Caráquez → San Vicente → Canoa\n📍 Día 2: Jama → Pedernales\n\n**4 días:** Todo lo anterior + Chone\n\n**7 días:** Recorrido completo por los 5 cantones\n\n💡 Hospédate al menos una noche en Canoa y una en Bahía. ¿Busco opciones de hospedaje en alguna zona?"
    },
    "ballenas": {
        "respuesta": "🐋 **Avistamiento de ballenas jorobadas:**\n\nMejor época: **junio a septiembre**.\n\n📍 Principal punto de salida: **Bahía de Caráquez** — tours desde el muelle turístico entre 7h00 y 9h00.\n\n¿Busco agencias de turismo en Bahía que ofrezcan este tour?"
    },
    "que_hacer": {
        "respuesta": "🌊 **Lo mejor del Norte de Manabí:**\n\n🏄 **Aventura:** Surf en Canoa, kayak, parapente\n🐋 **Naturaleza:** Ballenas (jun-sep), Isla Corazón, Humedal La Segua, Mache-Chindul\n🍽️ **Gastronomía:** Ceviche, seco de pato, viche de pescado, bolón con queso\n🏛️ **Cultura:** Museo de Bahía, sitios Jama-Coaque en Chirije y San Isidro\n🌅 **Relax:** Playas en Pedernales, atardeceres en el mirador de Bahía\n\n¿Te busco lugares específicos en algún cantón?"
    },
    "seguridad": {
        "respuesta": "🔒 **Seguridad en el Norte de Manabí:**\n\nEn general es una zona turística tranquila.\n\n✅ Bahía, Canoa y Pedernales son seguros para visitantes\n✅ Mantén tus pertenencias cerca en mercados\n✅ Viaja durante el día entre cantones\n\n📞 **Emergencias:**\n- Policía: 101\n- Bomberos: 102\n- ECU911: 911\n\n¿Necesitas info sobre hospitales o policía en algún cantón?"
    },
}

def verificar_saludo(texto_norm: str):
    texto_limpio = texto_norm.strip()
    palabras_texto = set(texto_limpio.split())

    SALUDOS_PUROS = {"hola", "hey", "hi", "hello", "saludos", "buenas"}
    GRACIAS_PUROS = {"gracias", "grax", "thanks"}

    if len(palabras_texto) <= 3 and palabras_texto & SALUDOS_PUROS:
        return RESPUESTAS_FIJAS["saludo"]["respuesta"]
    if len(palabras_texto) <= 4 and palabras_texto & GRACIAS_PUROS:
        return RESPUESTAS_FIJAS["gracias"]["respuesta"]

    FRASES_EXACTAS = {
        "buenos dias": "saludo",
        "buenas tardes": "saludo",
        "buenas noches": "saludo",
        "quien eres": "quien_eres",
        "que eres": "quien_eres",
        "como te llamas": "quien_eres",
        "quien es mana": "quien_eres",
        "que es mana": "quien_eres",
        "para que sirves": "quien_eres",
        "que puedes hacer": "quien_eres",
        "que puedes": "quien_eres",
        "en que me ayudas": "quien_eres",
        "como me ayudas": "quien_eres",
        "que sabes": "quien_eres",
        "muchas gracias": "gracias",
        "thank you": "gracias",
        "como llegar": "como_llegar",
        "como ir": "como_llegar",
        "desde quito": "como_llegar",
        "desde guayaquil": "como_llegar",
        "desde manta": "como_llegar",
        "llegar al norte": "como_llegar",
        "como me movilizo": "como_llegar",
        "ver ballenas": "ballenas",
        "ballena jorobada": "ballenas",
        "avistamiento de ballenas": "ballenas",
        "avistamiento": "ballenas",
        "fin de semana": "rutas",
        "plan de viaje": "rutas",
        "es seguro": "seguridad",
        "es peligroso": "seguridad",
        "que hacer en el norte": "que_hacer",
        "que visitar en el norte": "que_hacer",
        "recomendaciones": "que_hacer",
    }

    for frase, clave in FRASES_EXACTAS.items():
        if frase in texto_limpio:
            return RESPUESTAS_FIJAS[clave]["respuesta"]

    PALABRAS_CORTAS = {
        "clima": "clima",
        "temperatura": "clima",
        "itinerario": "rutas",
        "recorrido": "rutas",
        "ballenas": "ballenas",
        "seguridad": "seguridad",
    }

    if len(palabras_texto) <= 4:
        for palabra, clave in PALABRAS_CORTAS.items():
            if palabra in palabras_texto:
                return RESPUESTAS_FIJAS[clave]["respuesta"]

    return None

def escapar_markdown(texto: str) -> str:
    """Elimina todos los asteriscos del texto"""
    return texto.replace('*', '')

# Palabras que se ignoran al buscar por nombre específico
PALABRAS_IGNORAR = {
    "dame", "dime", "busca", "buscar", "informacion", "informacion",
    "sobre", "del", "de", "la", "el", "los", "las", "un", "una",
    "quiero", "saber", "conocer", "hay", "existe", "tienen",
    "donde", "cual", "cuales", "como", "que", "me", "si"
}

@app.post("/mana/chat")
def chat_mana(request: PreguntaRequest):
    texto = request.texto.strip()
    if not texto:
        return {"respuesta": "¡Hola! Soy Mana 🌊 ¿En qué puedo ayudarte hoy?"}

    texto_norm = normalizar(texto)

    # 1. Verificar respuestas fijas primero
    respuesta_fija = verificar_saludo(texto_norm)
    if respuesta_fija:
        return {"respuesta": respuesta_fija}

    # 2. Interpretar categoría y cantón
    categoria, canton = interpretar_consulta(texto)

    resultados = []

    # 3. Búsqueda por nombre específico — limpia palabras vacías
    palabras_busqueda = [p for p in texto.split() if normalizar(p) not in PALABRAS_IGNORAR]
    texto_limpio_busqueda = " ".join(palabras_busqueda)

    if len(palabras_busqueda) >= 1 and not canton and not categoria:
        resultados = buscar_lugares(consulta=texto_limpio_busqueda)

    # 4. Si hay categoría Y cantón
    if not resultados and categoria and categoria != "GENERAL" and canton:
        resultados = buscar_lugares(categoria=categoria, canton=canton)

    # 5. Si hay solo categoría
    if not resultados and categoria and categoria != "GENERAL" and not canton:
        resultados = buscar_lugares(categoria=categoria)

    # 6. Si hay cantón con categoría GENERAL → buscar todo en ese cantón
    if not resultados and canton:
        resultados = buscar_lugares(canton=canton, consulta=texto_limpio_busqueda)
        if not resultados:
            resultados = buscar_lugares(canton=canton)

    # 7. Búsqueda libre general
    if not resultados:
        resultados = buscar_lugares(consulta=texto_limpio_busqueda)

    # 8. Sin resultados → mostrar eventos
    if not resultados:
        resultados_eventos = buscar_eventos(canton=canton)
        if resultados_eventos:
            eventos_texto = "\n".join([
                f"• *{e.get('Nombre', '')}* — {e.get('Canton', e.get('Cantón', ''))} ({e.get('Fecha Inicio', '')})"
                for e in resultados_eventos[:3]
            ])
            return {"respuesta": f"No encontré establecimientos para eso, pero hay eventos próximos:\n\n{eventos_texto}\n\n¿Quieres más información sobre alguno?"}
        return {"respuesta": "Lo siento, no encontré información sobre eso en mi base de datos. Puedo ayudarte con hospedaje, restaurantes, cajeros, playas, naturaleza y más del Norte de Manabí. ¿Qué necesitas?"}

    return {"respuesta": armar_respuesta(texto, resultados, canton, categoria)}


def armar_respuesta(texto: str, resultados: list, canton: str, categoria: str) -> str:
    total = len(resultados)

    NOMBRES_CANTON = {
        "sucre": "Bahía de Caráquez / Sucre",
        "san vicente": "San Vicente / Canoa",
        "pedernales": "Pedernales",
        "jama": "Jama",
        "chone": "Chone",
        "bahia": "Bahía de Caráquez",
        "bahia de caraquez": "Bahía de Caráquez",
        "canoa": "Canoa",
        "charapoto": "Charapotó",
        "san isidro": "San Isidro",
        "cojimies": "Cojimíes",
        "leonidas": "Leónidas Plaza",
    }

    if canton:
        nombre_lugar = NOMBRES_CANTON.get(canton.lower(), canton.title())
        intro = f"Encontré {total} opción(es) en {nombre_lugar}:\n\n"
    elif categoria and categoria != "GENERAL":
        nombre_cat = categoria.split(",")[0].strip()
        intro = f"Encontré {total} opción(es) de {nombre_cat} en el Norte de Manabí:\n\n"
    else:
        intro = f"Encontré {total} resultado(s):\n\n"

    items = []
    for lugar in resultados[:5]:
        nombre = escapar_markdown(lugar.get("Nombre", ""))
        if not nombre:
            continue
        desc = lugar.get("Descripción", "")
        canton_lugar = lugar.get("Cantón", "")
        parroquia = lugar.get("Parroquia", "")
        subcategoria = lugar.get("Subcategoría", "")
        telefono = lugar.get("Teléfono", "")
        horario = lugar.get("Horario", "")
        precio = lugar.get("Precio", "")

        nombre_safe = nombre.replace('*', '')
        linea = f"📍 {nombre}"
        ubicacion = ", ".join(filter(None, [parroquia, canton_lugar]))
        if ubicacion:
            linea += f" — {ubicacion}"
        if subcategoria:
            linea += f"\n   🏷️ {subcategoria}"
        if desc:
            linea += f"\n   {desc[:120]}{'...' if len(desc) > 120 else ''}"
        if horario:
            linea += f"\n   🕐 {horario}"
        if precio:
            linea += f"\n   💰 {precio}"
        if telefono:
            linea += f"\n   📞 {telefono}"
        items.append(linea)

    cuerpo = "\n\n".join(items)

    if total > 5:
        pie = f"\n\n_...y {total - 5} más. ¿Quieres que filtre por alguna zona específica?_"
    else:
        pie = "\n\n¿Te ayudo con algo más?"

    return intro + cuerpo + pie
