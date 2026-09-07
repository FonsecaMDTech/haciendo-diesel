# Automatización del precio del diésel — Valle de Santiago
### Guía paso a paso (GitHub Actions + Pages → widget de Hostinger)

Al terminar tendrás:
- Una GitHub Action que **cada día** baja el XML nacional de la CNE, calcula el
  promedio de diésel de tus 7 estaciones de Valle de Santiago y publica
  `diesel.json`.
- Ese JSON servido gratis por **GitHub Pages** (HTTPS + CORS abiertos).
- Un **widget** en Hostinger que lo muestra, y que NUNCA enseña un precio viejo:
  si el dato tiene más de 7 días o falla la descarga, muestra
  "datos desactualizados" / "datos no disponibles".

Archivos en este paquete:
- `diesel_valle.py` — el cálculo (ya verificado con datos reales).
- `.github/workflows/diesel.yml` — la automatización.
- `widget-hostinger.html` — lo que pegas en Hostinger.
- `public/diesel.json` — ejemplo del resultado (se regenera solo).

---

## PARTE 1 — Crear el repositorio en GitHub

**Paso 1.** Entra a https://github.com e inicia sesión (o crea cuenta gratis).

**Paso 2.** Arriba a la derecha, clic en **+** → **New repository**.

**Paso 3.** Llénalo así:
- Repository name: `haciendo-diesel`
- Visibilidad: **Public** (necesario para Pages gratis)
- NO marques "Add a README"
- Clic en **Create repository**.

**Paso 4.** Verás una página con instrucciones. Déjala abierta; volveremos.

---

## PARTE 2 — Subir los archivos

La forma más fácil (sin instalar nada), por la web:

**Paso 5.** En tu repo nuevo, clic en **uploading an existing file**
(o ve a **Add file → Upload files**).

**Paso 6.** Arrastra estos archivos y carpetas **conservando la estructura**:
```
haciendo-diesel/
├── diesel_valle.py
├── widget-hostinger.html
├── public/
│   └── diesel.json
└── .github/
    └── workflows/
        └── diesel.yml
```
> ⚠️ La carpeta `.github/workflows/` es la que hace que la Action exista.
> Si GitHub no te deja arrastrar carpetas, sube primero los archivos sueltos
> y luego usa **Add file → Create new file** y escribe la ruta completa
> `.github/workflows/diesel.yml` en el nombre — GitHub crea las carpetas solo.

**Paso 7.** Abajo, clic en **Commit changes**.

---

## PARTE 3 — Encender GitHub Pages

**Paso 8.** En el repo, ve a **Settings** (arriba) → **Pages** (menú izquierdo).

**Paso 9.** En "Build and deployment" → "Source", elige **Deploy from a branch**.

**Paso 10.** En "Branch" elige **gh-pages** y carpeta **/ (root)**, clic **Save**.
> Si `gh-pages` aún no aparece, es normal: aparecerá después de que la Action
> corra por primera vez (Parte 4). Vuelve aquí luego a elegirla.

---

## PARTE 4 — Correr la automatización por primera vez

**Paso 11.** Ve a la pestaña **Actions**. Si te pide habilitar workflows,
clic en **I understand my workflows, go ahead and enable them**.

**Paso 12.** En la lista de la izquierda, clic en
**"Actualizar precio diésel (Valle de Santiago)"**.

**Paso 13.** A la derecha, botón **Run workflow** → **Run workflow**.
Espera ~1-2 min y refresca. Debe salir una palomita verde ✔.
> Si sale roja ✗: clic en la corrida para ver el error. Lo más común es que
> la CNE tardó; simplemente vuelve a darle **Run workflow**.

**Paso 14.** Ahora vuelve a **Settings → Pages** y confirma que la rama
**gh-pages** está seleccionada (Paso 10).

**Paso 15.** Tu JSON quedará en:
```
https://TU-USUARIO.github.io/haciendo-diesel/diesel.json
```
Ábrelo en el navegador. Debes ver el JSON con `diesel_promedio`. 
Copia esta URL.

---

## PARTE 5 — El widget en Hostinger

**Paso 16.** Abre `widget-hostinger.html` en un editor de texto.

**Paso 17.** Cambia SOLO esta línea, pon tu URL real del Paso 15:
```js
var DIESEL_JSON_URL = "https://TU-USUARIO.github.io/haciendo-diesel/diesel.json";
```
Guarda.

**Paso 18.** En Hostinger, editor del sitio de San Diego Quíriceo:
**Add elements → Embed code → Enter code**.
> ⚠️ Crea un elemento NUEVO. No toques el embed de "Niveles de Presas".

**Paso 19.** Pega TODO el contenido de `widget-hostinger.html`. Clic fuera /
guarda.

**Paso 20.** El embed **no se ve dentro del editor** (así es Hostinger).
Usa **Preview** o publica para verlo. Debe mostrar el precio del diésel.

---

## Listo ✅

De aquí en adelante se actualiza solo, todos los días. Tú no tienes que hacer
nada — salvo revisar de vez en cuando (tu rutina quincenal) que:
1. El widget siga mostrando un precio (no "datos no disponibles").
2. La lista de 7 permisos siga vigente (si abre/cierra una gasolinera).

### Mantener la lista de estaciones
Si necesitas agregar o quitar una estación, edita `diesel_valle.py`, el bloque
`PERMISOS_VALLE`, y sube el cambio. La Action lo toma en la siguiente corrida.

### Cómo agregar una estación nueva
1. En el portal CNE, filtra Guanajuato → Valle de Santiago.
2. Copia el "No de Permiso" de la estación nueva.
3. Agrégalo a `PERMISOS_VALLE` con un nombre para recordarlo.
4. Commit. Corre la Action a mano para probar (Paso 13).
