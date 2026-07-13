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
        # Forzar UTF-8 explícitamente
        response.encoding = 'utf-8'
        df = pd.read_csv(StringIO(response.text), encoding='utf-8')
        df = df.dropna(how="all")
        # Limpiar nombres de columnas
        df.columns = [c.strip().replace('\ufeff', '') for c in df.columns]
        return df
    except Exception as e:
        print(f"Error cargando {nombre}: {e}")
        return pd.DataFrame()

def normalizar(texto):
    """Normaliza texto para búsqueda sin tildes"""
    if not texto:
        return ""
    reemplazos = {
        'á': 'a', 'é': 'e', 'í': 'i', 'ó': 'o', 'ú': 'u',
        'Á': 'A', 'É': 'E', 'Í': 'I', 'Ó': 'O', 'Ú': 'U',
        'ñ': 'n', 'Ñ': 'N'
    }
    for orig, repl in reemplazos.items():
        texto = texto.replace(orig, repl)
    return texto.lower()

def encontrar_columna(df, opciones):
    """Encuentra la primera columna que coincida con las opciones dadas"""
    cols_norm = {normalizar(c): c for c in df.columns}
    for op in opciones:
        op_norm = normalizar(op)
        if op_norm in cols_norm:
            return cols_norm[op_norm]
    return None

def buscar_lugares(consulta: str = "", canton: str = "", categoria: str = "", tags: str = ""):
    df = cargar_hoja("lugares")
    if df.empty:
        print("DataFrame vacío")
        return []

    print(f"Columnas disponibles: {list(df.columns)}")
    print(f"Total filas: {len(df)}")

    # Detectar columnas con normalización
    col_nombre = encontrar_columna(df, ["Nombre", "Nombre Lugar", "Nombre Comercial"])
    col_desc = encontrar_columna(df, ["Descripción", "Descripcion", "Descripción corta", "Descripcion corta"])
    col_canton = encontrar_columna(df, ["Cantón", "Canton"])
    col_categoria = encontrar_columna(df, ["Categoría", "Categoria"])
    col_subcategoria = encontrar_columna(df, ["Subcategoría", "Subcategoria"])
    col_parroquia = encontrar_columna(df, ["Parroquia"])
    col_tags = encontrar_columna(df, ["Tags", "Tags IA", "Tags_IA"])
    col_estado = encontrar_columna(df, ["Estado", "Estado Verificación", "Estado Verificacion"])
    col_tel = encontrar_columna(df, ["Teléfono", "Telefono", "Teléfono Principal", "Telefono Principal"])
    col_horario = encontrar_columna(df, ["Horario"])
    col_precio = encontrar_columna(df, ["Precio", "Rango de precios"])
    col_wa = encontrar_columna(df, ["WhatsApp"])

    print(f"canton col: {col_canton}, nombre col: {col_nombre}, desc col: {col_desc}")

    # Filtrar por cantón (también busca en parroquia)
    if canton:
        canton_norm = normalizar(canton)
        mask_canton = pd.Series([False] * len(df))
        for col in [col_canton, col_parroquia]:
            if col:
                mask_canton = mask_canton | df[col].astype(str).apply(normalizar).str.contains(canton_norm, na=False)
        df = df[mask_canton]
        print(f"Después de filtro canton '{canton}': {len(df)} filas")

    # Filtrar por categoría
    if categoria:
        cat_norm = normalizar(categoria)
        mask_cat = pd.Series([False] * len(df))
        for col in [col_categoria, col_subcategoria]:
            if col:
                mask_cat = mask_cat | df[col].astype(str).apply(normalizar).str.contains(cat_norm, na=False)
        df = df[mask_cat]
        print(f"Después de filtro categoria '{categoria}': {len(df)} filas")

    # Búsqueda por texto libre
    if consulta:
        consulta_norm = normalizar(consulta)
        mask = pd.Series([False] * len(df))
        for col in [col_nombre, col_desc, col_subcategoria, col_parroquia, col_canton, col_tags, col_categoria]:
            if col:
                mask = mask | df[col].astype(str).apply(normalizar).str.contains(consulta_norm, na=False)
        df = df[mask]
        print(f"Después de búsqueda '{consulta}': {len(df)} filas")

    # Construir resultado normalizado
    result = []
    for _, row in df.head(20).iterrows():
        item = {
            "Nombre": str(row.get(col_nombre, "") or "") if col_nombre else "",
            "Categoría": str(row.get(col_categoria, "") or "") if col_categoria else "",
            "Subcategoría": str(row.get(col_subcategoria, "") or "") if col_subcategoria else "",
            "Cantón": str(row.get(col_canton, "") or "") if col_canton else "",
            "Parroquia": str(row.get(col_parroquia, "") or "") if col_parroquia else "",
            "Descripción": str(row.get(col_desc, "") or "") if col_desc else "",
            "Teléfono": str(row.get(col_tel, "") or "") if col_tel else "",
            "WhatsApp": str(row.get(col_wa, "") or "") if col_wa else "",
            "Horario": str(row.get(col_horario, "") or "") if col_horario else "",
            "Precio": str(row.get(col_precio, "") or "") if col_precio else "",
            "Tags": str(row.get(col_tags, "") or "") if col_tags else "",
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
        canton_norm = normalizar(canton)
        df = df[df[col_canton].astype(str).apply(normalizar).str.contains(canton_norm, na=False)]
    if categoria and col_categoria:
        cat_norm = normalizar(categoria)
        df = df[df[col_categoria].astype(str).apply(normalizar).str.contains(cat_norm, na=False)]

    result = []
    for _, row in df.head(10).iterrows():
        item = {
            "Nombre": str(row.get(col_nombre, "") or "") if col_nombre else "",
            "Categoría": str(row.get(col_categoria, "") or "") if col_categoria else "",
            "Cantón": str(row.get(col_canton, "") or "") if col_canton else "",
            "Fecha Inicio": str(row.get(col_fecha, "") or "") if col_fecha else "",
            "Descripción": str(row.get(col_desc, "") or "") if col_desc else "",
            "Organizador": str(row.get(col_org, "") or "") if col_org else "",
        }
        result.append(item)
    return result

def obtener_cantones():
    df = cargar_hoja("cantones")
    if df.empty:
        return []
    return df.fillna("").to_dict(orient="records")

PALABRAS_CLAVE = {
    "alojamiento": ["hotel", "hostal", "cabaña", "glamping", "hostería", "alojamiento", "camping", "hospedaje", "lodge"],
    "restaurante": ["restaurante", "mariscos", "comida", "gastronomía", "cafetería", "típica", "ceviche", "bar", "comer"],
    "playa": ["playa", "surf", "mar", "costa", "malecón", "balneario"],
    "naturaleza": ["reserva", "ecológico", "cascada", "senderismo", "bosque", "manglar", "naturaleza"],
    "cultura": ["museo", "patrimonio", "artesanía", "arte", "cultura", "iglesia", "parque"],
    "deporte": ["surf", "ciclismo", "parapente", "deporte", "náutico", "pesca", "kayak", "aventura"],
    "salud": ["hospital", "clínica", "médico", "salud", "bomberos", "farmacia"],
    "banco": ["banco", "cajero", "atm", "cooperativa"],
    "agencia": ["agencia", "tour", "operadora", "viajes"],
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
        "bahia", "canoa", "pedernales", "jama", "san vicente",
        "chone", "tosagua", "sucre", "cojimies", "charapoto",
        "leonidas", "san isidro"
    ]
    for c in cantones_conocidos:
        if c in texto_norm:
            canton_detectado = c
            break

    return categoria_detectada, canton_detectado
