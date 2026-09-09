#!/usr/bin/env python3
"""
combustibles_valle.py - Precios de DIESEL, GASOLINA REGULAR, GASOLINA PREMIUM
Calcula el promedio de tres tipos de combustible en Valle de Santiago, Guanajuato.
Descarga datos de CNE/SENER y publica JSON para cada tipo.
"""

import requests
import xml.etree.ElementTree as ET
import json
from datetime import datetime
import sys

# Estaciones de Valle de Santiago (permisos)
PERMISOS_VALLE = {
    "PL/2353/EDP/ES/2015": "Servicios Llanster",
    "PL/2894/EDP/ES/2022": "Servicios Conalcar",
    "PL/2133/EDP/ES/2013": "Servicio Puenta Grande",
    "PL/2131/EDP/ES/2013": "Mega Gasolineras (Niños Héroes)",
    "PL/2132/EDP/ES/2013": "Mega Gasolineras (Revolución)",
    "PL/3375/EDP/ES/2018": "Estación SD Espitia",
    "PL/1270/EDP/ES/2015": "Ruiz Guzmán",
}

COMBUSTIBLES = {
    "diesel": "Diesel",
    "gasolina_regular": "Gasolina Regular",
    "gasolina_premium": "Gasolina Premium",
}

MESES_ES = ["", "enero", "febrero", "marzo", "abril", "mayo", "junio",
            "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]


def obtener_fecha_mexicana():
    """Devuelve la fecha en formato mexicano: '9 de septiembre de 2026'"""
    hoy = datetime.now()
    return f"{hoy.day} de {MESES_ES[hoy.month]} de {hoy.year}"


def descargar_xml_cne():
    """Descarga el XML de precios de CNE/SENER"""
    print("📥 Descargando datos de CNE/SENER...")
    url = "https://publicacionexterna.azurewebsites.net/publicaciones/prices"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return ET.fromstring(response.content)
    except Exception as e:
        print(f"❌ Error descargando XML: {e}")
        sys.exit(1)


def extraer_precios(root, tipo_combustible):
    """
    Extrae precios de un tipo de combustible específico.
    tipo_combustible: "diesel", "gasolina_regular", "gasolina_premium"
    """
    precios = {}
    
    # Buscar todas las estaciones en el XML
    for estacion in root.findall(".//estacion"):
        permiso = estacion.get("permiso", "").strip()
        
        # Solo procesar si está en nuestra lista de Valle de Santiago
        if permiso not in PERMISOS_VALLE:
            continue
        
        # Buscar el producto con el tipo correcto
        for producto in estacion.findall("producto"):
            tipo = (producto.get("tipo") or "").lower().strip()
            precio_str = (producto.get("precio") or "").strip()
            
            # Identificar el tipo de combustible
            buscar = ""
            if tipo_combustible == "diesel":
                buscar = "diesel"
            elif tipo_combustible == "gasolina_regular":
                buscar = "regular"
            elif tipo_combustible == "gasolina_premium":
                buscar = "premium"
            
            # Si coincide, extraer precio
            if buscar in tipo.lower():
                try:
                    precio = float(precio_str)
                    precios[permiso] = precio
                except ValueError:
                    continue
    
    return precios


def calcular_estadisticas(precios_dict):
    """Calcula promedio, mín, máx de un conjunto de precios"""
    if not precios_dict:
        return None
    
    valores = list(precios_dict.values())
    promedio = sum(valores) / len(valores)
    minimo = min(valores)
    maximo = max(valores)
    
    return {
        "promedio": round(promedio, 2),
        "minimo": round(minimo, 2),
        "maximo": round(maximo, 2),
        "cantidad_estaciones": len(precios_dict),
    }


def crear_json(tipo_combustible, estadisticas):
    """Crea el JSON a publicar para un tipo de combustible"""
    if not estadisticas:
        return None
    
    nombre_tipo = COMBUSTIBLES.get(tipo_combustible, tipo_combustible)
    
    return {
        "tipo_combustible": nombre_tipo,
        "region": "Valle de Santiago, Guanajuato",
        "moneda": "MXN",
        "precio_promedio": estadisticas["promedio"],
        "precio_minimo": estadisticas["minimo"],
        "precio_maximo": estadisticas["maximo"],
        "diferencia": round(estadisticas["maximo"] - estadisticas["minimo"], 2),
        "estaciones_muestreadas": estadisticas["cantidad_estaciones"],
        "fecha_actualizacion": obtener_fecha_mexicana(),
        "fuente": "CNE/SENER",
        "nota": f"Promedio de {estadisticas['cantidad_estaciones']} estaciones en Valle de Santiago. Actualizado diariamente.",
    }


def guardar_json(nombre_archivo, datos_json):
    """Guarda JSON a archivo en public/"""
    ruta = f"public/{nombre_archivo}"
    try:
        with open(ruta, "w", encoding="utf-8") as f:
            json.dump(datos_json, f, ensure_ascii=False, indent=2)
        print(f"✅ Guardado: {ruta}")
    except Exception as e:
        print(f"❌ Error guardando {ruta}: {e}")


def main():
    print("🚀 Iniciando descarga de precios de combustibles...\n")
    
    # Descargar XML
    root = descargar_xml_cne()
    
    # Procesar cada tipo de combustible
    for tipo_clave, nombre_tipo in COMBUSTIBLES.items():
        print(f"💧 Procesando {nombre_tipo}...")
        
        # Extraer precios
        precios = extraer_precios(root, tipo_clave)
        
        if precios:
            # Calcular estadísticas
            stats = calcular_estadisticas(precios)
            
            # Crear JSON
            json_data = crear_json(tipo_clave, stats)
            
            # Guardar
            archivo = f"{tipo_clave}.json"
            guardar_json(archivo, json_data)
            
            print(f"   → Promedio: ${json_data['precio_promedio']} MXN/L")
            print(f"   → Rango: ${json_data['precio_minimo']}-${json_data['precio_maximo']}\n")
        else:
            print(f"   ⚠️  No se encontraron precios para {nombre_tipo}\n")
    
    print("✅ Proceso completado!")


if __name__ == "__main__":
    main()
