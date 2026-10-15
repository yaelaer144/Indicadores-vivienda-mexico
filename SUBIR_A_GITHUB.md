# Cómo generar el enlace de GitHub Pages sin Actions

## 1. Verifica la raíz del repositorio
En la pestaña **Code** deben verse directamente archivos como:

- `index.html`
- `styles.css`
- `app.js`
- los CSV y JSON del dashboard

No debe verse una carpeta contenedora como `dashboard_vivienda_GITHUB_STATIC_20260908/` con todos los archivos adentro.

## 2. Configura Pages
Ve a:

**Settings → Pages → Build and deployment**

Selecciona:

- **Source:** Deploy from a branch
- **Branch:** main
- **Folder:** /(root)

Después pulsa **Save**.

## 3. Enlace
GitHub mostrará en la misma pantalla un aviso **Your site is live at** cuando la publicación esté disponible.

La dirección normalmente tendrá la forma:

`https://USUARIO.github.io/REPOSITORIO/`

## 4. Esta versión no usa Actions
No se incluye `.github/workflows` ni se necesita seleccionar **GitHub Actions** como fuente de Pages.
