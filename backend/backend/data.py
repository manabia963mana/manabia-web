import pandas as pd
import requests
from io import StringIO

SHEETS = {
    "lugares": "https://docs.google.com/spreadsheets/d/e/2PACX-1vSyU7JFnYAE1WvoH1HGbwOzIQyjkdFJrzuGQ0T0xHxh3iqtYpOHXmH1vj5Casg3oxWZEL8OBSFFPSUd/pub?gid=662364550&single=true&output=csv",
    "eventos": "https://docs.google.com/spreadsheets/d/e/2PACX-1vSyU7JFnYAE1WvoH1HGbwOzIQyjkdFJrzuGQ0T0xHxh3iqtYpOHXmH1vj5Casg3oxWZEL8OBSFFPSUd/pub?gid=702277477&single=true&output=csv",
    "cantones": "https://docs.google.com/spreadsheets/d/e/2PACX-1vSyU7JFnYAE1WvoH1HGbwOzIQyjkdFJrzuGQ0T0xHxh3iqtYpOHXmH1vj5Casg3oxWZEL8OBSFFPSUd/pub?gid=0&single=true&output=csv"
}

def cargar_hoja(nombre):
    try:
        url = SHEETS[nombre]
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        df = pd.read_csv(StringIO(response.text))
        df = df.dropna(how="all")
        return df
    except Exception as e:
        print(f"Error cargando {nombre}: {e}")
        return pd.DataFrame()

def buscar_lugares(consulta: str = "", canton: str = "", categoria: str = "", tags: str = ""):
    df = cargar_hoja("lugares")
    if df.empty:
        return []

    df.columns = df.columns.str.strip()

    if canton:
        df = df[df["Cantón"].str.lower().str.contains(canton.lower(), na=False)]
    if categoria:
        df = df[df["Categoría"].str.lower().str.contains(categoria.lower(), na=False)]
    if tags:
        df = df[df["Tags"].str.lower().str.contains(tags.lower(), na=False)]
    if consulta:
        mask = (
            df["Nombre"].str.lower().str.contains(consulta.lower(), na=False) |
            df["Descripción"].str.lower().str.contains(consulta.lower(), na=False) |
            df["Subcategoría"].str.lower().str.contains(consulta.lower(), na=False) |
            df["Parroquia"].str.lower().str.contains(consulta.lower(), na=False)
        )
        df = df[mask]

    df = df[df["Estado"].str.lower().str.strip() == "activo"] if "Estado" in df.columns else df
    return df.to_dict(orient="records")

def buscar_eventos(canton: str = "", categoria: str = ""):
    df = cargar_hoja("eventos")
    if df.empty:
        return []

    df.columns = df.columns.str.strip()

    if canton:
        df = df[df["Cantón"].str.lower().str.contains(canton.lower(), na=False)]
    if categoria:
        df = df[df["Categoría"].str.lower().str.contains(categoria.lower(), na=False)]

    df = df[df["Estado"].str.lower().str.strip() == "activo"] if "Estado" in df.columns else df
    return df.to_dict(orient="records")

def obtener_cantones():
    df = cargar_hoja("cantones")
    if df.empty:
        return []
    return df.to_dict(orient="records")

PALABRAS_CLAVE = {
    "hospedaje": ["hotel", "hostal", "cabaña", "glamping", "ecohotel", "hostería", "alojamiento", "camping"],
    "comer": ["restaurante", "mariscos", "comida", "gastronomía", "cafetería", "típica"],
    "playa": ["playa", "surf", "mar", "costa"],
    "naturaleza": ["reserva", "ecológico", "cascada", "senderismo", "bosque"],
    "cultura": ["museo", "patrimonio", "artesanía", "arte", "cultura"],
    "deporte": ["surf", "ciclismo", "parapente", "deporte", "náutico"],
    "transporte": ["taxi", "bus", "transporte", "mototaxi"],
    "salud": ["hospital", "clínica", "médico", "salud"],
    "banco": ["banco", "cajero", "atm", "cooperativa"],
}

def interpretar_consulta(texto: str):
    texto_lower = texto.lower()
    categoria_detectada = ""
    canton_detectado = ""

    for categoria, palabras in PALABRAS_CLAVE.items():
        for palabra in palabras:
            if palabra in texto_lower:
                categoria_detectada = categoria
                break

    cantones_conocidos = [
        "bahía", "canoa", "pedernales", "jama", "san vicente",
        "chone", "tosagua", "sucre", "cojimíes", "charapotó"
    ]
    for c in cantones_conocidos:
        if c in texto_lower:
            canton_detectado = c
            break

    return categoria_detectada, canton_detectado
