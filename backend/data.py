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
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        df = pd.read_csv(StringIO(response.content.decode('utf-8')))
        df = df.dropna(how="all")
        df.columns = df.columns.str.strip()
        return df
    except Exception as e:
        print(f"Error cargando {nombre}: {e}")
        return pd.DataFrame()

def buscar_lugares(consulta: str = "", canton: str = "", categoria: str = "", tags: str = ""):
    df = cargar_hoja("lugares")
    if df.empty:
        return []

    # Columna nombre puede llamarse Nombre o Nombre Lugar
    col_nombre = "Nombre" if "Nombre" in df.columns else "Nombre Lugar" if "Nombre Lugar" in df.columns else None
    col_desc = "Descripción" if "Descripción" in df.columns else "Descripción corta" if "Descripción corta" in df.columns else None
    col_canton = "Cantón" if "Cantón" in df.columns else "Canton" if "Canton" in df.columns else None
    col_categoria = "Categoría" if "Categoría" in df.columns else "Categoria" if "Categoria" in df.columns else None
    col_tags = "Tags" if "Tags" in df.columns else "Tags IA" if "Tags IA" in df.columns else None
    col_parroquia = "Parroquia" if "Parroquia" in df.columns else None
    col_subcategoria = "Subcategoría" if "Subcategoría" in df.columns else "Subcategoria" if "Subcategoria" in df.columns else None
    col_estado = "Estado" if "Estado" in df.columns else None

    if col_estado and col_estado in df.columns:
        df = df[df[col_estado].astype(str).str.lower().str.strip().isin(["activo", "verificado", "pendiente"])]

    if canton and col_canton:
        df = df[df[col_canton].astype(str).str.lower().str.contains(canton.lower(), na=False)]
    if categoria and col_categoria:
        df = df[df[col_categoria].astype(str).str.lower().str.contains(categoria.lower(), na=False)]
    if tags and col_tags:
        df = df[df[col_tags].astype(str).str.lower().str.contains(tags.lower(), na=False)]

    if consulta:
        masks = []
        for col in [col_nombre, col_desc, col_subcategoria, col_parroquia, col_canton, col_tags, col_categoria]:
            if col and col in df.columns:
                masks.append(df[col].astype(str).str.lower().str.contains(consulta.lower(), na=False))
        if masks:
            mask_final = masks[0]
            for m in masks[1:]:
                mask_final = mask_final | m
            df = df[mask_final]

    # Normalizar nombres de columnas para la respuesta
    result = []
    for _, row in df.head(20).iterrows():
        item = {
            "Nombre": str(row.get(col_nombre, "") or row.get("Nombre Lugar", "") or ""),
            "Categoría": str(row.get(col_categoria, "") or ""),
            "Subcategoría": str(row.get(col_subcategoria, "") or ""),
            "Cantón": str(row.get(col_canton, "") or ""),
            "Parroquia": str(row.get(col_parroquia, "") or ""),
            "Descripción": str(row.get(col_desc, "") or row.get("Descripción corta", "") or ""),
            "Teléfono": str(row.get("Teléfono", "") or row.get("Teléfono Principal", "") or ""),
            "WhatsApp": str(row.get("WhatsApp", "") or ""),
            "Horario": str(row.get("Horario", "") or ""),
            "Precio": str(row.get("Precio", "") or row.get("Rango de precios", "") or ""),
            "Tags": str(row.get(col_tags, "") or ""),
            "Estado": str(row.get(col_estado, "") or "Activo"),
        }
        result.append(item)
    return result

def buscar_eventos(canton: str = "", categoria: str = ""):
    df = cargar_hoja("eventos")
    if df.empty:
        return []

    col_canton = "Cantón" if "Cantón" in df.columns else "Canton" if "Canton" in df.columns else None
    col_categoria = "Categoría" if "Categoría" in df.columns else "Categoria" if "Categoria" in df.columns else None
    col_estado = "Estado" if "Estado" in df.columns else None

    if canton and col_canton:
        df = df[df[col_canton].astype(str).str.lower().str.contains(canton.lower(), na=False)]
    if categoria and col_categoria:
        df = df[df[col_categoria].astype(str).str.lower().str.contains(categoria.lower(), na=False)]

    result = []
    for _, row in df.head(10).iterrows():
        col_nombre = "Nombre" if "Nombre" in df.columns else "Nombre Evento o Actividad" if "Nombre Evento o Actividad" in df.columns else None
        item = {
            "Nombre": str(row.get(col_nombre or "Nombre", "") or ""),
            "Categoría": str(row.get(col_categoria or "Categoría", "") or ""),
            "Cantón": str(row.get(col_canton or "Cantón", "") or ""),
            "Fecha Inicio": str(row.get("Fecha Inicio", "") or row.get("Fecha_Inicio", "") or ""),
            "Descripción": str(row.get("Descripción", "") or row.get("Descripción corta", "") or ""),
            "Organizador": str(row.get("Organizador", "") or row.get("Entidad o Persona organizadora", "") or ""),
        }
        result.append(item)
    return result

def obtener_cantones():
    df = cargar_hoja("cantones")
    if df.empty:
        return []
    return df.fillna("").to_dict(orient="records")

PALABRAS_CLAVE = {
    "alojamiento": ["hotel", "hostal", "cabaña", "glamping", "hostería", "alojamiento", "camping", "hospedaje", "lodge", "ecohotel"],
    "restaurante": ["restaurante", "mariscos", "comida", "gastronomía", "cafetería", "típica", "ceviche", "bar", "comer", "food", "soda"],
    "playa": ["playa", "surf", "mar", "costa", "malecón", "balneario"],
    "naturaleza": ["reserva", "ecológico", "cascada", "senderismo", "bosque", "manglar", "naturaleza", "ecoturismo"],
    "cultura": ["museo", "patrimonio", "artesanía", "arte", "cultura", "iglesia", "parque", "monumento"],
    "deporte": ["surf", "ciclismo", "parapente", "deporte", "náutico", "pesca", "kayak", "aventura"],
    "transporte": ["taxi", "bus", "transporte", "mototaxi", "cooperativa transporte"],
    "salud": ["hospital", "clínica", "médico", "salud", "bomberos", "farmacia", "dispensario"],
    "banco": ["banco", "cajero", "atm", "cooperativa", "financiero"],
    "agencia": ["agencia", "tour", "operadora", "viajes", "turismo"],
    "servicios": ["servicio", "público", "municipio", "gobierno", "gasolinera", "ferretería"],
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
        if categoria_detectada:
            break

    cantones_conocidos = [
        "bahía", "bahia", "canoa", "pedernales", "jama", "san vicente",
        "chone", "tosagua", "sucre", "cojimíes", "cojimies", "charapotó",
        "charapoto", "leonidas", "san isidro"
    ]
    for c in cantones_conocidos:
        if c in texto_lower:
            canton_detectado = c
            break

    return categoria_detectada, canton_detectado
