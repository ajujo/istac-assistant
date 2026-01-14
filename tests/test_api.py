import requests
import json
import pandas as pd

# URL base de la API del ISTAC para recursos estadísticos
BASE_URL = "https://datos.canarias.es/api/estadisticas/statistical-resources/v1.0"

# ID del dataset de población por sexos e islas
# Este dataset contiene población según sexos, edades y territorios
DATASET_ID = "E30260A_000001"  # Población según sexos y edades por municipios/islas
VERSION = "~latest"  # Última versión disponible

def obtener_poblacion_hombres_islas_2025():
    """
    Obtiene los datos de población de hombres en Canarias por islas para 2025
    """
    
    # Construir la URL del dataset
    url = f"{BASE_URL}/datasets/ISTAC/{DATASET_ID}/{VERSION}.json"
    
    print(f"Consultando: {url}\n")
    
    try:
        # Hacer la petición GET
        response = requests.get(url)
        response.raise_for_status()
        
        # Parsear la respuesta JSON
        data = response.json()
        
        # Extraer información básica
        print("=" * 60)
        print(f"Dataset: {data.get('name', {}).get('es', 'N/A')}")
        print(f"Descripción: {data.get('description', {}).get('es', 'N/A')[:100]}...")
        print("=" * 60)
        
        # Extraer las observaciones (datos)
        observations = data.get('data', {}).get('observations', {})
        dimensions = data.get('data', {}).get('dimensions', {})
        
        # Mostrar las dimensiones disponibles
        print("\nDimensiones disponibles:")
        for dim_id, dim_data in dimensions.items():
            print(f"  - {dim_id}: {dim_data.get('name', {}).get('es', dim_id)}")
            
        # Extraer códigos de dimensiones
        tiempo_dim = dimensions.get('TIME_PERIOD', {}).get('representation', {}).get('index', {})
        territorio_dim = dimensions.get('TERRITORY', {}).get('representation', {}).get('index', {})
        sexo_dim = dimensions.get('SEX', {}).get('representation', {}).get('index', {})
        edad_dim = dimensions.get('AGE', {}).get('representation', {}).get('index', {})
        
        # Crear DataFrame para resultados
        resultados = []
        
        # Buscar datos de 2025, hombres, todas las edades, por islas
        print("\nBuscando datos de población masculina por islas en 2025...")
        print("-" * 60)
        
        # Iterar sobre las observaciones
        for key, value in observations.items():
            indices = key.split(':')
            
            # Decodificar las dimensiones
            if len(indices) >= 4:
                # Obtener los valores de cada dimensión
                territorio_code = list(territorio_dim.keys())[int(indices[0])] if int(indices[0]) < len(territorio_dim) else None
                sexo_code = list(sexo_dim.keys())[int(indices[1])] if int(indices[1]) < len(sexo_dim) else None
                edad_code = list(edad_dim.keys())[int(indices[2])] if int(indices[2]) < len(edad_dim) else None
                tiempo_code = list(tiempo_dim.keys())[int(indices[3])] if int(indices[3]) < len(tiempo_dim) else None
                
                # Filtrar: año 2025, sexo masculino, total edades, nivel isla
                if (tiempo_code == '2025' and 
                    sexo_code == 'M' and 
                    edad_code == '_T' and
                    territorio_code and territorio_code.startswith('ES70')):
                    
                    # Obtener nombres descriptivos
                    territorio_nombre = territorio_dim[territorio_code].get('name', {}).get('es', territorio_code)
                    
                    # Solo islas (códigos de 5 caracteres como ES703, ES704, etc.)
                    if len(territorio_code) == 5:
                        resultados.append({
                            'Isla': territorio_nombre,
                            'Código': territorio_code,
                            'Población Hombres': value
                        })
        
        # Crear DataFrame y ordenar
        if resultados:
            df = pd.DataFrame(resultados)
            df = df.sort_values('Población Hombres', ascending=False)
            
            print("\n📊 POBLACIÓN MASCULINA POR ISLAS DE CANARIAS - 2025")
            print("=" * 60)
            print(df.to_string(index=False))
            print("=" * 60)
            print(f"\nTotal población masculina Canarias: {df['Población Hombres'].sum():,.0f}")
            
            return df
        else:
            print("⚠️  No se encontraron datos para 2025. El dataset puede no tener datos futuros.")
            print("Mostrando el año más reciente disponible...")
            
            # Buscar el año más reciente
            años_disponibles = sorted([k for k in tiempo_dim.keys() if k.isdigit()], reverse=True)
            if años_disponibles:
                año_reciente = años_disponibles[0]
                print(f"\n📅 Año más reciente con datos: {año_reciente}")
                
                # Repetir búsqueda con año más reciente
                for key, value in observations.items():
                    indices = key.split(':')
                    if len(indices) >= 4:
                        territorio_code = list(territorio_dim.keys())[int(indices[0])]
                        sexo_code = list(sexo_dim.keys())[int(indices[1])]
                        edad_code = list(edad_dim.keys())[int(indices[2])]
                        tiempo_code = list(tiempo_dim.keys())[int(indices[3])]
                        
                        if (tiempo_code == año_reciente and 
                            sexo_code == 'M' and 
                            edad_code == '_T' and
                            territorio_code.startswith('ES70') and
                            len(territorio_code) == 5):
                            
                            territorio_nombre = territorio_dim[territorio_code].get('name', {}).get('es', territorio_code)
                            resultados.append({
                                'Isla': territorio_nombre,
                                'Código': territorio_code,
                                'Población Hombres': value
                            })
                
                if resultados:
                    df = pd.DataFrame(resultados)
                    df = df.sort_values('Población Hombres', ascending=False)
                    print(f"\n📊 POBLACIÓN MASCULINA POR ISLAS - {año_reciente}")
                    print("=" * 60)
                    print(df.to_string(index=False))
                    print("=" * 60)
                    return df
            
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Error en la petición: {e}")
        return None
    except Exception as e:
        print(f"❌ Error procesando los datos: {e}")
        return None


def explorar_datasets_poblacion():
    """
    Explora diferentes datasets de población disponibles
    """
    print("\n🔍 Explorando otros datasets de población disponibles...\n")
    
    datasets_poblacion = [
        ("E30245A_000002", "Población según sexos por municipios e islas"),
        ("E30260A_000001", "Población según sexos y edades"),
        ("E30260A_000004", "Población según sexos, edades y nacionalidades"),
    ]
    
    for dataset_id, descripcion in datasets_poblacion:
        print(f"Dataset: {dataset_id}")
        print(f"Descripción: {descripcion}")
        print(f"URL: {BASE_URL}/datasets/ISTAC/{dataset_id}/~latest.json")
        print("-" * 60)


if __name__ == "__main__":
    print("🏝️  CONSULTA API ISTAC - POBLACIÓN MASCULINA CANARIAS POR ISLAS\n")
    
    # Ejecutar la consulta principal
    df = obtener_poblacion_hombres_islas_2025()
    
    # Mostrar información adicional
    print("\n" + "=" * 60)
    print("ℹ️  INFORMACIÓN ADICIONAL")
    print("=" * 60)
    print("• API Base: https://datos.canarias.es/api/estadisticas/")
    print("• Documentación: https://datos.canarias.es/api/estadisticas/statistical-resources")
    print("• Catálogo de datos: https://datos.canarias.es/catalogos/estadisticas")
    
    # Opcionalmente explorar otros datasets
    respuesta = input("\n¿Quieres ver otros datasets disponibles? (s/n): ")
    if respuesta.lower() == 's':
        explorar_datasets_poblacion()