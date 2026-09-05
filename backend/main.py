import re
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from data import buscar_lugares, buscar_eventos, obtener_cantones, obtener_comunidad, interpretar_consulta, normalizar, corregir_typos, construir_whatsapp_link, construir_maps_link, MESES_ES

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
    consulta = corregir_typos(consulta) if consulta else consulta
    categoria_resuelta = resolver_categoria(categoria) if categoria else ""

    # Si la persona escribió una sola palabra (sin elegir categoría manual en
    # el dropdown) y esa palabra es justo la que activa una categoría (ej.
    # "comida", "hotel"), se salta la búsqueda libre e se va directo a la
    # categoría completa — igual que en el chat de Mana. Sin esto, una palabra
    # genérica que por casualidad coincide con 1-2 nombres de negocios dejaba
    # la respuesta corta en vez de mostrar todos los lugares de esa categoría.
    categoria_detectada, canton_detectado = ("", "")
    es_solo_palabra_de_categoria = False
    if consulta and not categoria:
        palabras = consulta.split()
        if len(palabras) == 1:
            categoria_detectada, canton_detectado = interpretar_consulta(consulta)
            if categoria_detectada and categoria_detectada != "GENERAL":
                es_solo_palabra_de_categoria = True

    # 1. Búsqueda libre tal cual la escribió la persona (más específica primero),
    # salvo en el caso de "solo la palabra de categoría" de arriba.
    if es_solo_palabra_de_categoria:
        resultados = []
    else:
        resultados = buscar_lugares(consulta=consulta, canton=canton, categoria=categoria_resuelta) if (consulta or canton or categoria_resuelta) else []

    # 2. Si no encontró nada (o se saltó a propósito) y NO se eligió una
    # categoría manual en el dropdown, se intenta detectar la categoría real a
    # partir de lo que escribió (igual que hace Mana en el chat) — ej. "hotel"
    # -> Alojamiento, "surf" -> combinar playas + surf, etc. Esto evita que el
    # buscador de la página quede "más tonto" que el chat para el mismo tipo
    # de búsqueda.
    if not resultados and consulta and not categoria:
        texto_norm = normalizar(consulta)
        if "surf" in texto_norm:
            resultados_surf = buscar_lugares(consulta="surf", canton=canton)
            resultados_playas = buscar_lugares(consulta="playas", canton=canton)
            vistos = {r["Nombre"] for r in resultados_surf}
            resultados = resultados_surf + [r for r in resultados_playas if r["Nombre"] not in vistos]
        else:
            if not es_solo_palabra_de_categoria:
                categoria_detectada, canton_detectado = interpretar_consulta(consulta)
            canton_final = canton or canton_detectado
            if categoria_detectada and categoria_detectada != "GENERAL":
                resultados = buscar_lugares(categoria=categoria_detectada, canton=canton_final)
            elif canton_final:
                resultados = buscar_lugares(canton=canton_final)

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
    "que_es_manabia": {
        "respuesta": "Manabía es la plataforma inteligente del Norte de Manabí. Reúne en un solo lugar información sobre playas, naturaleza, gastronomía, cultura, eventos, rutas y experiencias para ayudarte a descubrir la región de forma sencilla y personalizada. 🌊"
    },
    "es_gratis": {
        "respuesta": "Sí, es completamente gratuito. El acceso a la plataforma y todas las consultas conmigo son gratis, y no necesitas registrarte para usar la mayor parte del sitio. 🌊"
    },
    "registrar_negocio": {
        "respuesta": "¡Con gusto! Puedes solicitar la incorporación de tu negocio (hotel, restaurante, cafetería, operador turístico, artesanía, museo, etc.) escribiendo a **manabia963@gmail.com** o a través del formulario de Contáctanos en el sitio."
    },
    "publicar_evento": {
        "respuesta": "Sí, instituciones públicas, organizaciones, empresas y gestores culturales pueden solicitar la publicación de un evento en el calendario oficial. Escríbenos a **manabia963@gmail.com** con los detalles."
    },
    "reportar_error": {
        "respuesta": "Gracias por avisar — usa el formulario de Contáctanos (elige 'Reportar información incorrecta') o escríbenos directo a **manabia963@gmail.com** contándonos qué dato está mal, y lo corregimos lo antes posible."
    },
    "privacidad_datos": {
        "respuesta": "Respetamos tu privacidad. Tus datos personales se usan únicamente para mejorar tu experiencia y se manejan según nuestra Política de Privacidad, que puedes revisar en el footer del sitio."
    },
    "contactar_equipo": {
        "respuesta": "Puedes contactarnos por el formulario de Contáctanos en el sitio, o directo a **manabia963@gmail.com**. ¡Con gusto te ayudamos!"
    },
    "cantones_cubiertos": {
        "respuesta": "Actualmente cubrimos los cinco cantones del Norte de Manabí: **Pedernales, Jama, San Vicente, Sucre (Bahía de Caráquez) y Chone**. 🌊"
    },
    "como_usar_sitio": {
        "respuesta": "Puedes encontrar lugares de tres maneras: conversando conmigo (como ahora), explorando el mapa interactivo, o navegando por categorías como playas, gastronomía, naturaleza, cultura y eventos."
    },
    "que_info_hay": {
        "respuesta": "Tenemos información sobre playas, restaurantes, hoteles, cafeterías, museos, iglesias, miradores, senderos, reservas naturales, deportes, eventos, ferias y fiestas tradicionales del Norte de Manabí."
    },
    "que_es_mapa": {
        "respuesta": "El Mapa Interactivo te permite localizar fácilmente playas, restaurantes, hoteles, atractivos turísticos, eventos y otros lugares de interés — lo encuentras en el botón de mapa dentro del sitio."
    },
    "que_es_calendario": {
        "respuesta": "El Calendario de Eventos es la agenda actualizada del Norte de Manabí — ahí encuentras festivales, actividades culturales, eventos deportivos, ferias gastronómicas y celebraciones."
    },
    "recomendaciones_personalizadas": {
        "respuesta": "Sí, adapto mis sugerencias según lo que me cuentes: viajes en pareja, familias, aventura, naturaleza, gastronomía, presupuesto o el tiempo que tengas disponible. Cuéntame más y te ayudo. 🌊"
    },
    "perfiles_destacados": {
        "respuesta": "Sí, Manabía cuenta con perfiles Premium para negocios que quieran mejorar su presencia, mostrar más fotos, incluir promociones y acceder a herramientas adicionales. Escribe a **manabia963@gmail.com** para más info."
    },
    "financiamiento": {
        "respuesta": "Manabía se sostiene mediante servicios Premium para empresas, campañas promocionales y alianzas institucionales, siempre manteniendo una experiencia clara y transparente para quien la usa."
    },
    "contenido_patrocinado": {
        "respuesta": "Sí, cuando un contenido sea patrocinado va a aparecer claramente identificado. Siempre priorizo lo que de verdad te sirve, no lo que paguen más."
    },
    "fuente_informacion": {
        "respuesta": "Trabajamos con fuentes oficiales, instituciones locales, organizaciones, empresas y colaboradores del territorio. Toda la información se revisa y actualiza periódicamente."
    },
    "frecuencia_actualizacion": {
        "respuesta": "La plataforma está en actualización permanente — eventos, horarios y servicios se revisan continuamente para que la información sea lo más precisa posible."
    },
    "funciona_movil": {
        "respuesta": "Sí, Manabía funciona en computadoras, tabletas y celulares sin necesidad de descargar nada — simplemente entra desde el navegador de tu teléfono. 📱"
    },
    "los_5_cantones": {
        "respuesta": "El Norte de Manabí está formado por **5 cantones**:\n\n📍 **Pedernales** — cabecera cantonal, con Cojimíes (puerto pesquero) y 10 de Agosto\n📍 **Jama** — su única parroquia formal es Jama; incluye comunas como El Matal, Tabuga y Don Juan\n📍 **San Vicente** — el cantón más joven de Manabí (1999), incluye Canoa, famosa por sus playas de surf\n📍 **Sucre** — cabecera en Bahía de Caráquez, con Leónidas Plaza, Charapotó y San Isidro\n📍 **Chone** — el cantón más extenso de Manabí, con 7 parroquias rurales\n\n¿Quieres que te cuente las parroquias de alguno en particular?"
    },
}

# Parroquias reales por cantón (de la hoja Cantones), para responder preguntas
# como "parroquias de Chone" con datos exactos en vez de perderse.
PARROQUIAS_POR_CANTON = {
    "pedernales": "Pedernales tiene 3 parroquias: **Pedernales** (cabecera cantonal), **Cojimíes** (puerto pesquero, con playa a 35 km al norte) y **10 de Agosto** (zona montañosa).",
    "jama": "Jama tiene una sola parroquia formal, que es **Jama** (la cabecera cantonal). El resto del cantón se organiza en 42 comunas sin parroquias rurales formales, entre las que destacan La Cabuya, El Matal, Puerto Cabuyal, La Mocora, Venado, Colorado, Tabuga y Don Juan.",
    "san vicente": "San Vicente tiene 2 parroquias: **San Vicente** (cabecera cantonal, el cantón más joven de Manabí, creado en 1999) y **Canoa** (su principal destino turístico, con ~40 km de playas para surf y deportes acuáticos).",
    "sucre": "Sucre tiene 4 parroquias: **Bahía de Caráquez** (cabecera cantonal), **Leónidas Plaza** (parroquia urbana), **Charapotó** (una de las poblaciones más antiguas de Manabí, con las playas de San Jacinto y San Clemente) y **San Isidro** (separada geográficamente del resto del cantón, con el importante sitio arqueológico Jama Coaque).",
    "chone": "Chone es el cantón más extenso de Manabí, con 9 parroquias: **Chone** y **Santa Rita** (urbanas), y **Canuto, Convento, Chibunga, San Antonio, Eloy Alfaro, Ricaurte y Boyacá** (rurales).",
}
# La gente suele decir "Bahía" en vez de "Sucre" (el nombre real del cantón) --
# se apunta al mismo texto para que responda igual sin importar cuál use.
PARROQUIAS_POR_CANTON["bahia de caraquez"] = PARROQUIAS_POR_CANTON["sucre"]
PARROQUIAS_POR_CANTON["bahia"] = PARROQUIAS_POR_CANTON["sucre"]

# Cultura e historia del Norte de Manabí — mismo contenido que ya usamos en la
# sección "Historia y Cultura" del sitio, resumido para que Mana lo sepa
# también en el chat. Se suman al mismo diccionario de respuestas fijas.
RESPUESTAS_FIJAS["jama_coaque"] = {"respuesta": "La cultura Jama-Coaque floreció entre el 350 a.C. y 1530 d.C. en la costa norte de Manabí, desde el cabo de San Francisco hasta Bahía de Caráquez, en los valles de los ríos Jama y Coaque. Fue una sociedad jerarquizada de carácter teocrático, célebre por sus figurinas de arcilla con pastillaje (chamanes, guerreros, músicos) y su orfebrería en oro y platino. Puedes conocer más en el Museo Arqueológico de Jama o en la sección 'Sobre Manabí' del sitio. 🏺"}
RESPUESTAS_FIJAS["amorfino"] = {"respuesta": "El amorfino es la voz poética tradicional del Norte de Manabí — versos breves, muchas veces improvisados, que combinan la herencia de las coplas españolas con el ingenio del campo manabita. Se cantan en contrapunto entre hombres y mujeres durante rodeos montuvios, fiestas patronales y ferias. En 2011 fue declarado Patrimonio Cultural Inmaterial del Ecuador. 🎶"}
RESPUESTAS_FIJAS["mision_geodesica"] = {"respuesta": "En 1736 llegó a Manabí la Misión Geodésica Francesa, liderada por Charles Marie de La Condamine, para medir la verdadera forma de la Tierra. El norte de la provincia formaba parte de la Gobernación de Esmeraldas bajo el sabio riobambeño Pedro Vicente Maldonado, clave en la expedición y autor del primer mapa detallado de la región. 🗺️"}
RESPUESTAS_FIJAS["iche_cultura"] = {"respuesta": "Iche es un ecosistema gastronómico en San Vicente, impulsado por la Fundación Fuegos tras el terremoto de 2016. Combina una escuela de cocina, un restaurante laboratorio y un incubador de emprendimientos, rescatando ingredientes ancestrales como el maní, el plátano y la salprieta. 🔥"}
RESPUESTAS_FIJAS["museo_montubio"] = {"respuesta": "El Museo de la Cultura Montubia, en San Isidro (cantón Sucre), es el primero dedicado a la cultura montubia en todo Ecuador. Abierto desde marzo de 2024 por la Fundación Raíces y Sueños, reúne amorfinos, música tradicional y piezas arqueológicas de las culturas Valdivia, Manteña y Jama-Coaque que habitaron la zona antes que el pueblo montubio. 🌾"}
RESPUESTAS_FIJAS["temporada_ballenas_info"] = {"respuesta": "La temporada de avistamiento de ballenas jorobadas en el Norte de Manabí va de **junio a septiembre**, con Bahía de Caráquez como principal punto de salida de los tours. 🐋"}

# Preguntas frecuentes que Mana puede responder directamente (además de todo lo
# de arriba). El texto completo de estas y otras preguntas también está
# disponible para el usuario en la sección "Preguntas frecuentes" del sitio.
FRASES_FAQ = {
    "que es manabia": "que_es_manabia",
    "que es esta pagina": "que_es_manabia",
    "que es este sitio": "que_es_manabia",
    "manabia es gratis": "es_gratis",
    "app es gratis": "es_gratis",
    "sitio es gratis": "es_gratis",
    "pagina es gratis": "es_gratis",
    "tiene costo usar": "es_gratis",
    "cuesta usar manabia": "es_gratis",
    "cuesta usar la app": "es_gratis",
    "necesito registrarme": "es_gratis",
    "necesito crear cuenta": "es_gratis",
    "necesito una cuenta": "es_gratis",
    "aparecer mi negocio": "registrar_negocio",
    "registrar mi negocio": "registrar_negocio",
    "registro mi negocio": "registrar_negocio",
    "como registro": "registrar_negocio",
    "publicar mi negocio": "registrar_negocio",
    "incluir mi negocio": "registrar_negocio",
    "agregar mi negocio": "registrar_negocio",
    "sumar mi negocio": "registrar_negocio",
    "tengo un negocio": "registrar_negocio",
    "tengo un hotel": "registrar_negocio",
    "tengo un restaurante": "registrar_negocio",
    "publicar un evento": "publicar_evento",
    "publicar mi evento": "publicar_evento",
    "agregar un evento": "publicar_evento",
    "dato incorrecto": "reportar_error",
    "informacion incorrecta": "reportar_error",
    "informacion esta mal": "reportar_error",
    "reportar un error": "reportar_error",
    "reportar informacion": "reportar_error",
    "protegen mi informacion": "privacidad_datos",
    "politica de privacidad": "privacidad_datos",
    "que hacen con mis datos": "privacidad_datos",
    "contactar al equipo": "contactar_equipo",
    "hablar con el equipo": "contactar_equipo",
    "contactar manabia": "contactar_equipo",
    "hablar con una persona": "contactar_equipo",
    "que cantones cubre": "cantones_cubiertos",
    "que cantones tiene manabia": "cantones_cubiertos",
    "cuantos cantones": "cantones_cubiertos",
    "que cantones abarca": "cantones_cubiertos",
    "como funciona el sitio": "como_usar_sitio",
    "como funciona la pagina": "como_usar_sitio",
    "como funciona esta pagina": "como_usar_sitio",
    "como uso esta pagina": "como_usar_sitio",
    "como uso este sitio": "como_usar_sitio",
    "como uso manabia": "como_usar_sitio",
    "que informacion tiene manabia": "que_info_hay",
    "que puedo encontrar en manabia": "que_info_hay",
    "que hay en esta pagina": "que_info_hay",
    "que hay en este sitio": "que_info_hay",
    "que es el mapa interactivo": "que_es_mapa",
    "para que sirve el mapa": "que_es_mapa",
    "que es el calendario de eventos": "que_es_calendario",
    "para que sirve el calendario": "que_es_calendario",
    "recomendaciones son personalizadas": "recomendaciones_personalizadas",
    "recomendaciones de mana son personalizadas": "recomendaciones_personalizadas",
    "perfiles destacados": "perfiles_destacados",
    "perfil premium": "perfiles_destacados",
    "cuenta premium": "perfiles_destacados",
    "planes premium": "perfiles_destacados",
    "como se financia manabia": "financiamiento",
    "de que vive manabia": "financiamiento",
    "como ganan dinero": "financiamiento",
    "recomendaciones patrocinadas": "contenido_patrocinado",
    "contenido patrocinado": "contenido_patrocinado",
    "de donde sacan la informacion": "fuente_informacion",
    "de donde viene la informacion de manabia": "fuente_informacion",
    "fuentes de informacion de manabia": "fuente_informacion",
    "con que frecuencia se actualiza": "frecuencia_actualizacion",
    "cada cuanto actualizan": "frecuencia_actualizacion",
    "que tan actualizada esta la informacion": "frecuencia_actualizacion",
    "funciona en el celular": "funciona_movil",
    "funciona en el telefono": "funciona_movil",
    "hay app movil": "funciona_movil",
    "tienen aplicacion movil": "funciona_movil",
    "puedo usar manabia desde el celular": "funciona_movil",
    "5 cantones": "los_5_cantones",
    "cinco cantones": "los_5_cantones",
    "cuantos cantones": "los_5_cantones",
    "cuales son los cantones": "los_5_cantones",
    "que cantones hay": "los_5_cantones",
    "cantones de manabi": "los_5_cantones",
    "cantones del norte de manabi": "los_5_cantones",
}
FRASES_FAQ["que es la cultura jama coaque"] = "jama_coaque"
FRASES_FAQ["que es la cultura jama-coaque"] = "jama_coaque"
FRASES_FAQ["quienes fueron los jama coaque"] = "jama_coaque"
FRASES_FAQ["quienes fueron los jama-coaque"] = "jama_coaque"
FRASES_FAQ["que es jama coaque"] = "jama_coaque"
FRASES_FAQ["que es jama-coaque"] = "jama_coaque"
FRASES_FAQ["que es el amorfino"] = "amorfino"
FRASES_FAQ["que es un amorfino"] = "amorfino"
FRASES_FAQ["que es la mision geodesica"] = "mision_geodesica"
FRASES_FAQ["que es la mision geodesica francesa"] = "mision_geodesica"
FRASES_FAQ["quien fue pedro vicente maldonado"] = "mision_geodesica"
FRASES_FAQ["que es el proyecto iche"] = "iche_cultura"
FRASES_FAQ["que es el museo de la cultura montubia"] = "museo_montubio"
FRASES_FAQ["que es la cultura montubia"] = "museo_montubio"
FRASES_FAQ["cuando es la temporada de ballenas"] = "temporada_ballenas_info"
FRASES_FAQ["cuando puedo ver ballenas"] = "temporada_ballenas_info"

def verificar_saludo(texto_norm: str):
    texto_limpio = texto_norm.strip()
    palabras_texto = set(texto_limpio.split())

    SALUDOS_PUROS = {"hola", "hey", "hi", "hello", "saludos", "buenas"}
    GRACIAS_PUROS = {"gracias", "grax", "thanks"}

    if len(palabras_texto) <= 3 and palabras_texto & SALUDOS_PUROS:
        return RESPUESTAS_FIJAS["saludo"]["respuesta"], "saludo"
    if len(palabras_texto) <= 4 and palabras_texto & GRACIAS_PUROS:
        return RESPUESTAS_FIJAS["gracias"]["respuesta"], "gracias"

    for frase, clave in FRASES_FAQ.items():
        if frase in texto_limpio:
            return RESPUESTAS_FIJAS[clave]["respuesta"], clave

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

PALABRAS_EVENTO = {"evento", "eventos", "festival", "festivales", "feria", "ferias", "actividad", "actividades", "agenda", "fiesta", "fiestas"}

def detectar_consulta_evento(texto_norm: str):
    """Detecta si la pregunta es sobre eventos, y si menciona un mes específico
    (ej. 'eventos en septiembre'). Devuelve (es_sobre_eventos, mes_numero_o_None)."""
    palabras = set(texto_norm.split())
    es_evento = bool(palabras & PALABRAS_EVENTO)
    mes_detectado = None
    for nombre_mes, numero in MESES_ES.items():
        if nombre_mes in texto_norm:
            mes_detectado = numero
            break
    return es_evento, mes_detectado

def armar_respuesta_eventos(eventos: list, mes: int = None) -> tuple:
    """Arma la respuesta de eventos ordenada cronológicamente, con enlaces
    clicables (mismo patrón que armar_respuesta usa para lugares)."""
    import datetime as _dt
    hoy = _dt.date.today()

    def fecha_ordenable(ev):
        f = ev.get("Fecha Inicio", "")
        try:
            return _dt.datetime.strptime(f[:10], "%Y-%m-%d").date()
        except (ValueError, TypeError):
            return _dt.date.max  # los "Variable" quedan al final

    vigentes = []
    for ev in eventos:
        f = ev.get("Fecha Inicio", "")
        if not f:
            continue
        if f.strip().lower().startswith("variable"):
            if mes is None:  # solo se muestran eventos "Variable" si no se pidió un mes específico
                vigentes.append(ev)
            continue
        try:
            fecha_ev = _dt.datetime.strptime(f[:10], "%Y-%m-%d").date()
        except (ValueError, TypeError):
            continue
        if fecha_ev < hoy:
            continue
        if mes is not None and fecha_ev.month != mes:
            continue
        vigentes.append(ev)

    vigentes.sort(key=fecha_ordenable)

    if not vigentes:
        mes_txt = f" en {[k for k,v in MESES_ES.items() if v==mes][0]}" if mes else ""
        return f"No encontré eventos próximos{mes_txt}. ¿Te ayudo con algo más? 🌊", []

    items = []
    for i, ev in enumerate(vigentes[:6]):
        nombre = escapar_markdown(ev.get("Nombre", ""))
        canton = escapar_markdown(ev.get("Cantón", ""))
        fecha_txt = ev.get("Fecha Inicio", "")
        if fecha_txt and not fecha_txt.lower().startswith("variable"):
            try:
                d = _dt.datetime.strptime(fecha_txt[:10], "%Y-%m-%d").date()
                fecha_txt = d.strftime("%d de %B").replace(
                    "January","enero").replace("February","febrero").replace("March","marzo"
                ).replace("April","abril").replace("May","mayo").replace("June","junio"
                ).replace("July","julio").replace("August","agosto").replace("September","septiembre"
                ).replace("October","octubre").replace("November","noviembre").replace("December","diciembre")
            except (ValueError, TypeError):
                pass
        linea = f"<span class='chat-evento-link' data-idx='{i}' style='cursor:pointer;text-decoration:underline;text-decoration-style:dotted;'>📅 {nombre}</span>"
        detalles = " — ".join(filter(None, [canton, fecha_txt]))
        if detalles:
            linea += f" ({detalles})"
        if ev.get("Descripción"):
            linea += f"\n   {ev['Descripción'][:100]}"
        items.append(linea)

    cuerpo = "\n\n".join(items)
    pie = "\n\n¿Quieres más información sobre alguno?" if len(vigentes) <= 6 else f"\n\n_...y {len(vigentes)-6} más._"
    return f"Encontré estos eventos:\n\n{cuerpo}{pie}", vigentes[:6]

# Palabras que se ignoran al buscar por nombre específico
PALABRAS_IGNORAR = {
    "dame", "dime", "busca", "buscar", "informacion", "informacion",
    "sobre", "del", "de", "la", "el", "los", "las", "un", "una",
    "quiero", "saber", "conocer", "hay", "existe", "tienen",
    "donde", "cual", "cuales", "como", "que", "me", "si",
    "tener", "necesito", "necesitas", "busco", "encontrar", "encuentrame",
    "mostrar", "muestrame", "muestra", "cuentame", "dime", "por", "favor",
    "porfavor", "porfa", "para", "puedes", "podrias", "ayuda", "ayudame",
    "algo", "algun", "alguna", "en", "y", "a",
    "manabi", "manabia", "ecuador", "norte", "hacer", "hago", "haciendo",
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
        if clave_fija == "los_5_cantones":
            contexto_salida["ultimo_canton_mencionado"] = "chone"  # el último de la lista
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

    # 2.4. Consulta sobre parroquias de un cantón — se resuelve con datos reales
    # de la hoja Cantones, en vez de caer en una búsqueda libre que no tiene
    # sentido para este tipo de pregunta. Si el mensaje no nombra el cantón
    # (ej. "y cuáles son SUS parroquias"), se usa el último cantón del que se
    # habló, guardado en el contexto de la conversación.
    if "parroquia" in texto_norm or "parroquias" in texto_norm:
        _, canton_parroquia = interpretar_consulta(texto)
        if not canton_parroquia:
            canton_parroquia = contexto_previo.get("ultimo_canton_mencionado", "")
        if canton_parroquia and canton_parroquia in PARROQUIAS_POR_CANTON:
            return {
                "respuesta": PARROQUIAS_POR_CANTON[canton_parroquia],
                "contexto": {"ultimo_canton_mencionado": canton_parroquia}
            }

    # 2.5. Consulta sobre eventos (con o sin mes específico) — se resuelve aparte,
    # con prioridad sobre la búsqueda de negocios, porque "eventos en septiembre"
    # no es una búsqueda de un lugar.
    es_evento, mes_detectado = detectar_consulta_evento(texto_norm)
    if es_evento:
        _, canton_evento = interpretar_consulta(texto)
        eventos_encontrados = buscar_eventos(canton=canton_evento)
        respuesta_ev, lista_eventos = armar_respuesta_eventos(eventos_encontrados, mes_detectado)
        return {"respuesta": respuesta_ev, "contexto": {}, "eventos": lista_eventos}

    # 3. Interpretar categoría y cantón
    categoria, canton = interpretar_consulta(texto)

    resultados = []
    # Filtros que realmente produjeron 'resultados' — se guardan en el contexto
    # tal cual se usaron, para que "sí"/"más" reproduzca la MISMA búsqueda
    # exacta en vez de combinar cantón+categoría+texto a la fuerza.
    canton_usado, categoria_usado, consulta_usada = "", "", ""

    # 2.7. Caso especial: "surf". Casi no hay lugares etiquetados con la
    # subcategoría "Surf" en la base (2 nada más), así que preguntar por surf
    # se combina con las playas reales (que sí están bien pobladas) para dar
    # una respuesta útil en vez de casi vacía.
    if "surf" in texto_norm:
        resultados_surf = buscar_lugares(consulta="surf")
        resultados_playas = buscar_lugares(consulta="playas")
        vistos = {r["Nombre"] for r in resultados_surf}
        resultados = resultados_surf + [r for r in resultados_playas if r["Nombre"] not in vistos]
        if resultados:
            consulta_usada = "surf"
            respuesta, nuevo_contexto, lugares_mostrados = armar_respuesta(resultados, "", "", offset=0, consulta=consulta_usada)
            return {"respuesta": respuesta, "contexto": nuevo_contexto, "lugares": lugares_mostrados}

    # 3. Búsqueda por nombre específico — limpia palabras vacías.
    # Normalmente se intenta primero, aunque se haya detectado una categoría o
    # cantón, porque una palabra como "iglesia" puede ser tanto el nombre de un
    # lugar específico como una palabra clave de categoría.
    #
    # EXCEPCIÓN importante: si después de quitar palabras vacías queda una sola
    # palabra Y esa palabra es justamente la que activó la categoría (ej.
    # "comida", "hotel"), se salta la búsqueda de nombre específico e se va
    # directo a la categoría completa. La razón: con una sola palabra genérica,
    # la búsqueda de nombre libre a veces encuentra 1 o 2 coincidencias sueltas
    # (lugares que por casualidad tienen esa palabra en su nombre), y eso hacía
    # que la respuesta se quedara corta en vez de mostrar TODOS los lugares de
    # esa categoría, que es lo que la persona realmente quería.
    palabras_busqueda = [p for p in texto.split() if normalizar(p) not in PALABRAS_IGNORAR]
    texto_limpio_busqueda = " ".join(palabras_busqueda)

    es_solo_la_palabra_de_categoria = (
        len(palabras_busqueda) == 1
        and categoria
        and categoria != "GENERAL"
    )

    if len(palabras_busqueda) >= 1 and not es_solo_la_palabra_de_categoria:
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
            respuesta_ev, lista_eventos = armar_respuesta_eventos(resultados_eventos)
            if lista_eventos:
                return {
                    "respuesta": f"No encontré establecimientos para eso, pero hay eventos próximos:\n\n{respuesta_ev.split(':',1)[1].strip()}",
                    "contexto": {},
                    "eventos": lista_eventos
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
