import io
import json
import os
import sys
import types
import urllib.parse
import unittest
from datetime import date, datetime

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

    def test_porcentaje_faltante(self):
        regs = [reg(1, "2026-11-02", 100, "exitosa"), reg(2, "2026-11-03", 300, "activa"), reg(3, "2026-11-04", 100, "perdida")]
        # semana: meta semanal 250 de 1,000 mensual; vendido 100 -> 25% - 10% = 15%; tasa 20% -> faltan 750 por proyectar
        sem = P.con_necesaria(P.calcular_tarjeta(regs, 250), 1000)
        self.assertAlmostEqual(sem["pct_falta"], 0.15)
        self.assertAlmostEqual(sem["nec_falta"], 750)
        # mes: 100% - 100/1000 = 90%
        mes = P.con_necesaria(P.calcular_tarjeta(regs, 1000), 1000)
        self.assertAlmostEqual(mes["pct_falta"], 0.90)
        self.assertAlmostEqual(mes["nec_falta"], 4500)

    def test_regresar_a_seguimiento(self):
        d = {"version": 3, "vendedores": [], "metas": {}, "reportes": [], "config": {},
             "periodos": {"2026-11": [reg(1, "2026-11-02", 100, "exitosa"), reg(2, "2026-11-03", 300, "activa")],
                          "2026-10": [reg(3, "2026-10-02", 50, "activa")]}}
        n = P.regresar_a_seguimiento(d, ["2", "3", "no-existe"], datetime(2026, 11, 17, 12, 0))
        self.assertEqual(n, 2)
        self.assertEqual([r["id"] for r in d["periodos"]["2026-11"]], ["1"])         # ya no cuentan en tablas ni totales
        self.assertEqual(d["periodos"]["2026-10"], [])
        self.assertEqual({h["reg"]["id"]: h["periodo"] for h in d["regresos"]}, {"2": "2026-11", "3": "2026-10"})
        rid = next(h["id"] for h in d["regresos"] if h["reg"]["id"] == "2")
        self.assertEqual(P.restaurar_regresos(d, [rid]), 1)                          # vuelve a su periodo
        self.assertEqual(sorted(r["id"] for r in d["periodos"]["2026-11"]), ["1", "2"])
        self.assertEqual(len(d["regresos"]), 1)
        self.assertEqual(P.restaurar_regresos(d, ["nada"]), 0)

    def test_enlaces(self):
        con = reg(7, "2026-11-02", 1, "activa")
        con["lead"] = "https://x.bitrix24.es/crm/deal/details/777/"
        sin = dict(con, lead="888")
        self.assertEqual(P.url_de(con), con["lead"])
        self.assertIsNone(P.url_de(sin))
        self.assertEqual(P.etiqueta_id(con), "↗ 777")
        self.assertEqual(P.etiqueta_id(sin), "888")


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


class PruebaVariosMeses(unittest.TestCase):
    def test_reporte_combinado(self):
        d = datos_base()
        d["metas"]["2026-10"] = {"A": {"mes": 10000, "sem": None}}
        d["metas"].pop("2026-11")
        d["periodos"] = {"2026-10": [reg(1, "2026-10-05", 4000, "exitosa"), reg(2, "2026-10-06", 1000, "perdida", "Peru")],
                         "2026-11": [reg(3, "2026-11-03", 6000, "exitosa"), reg(4, "2026-11-04", 2000, "activa", "Peru")]}
        m = P.construir_reporte_multi(d, ["2026-11", "2026-10"], hoy=date(2026, 11, 15))
        e = m["equipo"]
        self.assertEqual((m["periodo"], len(m["semanas"])), ("Oct–Nov 2026", 2))
        self.assertEqual((e["neto"], e["proy"], e["perdidas"], e["meta"]), (10000, 2000, 1000, 20000))
        self.assertAlmostEqual(e["esp_monto"], 15000)       # octubre completo + mitad de noviembre

    def test_etiquetas(self):
        self.assertEqual(P.etiqueta_meses(["2026-%02d" % i for i in range(1, 13)]), "Todo 2026")
        self.assertEqual(P.etiqueta_meses(["2026-01", "2026-03"]), "Ene, Mar 2026")
        self.assertEqual(P.etiqueta_meses(["2026-02", "2026-03", "2026-04"]), "Feb–Abr 2026")


class PruebaVersion(unittest.TestCase):
    def test_hay_version(self):
        self.assertRegex(P.VERSION_APP, r"^\d+\.\d+(\.\d+)?$")



# --------------------------------------------------- lectura desde Bitrix24
class _Respuesta(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        pass


def _bitrix_falso(deals, campos, usuarios):
    def abrir(req, timeout=0):
        metodo = req.full_url.rsplit("/", 1)[1][:-len(".json")]
        p = dict(urllib.parse.parse_qsl(req.data.decode("utf-8")))
        if metodo == "crm.deal.fields":
            res = campos
        elif metodo == "crm.item.get":
            res = {"item": {"title": PROMOS.get(p.get("id"), "")}} if p.get("entityTypeId") == "1040" else {}
        elif metodo == "crm.deal.get":
            res = deals.get(p.get("id"))
        else:
            res = [usuarios[p["ID"]]] if p.get("ID") in usuarios else []
        return _Respuesta(json.dumps({"result": res}).encode("utf-8"))
    return abrir


CAMPOS_BITRIX = {
    "UF_CRM_1": {"type": "enumeration", "formLabel": "Seleccione Campaña", "listLabel": "Seleccione Campaña",
                 "items": [{"ID": "913", "VALUE": "MEDELLÍN-PROMO-2026-08-26"}]},
    "UF_CRM_2": {"type": "enumeration", "formLabel": "Campaña Historico", "listLabel": "Campaña Historico",
                 "items": [{"ID": "7", "VALUE": "VIEJA"}]},
    "UF_CRM_3": {"type": "string", "formLabel": "Campaña", "listLabel": "Campaña"},
}
CAMPOS_BITRIX.update({
    "PARENT_ID_1040": {"type": "crm_entity", "title": "PROMOCIONES", "settings": {"parentEntityTypeId": 1040}},
    "UF_CRM_9": {"type": "double", "formLabel": "ID SPA Promocion", "listLabel": "ID SPA Promocion"},
    "UF_CRM_DEAL_DT_SELECCIONE_PROMOCION": {"type": "rest_133_dt_promo_picker", "formLabel": "Seleccione Promoción"},
})
PROMOS = {"139": "GUATEMALA-PERSONALIZADO", "79": "EL SALVADOR-AÑO NUEVO-2026-09-01"}
CFG_BITRIX = {"bitrix_webhook": "https://portal.bitrix24.es/rest/1/abc/"}


class PruebaLecturaBitrix(unittest.TestCase):
    def leer(self, deal):
        abrir = _bitrix_falso({"5": dict(deal, ID="5")}, CAMPOS_BITRIX,
                              {"9": {"NAME": "Josue", "LAST_NAME": "Muñoz"}})
        return P.leer_negociacion(CFG_BITRIX, "5", abrir)

    def test_prefiere_la_campana_que_elige_el_vendedor(self):
        d = self.leer({"OPPORTUNITY": "3085.43", "ASSIGNED_BY_ID": "9", "UF_CRM_1": "913", "UF_CRM_3": ["RIO-2026-08-03"]})
        self.assertEqual(d["campana"], "Medellín-promo-2026-08-26")
        self.assertEqual(d["monto"], 3085.43)
        self.assertFalse(d["monto_vacio"])
        self.assertEqual(d["vendedor"], "Josue Muñoz")

    def test_usa_el_texto_si_la_lista_esta_vacia_e_ignora_el_historico(self):
        d = self.leer({"OPPORTUNITY": "0.00", "UF_CRM_1": "", "UF_CRM_2": "7", "UF_CRM_3": ["PANAMÁ-PROMO"]})
        self.assertEqual(d["campana"], "Panamá-promo")
        self.assertTrue(d["monto_vacio"])

    def test_sin_campana(self):
        d = self.leer({"OPPORTUNITY": "", "UF_CRM_1": "", "UF_CRM_2": "7", "UF_CRM_3": []})
        self.assertEqual(d["campana"], "")
        self.assertTrue(d["monto_vacio"])


class PruebaPromocion(unittest.TestCase):
    def leer(self, deal, cfg=CFG_BITRIX):
        abrir = _bitrix_falso({"5": dict(deal, ID="5", TITLE="ANTONIO-SALVADOR - ELMER")}, CAMPOS_BITRIX, {})
        return P.leer_negociacion(cfg, "5", abrir)

    def test_coinciden(self):
        d = self.leer({"PARENT_ID_1040": "139", "UF_CRM_9": "139", "UF_CRM_DEAL_DT_SELECCIONE_PROMOCION": "139",
                       "UF_CRM_1": "913"})
        self.assertEqual(d["campana"], "Guatemala-personalizado")
        self.assertEqual(d["aviso_campana"], "")

    def test_no_coinciden_usa_el_utm_y_avisa(self):
        d = self.leer({"PARENT_ID_1040": "139", "UF_CRM_9": "139.00", "UF_CRM_DEAL_DT_SELECCIONE_PROMOCION": "79"})
        self.assertEqual(d["campana"], "Guatemala-personalizado")
        self.assertIn("no coinciden", d["aviso_campana"])
        self.assertIn("El salvador-año nuevo-2026-09-01", d["aviso_campana"])

    def test_solo_seleccionada_o_solo_id(self):
        self.assertEqual(self.leer({"UF_CRM_DEAL_DT_SELECCIONE_PROMOCION": "79"})["campana"], "El salvador-año nuevo-2026-09-01")
        self.assertEqual(self.leer({"UF_CRM_9": 139.0})["campana"], "Guatemala-personalizado")

    def test_nunca_usa_el_titulo_si_hay_promocion(self):
        cfg = dict(CFG_BITRIX, campo_campana="TITLE")
        self.assertEqual(self.leer({"PARENT_ID_1040": "139"}, cfg)["campana"], "Guatemala-personalizado")


class _Var:
    def __init__(self, v=""):
        self.v = v

    def get(self):
        return self.v

    def set(self, v):
        self.v = v


class PruebaLlenadoFormulario(unittest.TestCase):
    """Una lectura nueva reemplaza lo que lleno la anterior, aunque ahora venga vacio."""

    def setUp(self):
        app = types.SimpleNamespace(
            datos={"vendedores": [{"id": "v1", "nombre": "Josue"}, {"id": "v2", "nombre": "Elmer"}], "periodos": {}},
            nombre=lambda vid: {"v1": "Josue", "v2": "Elmer"}[vid])
        self.avisos = []
        self.f = types.SimpleNamespace(
            app=app, editando=None, _auto={}, var_lead=_Var(), var_asesor=_Var(), var_camp=_Var(), var_monto=_Var(),
            lbl_auto=types.SimpleNamespace(config=lambda **k: None),
            aviso_monto=lambda mostrar, campana="": self.avisos.append(mostrar))

    def leer(self, did, monto, campana, vendedor):
        self.f.var_lead.set(did)
        res = {"ok": {"monto": monto, "monto_vacio": monto <= 0, "campana": campana, "vendedor": vendedor, "titulo": ""}}
        P.PaginaIngreso.aplicar_lectura(self.f, did, res)

    def test_no_arrastra_datos_de_la_negociacion_anterior(self):
        self.leer("1", 990.0, "Panamá", "Josue Muñoz")
        self.assertEqual((self.f.var_monto.get(), self.f.var_camp.get(), self.f.var_asesor.get()), ("990.00", "Panamá", "Josue"))
        self.assertEqual(self.avisos[-1], False)
        self.leer("2", 0.0, "", "Elmer Aceituno")
        self.assertEqual((self.f.var_monto.get(), self.f.var_camp.get(), self.f.var_asesor.get()), ("", "", "Elmer"))
        self.assertEqual(self.avisos[-1], True)

    def test_respeta_lo_escrito_a_mano(self):
        self.leer("1", 990.0, "Panamá", "Josue Muñoz")
        self.f.var_monto.set("1200")
        self.f.var_camp.set("Mi campaña")
        self.leer("2", 0.0, "", "Josue Muñoz")
        self.assertEqual((self.f.var_monto.get(), self.f.var_camp.get()), ("1200", "Mi campaña"))


if __name__ == "__main__":
    unittest.main()
