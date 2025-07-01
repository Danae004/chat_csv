import re
from io import StringIO

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
</style>
""", unsafe_allow_html=True)

# Cliente Groq
@st.cache_resource
def get_groq_client():
    try:
        return Groq(api_key=st.secrets["GROQ_API_KEY"])
    except:
        return None

def sanitize_csv_content(content: str) -> str:
    """Limpia el contenido CSV de posibles inyecciones"""
    # Elimina fórmulas de Excel/Google Sheets
    sanitized = re.sub(r'^=[\+\-]?[A-Z]+\(.*\)', '', content, flags=re.MULTILINE | re.IGNORECASE)
    
    # Bloquea comandos de sistema
    if re.search(r'=(\!|\||CMD|POWERSHELL)', sanitized, re.IGNORECASE):
        raise ValueError("El archivo contiene comandos potencialmente peligrosos")
    
    # Limita el tamaño del archivo (max 10MB)
    if len(content) > 10 * 1024 * 1024:  # 10MB
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
        for col in df.columns:
            try:
                # Intentar convertir a numérico
                df[col] = pd.to_numeric(df[col], errors='raise')
                numeric_cols.append(col)
            except:
                # Si falla, verificar si es fecha
                try:
                    df[col] = pd.to_datetime(df[col], errors='raise')
                except:
                    # Mantener como texto si no se puede convertir
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



def main():
    st.title("📊 Analizador CSV v2")
    st.markdown("""
    <div class='security-alert'>
        🔒 <strong>Versión segura:</strong> Ahora con protección contra inyecciones CSV y sanitización de datos.
    </div>
    """, unsafe_allow_html=True)
    
    groq_client = get_groq_client()
    
    uploaded_file = st.file_uploader("Sube tu archivo CSV", type=["csv"])
    
    if uploaded_file:
        # Mostrar advertencia de seguridad
        with st.expander("🔒 Verificación de seguridad", expanded=True):
            st.info("""
            **Nuevas protecciones activas:**
            - Bloqueo de fórmulas Excel peligrosas
            - Sanitización de HTML/JavaScript
            - Validación de tamaño de archivo (max 10MB)
            - Detección de comandos de sistema
            """)
        
        df, numeric_cols, text_cols, date_cols, price_cols = process_csv(uploaded_file)
        
        if df is not None:
            st.success(f"✅ Datos cargados de forma segura: {len(df)} registros, {len(df.columns)} columnas")
            
            with st.expander("🔍 Vista previa de datos (sanitizados)"):
                st.dataframe(df.head())
                st.write(f"**Columnas numéricas:** {', '.join(numeric_cols)}")
                st.write(f"**Columnas de texto:** {', '.join(text_cols)}")
                st.write(f"**Columnas de precio:** {', '.join(price_cols)}")
            
            question = st.text_input("Haz tu pregunta sobre los datos (Ej: '¿Cuál es la bebida con el nombre más largo?')")
            
            if question:
                # Primero intentar análisis local avanzado
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
                        except:
                            st.warning("No se pudo conectar con el servicio de IA")
                else:
                    st.warning("No se encontró respuesta automática. Reformula tu pregunta.")

if __name__ == "__main__":
    main()
