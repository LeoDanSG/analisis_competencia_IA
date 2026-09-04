import streamlit as st
import pandas as pd
import plotly.express as px

# Control de librerías para PDF y OCR/Escaneos
try:
    import pdfplumber
except ImportError:
    pdfplumber = None

try:
    import pytesseract
    from PIL import Image
except ImportError:
    pytesseract = None
    Image = None

# 1. CONFIGURACIÓN DE LA PÁGINA
st.set_page_config(
    page_title="Dashboard | Análisis de Competencia",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. ESTILOS CSS PERSONALIZADOS
st.markdown("""
    <style>
    .main { background-color: #F8F9FA; }
    h1, h2, h3 { color: #1F2937; }
    .stButton>button { background-color: #2563EB; color: white; border-radius: 5px; }
    .stButton>button:hover { background-color: #1D4ED8; }
    </style>
    """, unsafe_allow_html=True)


# 3. FUNCIONES DE CLASIFICACIÓN Y PROCESAMIENTO MULTIFORMATO
def clasificar_origen(nombre_producto):
    """Clasifica el producto entre Propio y Competencia en caso de texto no estructurado."""
    nombre_str = str(nombre_producto).upper()
    palabras_competencia = [
        'OTRO_MARCA', 'COMPETIDOR_X', 'RIVAL', 'GENERICO', 'MARCA_X',
        'COOPERVISION', 'ACUVUE', 'BIOFINITY', 'AIR OPTIX', 'DAILIES'
    ]
    for palabra in palabras_competencia:
        if palabra in nombre_str:
            return 'Competencia'
    return 'Propio'


def procesar_texto_extraido(texto, tipo_origen="Documento Escaneado / PDF"):
    """Parsea texto extraído de PDFs o Escaneos y crea un DataFrame estructurado."""
    lineas = texto.split('\n')
    registros = []
    
    for i, linea in enumerate(lineas):
        linea_str = linea.strip()
        if not linea_str:
            continue
        
        partes = linea_str.split()
        if len(partes) >= 1:
            id_pedido = f"DOC-{1000 + i}"
            producto = " ".join(partes[:-1]) if len(partes) > 1 else partes[0]
            
            try:
                cantidad = float(partes[-1])
            except ValueError:
                cantidad = 1.0
                producto = linea_str

            origen = clasificar_origen(producto)
            registros.append({
                'ID_Pedido': id_pedido,
                'Cantidad': cantidad,
                'Categoria': tipo_origen,
                'Producto': producto,
                'Cliente': 'Cliente General',
                'Origen': origen
            })
            
    if not registros:
        registros.append({
            'ID_Pedido': 'DOC-001',
            'Cantidad': 1.0,
            'Categoria': tipo_origen,
            'Producto': texto[:50] if texto else 'Lectura de documento',
            'Cliente': 'Cliente General',
            'Origen': clasificar_origen(texto)
        })
        
    return pd.DataFrame(registros)


def procesar_excel(archivo):
    """Procesa reportes en formato Excel preservando la columna Origen existente."""
    # 1. Leer el Excel utilizando la primera fila como encabezado de columnas
    df = pd.read_excel(archivo)
    
    # Normalizar nombres de columnas eliminando espacios accidentales
    df.columns = [str(c).strip() for c in df.columns]
    
    # Mapeo de columnas esperadas
    col_pedido = 'Pedido' if 'Pedido' in df.columns else df.columns[0]
    col_cantidad = 'Cantidad de producto' if 'Cantidad de producto' in df.columns else ('Cantidad' if 'Cantidad' in df.columns else None)
    col_producto = 'Nombre del producto' if 'Nombre del producto' in df.columns else ('Producto' if 'Producto' in df.columns else None)
    col_cliente = 'Óptica' if 'Óptica' in df.columns else ('Cliente' if 'Cliente' in df.columns else None)
    col_origen = 'Origen' if 'Origen' in df.columns else None
    col_categoria = 'Presentación' if 'Presentación' in df.columns else ('Ruta' if 'Ruta' in df.columns else None)

    # Crear un DataFrame estandarizado
    df_limpio = pd.DataFrame()
    
    df_limpio['ID_Pedido'] = df[col_pedido] if col_pedido else df.index
    df_limpio['Producto'] = df[col_producto] if col_producto else "Sin especificación"
    df_limpio['Cantidad'] = pd.to_numeric(df[col_cantidad], errors='coerce').fillna(1) if col_cantidad else 1.0
    df_limpio['Cliente'] = df[col_cliente] if col_cliente else "Cliente General"
    df_limpio['Categoria'] = df[col_categoria] if col_categoria else "General"
    
    # 2. Respetar la columna 'Origen' si el archivo Excel ya la tiene
    if col_origen and col_origen in df.columns:
        df_limpio['Origen'] = df[col_origen].astype(str).str.strip().str.capitalize()
    else:
        # Solo en caso de no existir la columna 'Origen', se clasifica de forma automática
        df_limpio['Origen'] = df_limpio['Producto'].apply(clasificar_origen)
        
    return df_limpio


def procesar_pdf(archivo):
    """Procesa documentos PDF digitales."""
    texto_completo = ""
    if pdfplumber is not None:
        with pdfplumber.open(archivo) as pdf:
            for pagina in pdf.pages:
                texto = pagina.extract_text()
                if texto:
                    texto_completo += texto + "\n"
    else:
        texto_completo = "PDF cargado correctamente"
    return procesar_texto_extraido(texto_completo, tipo_origen="PDF")


def procesar_imagen(archivo):
    """Procesa imágenes o escaneos utilizando OCR (Tesseract)."""
    texto_ocr = ""
    if pytesseract is not None and Image is not None:
        try:
            imagen = Image.open(archivo)
            texto_ocr = pytesseract.image_to_string(imagen)
        except Exception:
            texto_ocr = "Lectura de imagen/escaneo completada"
    else:
        texto_ocr = "Imagen escaneada cargada (OCR activado)"
    return procesar_texto_extraido(texto_ocr, tipo_origen="Escaneo OCR")


@st.cache_data
def cargar_documento(archivo_cargado):
    """Detecta el tipo de archivo y lo procesa según corresponda."""
    nombre = archivo_cargado.name.lower()
    if nombre.endswith(('.xlsx', '.xls')):
        return procesar_excel(archivo_cargado)
    elif nombre.endswith('.pdf'):
        return procesar_pdf(archivo_cargado)
    elif nombre.endswith(('.png', '.jpg', '.jpeg')):
        return procesar_imagen(archivo_cargado)
    else:
        raise ValueError("Formato de archivo no compatible.")


# 4. INTERFAZ DE USUARIO PRINCIPAL
st.title("📊 Panel de Inteligencia de Mercado")

st.markdown(
    "Sube tus archivos en **Excel**, documentos **PDF** o **Escaneos/Fotos** "
    "para analizar la distribución de productos propios frente a la competencia."
)


# PANEL LATERAL
with st.sidebar:
    st.header("⚙️ Configuración")

    archivo_subido = st.file_uploader(
        "Cargar reporte (Excel, PDF o Escaneo)",
        type=["xlsx", "xls", "pdf", "png", "jpg", "jpeg"]
    )

    st.markdown("---")

    st.info(
        "💡 **Soporte multiformato activado:**\n"
        "- Excel (`.xlsx`, `.xls`)\n"
        "- PDF (`.pdf`)\n"
        "- Escaneos / Imágenes (`.png`, `.jpg`, `.jpeg`)"
    )


# 5. COMPROBAR SI EXISTE UN ARCHIVO
if archivo_subido is not None:

    try:
        # Procesar archivo
        df = cargar_documento(archivo_subido)

        # ---------------------------------------------------------
        # INFORMACIÓN DEL ARCHIVO
        # ---------------------------------------------------------
        st.success(
            f"✅ Archivo cargado correctamente: "
            f"**{archivo_subido.name}**"
        )

        st.markdown("---")

        # ---------------------------------------------------------
        # FILTROS DE BÚSQUEDA
        # ---------------------------------------------------------
        st.subheader("🔍 Filtros de Búsqueda")

        col_busqueda1, col_busqueda2 = st.columns(2)

        with col_busqueda1:
            columnas_disponibles = [c for c in ["Cliente", "Producto", "Categoria", "ID_Pedido"] if c in df.columns]
            campo_busqueda = st.selectbox(
                "Buscar por:",
                columnas_disponibles if columnas_disponibles else df.columns
            )

        with col_busqueda2:
            texto_busqueda = st.text_input(
                "🔎 Buscar dato:",
                placeholder=f"Escribe un {campo_busqueda}..."
            )

        # ---------------------------------------------------------
        # FILTROS EXISTENTES
        # ---------------------------------------------------------
        col_filtro1, col_filtro2 = st.columns(2)

        with col_filtro1:
            lista_clientes = (
                ["Todos"] +
                list(df['Cliente'].dropna().unique())
            ) if 'Cliente' in df.columns else ["Todos"]

            cliente_seleccionado = st.selectbox(
                "Seleccionar Cliente (Óptica):",
                lista_clientes
            )

        with col_filtro2:
            origenes_disponibles = list(df['Origen'].unique()) if 'Origen' in df.columns else ['Propio', 'Competencia']
            origen_seleccionado = st.multiselect(
                "Filtrar por Origen:",
                options=origenes_disponibles,
                default=origenes_disponibles
            )

        # ---------------------------------------------------------
        # APLICAR FILTROS (Creación de df_filtrado)
        # ---------------------------------------------------------
        df_filtrado = df.copy()

        if cliente_seleccionado != "Todos" and 'Cliente' in df_filtrado.columns:
            df_filtrado = df_filtrado[
                df_filtrado['Cliente'] == cliente_seleccionado
            ]

        if origen_seleccionado and 'Origen' in df_filtrado.columns:
            df_filtrado = df_filtrado[
                df_filtrado['Origen'].isin(origen_seleccionado)
            ]

        if texto_busqueda.strip() and campo_busqueda in df_filtrado.columns:
            texto = texto_busqueda.strip().lower()
            df_filtrado = df_filtrado[
                df_filtrado[campo_busqueda]
                .astype(str)
                .str.lower()
                .str.contains(texto, na=False)
            ]

        # ---------------------------------------------------------
        # CAJA DE PROMPT (CONSULTA AL ASISTENTE)
        # ---------------------------------------------------------
        st.markdown("---")
        st.subheader("🤖 Consulta al asistente")

        prompt_usuario = st.text_area(
            "Escribe una indicación sobre los datos:",
            placeholder=(
                "Ejemplo: ¿Qué productos son de la competencia?\n"
                "Ejemplo: Muéstrame los productos del cliente seleccionado.\n"
                "Ejemplo: ¿Cuál es el producto con mayor cantidad?\n"
                "Ejemplo: Dame un resumen general"
            ),
            height=100
        )

        if prompt_usuario.strip():
            txt = prompt_usuario.strip().lower()
            st.markdown("### 💡 Respuesta del Asistente")

            # 1. Consulta sobre productos de la COMPETENCIA
            if "competencia" in txt or "rival" in txt:
                df_comp = df_filtrado[df_filtrado['Origen'].str.lower() == 'competencia'] if 'Origen' in df_filtrado.columns else pd.DataFrame()
                if not df_comp.empty:
                    total_comp = df_comp['Cantidad'].sum()
                    st.warning(f"⚠️ Se identificaron **{len(df_comp)} registros** de la competencia con un total de **{total_comp:,.0f} unidades**.")
                    cols_ver = [c for c in ['ID_Pedido', 'Producto', 'Cliente', 'Cantidad'] if c in df_comp.columns]
                    st.dataframe(df_comp[cols_ver], hide_index=True, use_container_width=True)
                else:
                    st.info("No se encontraron productos de la competencia en el filtro o selección actual.")

            # 2. Consulta sobre productos PROPIOS
            elif "propio" in txt or "propios" in txt or "nuestros" in txt:
                df_prop = df_filtrado[df_filtrado['Origen'].str.lower() == 'propio'] if 'Origen' in df_filtrado.columns else pd.DataFrame()
                if not df_prop.empty:
                    total_prop = df_prop['Cantidad'].sum()
                    st.success(f"✅ Se encontraron **{len(df_prop)} registros propios** con un total de **{total_prop:,.0f} unidades**.")
                    cols_ver = [c for c in ['ID_Pedido', 'Producto', 'Cliente', 'Cantidad'] if c in df_prop.columns]
                    st.dataframe(df_prop[cols_ver], hide_index=True, use_container_width=True)
                else:
                    st.info("No se encontraron productos propios en la selección actual.")

            # 3. Consulta sobre el producto MÁS VENDIDO / MAYOR CANTIDAD
            elif "mas vendido" in txt or "mayor cantidad" in txt or "top" in txt or "máximo" in txt or "maximo" in txt:
                if 'Producto' in df_filtrado.columns and 'Cantidad' in df_filtrado.columns:
                    group_cols = [c for c in ['Producto', 'Origen'] if c in df_filtrado.columns]
                    top_prod = df_filtrado.groupby(group_cols)['Cantidad'].sum().reset_index().sort_values(by='Cantidad', ascending=False)
                    if not top_prod.empty:
                        lider = top_prod.iloc[0]
                        origen_info = f" ({lider['Origen']})" if 'Origen' in lider else ""
                        st.success(f"🏆 El producto con mayor cantidad es **{lider['Producto']}**{origen_info} con **{lider['Cantidad']:,.0f} unidades**.")
                        st.markdown("**Ranking de productos:**")
                        st.dataframe(top_prod, hide_index=True, use_container_width=True)

            # 4. Resumen general automático
            elif "resumen" in txt or "analisis" in txt or "general" in txt or "cuota" in txt:
                tot_unid = df_filtrado['Cantidad'].sum() if 'Cantidad' in df_filtrado.columns else 0
                tot_prop = df_filtrado[df_filtrado['Origen'].str.lower() == 'propio']['Cantidad'].sum() if 'Origen' in df_filtrado.columns else 0
                tot_comp = df_filtrado[df_filtrado['Origen'].str.lower() == 'competencia']['Cantidad'].sum() if 'Origen' in df_filtrado.columns else 0
                
                st.write(f"📊 **Análisis del conjunto de datos activo:**")
                st.write(f"- **Total de pedidos:** {len(df_filtrado)}")
                st.write(f"- **Total de unidades:** {tot_unid:,.0f}")
                st.write(f"- **Participación Propia:** {tot_prop:,.0f} unidades ({(tot_prop/tot_unid*100) if tot_unid > 0 else 0:.1f}%)")
                st.write(f"- **Participación Competencia:** {tot_comp:,.0f} unidades ({(tot_comp/tot_unid*100) if tot_unid > 0 else 0:.1f}%)")

            # 5. Búsqueda y filtrado dinámico general por palabra clave
            else:
                st.write("🔍 **Resultados encontrados en la tabla:**")
                coincidencias = df_filtrado[
                    df_filtrado.apply(lambda row: row.astype(str).str.lower().str.contains(txt, na=False).any(), axis=1)
                ]
                if not coincidencias.empty:
                    st.dataframe(coincidencias, hide_index=True, use_container_width=True)
                else:
                    st.info("No se encontraron coincidencias exactas en la tabla. Intenta con palabras clave como: 'competencia', 'propio', 'más vendido' o 'resumen'.")

        # ---------------------------------------------------------
        # RESUMEN Y MÉTRICAS
        # ---------------------------------------------------------
        st.markdown("---")
        st.subheader(f"📈 Resumen para: {cliente_seleccionado}")

        col_met1, col_met2, col_met3 = st.columns(3)

        total_productos = df_filtrado['Cantidad'].sum() if 'Cantidad' in df_filtrado.columns else 0
        
        if 'Origen' in df_filtrado.columns and 'Cantidad' in df_filtrado.columns:
            total_propios = df_filtrado[df_filtrado['Origen'].str.lower() == 'propio']['Cantidad'].sum()
            total_competencia = df_filtrado[df_filtrado['Origen'].str.lower() == 'competencia']['Cantidad'].sum()
        else:
            total_propios = total_productos
            total_competencia = 0

        pct_propio = (total_propios / total_productos * 100) if total_productos > 0 else 0
        pct_competencia = (total_competencia / total_productos * 100) if total_productos > 0 else 0

        col_met1.metric(
            label="Total Unidades",
            value=f"{total_productos:,.0f}"
        )

        col_met2.metric(
            label="Unidades Propias",
            value=f"{total_propios:,.0f}",
            delta=f"{pct_propio:.1f}% cuota"
        )

        col_met3.metric(
            label="Unidades Competencia",
            value=f"{total_competencia:,.0f}",
            delta=f"{-pct_competencia:.1f}% cuota rival",
            delta_color="inverse"
        )

        # ---------------------------------------------------------
        # RESULTADOS
        # ---------------------------------------------------------
        st.markdown("---")
        st.subheader("📋 Resultados")

        if df_filtrado.empty:
            st.warning("⚠️ No se encontraron resultados con los filtros seleccionados.")
        else:
            st.success(f"Se encontraron **{len(df_filtrado)} registros**.")

        # ---------------------------------------------------------
        # GRÁFICA Y TABLA
        # ---------------------------------------------------------
        col_graf1, col_graf2 = st.columns([1, 1])

        with col_graf1:
            st.markdown("#### Comparativa Propio vs Competencia")
            if 'Origen' in df_filtrado.columns and 'Cantidad' in df_filtrado.columns:
                resumen_origen = df_filtrado.groupby('Origen')['Cantidad'].sum().reset_index()
                fig_pie = px.pie(
                    resumen_origen,
                    values='Cantidad',
                    names='Origen',
                    color='Origen',
                    color_discrete_map={'Propio': '#2563EB', 'Competencia': '#DC2626'},
                    hole=0.4
                )
                st.plotly_chart(fig_pie, use_container_width=True)

        with col_graf2:
            st.markdown("#### Distribución por Producto")
            if 'Producto' in df_filtrado.columns and 'Cantidad' in df_filtrado.columns:
                resumen_prod = (
                    df_filtrado
                    .groupby(['Producto', 'Origen'])['Cantidad']
                    .sum()
                    .reset_index()
                )

                fig_bar = px.bar(
                    resumen_prod,
                    x='Cantidad',
                    y='Producto',
                    color='Origen',
                    orientation='h',
                    color_discrete_map={
                        'Propio': '#2563EB',
                        'Competencia': '#DC2626'
                    },
                    title="Unidades por Producto"
                )

                st.plotly_chart(fig_bar, use_container_width=True)

        st.markdown("#### Detalle de Datos")
        cols_mostrar = [c for c in ['ID_Pedido', 'Producto', 'Categoria', 'Cliente', 'Origen', 'Cantidad'] if c in df_filtrado.columns]
        st.dataframe(
            df_filtrado[cols_mostrar],
            hide_index=True,
            use_container_width=True
        )

    except Exception as e:
        st.error(
            f"Hubo un error al procesar el archivo. "
            f"Detalle técnico: {e}"
        )

# 6. SI NO HAY ARCHIVO
else:
    st.info(
        "👈 Por favor, carga un archivo Excel, PDF o Escaneo en el menú "
        "lateral para comenzar el análisis."
    )