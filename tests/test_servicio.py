import csv
import json
import os
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import api  # noqa: E402
import nucleo as n  # noqa: E402
import servicio  # noqa: E402


class Dialogos(servicio.DialogosVacios):
    def __init__(self):
        self.abrir_ruta = self.guardar_ruta = None
        self.externos = []

    def abrir(self, tipos):
        return self.abrir_ruta

    def guardar(self, nombre, ext, tipos):
        return self.guardar_ruta

    def externo(self, ruta):
        self.externos.append(ruta)


class Base(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.dlg = Dialogos()
        self.s = servicio.Servicio(os.path.join(self.dir, "datos.json"), self.dlg)
        self.s.fijar_vista(meses=[10], anio=2026)

    def form(self, lead="555", monto="100", tipo="Activa", **kw):
        f = {"fecha": "03/11/2026", "asesor": "Lesly", "lead": lead, "campana": "Cuba", "monto": monto, "tipo": tipo}
        f.update(kw)
        return f


class PruebaProyecciones(Base):
    def test_alta_validaciones_y_duplicados(self):
        self.assertTrue(self.s.guardar_proyeccion(self.form())["ok"])
        self.assertEqual(self.s.guardar_proyeccion(self.form(monto="abc"))["campo"], "monto")
        self.assertEqual(self.s.guardar_proyeccion(self.form(fecha="32/13/2026"))["campo"], "fecha")
        self.assertEqual(self.s.guardar_proyeccion(self.form(asesor="Nadie"))["campo"], "asesor")
        self.assertEqual(self.s.guardar_proyeccion(self.form(lead=""))["campo"], "lead")
        rep = self.s.guardar_proyeccion(self.form())                      # mismo enlace: no se permite
        self.assertEqual(rep["titulo"], "Lead repetido")
        otro = self.s.guardar_proyeccion(self.form(lead="556"))           # misma campaña, otro enlace: pregunta
        self.assertIn("pregunta", otro)
        self.assertTrue(self.s.guardar_proyeccion(self.form(lead="556", confirmar_nombre=True))["ok"])
        self.assertEqual(len(self.s.registros), 2)

    def test_editar_marcar_regresar_eliminar_deshacer(self):
        self.s.guardar_proyeccion(self.form())
        rid = self.s.registros[0]["id"]
        self.assertTrue(self.s.guardar_proyeccion(self.form(monto="250", tipo="Exitosa", editando=rid))["ok"])
        self.assertEqual((self.s.registros[0]["monto"], self.s.registros[0]["tipo"]), (250.0, "exitosa"))
        self.s.marcar([rid], "perdida")
        self.assertEqual(self.s.registros[0]["tipo"], "perdida")
        self.assertEqual(self.s.historial(tipo="perdida")["conteo"]["perdida"], 1)
        self.assertEqual(self.s.eliminar([rid])["n"], 1)
        self.assertEqual(self.s.registros, [])
        self.assertTrue(self.s.deshacer()["ok"])
        self.assertEqual(len(self.s.registros), 1)
        self.assertEqual(self.s.regresar([rid])["n"], 1)
        self.assertEqual(self.s.registros, [])
        self.assertEqual(len(self.s.regresos()["filas"]), 1)
        self.assertEqual(self.s.restaurar_regresos([self.s.regresos()["filas"][0]["id"]])["n"], 1)
        self.assertEqual(len(self.s.registros), 1)

    def test_historial_filtros_orden_y_enlaces(self):
        self.s.guardar_proyeccion(self.form(lead="https://dreamtravel.bitrix24.es/crm/deal/details/777/", monto="50"))
        self.s.guardar_proyeccion(self.form(lead="778", monto="900", campana="Peru", tipo="Exitosa"))
        h = self.s.historial(texto="777")
        self.assertEqual([f["idlead"] for f in h["filas"]], ["777"])
        self.assertTrue(h["filas"][0]["url"].startswith("https://"))
        self.s.registros.append({"id": "solo", "fecha": "2026-11-04", "asesor": "Lesly", "lead": "779", "campana": "Peru", "vend": "A", "monto": 5.0, "tipo": "activa"})
        self.assertIsNone(self.s.historial(texto="779")["filas"][0]["url"])         # solo ID: sin enlace
        self.assertEqual(self.s.historial(col="monto", inverso=True)["filas"][0]["idlead"], "778")
        self.assertEqual(self.s.historial(campana="Peru")["filas"][0]["campana"], "Peru")
        self.assertEqual(self.s.historial(vendedor="Susana")["filas"], [])

    def test_borrador(self):
        self.s.guardar_borrador({"lead": "123", "monto": ""})
        self.assertEqual(self.s.estado()["borrador"]["lead"], "123")
        self.s.guardar_proyeccion(self.form(lead="123"))
        self.assertIsNone(self.s.estado()["borrador"])


class PruebaVistaYPanel(Base):
    def test_meses_semana_y_modelo(self):
        self.s.guardar_proyeccion(self.form(monto="1000", tipo="Exitosa"))
        self.s.guardar_vendedor("A", "Lesly", "4000", "")
        p = self.s.panel()
        self.assertEqual(p["modelo"]["equipo"]["neto"], 1000)
        self.assertEqual(p["modelo"]["equipo"]["meta"], 4000)
        self.s.fijar_vista(meses=[9, 10])
        self.assertTrue(self.s.panel()["modelo"]["multi"])
        v = self.s.fijar_vista(meses=[10], modo="Semana", semana=1)["vista"]
        self.assertEqual((v["modo"], v["semana"], v["multi"]), ("Semana", 1, False))
        self.assertEqual(self.s.fijar_vista(semana=99)["vista"]["semana"], 1)      # fuera de rango: se ignora
        self.assertEqual(self.s.campanas()["top"]["campana"], "Cuba")
        self.assertEqual(len(self.s.embudos()["items"]), 4)                       # equipo + 3 vendedores

    def test_vendedores_y_papelera(self):
        r = self.s.guardar_vendedor(None, "Carla", "12000", "3000")
        vid = r["id"]
        self.assertEqual(self.s.datos_vendedor(vid)["mes"], "12000.00")
        self.assertEqual(self.s.guardar_vendedor(None, "carla", "1", "")["campo"], "nombre")   # repetido
        self.assertEqual(self.s.guardar_vendedor(None, "X", "abc", "")["campo"], "mes")
        self.s.guardar_proyeccion(self.form(asesor="Carla"))
        self.s.eliminar_vendedor(vid)
        self.assertEqual(self.s.id_por_nombre("Carla"), None)
        self.assertTrue(self.s.deshacer()["vendedor"])
        self.assertEqual(len(self.s.registros), 1)


class PruebaLecturaBitrix(Base):
    def test_sin_webhook_y_con_lectura(self):
        self.assertEqual(self.s.leer_bitrix("555")["campo"], "sin_webhook")
        self.assertEqual(self.s.guardar_conexion("https://x.bitrix24.es/rest/1/abc/", "auto")["webhook"], "https://x.bitrix24.es/rest/1/abc/")
        lectura = {"monto": 990.0, "monto_vacio": False, "campana": "Panamá", "vendedor": "Susana Perez", "titulo": "", "aviso_campana": ""}
        with mock.patch.object(n, "leer_negociacion", return_value=lectura):
            r = self.s.leer_bitrix("https://x.bitrix24.es/crm/deal/details/555/")
        self.assertEqual((r["asesor"], r["monto"], r["campana"], r["vendedor_conocido"]), ("Susana", "990.00", "Panamá", True))
        with mock.patch.object(n, "leer_negociacion", side_effect=RuntimeError("sin red")):
            self.assertIn("sin red", self.s.leer_bitrix("555")["error"])
        self.assertEqual(self.s.guardar_conexion("http://malo", "")["campo"], "webhook")


class PruebaReportesYArchivos(Base):
    def test_reporte_y_pdf(self):
        self.s.guardar_proyeccion(self.form(monto="500", tipo="Exitosa"))
        r = self.s.guardar_reporte()
        self.assertTrue(r["ok"])
        self.assertIn("pregunta", self.s.guardar_reporte())                   # ya existe: pide confirmar
        self.assertTrue(self.s.guardar_reporte(reemplazar=True)["ok"])
        self.assertEqual(len(self.s.reportes()["filas"]), 1)
        rid = self.s.reportes()["filas"][0]["id"]
        self.assertEqual(self.s.reporte_guardado(rid)["modelo"]["id"], rid)
        self.assertTrue(self.s.descargar_pdf()["cancelado"])                  # el usuario no eligio ruta
        self.dlg.guardar_ruta = os.path.join(self.dir, "r.pdf")
        res = self.s.descargar_pdf(rid)
        with open(res["ruta"], "rb") as f:
            self.assertTrue(f.read().startswith(b"%PDF"))
        self.assertTrue(self.s.abrir_ruta(res["ruta"])["ok"])                 # el PDF recien creado si se puede abrir
        self.assertIn("error", self.s.abrir_ruta("/etc/passwd"))              # cualquier otra ruta no
        self.assertTrue(self.s.eliminar_reporte(rid)["ok"])

    def test_abrir_url_solo_web(self):
        with mock.patch("webbrowser.open") as ab:
            self.assertIn("error", self.s.abrir_url("file:///etc/passwd"))
            self.assertIn("error", self.s.abrir_url("javascript:alert(1)"))
            ab.assert_not_called()
            self.assertTrue(self.s.abrir_url("https://x.bitrix24.es/crm/deal/details/1/")["ok"])
            ab.assert_called_once()

    def test_importar_exportar(self):
        ruta = os.path.join(self.dir, "i.csv")
        with open(ruta, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(["Fecha", "Asesor", "Enlace", "Campaña", "Monto", "Estado"])
            w.writerow(["05/11/2026", "Lesly", "880001", "Imp", "100", "Activa"])
            w.writerow(["05/11/2026", "Nadie", "880002", "Imp", "100", "Activa"])
        self.dlg.abrir_ruta = ruta
        r = self.s.imp_elegir()
        self.assertEqual((r["vista"]["nuevos"], r["vista"]["n_errores"]), (1, 1))
        self.assertEqual(self.s.imp_aplicar(r["mapa"])["nuevos"], 1)
        self.assertEqual(self.s.imp_aplicar(r["mapa"])["error"], "Primero elige un archivo con «Elegir archivo…».")
        info = self.s.exp_info()
        self.assertEqual(len(info["columnas"]), len(n.EXP_COLUMNAS))
        o = {"formato": 1, "alcance": "todos", "tipos": ["activa", "perdida", "exitosa"], "preset": 1}
        self.assertEqual(self.s.exp_vista(o)["n"], 1)
        self.dlg.guardar_ruta = os.path.join(self.dir, "e.csv")
        self.assertEqual(self.s.exp_exportar(o)["n"], 1)
        self.assertIn("880001", open(self.dlg.guardar_ruta, encoding="utf-8").read())
        self.assertIn("error", self.s.exp_exportar(dict(o, tipos=[])))
        self.dlg.guardar_ruta = os.path.join(self.dir, "e.json")
        self.assertEqual(self.s.exp_exportar(dict(o, formato=2, extras=["completo"]))["n"], 1)
        self.assertNotIn("bitrix_webhook", open(self.dlg.guardar_ruta, encoding="utf-8").read())

    def test_borrados_con_copia(self):
        self.s.guardar_proyeccion(self.form())
        r = self.s.borrar_todo()
        self.assertEqual(r["n"], 1)
        self.assertTrue(os.path.exists(r["copia"]))
        self.assertIn("error", self.s.borrar_todo())
        self.s.guardar_proyeccion(self.form(lead="9"))
        self.assertEqual(self.s.vaciar_periodo()["n"], 1)
        self.assertTrue(self.s.deshacer()["ok"])

    def test_se_guarda_en_disco(self):
        self.s.guardar_proyeccion(self.form())
        otro = servicio.Servicio(os.path.join(self.dir, "datos.json"))
        self.assertEqual(len(otro.datos["periodos"]["2026-11"]), 1)


class PruebaApi(Base):
    def test_lista_cerrada_y_errores_controlados(self):
        a = api.Api(self.s)
        for nombre in api.PUBLICOS:
            self.assertTrue(callable(getattr(a, nombre)), nombre)
        self.assertIn("no permitido", api.llamar_por_nombre(a, "cerrar", [])["error"])
        self.assertIn("no permitido", api.llamar_por_nombre(a, "__init__", [])["error"])
        self.assertIn("Error inesperado", api.llamar_por_nombre(a, "fijar_vista", ["x", "y"])["error"])
        json.dumps(a.estado())                                            # todo lo que sale es JSON
        json.dumps(a.panel())
        json.dumps(a.historial())


if __name__ == "__main__":
    unittest.main()
