#!/usr/bin/env python3
"""
diesel_valle.py — Precio de referencia del DIÉSEL en Valle de Santiago, Gto.
============================================================================
Calcula el promedio de diésel de un conjunto FIJO de estaciones (por número
de permiso) a partir de los datos abiertos de la CNE/SENER.

FUENTES (CNE, actualizadas a diario ~18:00 GMT-6):
  prices: https://publicacionexterna.azurewebsites.net/publicaciones/prices
  places: https://publicacionexterna.azurewebsites.net/publicaciones/places

FORMATOS SOPORTADOS (auto-detectados):
  A) Formato oficial CNE (el que sirve el endpoint):
       <places>
         <place place_id="2039">
           <gas_price type="regular">22.95</gas_price>
           <gas_price type="diesel">27</gas_price>
         </place>
     El place_id NO es el permiso. El permiso vive en el archivo "places":
         <place place_id="2039">
           <name>...</name>
           <cre_id>PL/2355/EXP/ES/2015</cre_id>
     Por eso, en formato A se necesita TAMBIÉN el archivo de places para
     traducir permiso -> place_id.

  B) Formato simplificado (por si el archivo viene ya con permiso):
       <estacion permiso="PL/...."><producto tipo="diesel" precio="27"/>

DISEÑO A PRUEBA DE FALLOS:
  - Falla ruidosamente (exit!=0) si no reconoce el formato, si faltan
    campos, o si el archivo está más viejo que --max-dias.
  - Reporta qué permisos de la lista NO aparecieron.
  - Descarta precios fuera de rango sano.

Uso:
  python3 diesel_valle.py --xml prices.xml --places places.xml --diagnostico
  python3 diesel_valle.py --xml prices.xml --places places.xml --json-out public/diesel.json --max-dias 3
"""

import argparse
import json
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, date

# --- Estaciones de Valle de Santiago (verificadas en el portal CNE 2026-09-06) ---
PERMISOS_VALLE = {
    "PL/2355/EXP/ES/2015":  "Servicio Anillo Vial (Carr. Jaral-Valle Km 16.4)",
    "PL/23949/EXP/ES/2022": "Servicios Conalcer (Carr. Valle-Guarapo Km 16.3)",
    "PL/2869/EXP/ES/2015":  "Servicio Puente Grande (Blvd. Niños Héroes 17)",
    "PL/21338/EXP/ES/2018": "Mega Gasolineras (Blvrd. Niños Héroes 82)",
    "PL/21892/EXP/ES/2018": "Mega Gasolineras (Blvd. Revolución 30)",
    "PL/10752/EXP/ES/2015": "Estación SD Espitia (Carr. Valtierra-Pueblo Nuevo Km 15)",
    "PL/12799/EXP/ES/2015": "Ruiz Guzmán (Blvd. Niños Héroes 69)",
}

FUENTE_DEFAULT = "CNE/SENER"
DIESEL_MIN, DIESEL_MAX = 18.0, 40.0
DIAS_ARCHIVO_VIEJO = 3
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
         "agosto", "septiembre", "octubre", "noviembre", "diciembre"]


def fecha_es(d=None):
    d = d or datetime.now()
    return f"{d.day} de {MESES[d.month - 1]} de {d.year}"


def _norm(p):
    return (p or "").strip().upper()


def _fail(msg, code=2):
    print(f"\n❌ {msg}\n", file=sys.stderr)
    sys.exit(code)


def _parse(path):
    try:
        return ET.parse(path).getroot()
    except (ET.ParseError, FileNotFoundError) as e:
        _fail(f"No se pudo leer {path}: {e}")


# ---------------------------------------------------------------------------
# Lectores. Ambos devuelven dict permiso -> precio diésel (float).
# ---------------------------------------------------------------------------

def leer_formato_estacion(root):
    """Formato B: <estacion permiso=...><producto tipo="diesel" precio=.../>"""
    out = {}
    for est in root.iter("estacion"):
        permiso = _norm(est.get("permiso"))
        if not permiso:
            continue
        for prod in est.findall("producto"):
            if (prod.get("tipo") or "").lower().startswith("dies"):
                try:
                    out[permiso] = float(prod.get("precio"))
                except (TypeError, ValueError):
                    pass
    return out


def leer_formato_place(root_prices, root_places):
    """Formato A (oficial CNE): join place_id <-> cre_id."""
    # 1) place_id -> diésel
    diesel_por_pid = {}
    for pl in root_prices.iter("place"):
        pid = pl.get("place_id")
        if not pid:
            continue
        for gp in pl.findall("gas_price"):
            if (gp.get("type") or "").lower().startswith("dies"):
                try:
                    diesel_por_pid[pid] = float((gp.text or "").strip())
                except ValueError:
                    pass

    # 2) place_id -> permiso (cre_id) desde places
    if root_places is None:
        _fail("El archivo de precios está en formato oficial CNE (<place place_id>), "
              "que NO trae el número de permiso. Pasa también --places con el "
              "archivo de estaciones de la CNE para poder cruzar permiso -> place_id.")
    pid_por_permiso = {}
    for pl in root_places.iter("place"):
        pid = pl.get("place_id")
        cre = pl.findtext("cre_id")
        if pid and cre:
            pid_por_permiso[_norm(cre)] = pid

    if not pid_por_permiso:
        _fail("El archivo --places no trae <cre_id>; no se puede cruzar el permiso.")

    # 3) permiso -> diésel
    out = {}
    for permiso, pid in pid_por_permiso.items():
        if pid in diesel_por_pid:
            out[permiso] = diesel_por_pid[pid]
    return out, len(diesel_por_pid), len(pid_por_permiso)


def cargar(path_prices, path_places):
    """Devuelve (permiso->diesel, formato, n_estaciones, fecha_gen|None)."""
    root = _parse(path_prices)
    tag = root.tag.lower()
    fecha_gen = None
    fg = root.get("fecha_generacion")
    if fg:
        try:
            fecha_gen = datetime.strptime(fg[:10], "%Y-%m-%d").date()
        except ValueError:
            pass

    if root.find("estacion") is not None or tag == "precios":
        d = leer_formato_estacion(root)
        return d, "estacion(permiso)", len(list(root.iter("estacion"))), fecha_gen

    if root.find("place") is not None or tag == "places":
        root_places = _parse(path_places) if path_places else None
        d, n_prices, n_places = leer_formato_place(root, root_places)
        return d, f"place(place_id) + places(cre_id) [{n_prices} precios, {n_places} estaciones]", n_prices, fecha_gen

    _fail(f"Formato XML no reconocido (raíz <{root.tag}>). Esperaba <places>/<place> "
          f"o <precios>/<estacion>. Revisa el archivo descargado.")


def evaluar(diesel_por_permiso):
    usados, faltantes, atipicos = {}, [], []
    for permiso, nombre in PERMISOS_VALLE.items():
        key = _norm(permiso)
        if key not in diesel_por_permiso:
            faltantes.append((permiso, nombre))
            continue
        p = diesel_por_permiso[key]
        if not (DIESEL_MIN <= p <= DIESEL_MAX):
            atipicos.append((permiso, nombre, p))
            continue
        usados[permiso] = p
    return usados, faltantes, atipicos


def main():
    ap = argparse.ArgumentParser(description="Diésel de referencia — Valle de Santiago (CNE/SENER).")
    ap.add_argument("--xml", required=True, help="Archivo de precios CNE (prices)")
    ap.add_argument("--places", help="Archivo de estaciones CNE (places) — necesario en formato oficial")
    ap.add_argument("--fuente", default=FUENTE_DEFAULT)
    ap.add_argument("--diagnostico", action="store_true")
    ap.add_argument("--json-out")
    ap.add_argument("--max-dias", type=int, default=None,
                    help="Si el archivo trae fecha y es más viejo que esto, FALLA.")
    args = ap.parse_args()

    diesel_map, formato, n_est, fecha_gen = cargar(args.xml, args.places)
    usados, faltantes, atipicos = evaluar(diesel_map)

    # Frescura: el formato oficial NO trae fecha_generacion; en ese caso confiamos
    # en que el workflow acaba de descargarlo (la fecha del cálculo es la de hoy).
    aviso_fecha = None
    if fecha_gen:
        dias = (date.today() - fecha_gen).days
        if dias > DIAS_ARCHIVO_VIEJO:
            aviso_fecha = f"El archivo es del {fecha_gen} ({dias} días)."
        if args.max_dias is not None and not args.diagnostico and dias > args.max_dias:
            _fail(f"Archivo demasiado viejo ({dias} días > {args.max_dias}). No se publica.", 3)

    if args.diagnostico:
        print("\n" + "=" * 62)
        print(" VERIFICACIÓN — DIÉSEL VALLE DE SANTIAGO")
        print("=" * 62)
        print(f"  Formato detectado: {formato}")
        print(f"  Estaciones en archivo: {n_est:,} | fecha_generacion: {fecha_gen or '(no trae; formato oficial)'}")
        if aviso_fecha:
            print(f"  ⚠️  {aviso_fecha}")
        print(f"  En lista: {len(PERMISOS_VALLE)} | con diésel válido: {len(usados)}")
        for permiso, precio in usados.items():
            print(f"     ✓ {precio:>6.2f}  {PERMISOS_VALLE[permiso]}")
        for permiso, nombre in faltantes:
            print(f"     ✗ FALTA  {nombre}  [{permiso}]")
        for permiso, nombre, precio in atipicos:
            print(f"     ! ATÍPICO {precio}  {nombre}")
        print("=" * 62)
        if not usados:
            _fail("Sin estaciones válidas — revisa la lista de permisos o el cruce cre_id.", 1)
        print("  Esquema OK.\n")
        return

    if not usados:
        _fail(f"Ninguna estación válida — no se publica número. Faltantes: "
              f"{[p for p, _ in faltantes]}", 1)

    precios = list(usados.values())
    promedio = sum(precios) / len(precios)
    minimo, maximo = min(precios), max(precios)
    hoy = fecha_es()

    print(f"\n Diésel — Valle de Santiago  [{formato}]")
    print(f"  Estaciones usadas: {len(usados)} de {len(PERMISOS_VALLE)}")
    print(f"  Promedio: ${promedio:,.2f} /L   (rango ${minimo:,.2f} – ${maximo:,.2f})")
    if aviso_fecha:
        print(f"  ⚠️  {aviso_fecha}")
    if faltantes:
        print(f"  ⚠️  Sin diésel hoy: {[PERMISOS_VALLE[p] for p, _ in faltantes]}")
    if atipicos:
        print(f"  ⚠️  {len(atipicos)} atípico(s) descartado(s).")
    print("\n  Línea lista para pegar:")
    print(f'  "Diésel — referencia local (Valle de Santiago): ${promedio:,.2f}/L '
          f'(promedio de {len(usados)} estaciones). Fuente: {args.fuente} (Datos Abiertos). '
          f'Actualizado: {hoy}. Confirme en su gasolinera antes de cargar."')

    if args.json_out:
        payload = {
            "diesel_promedio": round(promedio, 2),
            "min": round(minimo, 2), "max": round(maximo, 2),
            "estaciones_usadas": len(usados),
            "estaciones_lista": len(PERMISOS_VALLE),
            "municipio": "Valle de Santiago",
            "fuente": args.fuente,
            "fecha_archivo": str(fecha_gen) if fecha_gen else None,
            "actualizado_iso": datetime.now().isoformat(),
            "actualizado_texto": hoy,
        }
        with open(args.json_out, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        print(f"\n  JSON guardado en {args.json_out}")


if __name__ == "__main__":
    main()
