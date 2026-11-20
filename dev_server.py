# -*- coding: utf-8 -*-
"""
Servidor de desarrollo (solo para programar y probar la interfaz en un navegador normal; NO va dentro del .exe).

    python dev_server.py [puerto] [--datos ruta.json]

Sirve la carpeta web/ y recibe las llamadas de la pagina en  POST /__api/<metodo>  (cuerpo: lista JSON de argumentos),
llamando al mismo Api que usa la ventana real. Los dialogos de archivo se controlan con POST /__dev/dialogo.
"""
import json
import mimetypes
import os
import sys
import tempfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from api import Api, llamar_por_nombre
from servicio import DialogosVacios, Servicio

RAIZ = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web")


class DialogosDev(DialogosVacios):
    """Las pruebas dejan aqui la ruta que 'eligio el usuario'."""

    def __init__(self):
        self.abrir_ruta = None
        self.guardar_ruta = None
        self.externos = []

    def abrir(self, tipos):
        return self.abrir_ruta

    def guardar(self, nombre, ext, tipos):
        return self.guardar_ruta

    def externo(self, ruta):
        self.externos.append(ruta)


def crear(puerto=8765, datos=None):
    dialogos = DialogosDev()
    svc = Servicio(datos or os.path.join(tempfile.mkdtemp(), "datos.json"), dialogos)
    api = Api(svc, salir=lambda: None)

    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _enviar(self, codigo, cuerpo, tipo):
            self.send_response(codigo)
            self.send_header("Content-Type", tipo)
            self.send_header("Content-Length", str(len(cuerpo)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(cuerpo)

        def do_GET(self):
            if self.path.split('?')[0] == '/__dev':
                self.send_response(200); self.send_header('Content-Type', 'text/plain'); self.send_header('Content-Length', '3'); self.end_headers(); self.wfile.write(b'dev'); return
            ruta = self.path.split("?")[0].lstrip("/") or "index.html"
            f = os.path.normpath(os.path.join(RAIZ, ruta))
            if not f.startswith(RAIZ) or not os.path.isfile(f):
                return self._enviar(404, b"no encontrado", "text/plain")
            tipo = mimetypes.guess_type(f)[0] or "application/octet-stream"
            with open(f, "rb") as fh:
                self._enviar(200, fh.read(), tipo + ("; charset=utf-8" if tipo.startswith("text") or "javascript" in tipo else ""))

        def do_POST(self):
            largo = int(self.headers.get("Content-Length") or 0)
            cuerpo = json.loads(self.rfile.read(largo) or b"[]")
            if self.path.startswith("/__api/"):
                res = llamar_por_nombre(api, self.path[len("/__api/"):], cuerpo)
            elif self.path == "/__dev/dialogo":
                dialogos.abrir_ruta = cuerpo.get("abrir", dialogos.abrir_ruta)
                dialogos.guardar_ruta = cuerpo.get("guardar", dialogos.guardar_ruta)
                res = {"ok": True, "externos": dialogos.externos}
            else:
                res = {"error": "ruta desconocida"}
            self._enviar(200, json.dumps(res, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")

    srv = ThreadingHTTPServer(("127.0.0.1", puerto), H)
    return srv, svc, dialogos


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    datos = sys.argv[sys.argv.index("--datos") + 1] if "--datos" in sys.argv else None
    srv, _, _ = crear(int(args[0]) if args and args[0].isdigit() else 8765, datos)
    print("http://127.0.0.1:{}/".format(srv.server_address[1]))
    srv.serve_forever()
