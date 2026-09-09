#!/usr/bin/env python3
"""
diesel_valle.py - Precios de DIESEL, GASOLINA REGULAR y GASOLINA PREMIUM
en Valle de Santiago, Guanajuato. Fuente: CNE/SENER (datos abiertos).

Descarga dos archivos:
  - prices: <place place_id="..."><gas_price type="regular">22.95</gas_price>...</place>
  - places: <place place_id="..."><cre_id>PL/.../EXP/ES/...</cre_id></place>
y los cruza para obtener permiso -> precios.
"""

import requests
import xml.etree.ElementTree as ET
import json
import sys
from datetime import datetime

# --- Estaciones de Valle de Santiago (verificadas en el portal CNE 2026-09-06) ---
PERMISOS_VALLE = {
    "PL/2355/EXP/ES/2015":  "Servicio Anillo Vial (Carr. Jaral-Valle Km 16.4)",
    "PL/23949/EXP/ES/2022": "Servicios Conalcer (Carr. Valle-Guarapo Km 16.3)",
    "PL/2869/EXP/ES/2015":  "Servicio Puente Grande (Blvd. Niños Héroes 17)",
    "PL/21338/EXP/ES/2018": "Mega Gasolineras (Blvd. Niños Héroes 82)",
    "PL/21892/EXP/ES/2018": "Mega Gasolineras (Blvd. Revolución 30)",
    "PL/10752/EXP/ES/2015": "Estación SD Espitia (Carr. Valtierra-Pueblo Nuevo Km 15)",
    "PL/12799/EXP/ES/2015": "Ruiz Guzmán (Blvd. Niños Héroes 69)",
}

BASE = "https://publicacionexterna.azurewebsites.net/publicaciones"
HEADERS = {"User-Agent": "Mozilla/5.0 (haciendo-diesel)", "Accept": "application/xml,text/xml,*/*"}

COMBUSTIBLES = {
    "diesel":           ("Diesel",           "diesel"),
    "gasolina_regular": ("Gasolina Regular", "regular"),
    "gasolina_premium": ("Gasolina Premium", "premium"),
}

PRECIO_MIN, PRECIO_MAX = 15.0, 40.0

MESES_ES = ["", "enero", "febrero", "marzo", "abril", "mayo", "junio",
            "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]


def fecha_mexicana():
    hoy = datetime.now()
    return f"{hoy.day} de {MESES_ES[hoy.month]} de {hoy.year}"


def descargar(nombre):
    url = f"{BASE}/{nombre}"
    print(f"📥 Descargando {nombre}...")
    for intento in range(1, 4):
        try:
            r = requests.get(url, headers=HEADERS, timeout=180)
            r.raise_for_status()
            return ET.fromstring(r.content)
        except Exception as e:
            print(f"   Intento {intento} falló: {e}")
    print(f"❌ No se pudo descargar {nombre}")
    sys.exit(1)


def mapa_permisos(root_places):
    """place_id -> permiso (cre_id)"""
    out = {}
    for pl in root_places.iter("place"):
        pid = pl.get("place_id")
        cre = pl.findtext("cre_id")
        if pid and cre:
            out[pid] = cre.strip().upper()
    return out


def precios_por_place(root_prices):
    """place_id -> {tipo_lower: precio}"""
    out = {}
    for pl in root_prices.iter("place"):
        pid = pl.get("place_id")
        if not pid:
            continue
        d = {}
        for gp in pl.findall("gas_price"):
            tipo = (gp.get("type") or "").strip().lower()
            try:
                d[tipo] = float((gp.text or "").strip())
            except ValueError:
                pass
        if d:
            out[pid] = d
    return out


def extraer(precios_pid, pid_a_permiso, palabra):
    """permiso -> precio para el combustible cuyo type contiene 'palabra'"""
    out = {}
    for pid, tipos in precios_pid.items():
        permiso = pid_a_permiso.get(pid)
        if permiso not in PERMISOS_VALLE:
            continue
        for tipo, precio in tipos.items():
            if palabra in tipo and PRECIO_MIN <= precio <= PRECIO_MAX:
                out[permiso] = precio
    return out


def stats(precios):
    v = list(precios.values())
    return {
        "promedio": round(sum(v) / len(v), 2),
        "minimo": round(min(v), 2),
        "maximo": round(max(v), 2),
        "cantidad": len(v),
    }


def guardar(nombre, data):
    ruta = f"public/{nombre}"
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"✅ Guardado: {ruta}")


def main():
    print("🚀 Iniciando descarga de precios de combustibles...\n")
    root_prices = descargar("prices")
    root_places = descargar("places")

    pid_a_permiso = mapa_permisos(root_places)
    precios_pid = precios_por_place(root_prices)
    print(f"📍 {len(precios_pid)} estaciones con precios, {len(pid_a_permiso)} con permiso\n")

    hoy = fecha_mexicana()
    resumen = {}

    for clave, (nombre, palabra) in COMBUSTIBLES.items():
        print(f"💧 Procesando {nombre}...")
        precios = extraer(precios_pid, pid_a_permiso, palabra)
        if not precios:
            print(f"   ⚠️  No se encontraron precios para {nombre}\n")
            continue
        s = stats(precios)
        data = {
            "tipo_combustible": nombre,
            "region": "Valle de Santiago, Guanajuato",
            "moneda": "MXN",
            "precio_promedio": s["promedio"],
            "precio_minimo": s["minimo"],
            "precio_maximo": s["maximo"],
            "estaciones_muestreadas": s["cantidad"],
            "estaciones_lista": len(PERMISOS_VALLE),
            "fecha_actualizacion": hoy,
            "actualizado_iso": datetime.now().isoformat(),
            "fuente": "CNE/SENER",
            "nota": f"Promedio de {s['cantidad']} estaciones en Valle de Santiago. Fuente: CNE/SENER. Confirme en su gasolinera antes de cargar.",
        }
        guardar(f"{clave}.json", data)
        resumen[clave] = data
        print(f"   → Promedio ${s['promedio']} MXN/L (rango ${s['minimo']}–${s['maximo']}, {s['cantidad']} estaciones)\n")

    if resumen:
        guardar("combustibles.json", {"region": "Valle de Santiago, Guanajuato",
                                       "fecha_actualizacion": hoy, "combustibles": resumen})
        print("✅ Proceso completado!")
    else:
        print("❌ Ninguna estación válida. Revisa permisos.")
        sys.exit(1)


if __name__ == "__main__":
    main()
