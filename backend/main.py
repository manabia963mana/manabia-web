from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from data import buscar_lugares, buscar_eventos, obtener_cantones, interpretar_consulta

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

# Respuestas fijas para preguntas genéricas y de conocimiento general
RESPUESTAS_FIJAS = {
    "saludo": {
        "palabras": ["hola", "buenos dias", "buenas tardes", "buenas noches", "hey", "saludos", "hi", "hello"],
        "respuesta": "¡Hola! Soy **Mana** 🌊, tu guía digital del Norte de Manabí.\n\nPuedo ayudarte a encontrar:\n📍 Lugares turísticos, playas y naturaleza\n🏨 Hospedaje en los cinco cantones\n🍽️ Restaurantes y gastronomía típica\n🏄 Actividades y deportes\n📅 Eventos y festivales\n💰 Cajeros, bancos y servicios\n\n¿Qué estás buscando hoy?"
    },
    "gracias": {
        "palabras": ["gracias", "muchas gracias", "thank you", "thanks", "grax"],
        "respuesta": "¡Con mucho gusto! 😊 Estoy aquí para ayudarte a descubrir el norte de Manabí. ¿Hay algo más en lo que pueda ayudarte?"
    },
    "quien_eres": {
        "palabras": ["quien eres", "que eres", "como te llamas", "quien es mana", "que es mana", "para que sirves"],
        "respuesta": "Soy **Mana** 🌊, la guía digital del Norte de Manabí.\n\nFui creada para ayudarte a descubrir los cinco cantones del norte de Manabí: **Pedernales, Jama, San Vicente, Sucre y Chone**.\n\nPuedes preguntarme sobre hospedaje, restaurantes, playas, eventos, cajeros, transporte y mucho más. Toda mi información proviene de una base de datos verificada del territorio. ¿En qué puedo ayudarte?"
    },
    "clima": {
        "palabras": ["clima", "temperatura", "llueve", "tiempo", "cuando ir", "mejor epoca", "temporada"],
        "respuesta": "🌤️ **Clima del Norte de Manabí:**\n\n**Temporada seca** (junio - noviembre): Ideal para visitar. Días soleados, pocas lluvias, perfecta para playa y surf. Temperatura promedio 24-28°C.\n\n**Temporada de lluvias** (diciembre - mayo): Más calurosa y húmeda. Es la temporada de mayor vegetación y cascadas. Temperatura promedio 26-32°C.\n\n🐋 **Avistamiento de ballenas:** Junio a septiembre es la mejor época, especialmente en Bahía de Caráquez.\n\n🏄 **Surf:** Todo el año en Canoa, con mejores olas en temporada seca.\n\n¿Quieres saber sobre actividades específicas en algún cantón?"
    },
    "como_llegar": {
        "palabras": ["como llegar", "como ir", "desde quito", "desde guayaquil", "desde manta", "bus", "transporte", "llegar al norte", "como me movilizo"],
        "respuesta": "🚌 **Cómo llegar al Norte de Manabí:**\n\n**Desde Quito:**\n- Bus directo a Pedernales (~5 hrs), Bahía de Caráquez (~6 hrs) o Chone (~5 hrs)\n- Cooperativas: Flota Bolívar, Reina del Camino, CITM\n\n**Desde Guayaquil:**\n- Bus a Bahía (~4 hrs) o Pedernales (~5 hrs)\n- Ruta por Santo Domingo también disponible\n\n**Desde Manta:**\n- Bus a Bahía de Caráquez (~2 hrs)\n- Bus a San Vicente/Canoa (~2.5 hrs)\n\n**Movilidad interna:**\n- Taxis y mototaxis disponibles en todos los cantones\n- Buses intercantonales frecuentes\n- Ferry entre Bahía de Caráquez y San Vicente (5 minutos)\n\n¿Necesitas información sobre transporte en algún cantón específico?"
    },
    "rutas": {
        "palabras": ["ruta", "itinerario", "que visitar", "plan de viaje", "dias", "fin de semana", "recorrido"],
        "respuesta": "🗺️ **Rutas recomendadas por el Norte de Manabí:**\n\n**Fin de semana (2 días):**\n📍 Día 1: Bahía de Caráquez → San Vicente → Canoa (surf y atardecer)\n📍 Día 2: Jama → Pedernales (playa y pesca artesanal)\n\n**4 días:**\nTodo lo anterior + Chone (gastronomía manabita y río Chone)\n\n**7 días:**\nRecorrido completo por los 5 cantones con estadías en cada uno\n\n💡 Te recomiendo hospedarte al menos una noche en Canoa y una en Bahía. ¿Quieres que Mana te busque opciones de hospedaje en alguna de estas zonas?"
    },
    "ballenas": {
        "palabras": ["ballenas", "avistamiento", "ballena jorobada", "ver ballenas"],
        "respuesta": "🐋 **Avistamiento de ballenas jorobadas:**\n\nLa mejor época es de **junio a septiembre**, cuando las ballenas jorobadas llegan al Pacífico ecuatoriano para reproducirse.\n\n📍 El principal punto de salida es **Bahía de Caráquez** — desde el muelle turístico salen tours diarios en esa temporada, generalmente entre las 7h00 y 9h00.\n\n¿Quieres que busque agencias de turismo en Bahía de Caráquez que ofrezcan este tour?"
    },
    "que_hacer": {
        "palabras": ["que hacer", "que ver", "actividades", "atractivos", "lugares para visitar", "recomendacion", "planes"],
        "respuesta": "🌊 **Lo mejor del Norte de Manabí:**\n\n🏄 **Aventura:** Surf en Canoa, kayak en el estuario, parapente\n🐋 **Naturaleza:** Avistamiento de ballenas (jun-sep), Isla Corazón, Humedal La Segua, Mache-Chindul\n🍽️ **Gastronomía:** Ceviche de concha, seco de pato, viche de pescado, bolón con queso\n🏛️ **Cultura:** Museo de Bahía, sitios arqueológicos Jama-Coaque en Chirije y San Isidro\n🌅 **Relax:** Playas tranquilas en Pedernales, atardeceres en el mirador de Bahía\n\n¿Te cuento más sobre alguna de estas experiencias o buscamos lugares específicos?"
    },
    "seguridad": {
        "palabras": ["seguro", "peligroso", "seguridad", "es seguro", "delincuencia", "robo"],
        "respuesta": "🔒 **Sobre seguridad en el Norte de Manabí:**\n\nEn general es una zona turística tranquila. Algunos consejos:\n\n✅ Los centros turísticos de Bahía, Canoa y Pedernales son seguros para visitantes\n✅ Mantén tus pertenencias cerca, especialmente en mercados y zonas concurridas\n✅ Viaja durante el día entre cantones\n✅ Consulta con tu hospedaje sobre las zonas recomendadas\n\n📞 **Emergencias:**\n- Policía: 101\n- Bomberos: 102\n- ECU911: 911\n\n¿Necesitas información sobre servicios de salud o policía en algún cantón?"
    },
}

def verificar_saludo(texto_norm: str):
    """Solo responde a saludos puros, nunca intercepta búsquedas"""
    from data import normalizar
    texto_limpio = texto_norm.strip()
    palabras_texto = set(texto_limpio.split())
    
    # Lista de palabras que SOLO activan saludo si están solas o casi solas
    SALUDOS_PUROS = {"hola", "hey", "hi", "hello", "saludos", "buenas"}
    GRACIAS_PUROS = {"gracias", "grax", "thanks"}
    
    # Solo activa si el mensaje tiene 1-3 palabras Y una es saludo puro
    if len(palabras_texto) <= 3 and palabras_texto & SALUDOS_PUROS:
        return RESPUESTAS_FIJAS["saludo"]["respuesta"]
    
    if len(palabras_texto) <= 4 and palabras_texto & GRACIAS_PUROS:
        return RESPUESTAS_FIJAS["gracias"]["respuesta"]
    
    # Para el resto, buscar frases completas exactas (no palabras sueltas)
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
        "fin de semana": "rutas",
        "plan de viaje": "rutas",
        "es seguro": "seguridad",
        "es peligroso": "seguridad",
    }
    
    for frase, clave in FRASES_EXACTAS.items():
        if frase in texto_limpio:
            return RESPUESTAS_FIJAS[clave]["respuesta"]
    
    # Palabras únicas que solo activan si el mensaje es corto (máx 4 palabras)
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

@app.post("/mana/chat")
def chat_mana(request: PreguntaRequest):
    from data import normalizar
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

    # 3. Si hay categoría Y cantón → filtrar por ambos primero
    if categoria and canton:
        resultados = buscar_lugares(categoria=categoria, canton=canton)

    # 4. Si hay categoría pero no cantón → buscar por categoría
    if not resultados and categoria and not canton:
        resultados = buscar_lugares(categoria=categoria)

    # 5. Si hay categoría y cantón pero no encontró → solo por categoría
    if not resultados and categoria:
        resultados = buscar_lugares(categoria=categoria)

    # 6. Si no hay categoría → búsqueda libre con cantón
    if not resultados and not categoria:
        resultados = buscar_lugares(consulta=texto, canton=canton)

    # 7. Último recurso → búsqueda libre sin filtros
    if not resultados:
        resultados = buscar_lugares(consulta=texto)

    # 8. Si aún no hay nada → mostrar eventos
    if not resultados:
        resultados_eventos = buscar_eventos(canton=canton)
        if resultados_eventos:
            eventos_texto = "\n".join([
                f"• *{e.get('Nombre', '')}* — {e.get('Cantón', '')} ({e.get('Fecha Inicio', '')})"
                for e in resultados_eventos[:3]
            ])
            return {"respuesta": f"No encontré establecimientos para eso, pero hay eventos próximos:\n\n{eventos_texto}\n\n¿Quieres más información?"}
        return {"respuesta": "Lo siento, no encontré información sobre eso en mi base de datos. Puedo ayudarte con hospedaje, restaurantes, cajeros, playas, naturaleza y más del Norte de Manabí. ¿Qué necesitas?"}

    return {"respuesta": armar_respuesta(texto, resultados, canton, categoria)}

def armar_respuesta(texto: str, resultados: list, canton: str, categoria: str) -> str:
    total = len(resultados)

    if canton:
        intro = f"Encontré **{total} opción(es)** en {canton.title()}:\n\n"
    elif categoria:
        nombre_cat = categoria.split(",")[0].strip()
        intro = f"Encontré **{total} opción(es)** de {nombre_cat} en el Norte de Manabí:\n\n"
    else:
        intro = f"Encontré **{total} resultado(s)**:\n\n"

    items = []
    for lugar in resultados[:5]:
        nombre = lugar.get("Nombre", "")
        if not nombre:
            continue
        desc = lugar.get("Descripción", "")
        canton_lugar = lugar.get("Cantón", "")
        parroquia = lugar.get("Parroquia", "")
        subcategoria = lugar.get("Subcategoría", "")
        telefono = lugar.get("Teléfono", "")
        horario = lugar.get("Horario", "")
        precio = lugar.get("Precio", "")

        linea = f"📍 *{nombre}*"
        ubicacion = ", ".join(filter(None, [parroquia, canton_lugar]))
        if ubicacion:
            linea += f" — {ubicacion}"
        if subcategoria:
            linea += f"\n   🏷️ {subcategoria}"
        if desc:
            linea += f"\n   {desc}"
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
