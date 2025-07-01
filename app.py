import numpy as np
import pandas as pd
import streamlit as st
from groq import Groq

# Configuración de la página
st.set_page_config(
    page_title="Analizador CSV Avanzado",
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
</style>
""", unsafe_allow_html=True)

# Cliente Groq
@st.cache_resource
def get_groq_client():
    try:
        return Groq(api_key=st.secrets["GROQ_API_KEY"])
    except:
        return None

def process_csv(uploaded_file):
    try:
        df = pd.read_csv(uploaded_file)
        df.columns = [col.strip() for col in df.columns]
        
        # Detección de tipos de columnas
        numeric_cols = df.select_dtypes(include=np.number).columns.tolist()
        text_cols = df.select_dtypes(include=['object']).columns.tolist()
        date_cols = df.select_dtypes(include=['datetime']).columns.tolist()
        
        # Detección especial de precios
        price_cols = [col for col in df.columns 
                     if any(word in col.lower() for word in ['precio', 'costo', 'valor', 'mxn', 'usd'])]
        
        return df, numeric_cols, text_cols, date_cols, price_cols
    
    except Exception as e:
        st.error(f"Error al procesar CSV: {str(e)}")
        return None, [], [], [], []

def advanced_analysis(df, numeric_cols, text_cols, date_cols, price_cols, question):
    try:
        question_lower = question.lower()
        
        # 1. Análisis de texto (nombre más largo)
        if 'nombre más largo' in question_lower or 'más largo' in question_lower:
            if text_cols:
                text_col = text_cols[0]  # Usamos la primera columna de texto
                df['longitud'] = df[text_col].str.len()
                max_len = df['longitud'].max()
                result_row = df[df['longitud'] == max_len].iloc[0]
                return f"""
                <div class='result-box'>
                    <h3>📏 {text_col} más largo:</h3>
                    <p><b>Nombre:</b> {result_row[text_col]}</p>
                    <p><b>Longitud:</b> {max_len} caracteres</p>
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
                    return f"""
                    <div class='result-box'>
                        <h3>🔥 Bebida/comida con más calorías:</h3>
                        <p><b>Nombre:</b> {result_row[name_col] if name_col else 'N/A'}</p>
                        <p class='highlight'><b>Calorías:</b> {max_val}</p>
                    </div>
                    """
        
        # 3. Datos faltantes
        if 'faltantes' in question_lower or 'missing' in question_lower or 'vacíos' in question_lower:
            missing = df.isnull().sum()
            missing = missing[missing > 0]
            if not missing.empty:
                return f"""
                <div class='result-box'>
                    <h3>⚠️ Datos faltantes:</h3>
                    <p class='missing-data'>{missing.to_string()}</p>
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
                    return f"""
                    <div class='result-box'>
                        <h3>💰 {name_col} más caro:</h3>
                        <p><b>Nombre:</b> {result_row[name_col] if name_col else 'N/A'}</p>
                        <p class='highlight'><b>Precio:</b> ${max_val:,.2f}</p>
                    </div>
                    """
                elif 'menor' in question_lower or 'más barat' in question_lower:
                    min_val = df[price_col].min()
                    result_row = df[df[price_col] == min_val].iloc[0]
                    name_col = next((col for col in text_cols if 'nombre' in col.lower()), text_cols[0] if text_cols else '')
                    return f"""
                    <div class='result-box'>
                        <h3>💸 {name_col} más económico:</h3>
                        <p><b>Nombre:</b> {result_row[name_col] if name_col else 'N/A'}</p>
                        <p class='highlight'><b>Precio:</b> ${min_val:,.2f}</p>
                    </div>
                    """
        
        return None
    
    except Exception as e:
        return f"<div class='result-box'>Error en análisis: {str(e)}</div>"

def main():
    st.title("📊 Analizador CSV Avanzado")
    groq_client = get_groq_client()
    
    uploaded_file = st.file_uploader("Sube tu archivo CSV", type=["csv"])
    
    if uploaded_file:
        df, numeric_cols, text_cols, date_cols, price_cols = process_csv(uploaded_file)
        
        if df is not None:
            st.success(f"✅ Datos cargados: {len(df)} registros, {len(df.columns)} columnas")
            
            with st.expander("🔍 Vista previa de datos"):
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