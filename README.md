# Projections-Dream

Aplicación de escritorio (Windows) de Dream & Travel para registrar las proyecciones de los vendedores
y medirlas contra sus metas: panel con anillos y semanas, proyección necesaria, embudos, campañas,
historial, importar/exportar (Excel, CSV, JSON), lectura de leads desde Bitrix24 y reportes en PDF.

Usa solo la biblioteca estándar de Python (Tkinter). Los datos se guardan en tu computadora, en
`C:\Users\<usuario>\ProyeccionesVendedores\datos.json`, con copias diarias en la carpeta `copias`.
Las actualizaciones **nunca** tocan esos datos.

## Desarrollo

```bash
python proyecciones_vendedores.py            # abrir la aplicación
python -m unittest discover -s tests -t .    # pruebas (no requieren pantalla para la lógica)
```

| Archivo | Contenido |
| --- | --- |
| `proyecciones_vendedores.py` | Aplicación completa (lógica, PDF, interfaz) y `VERSION_APP` |
| `actualizador.py` | Búsqueda, descarga (con SHA-256) e instalación de versiones nuevas desde GitHub Releases |
| `poner_version.py` | Escribe la versión de la etiqueta dentro del programa al publicar |
| `instalador.iss` | Instalador de Inno Setup (el `AppId` no debe cambiar jamás) |
| `.github/workflows/publicar.yml` | Pruebas, compilación con PyInstaller, instalador y release automáticos |
| `tests/` | Pruebas de la lógica y del actualizador |

## Publicar una versión nueva (actualización automática)

1. Sube tus cambios a `main`.
2. Crea y sube una etiqueta nueva:

   ```bash
   git tag v1.0.1
   git push origin v1.0.1
   ```

3. GitHub Actions ejecuta las pruebas, compila `Projections_Dream.exe`, arma
   `Projections_Dream_Setup.exe` y lo publica en **Releases**.
4. Los equipos con el programa instalado preguntan «¿Actualizar ahora?» al abrirlo (o desde
   ⚙ Configuración → Buscar actualización), descargan el instalador, lo verifican y se reinstalan solos.

La primera instalación se hace descargando `Projections_Dream_Setup.exe` del último release.
