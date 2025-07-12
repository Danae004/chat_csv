import re
from io import StringIO
import os
import numpy as np
import pandas as pd
import streamlit as st
from bs4 import BeautifulSoup
from groq import Groq

# Configuración de la página
st.set_page_config(
    page_title="Analizador CSV v2",
    page_icon="📊",
    layout="wide"
)

# CSS mejorado
st.markdown("""
<style>
    .main { font-family: Arial, sans-serif; }
    .result-box {
        border: 1px solid #4CAF50;
        border-radius: 10px;
        padding: 15px;
        margin: 10px 0;
        background: #0B0B0CFF;
    }
    .highlight {
        color: #d32f2f;
        font-weight: bold;
    }
    .data-preview {
        font-size: 0.85em;
        margin-top: 10px;
    }
    .missing-data {
        color: #FF9800;
        font-weight: bold;
    }
    .security-alert {
        border-left: 4px solid #d32f2f;
        background-color: #131212FF;
        padding: 12px;
        margin: 10px 0;
    }
    .metric-card {
        background: #1E1E1E;
        border-radius: 8px;
        padding: 12px;
        margin: 8px 0;
        box-shadow: 0 1px 3px rgba(0,0,0,0.2);
    }
    .metric-title {
        color: #4CAF50;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# Cliente Groq
@st.cache_resource
def get_groq_client():
    try:
        api_key = os.getenv("GROQ_API_KEY") or st.secrets.get("GROQ_API_KEY")
        if api_key:
            return Groq(api_key=api_key)
        else:
            st.warning("No se encontró la API key de Groq. Por favor, configúrala.")
            return None
    except Exception as e:
        st.error(f"Error al crear cliente Groq: {str(e)}")
        return None


def sanitize_csv_content(content: str) -> str:
    """Limpia el contenido CSV de posibles inyecciones"""
    # Elimina fórmulas de Excel/Google Sheets
    sanitized = re.sub(r'^=[\+\-]?[A-Z]+\(.*\)', '', content, flags=re.MULTILINE | re.IGNORECASE)
    
    # Bloquea comandos de sistema
    if re.search(r'=(\!|\||CMD|POWERSHELL)', sanitized, re.IGNORECASE):
        raise ValueError("El archivo contiene comandos potencialmente peligrosos")
    
    # Limita el tamaño del archivo (max 10MB)
    if len(content) > 10 * 1024 * 1024:
        raise ValueError("El archivo excede el tamaño máximo permitido (10MB)")
    
    return sanitized

def safe_read_csv(uploaded_file):
    """Lee un archivo CSV de manera segura"""
    try:
        content = uploaded_file.getvalue().decode('utf-8')
        sanitized_content = sanitize_csv_content(content)
        
        # Validación adicional con pandas
        df = pd.read_csv(StringIO(sanitized_content), dtype=str)
        
        # Sanitizar columnas de texto
        text_cols = df.select_dtypes(include=['object']).columns
        for col in text_cols:
            df[col] = df[col].apply(lambda x: BeautifulSoup(str(x), "html.parser").get_text() if pd.notnull(x) else x)
            
        return df
    
    except Exception as e:
        st.error(f"Error de seguridad al leer el CSV: {str(e)}")
        return None

def process_csv(uploaded_file):
    try:
        # Leer el archivo con sanitización
        df = safe_read_csv(uploaded_file)
        if df is None:
            return None, [], [], [], []
        
        # Limpieza de nombres de columnas
        df.columns = [col.strip() for col in df.columns]
        
        # Convertir tipos de datos de forma segura
        numeric_cols = []
        date_cols = []
        date_formats = ['%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%Y%m%d']
        
        for col in df.columns:
            # Intentar convertir a numérico
            try:
                df[col] = pd.to_numeric(df[col], errors='raise')
                numeric_cols.append(col)
                continue
            except:
                pass
            
            # Intentar convertir a fecha con múltiples formatos
            for fmt in date_formats:
                try:
                    df[col] = pd.to_datetime(df[col], format=fmt, errors='raise')
                    date_cols.append(col)
                    break
                except:
                    pass
        
        # Detección de tipos de columnas
        numeric_cols = df.select_dtypes(include=np.number).columns.tolist()
        text_cols = df.select_dtypes(include=['object']).columns.tolist()
        date_cols = df.select_dtypes(include=['datetime']).columns.tolist()
        
        # Detección especial de precios
        price_cols = [col for col in numeric_cols 
                     if any(word in col.lower() for word in ['precio', 'costo', 'valor', 'mxn', 'usd'])]
        
        return df, numeric_cols, text_cols, date_cols, price_cols
    
    except Exception as e:
        st.error(f"Error al procesar CSV: {str(e)}")
        return None, [], [], [], []

def create_metric_card(title, value, extra_info=None):
    """Crea una tarjeta de métrica visual"""
    card = f"""
    <div class='metric-card'>
        <div class='metric-title'>{title}</div>
        <div class='highlight'>{value}</div>
    """
    if extra_info:
        card += f"""<div style='font-size:0.8em; color:#666; margin-top:5px;'>{extra_info}</div>"""
    card += "</div>"
    return card

def advanced_analysis(df, numeric_cols, text_cols, date_cols, price_cols, question):
    try:
        question_lower = question.lower()
        
        # 1. Análisis de texto (nombre más largo)
        if 'nombre más largo' in question_lower or 'más largo' in question_lower:
            if text_cols:
                text_col = text_cols[0]
                df['longitud'] = df[text_col].str.len()
                max_len = df['longitud'].max()
                result_row = df[df['longitud'] == max_len].iloc[0]
                
                metrics = [
                    create_metric_card("Nombre más largo", result_row[text_col]),
                    create_metric_card("Longitud", f"{max_len} caracteres")
                ]
                
                return f"""
                <div class='result-box'>
                    <h3>📏 {text_col} más largo</h3>
                    <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 15px;">
                        {''.join(metrics)}
                    </div>
                </div>
                """
        
        # 2. Análisis de calorías
        if 'calorías' in question_lower or 'calorias' in question_lower:
            calorie_col = next((col for col in numeric_cols if 'calor' in col.lower()), None)
            if calorie_col:
                if 'mayor' in question_lower or 'más alt' in question_lower:
                    max_val = df[calorie_col].max()
                    result_row = df[df[calorie_col] == max_val].iloc[0]
                    name_col = next((col for col in text_cols if 'nombre' in col.lower()), text_cols[0] if text_cols else '')
                    
                    metrics = [
                        create_metric_card("Producto", result_row[name_col] if name_col else 'N/A'),
                        create_metric_card("Calorías", max_val)
                    ]
                    
                    return f"""
                    <div class='result-box'>
                        <h3>🔥 Producto con más calorías</h3>
                        <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 15px;">
                            {''.join(metrics)}
                        </div>
                    </div>
                    """
        
        # 3. Datos faltantes
        if 'faltantes' in question_lower or 'missing' in question_lower or 'vacíos' in question_lower:
            missing = df.isnull().sum()
            missing = missing[missing > 0]
            if not missing.empty:
                missing_info = "<br>".join([f"{col}: {count}" for col, count in missing.items()])
                return f"""
                <div class='result-box'>
                    <h3>⚠️ Datos faltantes</h3>
                    <p class='missing-data'>{missing_info}</p>
                </div>
                """
            else:
                return """
                <div class='result-box'>
                    <h3>✅ No hay datos faltantes</h3>
                </div>
                """
        
        # 4. Análisis de precios (mayor/menor)
        if any(word in question_lower for word in ['precio', 'costo', 'valor']):
            price_col = price_cols[0] if price_cols else None
            if price_col:
                if 'mayor' in question_lower or 'más car' in question_lower:
                    max_val = df[price_col].max()
                    result_row = df[df[price_col] == max_val].iloc[0]
                    name_col = next((col for col in text_cols if 'nombre' in col.lower()), text_cols[0] if text_cols else '')
                    
                    metrics = [
                        create_metric_card("Producto", result_row[name_col] if name_col else 'N/A'),
                        create_metric_card("Precio", f"${max_val:,.2f}")
                    ]
                    
                    return f"""
                    <div class='result-box'>
                        <h3>💰 Producto más caro</h3>
                        <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 15px;">
                            {''.join(metrics)}
                        </div>
                    </div>
                    """
                elif 'menor' in question_lower or 'más barat' in question_lower:
                    min_val = df[price_col].min()
                    result_row = df[df[price_col] == min_val].iloc[0]
                    name_col = next((col for col in text_cols if 'nombre' in col.lower()), text_cols[0] if text_cols else '')
                    
                    metrics = [
                        create_metric_card("Producto", result_row[name_col] if name_col else 'N/A'),
                        create_metric_card("Precio", f"${min_val:,.2f}")
                    ]
                    
                    return f"""
                    <div class='result-box'>
                        <h3>💸 Producto más económico</h3>
                        <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 15px;">
                            {''.join(metrics)}
                        </div>
                    </div>
                    """
        
        return None
    
    except Exception as e:
        return f"<div class='result-box'>Error en análisis: {str(e)}</div>"

def main():
    st.title("📊 Analizador CSV v2")
    st.markdown("""
    <div class='security-alert'>
        🔒 <strong>Versión segura:</strong> Protección contra inyecciones CSV y sanitización de datos
    </div>
    """, unsafe_allow_html=True)
    
    groq_client = get_groq_client()
    
    uploaded_file = st.file_uploader("Sube tu archivo CSV", type=["csv"])
    
    if uploaded_file:
        with st.expander("🔒 Verificación de seguridad", expanded=True):
            st.info("""
            **Protecciones activas:**
            - Bloqueo de fórmulas peligrosas
            - Sanitización de HTML/JavaScript
            - Validación de tamaño (max 10MB)
            - Detección de comandos maliciosos
            """)
        
        df, numeric_cols, text_cols, date_cols, price_cols = process_csv(uploaded_file)
        
        if df is not None:
            st.success(f"✅ Datos cargados: {len(df)} registros, {len(df.columns)} columnas")
            
            with st.expander("🔍 Vista previa de datos", expanded=False):
                st.dataframe(df.head())
                
                cols = st.columns(3)
                with cols[0]:
                    st.metric("Columnas numéricas", len(numeric_cols))
                with cols[1]:
                    st.metric("Columnas de texto", len(text_cols))
                with cols[2]:
                    st.metric("Columnas de fecha", len(date_cols))
                
                if price_cols:
                    st.info(f"📌 Columnas de precio identificadas: {', '.join(price_cols)}")
            
            question = st.text_input("Haz tu pregunta sobre los datos (Ej: '¿Cuál es el producto más caro?')")
            
            if question:
                result = advanced_analysis(df, numeric_cols, text_cols, date_cols, price_cols, question)
                
                if result:
                    st.markdown(result, unsafe_allow_html=True)
                elif groq_client:
                    with st.spinner("Analizando con IA..."):
                        try:
                            sample = df.head(3).to_dict('records')
                            
                            response = groq_client.chat.completions.create(
                                model="llama3-70b-8192",
                                messages=[{
                                    "role": "system",
                                    "content": f"""
                                    Eres un experto analista de datos. Analiza este dataset:
                                    - Columnas: {df.columns.tolist()}
                                    - Muestra: {sample}
                                    
                                    Responde en español con información precisa.
                                    Para precios usa formato: $XX.XX
                                    Para análisis de texto, verifica longitudes.
                                    Reporta datos faltantes si existen.
                                    """
                                }, {
                                    "role": "user",
                                    "content": question
                                }],
                                temperature=0.1
                            )
                            
                            st.markdown(f"<div class='result-box'>{response.choices[0].message.content}</div>", 
                                      unsafe_allow_html=True)
                        except Exception as e:
                            st.warning(f"No se pudo conectar con el servicio de IA: {str(e)}")
                else:
                    st.warning("No se encontró respuesta automática. Reformula tu pregunta o usa términos más específicos.")

if __name__ == "__main__":
    main()
