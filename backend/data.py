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
        response.encoding = 'utf-8'
        df = pd.read_csv(StringIO(response.text), encoding='utf-8')
        df = df.dropna(how="all")
        df.columns = [c.strip().replace('\ufeff', '') for c in df.columns]
        return df
    except Exception as e:
        print(f"Error cargando {nombre}: {e}")
        return pd.DataFrame()

def normalizar(texto):
    if not texto:
        return ""
    reemplazos = {
        'á':'a','é':'e','í':'i','ó':'o','ú':'u',
        'Á':'A','É':'E','Í':'I','Ó':'O','Ú':'U',
        'ñ':'n','Ñ':'N'
    }
    for orig, repl in reemplazos.items():
        texto = texto.replace(orig, repl)
    return texto.lower()

def encontrar_columna(df, opciones):
    cols_norm = {normalizar(c): c for c in df.columns}
    for op in opciones:
        op_norm = normalizar(op)
        if op_norm in cols_norm:
            return cols_norm[op_norm]
    return None

def limpiar(valor):
    """Limpia valores nan, None, vacíos"""
    if valor is None:
        return ""
    s = str(valor).strip()
    if s.lower() in ("nan", "none", "n/a", "-", ""):
        return ""
    return s

def buscar_lugares(consulta: str = "", canton: str = "", categoria: str = "", tags: str = ""):
    df = cargar_hoja("lugares")
    if df.empty:
        return []

    col_nombre = encontrar_columna(df, ["Nombre", "Nombre Lugar", "Nombre Comercial"])
    col_desc = encontrar_columna(df, ["Descripción", "Descripcion", "Descripción corta", "Descripcion corta"])
    col_canton = encontrar_columna(df, ["Cantón", "Canton"])
    col_categoria = encontrar_columna(df, ["Categoría", "Categoria"])
    col_subcategoria = encontrar_columna(df, ["Subcategoría", "Subcategoria"])
    col_parroquia = encontrar_columna(df, ["Parroquia"])
    col_tags = encontrar_columna(df, ["Tags", "Tags IA", "Tags_IA"])
    col_estado = encontrar_columna(df, ["Estado", "Estado Verificación", "Estado Verificacion"])
    col_tel = encontrar_columna(df, ["Teléfono", "Telefono", "Teléfono Principal"])
    col_horario = encontrar_columna(df, ["Horario"])
    col_precio = encontrar_columna(df, ["Precio", "Rango de precios"])
    col_wa = encontrar_columna(df, ["WhatsApp"])

    # Filtrar por cantón (busca en cantón Y parroquia, excluye Tosagua)
    if canton:
        canton_norm = normalizar(canton)
        mask = pd.Series([False] * len(df))
        for col in [col_canton, col_parroquia]:
            if col:
                mask = mask | df[col].astype(str).apply(normalizar).str.contains(canton_norm, na=False)
        df = df[mask]

    # Filtrar por categoría o subcategoría
    if categoria:
        cat_norm = normalizar(categoria)
        mask = pd.Series([False] * len(df))
        for col in [col_categoria, col_subcategoria]:
            if col:
                mask = mask | df[col].astype(str).apply(normalizar).str.contains(cat_norm, na=False)
        df = df[mask]

    # Búsqueda libre en todos los campos relevantes
    if consulta:
        consulta_norm = normalizar(consulta)
        mask = pd.Series([False] * len(df))
        for col in [col_nombre, col_desc, col_subcategoria, col_parroquia, col_canton, col_tags, col_categoria]:
            if col:
                mask = mask | df[col].astype(str).apply(normalizar).str.contains(consulta_norm, na=False)
        df = df[mask]

    result = []
    for _, row in df.head(20).iterrows():
        item = {
            "Nombre": limpiar(row.get(col_nombre, "")),
            "Categoría": limpiar(row.get(col_categoria, "")),
            "Subcategoría": limpiar(row.get(col_subcategoria, "")),
            "Cantón": limpiar(row.get(col_canton, "")),
            "Parroquia": limpiar(row.get(col_parroquia, "")),
            "Descripción": limpiar(row.get(col_desc, "")),
            "Teléfono": limpiar(row.get(col_tel, "")),
            "WhatsApp": limpiar(row.get(col_wa, "")),
            "Horario": limpiar(row.get(col_horario, "")),
            "Precio": limpiar(row.get(col_precio, "")),
            "Tags": limpiar(row.get(col_tags, "")),
        }
        if item["Nombre"]:
            result.append(item)
    return result

def buscar_eventos(canton: str = "", categoria: str = ""):
    df = cargar_hoja("eventos")
    if df.empty:
        return []

    col_canton = encontrar_columna(df, ["Cantón", "Canton"])
    col_categoria = encontrar_columna(df, ["Categoría", "Categoria"])
    col_nombre = encontrar_columna(df, ["Nombre", "Nombre Evento o Actividad"])
    col_desc = encontrar_columna(df, ["Descripción", "Descripcion", "Descripción corta"])
    col_fecha = encontrar_columna(df, ["Fecha Inicio", "Fecha_Inicio"])
    col_org = encontrar_columna(df, ["Organizador", "Entidad o Persona organizadora"])

    if canton and col_canton:
        df = df[df[col_canton].astype(str).apply(normalizar).str.contains(normalizar(canton), na=False)]
    if categoria and col_categoria:
        df = df[df[col_categoria].astype(str).apply(normalizar).str.contains(normalizar(categoria), na=False)]

    result = []
    for _, row in df.head(10).iterrows():
        item = {
            "Nombre": limpiar(row.get(col_nombre, "")),
            "Categoría": limpiar(row.get(col_categoria, "")),
            "Cantón": limpiar(row.get(col_canton, "")),
            "Fecha Inicio": limpiar(row.get(col_fecha, "")),
            "Descripción": limpiar(row.get(col_desc, "")),
            "Organizador": limpiar(row.get(col_org, "")),
        }
        if item["Nombre"]:
            result.append(item)
    return result

def obtener_cantones():
    df = cargar_hoja("cantones")
    if df.empty:
        return []
    return df.fillna("").to_dict(orient="records")

# Mapa completo de palabras clave basado en categorías REALES de la base de datos
PALABRAS_CLAVE = {
    # Alojamiento
    "Alojamiento": ["hotel", "hostal", "cabaña", "glamping", "hosteria", "alojamiento", "camping",
                    "hospedaje", "lodge", "resort", "refugio", "casa de huespedes", "hacienda",
                    "dormir", "quedarme", "hospedarme", "habitacion", "cuarto"],
    # Comida y bebida
    "Alimentos, Bebidas Y Entretenimiento": ["restaurante", "mariscos", "comida", "gastronomia",
                    "cafeteria", "tipica", "ceviche", "bar", "comer", "almorzar", "cenar",
                    "desayunar", "beber", "discoteca", "entretenimiento", "soda"],
    # Servicios financieros
    "Servicios Financieros": ["cajero", "atm", "banco", "cooperativa", "dinero", "efectivo",
                    "sacar dinero", "plata", "financiero", "credito", "debito"],
    # Salud
    "Salud": ["hospital", "clinica", "medico", "salud", "bomberos", "farmacia",
                    "dispensario", "dentista", "emergencia", "doctor", "enfermo"],
    # Transporte
    "Movilidad Y Transporte": ["taxi", "bus", "transporte", "mototaxi", "movilizarme",
                    "llegar", "interprovincial", "terminal", "movilidad"],
    # Naturaleza
    "Ecología Y Naturaleza": ["reserva", "ecologico", "cascada", "senderismo", "bosque",
                    "manglar", "naturaleza", "ecoturismo", "playa", "playa", "humedal",
                    "isla", "mirador", "rio", "area natural"],
    # Cultura
    "Cultura y Patrimonio": ["museo", "patrimonio", "artesania", "arte", "cultura",
                    "iglesia", "arqueologico", "historia", "teatro", "biblioteca"],
    # Deportes
    "Instalaciones Deportivas": ["surf", "deporte", "cancha", "estadio", "gimnasio",
                    "piscina", "tenis", "voley", "patinaje", "yoga", "fitness"],
    # Agencias
    "Agenciamiento Turístico": ["agencia", "tour", "operadora", "viajes", "paquete", "excursion"],
    # Servicios públicos
    "Servicios Públicos": ["municipio", "gobierno", "policia", "tramite", "publico"],
    # Wellness
    "Wellness": ["spa", "masaje", "relajacion", "wellness", "belleza"],
    # Educación
    "Educación Y Formación": ["universidad", "instituto", "idiomas", "curso", "educacion"],
}

def interpretar_consulta(texto: str):
    texto_norm = normalizar(texto)
    categoria_detectada = ""
    canton_detectado = ""

    for categoria, palabras in PALABRAS_CLAVE.items():
        for palabra in palabras:
            if normalizar(palabra) in texto_norm:
                categoria_detectada = categoria
                break
        if categoria_detectada:
            break

    cantones_conocidos = [
        "bahia", "caraquez", "canoa", "pedernales", "jama",
        "san vicente", "chone", "sucre", "cojimies", "charapoto",
        "leonidas", "san isidro", "norte de manabi", "manabi"
    ]
    for c in cantones_conocidos:
        if c in texto_norm:
            canton_detectado = c
            break

    return categoria_detectada, canton_detectado
