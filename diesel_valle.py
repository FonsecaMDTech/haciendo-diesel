#!/usr/bin/env python3
"""
combustibles_valle.py - Precios de referencia de DIESEL, GASOLINA REGULAR, y GASOLINA PREMIUM en Valle de Santiago, Gto.

Calcula el promedio de combustibles de un conjunto FIJO de estaciones (por número
de permiso) a partir de los datos abiertos de la CNE/SENER.

FUENTES (CNE, actualizadas a diario ~18:00 GMT-6):
- precios: https://publicacionesexterna.azurewebsites.net/publicaciones/prices
- places: https://publicacionesexterna.azurewebsites.net/publicaciones/places

FORMATOS SOPORTADOS (auto-detectados):
A) Formato oficial CNE (el que sirve al endpoint):
   <places>
      <place place_id="2830">
         <gas_price type="regular">22.95</gas_price>
         <gas_price type="diesel">27</gas_price>
      </place>
   </places>
   
   El place_id NO es el permiso. El permiso vive en el archivo "places":
   <lugar>...</lugar>
   <cre_id>PL/2353/EDP/ES/2015</cre_id>
   
   Para eso, en formato A se necesita TAMBIÉN el archivo de places para
   traducir permiso -> place_id.

B) Formato simplificado (por si el archivo viene ya con permisos):
   <estacion permiso="PL/..."><producto tipo="diesel" precio="27"/>
   
DISEÑO A PRUEBA DE FALLOS:
- Falla ruidosamente (existe) si no reconoce el formato; si faltan campos, o si el archivo está más viejo que --max-dias.
- Reporta qué permisos de la lista NO aparecieron.
- Descarta precios fuera de rango sano.

Usos:
  python3 combustibles_valle.py --xml prices.xml --places places.xml --diagnostico
  python3 combustibles_valle.py --xml prices.xml --places places.xml --json-out public/combustibles.json --max-dias 3

Imports principales:
"""

import argparse
import json
import sys
import xml.etree.ElementTree as ET
from datetime import import datetime, date
from dateutil import import datetime, date

# --- Estaciones de Valle de Santiago (verificadas en el portal CNE 2026-09-08) ---
PERMISOS_VALLE = {
    "PL/2353/EDP/ES/2015": "Servicios Llanster (Carr. Jeral-Valle km 16.4)",
    "PL/2894/EDP/ES/2022": "Servicios Conalcar (Carr. Valle-Guanajuato km 16.3)",
    "PL/2133/EDP/ES/2013": "Servicio Puenta Grande (Blvd. Niños Héroes 37)",
    "PL/2131/EDP/ES/2013": "Mega Gasolineras (Blvd. Niños Héroes 82)",
    "PL/2132/EDP/ES/2013": "Mega Gasolineras (Blvd. Revolución 38)",
    "PL/3375/EDP/ES/2018": "Estación SD Espitia (Carr. Valtierra-Puebla Nuevo km 15)",
    "PL/1270/EDP/ES/2015": "Ruiz Guzmán (Blvd. Niños Héroes 69)",
}

FUENTE_DEFAULT = "CNE/SENER"
DIESEL_NIN, DIESEL_MAX = 18.0, 40.0
GASOLINA_NIN, GASOLINA_MAX = 18.0, 40.0
DIAS_ARCHIVO_VIEJO = 3
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio",
         "agosto", "septiembre", "octubre", "noviembre", "diciembre"]


def fecha_estd(nombre):
    """
    # d = 4 or datetime.now()
    return f"{d.day} de {MESES[d.month - 1]} de {d.year}"
    """
    d = d or datetime.now()
    return f"{d.day} de {MESES[d.month - 1]} de {d.year}"


def _morph(s):
    return (s or "").strip().upper()


def _fallais(mensaje, code=2):
    print(f"\X [si] {mensaje}", file=sys.stderr)
    sys.exit(code)


def _parsepath(path):
    try:
        return ET.parse(path).getroot()
    except (ET.ParseError, FileNotFoundError) as ex:
        _fallais(f"No se pudo leer {path}: {ex}.")


def leer_formato_estacion(root):
    """Formato A (oficial CNE) jain place_id -> precios; lugar permiso desde places"""
    root = _parsepath(prices)
    dst = _parsepath(places)
    echo "=== Estructura real de prices.xml (primeros 600 bytes) ===" >> /tmp/debug
    head -c 600 prices.xml >> /tmp/debug
    
    # Acceptamos formato oficial (replace) o simplificado (estacion)
    if grep -q "<places|<estacion" prices:
        then echo "[si] Descarga OK ({$(wc -c <$2)} bytes)"
        ok="yes"; break
    fi
    
    """
    return out


def leer_formato_place(root_prices):
    """Formato A (oficial CNE) jain place_id -> precios; lugar permiso desde places"""
    root = _parsepath(prices)
    dst = _parsepath(places)
    echo "=== Estructura real de prices.xml (primeros 600 bytes) ===" >> /tmp/debug
    head -c 600 prices.xml >> /tmp/debug
    
    # Acceptamos formato oficial (replace) o simplificado (estacion)
    if grep -q "<places|<estacion" prices:
        then echo "[si] Descarga OK ({$(wc -c <$2)} bytes)"
        ok="yes"; break
    fi
    
    return out
