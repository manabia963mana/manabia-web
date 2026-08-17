import re
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from data import buscar_lugares, buscar_eventos, obtener_cantones, obtener_comunidad, interpretar_consulta, normalizar, corregir_typos, construir_whatsapp_link, construir_maps_link

app = FastAPI(title="Mana API", description="Backend del portal turistico Manabia")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Los <select> del frontend usan palabras simples que no siempre son subcadena exacta
# del nombre real de la categoría en el Sheet (ej. "deporte" no está contenido en
# "Instalaciones Deportivas"). Esta tabla traduce el filtro al nombre real antes de buscar.
CATEGORIA_ALIAS = {
    "alojamiento": "Alojamiento",
    "restaurante": "Alimentos, Bebidas Y Entretenimiento",
    "naturaleza": "Ecología Y Naturaleza",
    "cultura": "Cultura y Patrimonio",
    "deporte": "Instalaciones Deportivas",
}

def resolver_categoria(categoria: str) -> str:
    return CATEGORIA_ALIAS.get(normalizar(categoria), categoria) if categoria else categoria

class PreguntaRequest(BaseModel):
    texto: str
    contexto: dict = {}

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
    resultados = buscar_lugares(consulta=consulta, canton=canton, categoria=resolver_categoria(categoria))
    return {"total": len(resultados), "lugares": resultados}

@app.get("/eventos")
def eventos(canton: str = "", categoria: str = ""):
    resultados = buscar_eventos(canton=canton, categoria=categoria)
    return {"total": len(resultados), "eventos": resultados}

@app.get("/cantones")
@app.head("/cantones")
def cantones():
    return {"cantones": obtener_cantones()}

@app.get("/comunidad")
def comunidad():
    return {"publicaciones": obtener_comunidad()}

# ── RESPUESTAS FIJAS ──
# Varias respuestas fijas terminan con una pregunta de seguimiento implícita.
# Este mapa dice, para cada una, a qué categoría real de la base de datos apunta
# esa pregunta (y opcionalmente un cantón sugerido), para poder resolverla de
# verdad si el usuario confirma con un "sí" o similar.
CATEGORIA_SEGUIMIENTO_POR_CLAVE = {
    "como_llegar": {"categoria": "Movilidad Y Transporte", "canton": ""},
    "ballenas": {"categoria": "Agenciamiento Turístico", "canton": "sucre"},
    "rutas": {"categoria": "Alojamiento", "canton": ""},
    "ruta_pareja": {"categoria": "Alojamiento", "canton": ""},
    "ruta_familia": {"categoria": "Alojamiento", "canton": ""},
    "ruta_un_dia": {"categoria": "Alojamiento", "canton": ""},
}

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
        "respuesta": "🗺️ **Rutas recomendadas:**\n\n**Fin de semana (2 días):**\n📍 Día 1: Bahía de Caráquez → San Vicente → Canoa\n📍 Día 2: Jama → Pedernales\n\n**3 días:** Todo lo anterior + una noche extra en Canoa para surfear con calma\n\n**4 días:** Todo lo anterior + Chone\n\n**7 días:** Recorrido completo por los 5 cantones\n\n**2 semanas:** El recorrido completo, sin prisa, con 2-3 noches por cantón para conocer también las parroquias rurales\n\n💡 Hospédate al menos una noche en Canoa y una en Bahía. ¿Busco opciones de hospedaje en alguna zona?"
    },
    "ruta_pareja": {
        "respuesta": "💑 **Ruta romántica para pareja:**\n\n📍 **Bahía de Caráquez** — atardecer en el malecón, cena con vista al mar\n📍 **Canoa** — caminata por la playa al amanecer, surf en pareja\n📍 **San Vicente** — hospedaje boutique con vista al océano\n\n💡 Los ecolodges de la zona suelen tener las vistas más románticas. ¿Busco opciones de hospedaje para dos?"
    },
    "ruta_familia": {
        "respuesta": "👨‍👩‍👧‍👦 **Ruta en familia:**\n\n📍 **Pedernales** — playas extensas y tranquilas, ideal para niños\n📍 **Jama** — naturaleza y espacios abiertos\n📍 **Bahía de Caráquez** — Museo Bahía de Caráquez, actividades culturales\n\n💡 Busca hospedajes con piscina y zonas de juego. ¿Te ayudo a encontrar opciones familiares en algún cantón?"
    },
    "ruta_un_dia": {
        "respuesta": "☀️ **Conoce un cantón en un día:**\n\nCada cantón se puede explorar bien en una jornada:\n📍 **Canoa/San Vicente** — playa, surf y malecón\n📍 **Bahía de Caráquez** — cultura, gastronomía y el muelle\n📍 **Pedernales** — playas tranquilas\n📍 **Jama** — naturaleza y sitios arqueológicos\n📍 **Chone** — gastronomía y vida de río\n\n¿Cuál cantón te interesa? Te doy un itinerario más detallado."
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
        return RESPUESTAS_FIJAS["saludo"]["respuesta"], "saludo"
    if len(palabras_texto) <= 4 and palabras_texto & GRACIAS_PUROS:
        return RESPUESTAS_FIJAS["gracias"]["respuesta"], "gracias"

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
        "2 dias": "rutas",
        "dos dias": "rutas",
        "3 dias": "rutas",
        "tres dias": "rutas",
        "1 semana": "rutas",
        "una semana": "rutas",
        "2 semanas": "rutas",
        "dos semanas": "rutas",
        "viaje en pareja": "ruta_pareja",
        "ruta en pareja": "ruta_pareja",
        "plan en pareja": "ruta_pareja",
        "escapada romantica": "ruta_pareja",
        "viaje romantico": "ruta_pareja",
        "viaje en familia": "ruta_familia",
        "ruta en familia": "ruta_familia",
        "plan en familia": "ruta_familia",
        "con niños": "ruta_familia",
        "con ninos": "ruta_familia",
        "un cantón en un día": "ruta_un_dia",
        "un canton en un dia": "ruta_un_dia",
        "conocer un canton": "ruta_un_dia",
        "es seguro": "seguridad",
        "es peligroso": "seguridad",
        "que hacer en el norte": "que_hacer",
        "que visitar en el norte": "que_hacer",
        "recomendaciones": "que_hacer",
    }

    for frase, clave in FRASES_EXACTAS.items():
        if frase in texto_limpio:
            return RESPUESTAS_FIJAS[clave]["respuesta"], clave

    PALABRAS_CORTAS = {
        "clima": "clima",
        "temperatura": "clima",
        "itinerario": "rutas",
        "recorrido": "rutas",
        "ruta": "rutas",
        "rutas": "rutas",
        "ballenas": "ballenas",
        "seguridad": "seguridad",
    }

    for palabra, clave in PALABRAS_CORTAS.items():
        if palabra in palabras_texto:
            return RESPUESTAS_FIJAS[clave]["respuesta"], clave

    return None, None

def escapar_markdown(texto: str) -> str:
    """Elimina todos los asteriscos del texto"""
    if not texto:
        return texto
    return str(texto).replace('*', '')

# Palabras que se ignoran al buscar por nombre específico
PALABRAS_IGNORAR = {
    "dame", "dime", "busca", "buscar", "informacion", "informacion",
    "sobre", "del", "de", "la", "el", "los", "las", "un", "una",
    "quiero", "saber", "conocer", "hay", "existe", "tienen",
    "donde", "cual", "cuales", "como", "que", "me", "si",
    "tener", "necesito", "necesitas", "busco", "encontrar", "encuentrame",
    "mostrar", "muestrame", "muestra", "cuentame", "dime", "por", "favor",
    "porfavor", "porfa", "para", "puedes", "podrias", "ayuda", "ayudame",
    "algo", "algun", "alguna", "en", "y", "a"
}

# ── MEMORIA DE 1 MENSAJE ──
# Frases cortas que SOLO tienen sentido si vienen después de una pregunta de Mana.
# Ojo: nunca incluir palabras que empiecen una pregunta real (ej. "quiero", "busco"),
# o interceptarían preguntas nuevas como si fueran continuaciones.
PALABRAS_CONTINUACION = {
    "si", "dale", "ok", "okay", "claro", "vale",
    "porfa", "porfavor", "sip", "obvio", "aja", "listo", "mas", "eso"
}

def es_continuacion(texto_norm: str) -> bool:
    palabras = set(texto_norm.split())
    if len(palabras) == 0 or len(palabras) > 3:
        return False
    return bool(palabras & PALABRAS_CONTINUACION)


@app.post("/mana/chat")
def chat_mana(request: PreguntaRequest):
    texto = request.texto.strip()
    contexto_previo = request.contexto or {}

    if not texto:
        return {"respuesta": "¡Hola! Soy Mana 🌊 ¿En qué puedo ayudarte hoy?", "contexto": {}}

    texto = corregir_typos(texto)
    texto_norm = normalizar(texto)

    # 1. Verificar respuestas fijas PRIMERO (saludo, ballenas, clima, rutas, etc.)
    #    Esto tiene prioridad sobre la memoria de continuación, para que una pregunta
    #    real como "quiero ver ballenas" nunca sea interceptada por error.
    respuesta_fija, clave_fija = verificar_saludo(texto_norm)
    if respuesta_fija:
        # Varias respuestas fijas terminan haciendo una pregunta de seguimiento
        # ("¿Busco agencias de turismo en Bahía?", "¿Necesitas info de transporte?").
        # Se guarda a qué categoría apunta esa pregunta, para que si el usuario
        # responde "sí" (o nombra un cantón), Mana sepa qué buscar de verdad.
        seguimiento = CATEGORIA_SEGUIMIENTO_POR_CLAVE.get(clave_fija)
        contexto_salida = {
            "categoria_seguimiento": seguimiento["categoria"],
            "canton_mencionado": seguimiento["canton"],
        } if seguimiento else {}
        return {"respuesta": respuesta_fija, "contexto": contexto_salida}

    # 1.5. El mensaje confirma la pregunta de seguimiento de una respuesta fija
    # anterior (ej. dijo "sí" después de que Mana preguntó por agencias de turismo,
    # o "sí, de Canoa" después de la pregunta sobre transporte) -> se busca
    # directamente en la categoría implícita, en vez de perderse.
    categoria_seguimiento_previa = contexto_previo.get("categoria_seguimiento", "")
    if categoria_seguimiento_previa:
        palabras_msg = set(texto_norm.split())
        tiene_confirmacion = bool(palabras_msg & PALABRAS_CONTINUACION)
        categoria_nueva, canton_nuevo = interpretar_consulta(texto)
        if tiene_confirmacion and not categoria_nueva:
            canton_final = canton_nuevo or contexto_previo.get("canton_mencionado", "")
            resultados_seg = buscar_lugares(categoria=categoria_seguimiento_previa, canton=canton_final)
            if resultados_seg:
                respuesta_seg, nuevo_contexto_seg, lugares_seg = armar_respuesta(resultados_seg, canton_final, categoria_seguimiento_previa, offset=0, consulta="")
                return {"respuesta": respuesta_seg, "contexto": nuevo_contexto_seg, "lugares": lugares_seg}
            else:
                lugar_txt = f" en {canton_final.title()}" if canton_final else ""
                return {
                    "respuesta": f"No encontré opciones para eso{lugar_txt} por ahora. ¿Te ayudo con algo más? 🌊",
                    "contexto": {}
                }

    # 2. Memoria de 1 mensaje: el usuario responde algo corto tipo "sí" / "dale" / "más"
    if es_continuacion(texto_norm):
        total_previo = contexto_previo.get("total", 0)
        mostrados_previo = contexto_previo.get("mostrados", 0)

        if total_previo > mostrados_previo:
            # Había más resultados pendientes de la búsqueda anterior -> mostrar el siguiente tramo
            canton = contexto_previo.get("canton", "")
            categoria = contexto_previo.get("categoria", "")
            consulta = contexto_previo.get("consulta", "")
            resultados = buscar_lugares(consulta=consulta, canton=canton, categoria=categoria)
            respuesta, nuevo_contexto, lugares_mostrados = armar_respuesta(resultados, canton, categoria, offset=mostrados_previo, consulta=consulta)
            return {"respuesta": respuesta, "contexto": nuevo_contexto, "lugares": lugares_mostrados}
        else:
            # No hay contexto pendiente claro -> pedir que aclare, en vez de perderse
            return {
                "respuesta": "¡Cuéntame! ¿Qué necesitas: hospedaje, restaurantes, playas, eventos o algo más? 🌊",
                "contexto": {}
            }

    # 3. Interpretar categoría y cantón
    categoria, canton = interpretar_consulta(texto)

    resultados = []
    # Filtros que realmente produjeron 'resultados' — se guardan en el contexto
    # tal cual se usaron, para que "sí"/"más" reproduzca la MISMA búsqueda
    # exacta en vez de combinar cantón+categoría+texto a la fuerza.
    canton_usado, categoria_usado, consulta_usada = "", "", ""

    # 3. Búsqueda por nombre específico — limpia palabras vacías.
    # SIEMPRE se intenta primero, aunque se haya detectado una categoría o cantón,
    # porque una palabra como "iglesia" puede ser tanto el nombre de un lugar
    # específico como una palabra clave de categoría — y el nombre específico
    # es más útil si existe. Solo si esta búsqueda no encuentra nada se cae a
    # la categoría/cantón completos.
    palabras_busqueda = [p for p in texto.split() if normalizar(p) not in PALABRAS_IGNORAR]
    texto_limpio_busqueda = " ".join(palabras_busqueda)

    if len(palabras_busqueda) >= 1:
        resultados = buscar_lugares(consulta=texto_limpio_busqueda)
        if resultados:
            consulta_usada = texto_limpio_busqueda

    # 4. Si hay categoría Y cantón
    if not resultados and categoria and categoria != "GENERAL" and canton:
        resultados = buscar_lugares(categoria=categoria, canton=canton)
        if resultados:
            categoria_usado, canton_usado = categoria, canton

    # 5. Si hay solo categoría
    if not resultados and categoria and categoria != "GENERAL" and not canton:
        resultados = buscar_lugares(categoria=categoria)
        if resultados:
            categoria_usado = categoria

    # 6. Si hay cantón con categoría GENERAL → buscar todo en ese cantón
    if not resultados and canton:
        resultados = buscar_lugares(canton=canton, consulta=texto_limpio_busqueda)
        if resultados:
            canton_usado, consulta_usada = canton, texto_limpio_busqueda
        if not resultados:
            resultados = buscar_lugares(canton=canton)
            if resultados:
                canton_usado = canton

    # 7. Búsqueda libre general
    if not resultados:
        resultados = buscar_lugares(consulta=texto_limpio_busqueda)
        if resultados:
            consulta_usada = texto_limpio_busqueda

    # 8. Sin resultados → mostrar eventos
    if not resultados:
        resultados_eventos = buscar_eventos(canton=canton)
        if resultados_eventos:
            eventos_texto = "\n".join([
                f"• {escapar_markdown(e.get('Nombre', ''))} — {e.get('Canton', e.get('Cantón', ''))} ({e.get('Fecha Inicio', '')})"
                for e in resultados_eventos[:3]
            ])
            return {
                "respuesta": f"No encontré establecimientos para eso, pero hay eventos próximos:\n\n{eventos_texto}\n\n¿Quieres más información sobre alguno?",
                "contexto": {}
            }
        return {
            "respuesta": "Lo siento, no encontré información sobre eso en mi base de datos. Puedo ayudarte con hospedaje, restaurantes, cajeros, playas, naturaleza y más del Norte de Manabí. ¿Qué necesitas?",
            "contexto": {}
        }

    respuesta, nuevo_contexto, lugares_mostrados = armar_respuesta(resultados, canton_usado, categoria_usado, offset=0, consulta=consulta_usada)
    return {"respuesta": respuesta, "contexto": nuevo_contexto, "lugares": lugares_mostrados}


def armar_respuesta(resultados: list, canton: str, categoria: str, offset: int = 0, consulta: str = "") -> tuple:
    total = len(resultados)
    tramo = resultados[offset:offset + 5]

    # Defensivo: si esto es una continuación ("sí", "más") y no queda nada que mostrar
    # (por ejemplo porque la búsqueda en vivo trajo menos resultados que la vez anterior),
    # se cierra la conversación con honestidad en vez de mostrar una burbuja vacía.
    if offset > 0 and not tramo:
        contexto_cerrado = {"canton": canton, "categoria": categoria, "consulta": consulta, "mostrados": offset, "total": offset}
        return "Eso era todo lo que tenía para esta búsqueda. ¿Te ayudo con algo más? 🌊", contexto_cerrado

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

    if offset == 0:
        if canton:
            nombre_lugar = NOMBRES_CANTON.get(canton.lower(), canton.title())
            intro = f"Encontré {total} opción(es) en {nombre_lugar}:\n\n"
        elif categoria and categoria != "GENERAL":
            nombre_cat = categoria.split(",")[0].strip()
            intro = f"Encontré {total} opción(es) de {nombre_cat} en el Norte de Manabí:\n\n"
        else:
            intro = f"Encontré {total} resultado(s):\n\n"
    else:
        intro = "Aquí tienes más opciones:\n\n"

    items = []
    lugares_mostrados = []
    for indice, lugar in enumerate(tramo):
        nombre = escapar_markdown(lugar.get("Nombre", ""))
        if not nombre:
            continue
        desc = escapar_markdown(lugar.get("Descripción", ""))
        canton_lugar = escapar_markdown(lugar.get("Cantón", ""))
        parroquia = escapar_markdown(lugar.get("Parroquia", ""))
        subcategoria = escapar_markdown(lugar.get("Subcategoría", ""))
        telefono = lugar.get("Teléfono", "")
        whatsapp = lugar.get("WhatsApp", "") or telefono
        horario = escapar_markdown(lugar.get("Horario", ""))
        precio = escapar_markdown(lugar.get("Precio", ""))

        linea = f"<span class='chat-lugar-link' data-idx='{indice}' style='cursor:pointer;text-decoration:underline;text-decoration-style:dotted;'>📍 {nombre}</span>"
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
            linea += f"\n   $ {precio}"
        if telefono:
            linea += f"\n   📞 {telefono}"
        wa_link = construir_whatsapp_link(whatsapp)
        if wa_link:
            linea += f"\n   <a href='{wa_link}' target='_blank' rel='noopener' style='color:#25D366;font-weight:600;text-decoration:none;'>💬 Escribir por WhatsApp</a>"
        maps_link = construir_maps_link(lugar.get("Lat"), lugar.get("Lng"), nombre, parroquia, canton_lugar, lugar.get("Dirección", ""))
        if maps_link:
            linea += f"\n   <a href='{maps_link}' target='_blank' rel='noopener' style='color:#1E3A6E;font-weight:600;text-decoration:none;'>📍 Cómo llegar</a>"
        items.append(linea)
        lugares_mostrados.append(lugar)

    cuerpo = "\n\n".join(items)
    mostrados = offset + len(tramo)

    if total > mostrados:
        pie = f"\n\n_...y {total - mostrados} más. ¿Quieres que te muestre más opciones?_"
    else:
        pie = "\n\n¿Te ayudo con algo más?"

    nuevo_contexto = {
        "canton": canton,
        "categoria": categoria,
        "consulta": consulta,
        "mostrados": mostrados,
        "total": total,
    }

    return intro + cuerpo + pie, nuevo_contexto, lugares_mostrados
