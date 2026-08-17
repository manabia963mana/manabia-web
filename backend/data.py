import pandas as pd
import requests
import time
from io import StringIO

SHEETS = {
    "lugares": "https://docs.google.com/spreadsheets/d/e/2PACX-1vSyU7JFnYAE1WvoH1HGbwOzIQyjkdFJrzuGQ0T0xHxh3iqtYpOHXmH1vj5Casg3oxWZEL8OBSFFPSUd/pub?gid=662364550&single=true&output=csv",
    "eventos": "https://docs.google.com/spreadsheets/d/e/2PACX-1vSyU7JFnYAE1WvoH1HGbwOzIQyjkdFJrzuGQ0T0xHxh3iqtYpOHXmH1vj5Casg3oxWZEL8OBSFFPSUd/pub?gid=702277477&single=true&output=csv",
    "cantones": "https://docs.google.com/spreadsheets/d/e/2PACX-1vSyU7JFnYAE1WvoH1HGbwOzIQyjkdFJrzuGQ0T0xHxh3iqtYpOHXmH1vj5Casg3oxWZEL8OBSFFPSUd/pub?gid=0&single=true&output=csv",
    "comunidad": "https://docs.google.com/spreadsheets/d/e/2PACX-1vTlaKpITkeXMq49lTCZ07fbnHL3WYAP7oacsSrWrxTCKsk4GgZPWVjL6dq_m_nK5JYW8nwDYZIf6qlc/pub?gid=32821269&single=true&output=csv"
}

# Caché en memoria: evita releer todo el Sheet en cada visita si ya se leyó hace
# poco. TTL corto (90s) para que los cambios en el Sheet sigan reflejándose casi
# en vivo, pero sin pedirle a Google los mismos datos una y otra vez en segundos.
_CACHE = {}
_CACHE_TTL_SEGUNDOS = 90

def cargar_hoja(nombre):
    ahora = time.time()
    if nombre in _CACHE:
        df_cacheado, guardado_en = _CACHE[nombre]
        if ahora - guardado_en < _CACHE_TTL_SEGUNDOS:
            return df_cacheado
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
        _CACHE[nombre] = (df, ahora)
        return df
    except Exception as e:
        print(f"Error cargando {nombre}: {e}")
        # Si falla la lectura pero hay una versión en caché (aunque esté vencida),
        # mejor devolver esa que dejar la página sin datos por completo.
        if nombre in _CACHE:
            return _CACHE[nombre][0]
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

# Palabras clave frecuentes que Mana reconoce — se usan como diccionario de referencia
# para corregir errores de tipeo comunes (letras faltantes, cambiadas o de más).
PALABRAS_CONOCIDAS = {
    "como", "que", "donde", "cuando", "cual", "cuales", "quien", "porque",
    "hola", "gracias", "quiero", "necesito", "busco", "tener", "informacion",
    "llegar", "ballenas", "ballena", "clima", "temperatura", "rutas", "ruta",
    "seguridad", "hospedaje", "hotel", "restaurante", "restaurantes", "playa",
    "playas", "ceviche", "cultura", "deporte", "deportes", "naturaleza",
    "eventos", "evento", "pedernales", "jama", "canoa", "sanvicente",
    "bahia", "sucre", "chone", "caraquez", "familia", "pareja", "semana",
    "dias", "dia", "gastronomia", "turismo", "guia", "mapa",
}

def corregir_typos(texto: str) -> str:
    """Corrige errores de tipeo leves (1-2 letras de diferencia) comparando cada
    palabra contra el diccionario de palabras clave conocidas de Mana. Se excluyen
    palabras muy cortas de uso común (el, la, un, de...) para evitar falsos positivos."""
    import difflib
    if not texto:
        return texto
    STOPWORDS_CORTAS = {
        "el","la","los","las","un","una","de","en","y","o","a","mi","tu","su",
        "si","no","es","me","te","se","lo","le","del","al","con","por","para",
    }
    palabras = texto.split()
    corregidas = []
    for palabra in palabras:
        base = palabra.strip(".,;:!?¡¿")
        base_norm = normalizar(base)
        if len(base) >= 3 and base_norm not in STOPWORDS_CORTAS:
            coincidencia = difflib.get_close_matches(base_norm, PALABRAS_CONOCIDAS, n=1, cutoff=0.7)
            if coincidencia and coincidencia[0] != base_norm:
                corregidas.append(coincidencia[0])
                continue
        corregidas.append(palabra)
    return " ".join(corregidas)

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
    # Errores de fórmula rota de Google Sheets/Excel que no se le deben mostrar al usuario
    if s.upper() in ("#ERROR!", "#REF!", "#N/A", "#DIV/0!", "#VALUE!", "#NULL!", "#NAME?", "#NUM!"):
        return ""
    # Excel/Sheets a veces guarda columnas de texto que "parecen número" (teléfonos,
    # WhatsApp con código de país) como float, y al convertir a texto queda un ".0"
    # final falso (ej. "593990192915.0"). Si el resto son solo dígitos, se descarta.
    if s.endswith(".0") and s[:-2].replace("+", "").isdigit():
        s = s[:-2]
    return s

def limpiar_coordenada(valor, tipo="lat"):
    """Convierte una coordenada a float. Corrige automáticamente el error de captura
    más común en el Sheet: coordenadas guardadas sin separador decimal
    (ej. '-804239' en vez de '-80.4239'). Rango esperado para Norte de Manabí:
    latitud entre -2 y 2, longitud entre -82 y -75."""
    s = limpiar(valor)
    if not s:
        return None
    try:
        val = float(str(s).replace(",", "."))
    except (ValueError, TypeError):
        return None
    limite = 2 if tipo == "lat" else 90
    intentos = 0
    while abs(val) >= limite and intentos < 6:
        val /= 10
        intentos += 1
    # Si tras corregir sigue fuera de rango razonable, se descarta en vez de mandar un pin roto
    if tipo == "lng" and not (-82 <= val <= -75):
        return None
    if tipo == "lat" and not (-3 <= val <= 3):
        return None
    return val

def construir_whatsapp_link(numero: str):
    """Convierte un número de teléfono ecuatoriano en un link wa.me válido"""
    import re as _re
    if not numero:
        return None
    s = str(numero).strip()
    # Excel guarda números largos (ej. WhatsApp con código de país "593990192915")
    # como float, y al convertirlos a texto quedan como "593990192915.0" — ese ".0"
    # se debe descartar entero, no solo el punto, o se cuela un dígito falso al final.
    if s.endswith(".0"):
        s = s[:-2]
    digitos = _re.sub(r'\D', '', s)
    if not digitos or len(digitos) < 7:
        return None
    if digitos.startswith('0'):
        digitos = '593' + digitos[1:]
    elif not digitos.startswith('593'):
        digitos = '593' + digitos
    return f"https://wa.me/{digitos}"

def construir_maps_link(lat, lng, nombre="", parroquia="", canton="", direccion=""):
    """Link de Google Maps: usa coordenadas si existen; si no, busca por dirección real;
    si tampoco hay dirección, busca por nombre + ubicación como último recurso."""
    import urllib.parse
    if lat and lng:
        return f"https://www.google.com/maps/search/?api=1&query={lat},{lng}"
    if direccion:
        partes = [direccion, canton, "Ecuador"]
    else:
        partes = [nombre, parroquia, canton, "Ecuador"]
    partes = [p for p in partes if p]
    if not partes:
        return None
    query = urllib.parse.quote(" ".join(partes))
    return f"https://www.google.com/maps/search/?api=1&query={query}"

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
    col_lat = encontrar_columna(df, ["Latitud", "Lat"])
    col_lng = encontrar_columna(df, ["Longitud", "Lng", "Long"])
    col_direccion = encontrar_columna(df, ["Dirección", "Direccion"])
    col_ref_direccion = encontrar_columna(df, ["Referencia de Dirección", "Referencia de Direccion"])
    col_desc_larga = encontrar_columna(df, ["Descripción larga", "Descripcion larga"])
    col_email = encontrar_columna(df, ["Email", "Correo", "Correo Electrónico"])
    col_web = encontrar_columna(df, ["Sitio web", "Sitio Web", "Dirección Web", "Direccion Web"])
    col_fb = encontrar_columna(df, ["Facebook"])
    col_ig = encontrar_columna(df, ["Instagram"])
    col_tiktok = encontrar_columna(df, ["TikTok", "Tiktok"])
    col_pago = encontrar_columna(df, ["Métodos de pago", "Metodos de pago"])
    col_idiomas = encontrar_columna(df, ["Idiomas"])
    col_servicios = encontrar_columna(df, ["Servicios"])
    col_pet = encontrar_columna(df, ["Pet Friendly"])
    col_wifi = encontrar_columna(df, ["WiFi", "Wifi"])
    col_parking = encontrar_columna(df, ["Parking"])
    col_accesibilidad = encontrar_columna(df, ["Accesibilidad"])
    col_nivel = encontrar_columna(df, ["Nivel turístico", "Nivel turistico"])
    col_publico = encontrar_columna(df, ["Público objetivo", "Publico objetivo"])
    col_actividad = encontrar_columna(df, ["Actividad/Modalidad", "Actividad / Modalidad"])
    col_clasificacion = encontrar_columna(df, ["Clasificación", "Clasificacion"])
    col_ninos = encontrar_columna(df, ["Es para niños", "Es para ninos"])
    col_aforo = encontrar_columna(df, ["Aforo aproximado"])
    col_inscripcion = encontrar_columna(df, ["Requiere inscripción previa", "Requiere inscripcion previa"])

    print(f"Columnas detectadas -> canton:{col_canton}, categoria:{col_categoria}, nombre:{col_nombre}, parroquia:{col_parroquia}, lat:{col_lat}, lng:{col_lng}")

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

    # BÚSQUEDA LIBRE — exige que CADA palabra de la consulta aparezca en algún lugar
    # del registro (no la frase completa pegada), para tolerar frases naturales como
    # "quiero tener información de casa monteros"
    if consulta:
        palabras_consulta = [p for p in normalizar(consulta).split() if len(p) > 1]
        if palabras_consulta:
            columnas_busqueda = [c for c in [col_nombre, col_desc, col_subcategoria, col_parroquia, col_canton, col_tags, col_categoria] if c]
            if columnas_busqueda:
                def _texto_fila(fila):
                    # Cada valor se convierte a texto explícitamente; los vacíos (NaN) se
                    # tratan como cadena vacía en vez de dejar que astype(str) los mezcle
                    # con floats, que es lo que causaba que la búsqueda fallara en filas
                    # con campos incompletos.
                    valores = [str(v) if pd.notna(v) else "" for v in fila]
                    return normalizar(" ".join(valores))
                texto_fila = df[columnas_busqueda].apply(_texto_fila, axis=1)
                mask = texto_fila.apply(lambda t: all(p in t for p in palabras_consulta))
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
            "Lat": limpiar_coordenada(row.get(col_lat, ""), "lat") if col_lat else None,
            "Lng": limpiar_coordenada(row.get(col_lng, ""), "lng") if col_lng else None,
            "Dirección": limpiar(row.get(col_direccion, "")) if col_direccion else "",
            "Referencia de Dirección": limpiar(row.get(col_ref_direccion, "")) if col_ref_direccion else "",
            "Descripción larga": limpiar(row.get(col_desc_larga, "")) if col_desc_larga else "",
            "Email": limpiar(row.get(col_email, "")) if col_email else "",
            "Sitio web": limpiar(row.get(col_web, "")) if col_web else "",
            "Facebook": limpiar(row.get(col_fb, "")) if col_fb else "",
            "Instagram": limpiar(row.get(col_ig, "")) if col_ig else "",
            "TikTok": limpiar(row.get(col_tiktok, "")) if col_tiktok else "",
            "Métodos de pago": limpiar(row.get(col_pago, "")) if col_pago else "",
            "Idiomas": limpiar(row.get(col_idiomas, "")) if col_idiomas else "",
            "Servicios": limpiar(row.get(col_servicios, "")) if col_servicios else "",
            "Pet Friendly": limpiar(row.get(col_pet, "")) if col_pet else "",
            "WiFi": limpiar(row.get(col_wifi, "")) if col_wifi else "",
            "Parking": limpiar(row.get(col_parking, "")) if col_parking else "",
            "Accesibilidad": limpiar(row.get(col_accesibilidad, "")) if col_accesibilidad else "",
            "Nivel turístico": limpiar(row.get(col_nivel, "")) if col_nivel else "",
            "Público objetivo": limpiar(row.get(col_publico, "")) if col_publico else "",
            "Actividad/Modalidad": limpiar(row.get(col_actividad, "")) if col_actividad else "",
            "Clasificación": limpiar(row.get(col_clasificacion, "")) if col_clasificacion else "",
            "Es para niños": limpiar(row.get(col_ninos, "")) if col_ninos else "",
            "Aforo aproximado": limpiar(row.get(col_aforo, "")) if col_aforo else "",
            "Requiere inscripción previa": limpiar(row.get(col_inscripcion, "")) if col_inscripcion else "",
            # NOTA: a propósito NO se exponen aquí columnas de uso interno de la base
            # (Fecha actualización, Responsable datos, Fuente información, Slug,
            # Embeddings_Status, Prioridad_IA, Relacionado_Con, Score_Calidad_Datos,
            # Persona de contacto) — son metadata de gestión, no información para el público.
        }
        result.append(item)

    print(f"Resultado final: {len(result)} lugares")
    return result

MESES_ES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
    "julio": 7, "agosto": 8, "septiembre": 9, "setiembre": 9, "octubre": 10,
    "noviembre": 11, "diciembre": 12,
}

def construir_fecha_evento(fecha_raw, mes_raw):
    """Muchas fiestas patronales anuales solo tienen el día en 'Fecha Inicio' (ej. 7)
    y el mes en una columna aparte ('Agosto'), porque se repiten cada año. Sin esto,
    el frontend intenta convertir el número suelto en fecha y da resultados absurdos.
    Aquí se arma la fecha real de la próxima ocurrencia. Si ya viene una fecha completa
    (o es texto como 'Variable'), se deja tal cual."""
    import datetime as _dt
    if isinstance(fecha_raw, (_dt.datetime, _dt.date)):
        return fecha_raw.strftime("%Y-%m-%d")
    fecha_str = limpiar(fecha_raw)
    if not fecha_str:
        return fecha_str
    if "-" in fecha_str or "/" in fecha_str:
        return fecha_str
    if fecha_str.isdigit():
        dia = int(fecha_str)
        mes_num = MESES_ES.get(normalizar(limpiar(mes_raw)))
        if mes_num and 1 <= dia <= 31:
            hoy = _dt.date.today()
            for anio in (hoy.year, hoy.year + 1):
                try:
                    fecha_evento = _dt.date(anio, mes_num, dia)
                except ValueError:
                    continue
                if fecha_evento >= hoy:
                    return fecha_evento.strftime("%Y-%m-%d")
            try:
                return _dt.date(hoy.year, mes_num, dia).strftime("%Y-%m-%d")
            except ValueError:
                return fecha_str
    return fecha_str

def buscar_eventos(canton: str = "", categoria: str = ""):
    df = cargar_hoja("eventos")
    if df.empty:
        return []

    col_canton = encontrar_columna(df, ["Cantón", "Canton"])
    col_categoria = encontrar_columna(df, ["Categoría", "Categoria"])
    col_nombre = encontrar_columna(df, ["Nombre", "Nombre Evento o Actividad"])
    col_desc = encontrar_columna(df, ["Descripción", "Descripcion", "Descripción corta"])
    col_fecha = encontrar_columna(df, ["Fecha Inicio", "Fecha_Inicio"])
    col_mes = encontrar_columna(df, ["Mes"])
    col_org = encontrar_columna(df, ["Organizador", "Entidad o Persona organizadora"])
    col_horario = encontrar_columna(df, ["Horario"])
    col_tel = encontrar_columna(df, ["Teléfono", "Telefono"])
    col_wa = encontrar_columna(df, ["WhatsApp"])
    col_web = encontrar_columna(df, ["Sitio web", "Sitio Web", "Dirección Web", "Direccion Web"])
    col_precios = encontrar_columna(df, ["Precios", "Precio"])
    col_direccion = encontrar_columna(df, ["Dirección", "Direccion"])
    col_parroquia = encontrar_columna(df, ["Parroquia"])
    col_tiktok = encontrar_columna(df, ["TikTok", "Tiktok"])
    col_fb = encontrar_columna(df, ["Facebook"])
    col_ig = encontrar_columna(df, ["Instagram"])
    col_duracion = encontrar_columna(df, ["Duración aproximada", "Duracion aproximada"])
    col_publico = encontrar_columna(df, ["Público objetivo", "Publico objetivo", "Público Objetivo"])
    col_ninos = encontrar_columna(df, ["Es para niños", "Es para ninos"])
    col_aforo = encontrar_columna(df, ["Aforo aproximado"])
    col_descuento = encontrar_columna(df, ["Descuento mayores y niños", "Descuento para mayores y niños"])
    col_pago = encontrar_columna(df, ["Métodos de pago", "Metodos de pago"])
    col_frecuencia = encontrar_columna(df, ["Frecuencia"])

    if canton and col_canton:
        df = df[df[col_canton].astype(str).apply(normalizar).str.contains(normalizar(canton), na=False)]
    if categoria and col_categoria:
        df = df[df[col_categoria].astype(str).apply(normalizar).str.contains(normalizar(categoria), na=False)]

    result = []
    for _, row in df.iterrows():
        nombre = limpiar(row.get(col_nombre, "")) if col_nombre else ""
        if not nombre:
            continue
        item = {
            "Nombre": nombre,
            "Categoría": limpiar(row.get(col_categoria, "")) if col_categoria else "",
            "Cantón": limpiar(row.get(col_canton, "")) if col_canton else "",
            "Fecha Inicio": construir_fecha_evento(row.get(col_fecha, ""), row.get(col_mes, "") if col_mes else "") if col_fecha else "",
            "Descripción": limpiar(row.get(col_desc, "")) if col_desc else "",
            "Organizador": limpiar(row.get(col_org, "")) if col_org else "",
            "Horario": limpiar(row.get(col_horario, "")) if col_horario else "",
            "Teléfono": limpiar(row.get(col_tel, "")) if col_tel else "",
            "WhatsApp": limpiar(row.get(col_wa, "")) if col_wa else "",
            "Sitio web": limpiar(row.get(col_web, "")) if col_web else "",
            "Precios": limpiar(row.get(col_precios, "")) if col_precios else "",
            "Dirección": limpiar(row.get(col_direccion, "")) if col_direccion else "",
            "Parroquia": limpiar(row.get(col_parroquia, "")) if col_parroquia else "",
            "TikTok": limpiar(row.get(col_tiktok, "")) if col_tiktok else "",
            "Facebook": limpiar(row.get(col_fb, "")) if col_fb else "",
            "Instagram": limpiar(row.get(col_ig, "")) if col_ig else "",
            "Duración aproximada": limpiar(row.get(col_duracion, "")) if col_duracion else "",
            "Público objetivo": limpiar(row.get(col_publico, "")) if col_publico else "",
            "Es para niños": limpiar(row.get(col_ninos, "")) if col_ninos else "",
            "Aforo aproximado": limpiar(row.get(col_aforo, "")) if col_aforo else "",
            "Descuento mayores y niños": limpiar(row.get(col_descuento, "")) if col_descuento else "",
            "Métodos de pago": limpiar(row.get(col_pago, "")) if col_pago else "",
            "Frecuencia": limpiar(row.get(col_frecuencia, "")) if col_frecuencia else "",
        }
        result.append(item)
    return result

def obtener_cantones():
    df = cargar_hoja("cantones")
    if df.empty:
        return []
    return df.fillna("").to_dict(orient="records")

def obtener_comunidad():
    """Lee las respuestas del Google Form de Comunidad y devuelve solo las que
    el equipo de Manabía marcó manualmente como 'Aprobado' en la columna Estado."""
    df = cargar_hoja("comunidad")
    if df.empty:
        return []

    col_nombre = encontrar_columna(df, ["Tu nombre", "Nombre"])
    col_tipo = encontrar_columna(df, ["Tipo de publicación", "Tipo de publicacion", "Tipo"])
    col_mensaje = encontrar_columna(df, ["Tu mensaje", "Mensaje"])
    col_estado = encontrar_columna(df, ["Estado"])
    col_fecha = encontrar_columna(df, ["Marca temporal", "Fecha"])

    if not col_estado:
        return []

    df = df[df[col_estado].astype(str).apply(normalizar) == "aprobado"]

    result = []
    for _, row in df.tail(30).iloc[::-1].iterrows():
        nombre = limpiar(row.get(col_nombre, "")) if col_nombre else ""
        mensaje = limpiar(row.get(col_mensaje, "")) if col_mensaje else ""
        if not mensaje:
            continue
        result.append({
            "Nombre": nombre or "Anónimo",
            "Tipo": limpiar(row.get(col_tipo, "")) if col_tipo else "",
            "Mensaje": mensaje,
            "Fecha": limpiar(row.get(col_fecha, "")) if col_fecha else "",
        })
    return result

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
    "Guianza Turística": ["guia turistico", "guia turistica", "guianza", "tour guiado", "acompañante turistico"],
    "Organizadores De Eventos, Congresos Y Convenciones": ["organizador de eventos", "planificador de bodas", "organizacion de congresos", "convenciones", "organizador de bodas"],
    "Parques Temáticos Y Atracciones Estables": ["parque tematico", "parque de diversiones", "juegos mecanicos", "atracciones"],
}

def interpretar_consulta(texto: str):
    texto_norm = normalizar(texto)
    categoria_detectada = ""
    canton_detectado = ""

    # Palabras generales que activan búsqueda libre en la BD
    PALABRAS_GENERAL = ["hacer", "visitar", "ver", "conocer", "recomendar",
                        "lugares", "sitios", "atracciones", "que hay"]

    for categoria, palabras in PALABRAS_CLAVE.items():
        for palabra in palabras:
            if normalizar(palabra) in texto_norm:
                categoria_detectada = categoria
                break
        if categoria_detectada:
            break

    if not categoria_detectada:
        for p in PALABRAS_GENERAL:
            if normalizar(p) in texto_norm:
                categoria_detectada = "GENERAL"
                break

    # Aliases con variantes ortográficas comunes
    ALIAS_CANTONES = {
        "bahia de caraquez": "bahia de caraquez",
        "baia de caraquez": "bahia de caraquez",
        "san vicente": "san vicente",
        "sanvicente": "san vicente",
        "canoa": "canoa",
        "kanoa": "canoa",
        "pedernales": "pedernales",
        "pedernals": "pedernales",
        "pedernalez": "pedernales",
        "cojimies": "cojimies",
        "charapoto": "charapoto",
        "san isidro": "san isidro",
        "leonidas": "leonidas",
        "jama": "jama",
        "chone": "chone",
        "sucre": "sucre",
        "bahia": "bahia",
        "baia": "bahia",
        "santa rita": "santa rita",
        "canuto": "canuto",
        "el matal": "el matal",
        "don juan": "don juan",
        "tabuga": "tabuga",
        "briceno": "briceno",
        "san jacinto": "san jacinto",
        "san clemente": "san clemente",
        "chirije": "chirije",
        "la cabuya": "la cabuya",
        "atahualpa": "atahualpa",
        "cabo pasado": "cabo pasado",
    }

    for alias in sorted(ALIAS_CANTONES.keys(), key=len, reverse=True):
        if normalizar(alias) in texto_norm:
            canton_detectado = ALIAS_CANTONES[alias]
            break

    return categoria_detectada, canton_detectado
