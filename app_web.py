# -*- coding: utf-8 -*-
"""
Proyecciones de Vendedores: ventana de escritorio con pywebview (interfaz en HTML/CSS/JS dentro de la carpeta web/).

Ejecutar:  python app_web.py
La logica vive en nucleo.py / servicio.py; este archivo solo abre la ventana.
"""
import os
import sys
import webbrowser

import nucleo as n
from api import Api
from servicio import Servicio

WEBVIEW2_URL = "https://developer.microsoft.com/microsoft-edge/webview2/"
WEBVIEW2_GUID = "{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}"


def hay_webview2():
    """En Windows la ventana necesita el 'WebView2 Runtime' (ya viene con Windows 11 y con Edge actualizado)."""
    if os.name != "nt":
        return True
    try:
        import winreg
        for raiz, sub in ((winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\\" + WEBVIEW2_GUID),
                          (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\EdgeUpdate\Clients\\" + WEBVIEW2_GUID),
                          (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\EdgeUpdate\Clients\\" + WEBVIEW2_GUID)):
            try:
                with winreg.OpenKey(raiz, sub) as k:
                    v, _ = winreg.QueryValueEx(k, "pv")
                    if v and v != "0.0.0.0":
                        return True
            except OSError:
                continue
    except Exception:
        return True            # si no se puede comprobar, se intenta abrir igual
    return False


def aviso_sin_webview2():
    texto = ("Falta el componente «Microsoft Edge WebView2 Runtime», que dibuja la ventana del programa.\n\n"
             "Es gratuito y de Microsoft. Pulsa Aceptar para abrir la página de descarga (elige «Evergreen Standalone Installer»), "
             "instálalo y vuelve a abrir el programa.")
    try:
        import ctypes
        r = ctypes.windll.user32.MessageBoxW(0, texto, n.APP_NAME, 0x00000001 | 0x00000030)    # OK/Cancelar + aviso
        if r == 1:
            webbrowser.open(WEBVIEW2_URL)
    except Exception:
        print(texto)
        webbrowser.open(WEBVIEW2_URL)


class DialogosVentana:
    """Dialogos de archivo nativos sobre la ventana de pywebview."""

    def __init__(self):
        self.ventana = None

    def _tipos(self, tipos):
        return tuple("{} ({})".format(nombre, patron.replace(" ", ";")) for nombre, patron in tipos)

    def _const(self, que):
        import webview
        fd = getattr(webview, "FileDialog", None)
        if fd is not None:
            return getattr(fd, que)
        return getattr(webview, que + "_DIALOG")

    def abrir(self, tipos):
        r = self.ventana.create_file_dialog(self._const("OPEN"), allow_multiple=False, file_types=self._tipos(tipos))
        return r[0] if r else None

    def guardar(self, nombre, ext, tipos):
        r = self.ventana.create_file_dialog(self._const("SAVE"), save_filename=nombre, file_types=self._tipos(tipos))
        if not r:
            return None
        ruta = r if isinstance(r, str) else r[0]
        return ruta if os.path.splitext(ruta)[1] else ruta + ext

    def externo(self, ruta):
        try:
            if hasattr(os, "startfile"):
                os.startfile(ruta)
            else:
                webbrowser.open("file://" + os.path.abspath(ruta))
        except OSError:
            pass


def main():
    try:  # nitidez en Windows con pantallas de alta resolucion
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass
    try:  # identidad propia en la barra de tareas: al anclarla conserva su icono y no se agrupa con Python
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("DreamTravel.ProyeccionesDream")
    except Exception:
        pass
    if not hay_webview2():
        return aviso_sin_webview2()
    import webview
    dialogos = DialogosVentana()
    ruta_datos = sys.argv[sys.argv.index("--datos") + 1] if "--datos" in sys.argv else n.DATA_FILE
    svc = Servicio(ruta_datos, dialogos=dialogos)
    ventana = None

    def salir():
        if ventana is not None:
            ventana.destroy()
    api = Api(svc, salir=salir)
    index = n.ruta_recurso(os.path.join("web", "index.html"))
    ventana = webview.create_window(n.APP_NAME, url=index, js_api=api, width=1320, height=840, min_size=(1000, 660),
                                    background_color="#F4F6F9", maximized=True, text_select=False)
    dialogos.ventana = ventana
    ventana.events.closing += lambda: svc.cerrar()
    prueba = next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--autoprueba=")), None)
    gui = "edgechromium" if os.name == "nt" else None
    if prueba:
        webview.start(autoprueba, (ventana, prueba), gui=gui)
    else:
        webview.start(gui=gui, debug="--depurar" in sys.argv)


def autoprueba(ventana, archivo_resultado):
    """Usado por GitHub Actions: abre la ventana de verdad, espera a que dibuje el panel y sale con 0 (bien) o 1 (mal)."""
    import time
    ok, detalle = False, "la ventana no dibujo el panel a tiempo"
    t0 = time.time()
    while time.time() - t0 < 60:
        time.sleep(1)
        try:
            r = ventana.evaluate_js("document.querySelectorAll('.kpi .v').length + '|' + (typeof S !== 'undefined' && S.estado ? S.estado.version : '')")
        except Exception as e:
            detalle = "evaluate_js fallo: {}".format(e)
            continue
        if r and str(r).startswith("5|") and not str(r).endswith("|"):
            ok, detalle = True, "panel dibujado ({})".format(r)
            break
        detalle = "respuesta de la pagina: {}".format(r)
    try:
        with open(archivo_resultado, "w", encoding="utf-8") as f:
            f.write(("OK " if ok else "FALLA ") + detalle)
    finally:
        os._exit(0 if ok else 1)


if __name__ == "__main__":
    main()
