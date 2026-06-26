from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from data import buscar_lugares, buscar_eventos, obtener_cantones, interpretar_consulta

app = FastAPI(title="Mana API", description="Backend del portal turístico Manabía")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class PreguntaRequest(BaseModel):
    texto: str

@app.get("/")
def inicio():
    return {"mensaje": "Hola, soy Mana. El portal turístico del Norte de Manabí está activo."}

@app.get("/lugares")
def lugares(canton: str = "", categoria: str = "", consulta: str = ""):
    resultados = buscar_lugares(consulta=consulta, canton=canton, categoria=categoria)
    return {"total": len(resultados), "lugares": resultados}

@app.get("/eventos")
def eventos(canton: str = "", categoria: str = ""):
    resultados = buscar_eventos(canton=canton, categoria=categoria)
    return {"total": len(resultados), "eventos": resultados}

@app.get("/cantones")
def cantones():
    return {"cantones": obtener_cantones()}

@app.post("/mana/chat")
def chat_mana(request: PreguntaRequest):
    texto = request.texto.strip()
    if not texto:
        return {"respuesta": "Hola, soy Mana 👋 ¿En qué puedo ayudarte? Puedes preguntarme sobre lugares, hospedaje, restaurantes o eventos del Norte de Manabí."}

    categoria, canton = interpretar_consulta(texto)
    resultados = buscar_lugares(consulta=texto, canton=canton, categoria=categoria)

    if not resultados:
        resultados_eventos = buscar_eventos(canton=canton)
        if resultados_eventos:
            eventos_texto = "\n".join([
                f"• *{e.get('Nombre', '')}* — {e.get('Cantón', '')} ({e.get('Fecha_Inicio', '')})"
                for e in resultados_eventos[:3]
            ])
            return {"respuesta": f"No encontré lugares para eso, pero hay eventos próximos:\n\n{eventos_texto}"}
        return {
            "respuesta": f"Lo siento, no encontré información sobre eso en mi base de datos todavía. Puedo ayudarte con hospedaje, restaurantes, playas, naturaleza, cultura y más del Norte de Manabí. ¿Qué estás buscando?"
        }

    respuesta = armar_respuesta(texto, resultados, canton, categoria)
    return {"respuesta": respuesta}

def armar_respuesta(texto: str, resultados: list, canton: str, categoria: str) -> str:
    total = len(resultados)
    intro = ""

    if canton:
        intro = f"En {canton.title()} encontré {total} opción(es):\n\n"
    elif categoria:
        intro = f"Para {categoria} encontré {total} opción(es) en el Norte de Manabí:\n\n"
    else:
        intro = f"Encontré {total} resultado(s) para tu búsqueda:\n\n"

    items = []
    for lugar in resultados[:5]:
        nombre = lugar.get("Nombre", "")
        descripcion = lugar.get("Descripción", "")
        canton_lugar = lugar.get("Cantón", "")
        parroquia = lugar.get("Parroquia", "")
        telefono = lugar.get("Teléfono", "")
        horario = lugar.get("Horario", "")
        precio = lugar.get("Precio", "")

        linea = f"📍 *{nombre}*"
        if parroquia or canton_lugar:
            linea += f" — {parroquia or canton_lugar}"
        if descripcion:
            linea += f"\n   {descripcion}"
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
