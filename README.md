# Projections-Dream

Aplicación de escritorio (Windows) de Dream & Travel para registrar las proyecciones de los vendedores
y medirlas contra sus metas: panel con anillos y semanas, proyección necesaria, embudos, campañas,
historial, importar/exportar (Excel, CSV, JSON), lectura de leads desde Bitrix24 y reportes en PDF.

La interfaz es HTML/CSS/JS dentro de una ventana **pywebview** (en Windows usa el WebView2 de Microsoft Edge,
que ya viene con Windows 11 y con Edge actualizado). Los datos se guardan en tu computadora, en
`C:\Users\<usuario>\ProyeccionesVendedores\datos.json`, con copias diarias en la carpeta `copias`.
Las actualizaciones **nunca** tocan esos datos.

## Desarrollo

```bash
pip install -r requirements.txt              # una sola vez (pywebview)
python app_web.py                            # abrir la aplicación
python dev_server.py                         # la misma interfaz en el navegador (http://127.0.0.1:8765/), para programar/probar
python -m unittest discover -s tests -t .    # pruebas (no requieren pantalla)
```

| Archivo | Contenido |
| --- | --- |
| `nucleo.py` | Toda la lógica (metas, reportes, Bitrix24, importar/exportar, PDF, paleta) sin interfaz, y `VERSION_APP` |
| `servicio.py` | El estado de la app (meses, semana, guardado, deshacer…) con métodos que devuelven JSON |
| `api.py` | Puente con la ventana: lista cerrada de métodos que la página puede llamar |
| `app_web.py` | Abre la ventana pywebview, diálogos de archivo, aviso si falta WebView2 |
| `web/` | La interfaz: `index.html`, `styles.css` (diseño y animaciones), `charts.js` (gráficas SVG), `paginas.js`, `dialogos.js`, `app.js` |
| `dev_server.py` | Servidor local solo para desarrollo (no va dentro del `.exe`) |
| `novedades.py` | Notas de cada versión para la ventana «Actualización» |
| `actualizador.py` | Búsqueda, descarga (con SHA-256) e instalación de versiones nuevas desde GitHub Releases |
| `poner_version.py` | Escribe la versión de la etiqueta dentro del programa al publicar |
| `instalador.iss` | Instalador de Inno Setup (el `AppId` no debe cambiar jamás) |
| `.github/workflows/publicar.yml` | Pruebas, compilación con PyInstaller, prueba de que la ventana abre, instalador y release |
| `tests/` | Pruebas de la lógica, del servicio/API y del actualizador |

## Publicar una versión nueva (actualización automática)

1. Agrega las notas de la versión en `novedades.py` (cambios con «-», correcciones con «*»);
   se muestran en una ventana al terminar de actualizar.
2. Sube tus cambios a `main`.
3. Crea y sube una etiqueta nueva:

   ```bash
   git tag v1.0.1
   git push origin v1.0.1
   ```

4. GitHub Actions ejecuta las pruebas, compila `Projections_Dream.exe`, arma
   `Projections_Dream_Setup.exe` y lo publica en **Releases**.
5. Los equipos con el programa instalado preguntan «¿Actualizar ahora?» al abrirlo (o desde
   ⚙ Configuración → Buscar actualización), descargan el instalador, lo verifican y se reinstalan solos.

La primera instalación se hace descargando `Projections_Dream_Setup.exe` del último release.
