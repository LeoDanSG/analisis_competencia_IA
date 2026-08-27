import pandas as pd

def preparar_datos_powerbi():
    print("Iniciando procesamiento de datos...")
    
    # 1. Cargar el archivo Excel original
    try:
        df = pd.read_excel('archivosyl.xlsx', header=None)
    except FileNotFoundError:
        print("Error: No se encontró el archivo 'archivosyl.xlsx'. Asegúrate de que está en esta carpeta.")
        return

    # 2. Extraer las columnas importantes basándonos en tu estructura
    # Columna 0: ID_Pedido, 5: Cantidad, 6: Categoria, 7: Producto, 13: Cliente
    df_limpio = df.iloc[:, [0, 5, 6, 7, 13]].copy()
    
    # 3. Nombrar las columnas para que Power BI las entienda bien
    df_limpio.columns = ['ID_Pedido', 'Cantidad', 'Categoria', 'Producto', 'Cliente']
    
    # 4. Limpiar datos vacíos o errores
    df_limpio = df_limpio.dropna(subset=['Producto']) # Elimina filas sin nombre de producto
    df_limpio['Cantidad'] = pd.to_numeric(df_limpio['Cantidad'], errors='coerce').fillna(0)
    
    # 5. CREAR REGLA DE COMPETENCIA vs PROPIO
    # Aquí le decimos a la IA/Script cómo identificar los productos.
    # Por ejemplo, si "Biotrue" o "fp" (Presbicia) son de la competencia, los marcamos.
    # (Podremos ajustar estas reglas más adelante).
    def clasificar_origen(nombre_producto):
        nombre_str = str(nombre_producto).upper()
        # Modifica estas palabras clave según los nombres reales de la competencia
        palabras_competencia = ['OTRO_MARCA', 'COMPETIDOR_X'] 
        
        for palabra in palabras_competencia:
            if palabra in nombre_str:
                return 'Competencia'
        return 'Propio'
        
    df_limpio['Origen'] = df_limpio['Producto'].apply(clasificar_origen)

    # 6. Guardar el nuevo archivo optimizado
    nombre_salida = 'datos_limpios_competencia.xlsx'
    df_limpio.to_excel(nombre_salida, index=False)
    
    print(f"¡Éxito! Archivo guardado como: {nombre_salida}")
    print(f"Total de registros procesados: {len(df_limpio)}")

# Ejecutar la función
if __name__ == "__main__":
    preparar_datos_powerbi()