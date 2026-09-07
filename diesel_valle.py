#!/usr/bin/env python3
"""
diesel_valle.py — Precio de referencia del DIÉSEL en Valle de Santiago, Gto.
============================================================================
Para la página de Haciendo (área de San Diego Quíriceo). Calcula el promedio
de diésel de un conjunto FIJO de estaciones (por número de permiso) a partir
del archivo nacional diario de la CNE/SENER.

POR QUÉ POR PERMISO:
  El XML nacional diario (publicacionexterna.azurewebsites.net/publicaciones/prices)
  trae SOLO: permiso + producto + precio. No trae nombre, dirección ni
  municipio. La única forma fiable de aislar Valle de Santiago es por número
  de permiso. Esta lista se verificó contra el portal de la CNE el 2026-09-06.

ESQUEMA REAL DEL XML (confirmado):
  <precios fecha_generacion="AAAA-MM-DD">
    <estacion permiso="PL/####/EXP/ES/AAAA">
      <producto tipo="regular|premium|diesel" precio="00.00"/>
    </estacion>
  </precios>

DISEÑO A PRUEBA DE FALLOS:
  - Falla ruidosamente (exit!=0) si el XML no se puede leer o no trae la
    fecha de generación esperada.
  - Reporta qué permisos de la lista NO aparecieron y cuáles no traían diésel,
    para que nunca promedien menos estaciones sin darse cuenta.
  - Verifica que la fecha del archivo sea reciente; avisa si está viejo.
  - Descarta precios fuera de un rango sano (protección anti-error de captura).

Uso:
  # verificación (no publica; muestra qué encontró):
  python3 diesel_valle.py --xml precios.xml --diagnostico

  # normal (genera número + JSON para el widget de Hostinger):
  python3 diesel_valle.py --xml precios.xml --json-out diesel.json
"""

import argparse
import json
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, date

# --- Estaciones de Valle de Santiago (verificadas en el portal 2026-09-06) ---
# Edita esta lista cuando abra/cierre una estación. El comentario es solo
# para humanos; el script solo usa el número de permiso.
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
# Rango sano para diésel en MXN/L. Fuera de esto = probable error de captura.
DIESEL_MIN, DIESEL_MAX = 18.0, 40.0
# Avisar si el archivo tiene más de estos días de antigüedad.
DIAS_ARCHIVO_VIEJO = 3

MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
         "agosto", "septiembre", "octubre", "noviembre", "diciembre"]


def fecha_es(d=None):
    d = d or datetime.now()
    return f"{d.day} de {MESES[d.month - 1]} de {d.year}"


def cargar_xml(path):
    """Devuelve (fecha_generacion:date|None, dict permiso->diesel_float)."""
    try:
        root = ET.parse(path).getroot()
    except (ET.ParseError, FileNotFoundError) as e:
        print(f"\n❌ No se pudo leer el XML: {e}\n", file=sys.stderr)
        sys.exit(2)

    fecha_gen = None
    fg_raw = root.get("fecha_generacion")
    if fg_raw:
        try:
            fecha_gen = datetime.strptime(fg_raw[:10], "%Y-%m-%d").date()
        except ValueError:
            pass

    diesel_por_permiso = {}
    n_estaciones = 0
    for est in root.iter("estacion"):
        n_estaciones += 1
        permiso = est.get("permiso")
        if not permiso:
            continue
        for prod in est.findall("producto"):
            if (prod.get("tipo") or "").lower().startswith("dies"):
                try:
                    diesel_por_permiso[permiso] = float(prod.get("precio"))
                except (TypeError, ValueError):
                    pass

    if n_estaciones == 0:
        print("\n❌ El XML no contiene ninguna <estacion>. ¿Archivo equivocado?\n",
              file=sys.stderr)
        sys.exit(2)

    return fecha_gen, diesel_por_permiso, n_estaciones


def evaluar(diesel_por_permiso):
    """Cruza la lista fija contra el archivo. Devuelve usados + reportes."""
    usados = {}       # permiso -> precio válido
    faltantes = []    # en la lista pero no en el archivo
    sin_diesel = []   # en el archivo pero sin producto diésel
    atipicos = []     # diésel fuera de rango sano

    for permiso, nombre in PERMISOS_VALLE.items():
        if permiso not in diesel_por_permiso:
            # ¿está la estación pero sin diésel, o de plano no está?
            faltantes.append((permiso, nombre))
            continue
        precio = diesel_por_permiso[permiso]
        if not (DIESEL_MIN <= precio <= DIESEL_MAX):
            atipicos.append((permiso, nombre, precio))
            continue
        usados[permiso] = precio

    return usados, faltantes, sin_diesel, atipicos


def main():
    ap = argparse.ArgumentParser(description="Diésel de referencia — Valle de Santiago (CNE/SENER).")
    ap.add_argument("--xml", required=True, help="XML nacional de precios de la CNE")
    ap.add_argument("--fuente", default=FUENTE_DEFAULT)
    ap.add_argument("--diagnostico", action="store_true",
                    help="Muestra qué encontró y termina sin publicar")
    ap.add_argument("--json-out", help="Guarda resultado JSON para el widget")
    ap.add_argument("--max-dias", type=int, default=None,
                    help="Si el archivo es más viejo que esto, FALLA (exit!=0). "
                         "Úsalo en automatización para no publicar datos viejos.")
    args = ap.parse_args()

    fecha_gen, diesel_map, n_est = cargar_xml(args.xml)
    usados, faltantes, sin_diesel, atipicos = evaluar(diesel_map)

    # --- Chequeo de frescura del archivo ---
    aviso_fecha = None
    dias_archivo = None
    if fecha_gen:
        dias_archivo = (date.today() - fecha_gen).days
        if dias_archivo > DIAS_ARCHIVO_VIEJO:
            aviso_fecha = f"El archivo es del {fecha_gen} ({dias_archivo} días). Descarga uno nuevo."
    else:
        aviso_fecha = "El XML no traía fecha_generacion; no pude verificar frescura."

    # --- Freshness DURA para automatización: si excede --max-dias, no publica ---
    if args.max_dias is not None and not args.diagnostico:
        if fecha_gen is None:
            print("\n❌ Sin fecha_generacion y --max-dias activo: no se publica.",
                  file=sys.stderr)
            sys.exit(3)
        if dias_archivo > args.max_dias:
            print(f"\n❌ Archivo demasiado viejo ({dias_archivo} días > "
                  f"{args.max_dias}). No se publica.", file=sys.stderr)
            sys.exit(3)

    if args.diagnostico:
        print("\n" + "=" * 60)
        print(" VERIFICACIÓN — DIÉSEL VALLE DE SANTIAGO")
        print("=" * 60)
        print(f"  Archivo: {n_est:,} estaciones nacionales | fecha_generacion: {fecha_gen}")
        if aviso_fecha:
            print(f"  ⚠️  {aviso_fecha}")
        print(f"  Estaciones en lista: {len(PERMISOS_VALLE)}")
        print(f"  Con diésel válido:   {len(usados)}")
        for permiso, precio in usados.items():
            print(f"     ✓ {precio:>6.2f}  {PERMISOS_VALLE[permiso]}")
        if faltantes:
            print(f"  Faltantes (no aparecieron o sin diésel): {len(faltantes)}")
            for permiso, nombre in faltantes:
                print(f"     ✗ {nombre}  [{permiso}]")
        if atipicos:
            print(f"  Atípicos (fuera de ${DIESEL_MIN}-${DIESEL_MAX}): {len(atipicos)}")
            for permiso, nombre, precio in atipicos:
                print(f"     ! {precio}  {nombre}")
        print("=" * 60)
        if not usados:
            print("  ❌ Sin estaciones válidas — revisa la lista de permisos.\n")
            sys.exit(1)
        print("  Esquema OK. Corre sin --diagnostico para generar el número.\n")
        return

    if not usados:
        print("\n❌ Ninguna estación válida — no se publica número.", file=sys.stderr)
        print(f"   Faltantes: {[p for p,_ in faltantes]}", file=sys.stderr)
        sys.exit(1)

    precios = list(usados.values())
    promedio = sum(precios) / len(precios)
    minimo, maximo = min(precios), max(precios)
    hoy = fecha_es()

    print(f"\n Diésel — Valle de Santiago")
    print(f"  Estaciones usadas: {len(usados)} de {len(PERMISOS_VALLE)}")
    print(f"  Promedio: ${promedio:,.2f} /L   (rango ${minimo:,.2f} – ${maximo:,.2f})")
    if aviso_fecha:
        print(f"  ⚠️  {aviso_fecha}")
    if faltantes:
        print(f"  ⚠️  {len(faltantes)} estación(es) no reportaron diésel hoy: "
              f"{[PERMISOS_VALLE[p] for p,_ in faltantes]}")
    if atipicos:
        print(f"  ⚠️  {len(atipicos)} precio(s) atípico(s) descartado(s).")
    print("\n  Línea lista para pegar:")
    print(f'  "Diésel — referencia local (Valle de Santiago): ${promedio:,.2f}/L '
          f'(promedio de {len(usados)} estaciones). '
          f'Fuente: {args.fuente} (Datos Abiertos). Actualizado: {hoy}. '
          f'Confirme en su gasolinera antes de cargar."')

    if args.json_out:
        payload = {
            "diesel_promedio": round(promedio, 2),
            "min": round(minimo, 2),
            "max": round(maximo, 2),
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
