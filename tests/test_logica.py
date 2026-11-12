import json
import os
import sys
import unittest
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import proyecciones_vendedores as P  # noqa: E402


def datos_base():
    return {"version": 3, "vendedores": [{"id": "A", "nombre": "Lesly", "ci": 0}],
            "metas": {"2026-11": {"A": {"mes": 28000, "sem": 7000}}}, "reportes": [], "config": {}, "periodos": {}}


def reg(i, fecha, monto, tipo, campana="Cuba"):
    return {"id": str(i), "fecha": fecha, "asesor": "Lesly", "lead": "https://x/crm/deal/details/%d/" % i,
            "campana": campana, "vend": "A", "monto": monto, "tipo": tipo}


class PruebaMetas(unittest.TestCase):
    def test_arrastre_semanal(self):
        d = datos_base()
        d["periodos"]["2026-11"] = [reg(1, "2026-11-03", 3000, "exitosa"), reg(2, "2026-11-10", 12000, "exitosa")]
        semanas = P.metas_semanales(d, "2026-11", "A", hoy=date(2026, 11, 20))
        self.assertEqual([s["meta"] for s in semanas[:3]], [7000, 11000, 6000])   # 7k, 7k+4k, 7k-1k

    def test_necesaria(self):
        t = P.con_necesaria(P.calcular_tarjeta(
            [reg(1, "2026-11-03", 15000, "exitosa"), reg(2, "2026-11-04", 17000, "activa")], 28000))
        self.assertAlmostEqual(t["tasa"], 15000 / 32000)
        self.assertAlmostEqual(t["nec_total"], 28000 / (15000 / 32000))


class PruebaImportar(unittest.TestCase):
    def test_json_y_repetidos(self):
        d = datos_base()
        filas = P.tabla_desde_json([{"Fecha": "06/11/2026", "Asesor": "Lesly", "Enlace": "472763", "Monto": "1,500", "Estado": "Exitosa"}])
        r = P.importar_filas(d, filas, aplicar=True)
        self.assertEqual((r["nuevos"], r["total"]), (1, 1500))
        self.assertEqual(P.importar_filas(d, filas)["nuevos"], 0)      # ya existe: no se duplica

    def test_errores(self):
        d = datos_base()
        filas = [["Fecha", "Asesor", "Enlace", "Monto"], ["99/99/2026", "Lesly", "1", "5"], ["06/11/2026", "Nadie", "2", "5"]]
        r = P.importar_filas(d, filas)
        self.assertEqual((r["nuevos"], len(r["errores"])), (0, 2))


class PruebaCampanas(unittest.TestCase):
    def test_mas_solicitada(self):
        rank = P.ranking_campanas([reg(1, "2026-11-03", 10, "exitosa", "A"), reg(2, "2026-11-03", 1, "activa", "B"),
                                   reg(3, "2026-11-03", 1, "perdida", "B"), reg(4, "2026-11-03", 1, "activa", "B")])
        self.assertEqual(rank[0]["campana"], "A")                        # la que mas recaudo
        self.assertEqual(P.campana_mas_solicitada(rank)["campana"], "B")  # la de mas leads


class PruebaVersion(unittest.TestCase):
    def test_hay_version(self):
        self.assertRegex(P.VERSION_APP, r"^\d+\.\d+(\.\d+)?$")


if __name__ == "__main__":
    unittest.main()
