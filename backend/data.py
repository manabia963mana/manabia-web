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
        # Limpiar nombres de columnas de BOM y espacios
        df.columns = [c.strip().replace('\ufeff', '').replace('\u00c3\u00b3', 'ó').replace('\u00c3\u00a9', 'é').replace('\u00c3\u00a1', 'á') for c in df.columns]
        print(f"Columnas en {nombre}: {list(df.columns[:8])}")
        return df
    except Exception as e:
        print(f"Error cargando {nombre}: {e}")
        return pd.DataFrame()

def normalizar(texto):
    if not texto:
        return ""
    texto = str(texto)
    reemplazos = {
        'á':'a','é':'e','í':'i','ó':'o','ú':'u',
        'Á':'A','É':'E','Í':'I','Ó':'O','Ú':'U',
        'ñ':'n','Ñ':'N',
        # Encodings rotos comunes
        'Ã¡':'a','Ã©':'e','Ã­':'i','Ã³':'o','Ãº':'u',
        'Ã±':'n','Ã':'',
    }
    for orig, repl in reemplazos.items():
        texto = texto.replace(orig, repl)
    return texto.lower().strip()

def encontrar_columna(df, opciones):
    """Encuentra columna por nombre, tolerante a tildes y encoding roto"""
    # Mapa normalizado de columnas reales
    cols_norm = {normalizar(c): c for c in df.columns}
    # También buscar por posición conocida si el nombre está roto
    for op in opciones:
        op_norm = normalizar(op)
        if op_norm in cols_norm:
            return cols_norm[op_norm]
    # Búsqueda parcial como último recurso
    for op in opciones:
        op_norm = normalizar(op)
        for col_norm, col_real in cols_norm.items():
            if op_norm in col_norm or col_norm in op_norm:
                return col_real
    return None

def limpiar(valor):
    if valor is None:
        return ""
    s = str(valor).strip()
    if s.lower() in ("nan", "none", "n/a", "-", ""):
        return ""
    return s

def buscar_lugares(consulta: str = "", canton: str = "", categoria: str = "", tags: str = ""):
    df = cargar_hoja("lugares")
    if df.empty:
        print("ERROR: DataFrame vacío")
        return []

    # Detectar columnas
    col_nombre = encontrar_columna(df, ["Nombre", "Nombre Lugar", "Nombre Comercial"])
    col_desc = encontrar_columna(df, ["Descripción", "Descripcion", "Descripción corta"])
    col_canton = encontrar_columna(df, ["Cantón", "Canton", "Canton "])
    col_categoria = encontrar_columna(df, ["Categoría", "Categoria"])
    col_subcategoria = encontrar_columna(df, ["Subcategoría", "Subcategoria"])
    col_parroquia = encontrar_columna(df, ["Parroquia"])
    col_tags = encontrar_columna(df, ["Tags", "Tags IA"])
    col_tel = encontrar_columna(df, ["Teléfono", "Telefono", "Teléfono Principal"])
    col_horario = encontrar_columna(df, ["Horario"])
    col_precio = encontrar_columna(df, ["Precio", "Rango de precios"])
    col_wa = encontrar_columna(df, ["WhatsApp"])

    print(f"Columnas detectadas -> canton:{col_canton}, categoria:{col_categoria}, nombre:{col_nombre}, parroquia:{col_parroquia}")

    # Eliminar filas sin nombre
    if col_nombre:
        df = df[df[col_nombre].astype(str).str.strip().notna()]
        df = df[df[col_nombre].astype(str).str.strip() != '']
        df = df[df[col_nombre].astype(str).str.lower().str.strip() != 'nan']

    # FILTRO CANTÓN: busca en cantón Y parroquia de forma independiente
    if canton and (col_canton or col_parroquia):
        canton_norm = normalizar(canton)
        mask = pd.Series([False] * len(df), index=df.index)
        if col_canton:
            mask = mask | df[col_canton].astype(str).apply(normalizar).str.contains(canton_norm, na=False)
        if col_parroquia:
            mask = mask | df[col_parroquia].astype(str).apply(normalizar).str.contains(canton_norm, na=False)
        df = df[mask]
        print(f"Después de filtro cantón '{canton}': {len(df)} filas")

    # FILTRO CATEGORÍA: busca en categoría Y subcategoría de forma independiente
    if categoria and (col_categoria or col_subcategoria):
        cat_norm = normalizar(categoria)
        mask = pd.Series([False] * len(df), index=df.index)
        if col_categoria:
            mask = mask | df[col_categoria].astype(str).apply(normalizar).str.contains(cat_norm, na=False)
        if col_subcategoria:
            mask = mask | df[col_subcategoria].astype(str).apply(normalizar).str.contains(cat_norm, na=False)
        df = df[mask]
        print(f"Después de filtro categoría '{categoria}': {len(df)} filas")

    # BÚSQUEDA LIBRE
    if consulta:
        consulta_norm = normalizar(consulta)
        mask = pd.Series([False] * len(df), index=df.index)
        for col in [col_nombre, col_desc, col_subcategoria, col_parroquia, col_canton, col_tags, col_categoria]:
            if col:
                mask = mask | df[col].astype(str).apply(normalizar).str.contains(consulta_norm, na=False)
        df = df[mask]
        print(f"Después de búsqueda libre '{consulta}': {len(df)} filas")

    result = []
    for _, row in df.head(20).iterrows():
        nombre = limpiar(row.get(col_nombre, "")) if col_nombre else ""
        if not nombre or nombre.lower() == 'nan':
            continue
        item = {
            "Nombre": nombre,
            "Categoría": limpiar(row.get(col_categoria, "")) if col_categoria else "",
            "Subcategoría": limpiar(row.get(col_subcategoria, "")) if col_subcategoria else "",
            "Cantón": limpiar(row.get(col_canton, "")) if col_canton else "",
            "Parroquia": limpiar(row.get(col_parroquia, "")) if col_parroquia else "",
            "Descripción": limpiar(row.get(col_desc, "")) if col_desc else "",
            "Teléfono": limpiar(row.get(col_tel, "")) if col_tel else "",
            "WhatsApp": limpiar(row.get(col_wa, "")) if col_wa else "",
            "Horario": limpiar(row.get(col_horario, "")) if col_horario else "",
            "Precio": limpiar(row.get(col_precio, "")) if col_precio else "",
            "Tags": limpiar(row.get(col_tags, "")) if col_tags else "",
        }
        result.append(item)

    print(f"Resultado final: {len(result)} lugares")
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
        nombre = limpiar(row.get(col_nombre, "")) if col_nombre else ""
        if not nombre:
            continue
        item = {
            "Nombre": nombre,
            "Categoría": limpiar(row.get(col_categoria, "")) if col_categoria else "",
            "Cantón": limpiar(row.get(col_canton, "")) if col_canton else "",
            "Fecha Inicio": limpiar(row.get(col_fecha, "")) if col_fecha else "",
            "Descripción": limpiar(row.get(col_desc, "")) if col_desc else "",
            "Organizador": limpiar(row.get(col_org, "")) if col_org else "",
        }
        result.append(item)
    return result

def obtener_cantones():
    df = cargar_hoja("cantones")
    if df.empty:
        return []
    return df.fillna("").to_dict(orient="records")

PALABRAS_CLAVE = {
    "Alojamiento": ["hotel", "hostal", "cabaña", "glamping", "hosteria", "alojamiento", "camping",
                    "hospedaje", "lodge", "resort", "refugio", "casa de huespedes", "hacienda",
                    "dormir", "quedarme", "hospedarme", "habitacion", "cuarto"],
    "Alimentos, Bebidas Y Entretenimiento": ["restaurante", "mariscos", "comida", "gastronomia",
                    "cafeteria", "tipica", "ceviche", "bar", "comer", "almorzar", "cenar",
                    "desayunar", "beber", "discoteca", "entretenimiento", "soda"],
    "Servicios Financieros": ["cajero", "atm", "banco", "cooperativa", "dinero", "efectivo",
                    "sacar dinero", "plata", "financiero", "credito", "debito"],
    "Salud": ["hospital", "clinica", "medico", "salud", "farmacia",
                    "dispensario", "dentista", "emergencia", "doctor", "enfermo"],
    "Movilidad Y Transporte": ["taxi", "mototaxi", "movilizarme",
                    "interprovincial", "terminal", "movilidad", "como llegar"],
    "Ecología Y Naturaleza": ["reserva", "ecologico", "cascada", "senderismo", "bosque",
                    "manglar", "naturaleza", "ecoturismo", "playa", "humedal",
                    "isla", "mirador", "rio", "area natural"],
    "Cultura y Patrimonio": ["museo", "patrimonio", "artesania", "arte", "cultura",
                    "iglesia", "arqueologico", "historia", "teatro", "biblioteca"],
    "Instalaciones Deportivas": ["surf", "deporte", "cancha", "estadio", "gimnasio",
                    "piscina", "tenis", "voley", "patinaje", "yoga", "fitness"],
    "Agenciamiento Turístico": ["agencia", "tour", "operadora", "viajes", "paquete", "excursion"],
    "Servicios Públicos": ["municipio", "gobierno", "policia", "tramite"],
    "Wellness": ["spa", "masaje", "relajacion", "wellness", "belleza"],
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

    ALIAS_CANTONES = {
        "bahia de caraquez": "sucre",
        "bahia": "sucre",
        "caraquez": "sucre",
        "canoa": "san vicente",
        "san vicente": "san vicente",
        "pedernales": "pedernales",
        "jama": "jama",
        "chone": "chone",
        "sucre": "sucre",
        "cojimies": "pedernales",
        "charapoto": "sucre",
        "san isidro": "sucre",
        "leonidas": "sucre",
    }

    # Buscar frases más largas primero para evitar matches parciales
    for alias in sorted(ALIAS_CANTONES.keys(), key=len, reverse=True):
        if alias in texto_norm:
            canton_detectado = ALIAS_CANTONES[alias]
            break

    return categoria_detectada, canton_detectado
