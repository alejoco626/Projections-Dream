# -*- coding: utf-8 -*-
"""
Servicio: el "cerebro" de la app, sin ninguna interfaz.

Es lo que antes vivia en la clase App (Tkinter): el estado (meses, semana, medida), los datos, guardar,
eliminar/deshacer, reportes, importar/exportar, Bitrix24 y actualizaciones. La ventana (pywebview) y las pruebas
llaman a estos metodos; todos devuelven diccionarios simples (JSON) y nunca abren ventanas de aviso por si solos:
los avisos y las preguntas las muestra la interfaz web.

Convencion de respuesta:  {"ok": True, ...}  o  {"error": "texto", "campo": "nombre del campo (opcional)"}.
"""
import json
import os
import queue
import re
import sys
import threading
import traceback
import uuid
import webbrowser
from datetime import date, datetime

import actualizador
import novedades
import nucleo as n
from nucleo import (MESES, MESES_ABR, TIPOS_ORDEN, TIPO_LABEL, LABEL_TIPO, TODOS, TODAS, SIN_CAMP, VERSION_APP,
                    fm, pct, norm)

URL_WEB = re.compile(r"https?://[^\s]+$", re.I)


def _err(msg, campo=None):
    r = {"error": msg}
    if campo:
        r["campo"] = campo
    return r


class DialogosVacios:
    """Dialogos de archivo: la ventana real los reemplaza; en pruebas no elige nada."""

    def abrir(self, tipos):
        return None

    def guardar(self, nombre, ext, tipos):
        return None

    def externo(self, ruta):
        pass


class Servicio:
    def __init__(self, ruta=n.DATA_FILE, dialogos=None):
        self.ui = dialogos or DialogosVacios()
        self.almacen = n.Almacen(ruta)
        self.datos, self.aviso_carga = self.almacen.cargar()
        self.almacen.respaldar()
        self._guardado = self._serializar()
        self.papelera = None
        hoy = date.today()
        self.anio = hoy.year
        self.mes_principal = hoy.month - 1
        self.meses_sel = {hoy.month - 1}
        self.modo = "Mes"
        self.medida = n.MEDIDAS[0]
        self.semana = self.semana_defecto()
        self._imp = None
        self._info_act = None
        self._prog_act = {"pct": 0, "fin": False, "error": None, "ruta": None}
        self._pdfs = set()
        self._lock = threading.RLock()

    # ------------------------------------------------------------------ estado
    def _serializar(self):
        return json.dumps(self.datos, ensure_ascii=False, indent=1)

    def guardar_todo(self):
        with self._lock:
            try:
                s = self._serializar()
            except (TypeError, ValueError):
                return False
            if s == self._guardado:
                return True
            try:
                self.almacen.guardar(self.datos)
            except OSError:
                return False
            self._guardado = s
            return True

    def cerrar(self):
        self.guardar_todo()

    @property
    def nombres(self):
        return n.vend_nombres(self.datos)

    def nombre(self, vid):
        return self.nombres.get(vid, "(eliminado)")

    def id_por_nombre(self, nombre):
        for v in self.datos["vendedores"]:
            if v["nombre"] == nombre:
                return v["id"]
        return None

    def clave(self):
        return n.clave_periodo(self.anio, self.mes_principal)

    def claves(self):
        return [n.clave_periodo(self.anio, i) for i in sorted(self.meses_sel)]

    @property
    def es_multi(self):
        return len(self.meses_sel) > 1

    @property
    def registros(self):
        return self.datos["periodos"].setdefault(self.clave(), [])

    def registros_vista(self):
        return [r for c in self.claves() for r in self.datos["periodos"].get(c, [])]

    def registros_filtrados(self):
        if self.es_multi:
            return self.registros_vista()
        return n.filtrar_tiempo(self.registros, self.clave(), self.modo, self.semana)

    def etiquetas_semanas(self):
        return ["Semana {} ({}–{})".format(i, a, b) for i, (a, b) in enumerate(n.rangos_semanas(self.clave()), 1)]

    def semana_defecto(self):
        hoy = date.today()
        total = len(n.rangos_semanas(self.clave()))
        if n.clave_periodo(hoy.year, hoy.month - 1) == self.clave():
            return min((hoy.day - 1) // 7, total - 1) + 1
        return 1

    def grafica(self, area):
        v = self.datos.get("config", {}).get("graficas", {}).get(area)
        return v if v in [k for k, _ in n.GRAFICAS[area]] else n.GRAFICA_DEF[area]

    def reporte(self):
        if self.es_multi:
            return n.construir_reporte_multi(self.datos, self.claves())
        return n.construir_reporte(self.datos, self.clave(), self.modo, self.semana if self.modo == "Semana" else None)

    def etiqueta_periodo(self):
        return n.etiqueta_meses(self.claves())

    def cuando(self):
        txt = self.etiqueta_periodo()
        if self.modo == "Semana" and not self.es_multi:
            return txt + " · Semana {}".format(self.semana)
        return txt + (" · Meses combinados" if self.es_multi else " · Mes completo")

    def _vista(self):
        return {
            "anio": self.anio, "mes_principal": self.mes_principal, "meses": sorted(self.meses_sel),
            "modo": self.modo, "semana": self.semana, "medida": self.medida, "multi": self.es_multi,
            "semanas": self.etiquetas_semanas(), "periodo": self.etiqueta_periodo(),
            "titulo_periodo": n.nombre_periodo(self.clave()), "cuando": self.cuando(),
        }

    def _tras_cambio(self, guardar=True):
        if guardar:
            self.guardar_todo()

    # ---------------------------------------------------------------- arranque
    def estado(self):
        """Todo lo que la interfaz necesita al abrir (y despues de cambios que afectan a varias secciones)."""
        cfg = self.datos["config"]
        anios = sorted({str(y) for y in range(2024, 2036)} | {k[:4] for k in self.datos["periodos"]})
        return {
            "version": VERSION_APP, "app": n.APP_NAME, "ruta_datos": self.almacen.ruta,
            "tema": cfg.get("tema", "claro"), "paletas": {"claro": n.LIGHT, "oscuro": n.DARK},
            "vendedores": [dict(v) for v in self.datos["vendedores"]],
            "vista": self._vista(), "anios": anios, "meses": MESES, "meses_abr": MESES_ABR,
            "tipos": [{"id": t, "label": TIPO_LABEL[t]} for t in TIPOS_ORDEN],
            "graficas": {a: self.grafica(a) for a, _ in n.GRAFICA_AREAS},
            "opciones_graficas": {a: [{"id": k, "label": l} for k, l in n.GRAFICAS[a]] for a in n.GRAFICAS},
            "areas_graficas": [{"id": a, "label": l} for a, l in n.GRAFICA_AREAS],
            "medidas": n.MEDIDAS, "n_regresos": len(self.datos.get("regresos", [])),
            "bitrix": bool(cfg.get("bitrix_webhook")), "hay_papelera": bool(self.papelera),
            "borrador": cfg.get("borrador"), "aviso": self.aviso_carga, "empaquetado": bool(getattr(sys, "frozen", False)),
        }

    def fijar_vista(self, meses=None, anio=None, modo=None, semana=None, medida=None, mes_principal=None):
        if anio is not None:
            self.anio = int(anio)
        if meses is not None:
            sel = {int(m) for m in meses if 0 <= int(m) <= 11}
            if sel:
                self.meses_sel = sel
                if self.mes_principal not in sel:
                    self.mes_principal = min(sel)
        if mes_principal is not None and 0 <= int(mes_principal) <= 11:
            self.mes_principal = int(mes_principal)
            self.meses_sel = {self.mes_principal}
        if modo in ("Mes", "Semana"):
            self.modo = modo
        if medida in n.MEDIDAS:
            self.medida = medida
        total = len(n.rangos_semanas(self.clave()))
        if semana is not None and 1 <= int(semana) <= total:
            self.semana = int(semana)
        elif meses is not None or anio is not None or mes_principal is not None:
            self.semana = self.semana_defecto()
        self.semana = max(1, min(self.semana, total))
        return {"ok": True, "vista": self._vista()}

    def fijar_tema(self, tema):
        self.datos["config"]["tema"] = "oscuro" if tema == "oscuro" else "claro"
        self.guardar_todo()
        return {"ok": True}

    # ------------------------------------------------------------------ panel
    def panel(self):
        m = self.reporte()
        top = m["campanas"][0] if m["campanas"] and m["campanas"][0]["neto"] > 0 else None
        multi = bool(m.get("multi"))
        return {"ok": True, "modelo": m, "top": top, "vista": self._vista(), "tipo_grafica": self.grafica("panel"),
                "etq_semanas": [x["etq"] for x in m["semanas"]] if multi else None,
                "semanas_vend": {f["id"]: [[s["filas"][f["id"]]["neto"], s["filas"][f["id"]]["proy"]] for s in m["semanas"]]
                                 for f in m["filas"]}}

    # --------------------------------------------------------------- campañas
    def campanas(self, vendedor=TODOS):
        regs = self.registros_filtrados()
        if vendedor != TODOS:
            vid = self.id_por_nombre(vendedor)
            regs = [r for r in regs if r["vend"] == vid]
        rank = n.ranking_campanas(regs)
        top = n.campana_mas_solicitada(rank)
        return {"ok": True, "rank": rank, "total": sum(e["neto"] for e in rank), "top": top, "cuando": self.cuando(),
                "vendedores": [TODOS] + [v["nombre"] for v in self.datos["vendedores"]], "vendedor": vendedor,
                "tipo_rank": self.grafica("rank"), "tipo_dona": self.grafica("dona"), "vista": self._vista()}

    # ---------------------------------------------------------------- embudos
    def embudos(self):
        regs = self.registros_filtrados()
        items = [{"id": "TOTAL", "nombre": "Equipo (todos)", "ci": None, "embudo": n.calcular_embudo(regs)}]
        for v in self.datos["vendedores"]:
            items.append({"id": v["id"], "nombre": v["nombre"], "ci": v.get("ci", 0),
                          "embudo": n.calcular_embudo([r for r in regs if r["vend"] == v["id"]])})
        return {"ok": True, "items": items, "cuando": self.cuando(), "tipo": self.grafica("embudo"),
                "medida": self.medida, "vista": self._vista()}

    # --------------------------------------------------------------- historial
    def _fila(self, pos, r):
        d = date.fromisoformat(r["fecha"])
        return {"id": r["id"], "n": pos, "fecha": d.strftime("%d/%m/%Y"), "fecha_iso": r["fecha"], "vend": r["vend"],
                "vendedor": self.nombre(r["vend"]), "ci": next((v.get("ci", 0) for v in self.datos["vendedores"] if v["id"] == r["vend"]), 0),
                "idlead": n.extraer_id(r["lead"]), "etq_id": n.etiqueta_id(r), "lead": r["lead"], "url": n.url_de(r),
                "campana": r["campana"] or "", "monto": r["monto"], "tipo": r["tipo"]}

    def historial(self, texto="", vendedor=TODOS, campana=TODAS, tipo=TODOS, col="n", inverso=False):
        regs = self.registros_vista()
        nombres = self.nombres
        vid = TODOS if vendedor == TODOS else self.id_por_nombre(vendedor)
        if vendedor != TODOS and vid is None:
            vid = TODOS
        tipo = tipo if tipo in TIPOS_ORDEN else TODOS
        conteo = {t: 0 for t in TIPOS_ORDEN}
        for _, r in n.filtrar(regs, nombres, texto, vid, campana, TODOS):
            conteo[r["tipo"]] += 1
        filas = n.filtrar(regs, nombres, texto, vid, campana, tipo)
        claves = {
            "n": lambda p, r: p, "fecha": lambda p, r: r["fecha"], "vend": lambda p, r: norm(self.nombre(r["vend"])),
            "id": lambda p, r: int(n.extraer_id(r["lead"]) or 0), "lead": lambda p, r: norm(r["lead"]),
            "campana": lambda p, r: norm(r["campana"]), "monto": lambda p, r: r["monto"],
            "tipo": lambda p, r: TIPOS_ORDEN.index(r["tipo"]),
        }
        f = claves.get(col, claves["n"])
        filas = sorted(filas, key=lambda pr: f(*pr), reverse=bool(inverso))
        suma = {t: sum(r["monto"] for _, r in filas if r["tipo"] == t) for t in TIPOS_ORDEN}
        camps = sorted({r["campana"] for r in regs if r["campana"]})
        if any(not r["campana"] for r in regs):
            camps.append(SIN_CAMP)
        res = n.resumir(regs, [v["id"] for v in self.datos["vendedores"]])
        resumen = []
        for k in [v["id"] for v in self.datos["vendedores"]] + ["TOTAL"]:
            d = res[k]
            tn = sum(d[t][0] for t in TIPOS_ORDEN)
            tm = sum(d[t][1] for t in TIPOS_ORDEN)
            resumen.append({"id": k, "nombre": "Total" if k == "TOTAL" else self.nombre(k), "d": d, "n": tn, "m": tm,
                            "pp": pct(d["perdida"][1], tm)})
        return {"ok": True, "filas": [self._fila(p, r) for p, r in filas], "total_vista": len(regs),
                "conteo": conteo, "suma": suma, "total": sum(suma.values()), "campanas": camps,
                "vendedores": [v["nombre"] for v in self.datos["vendedores"]], "resumen": resumen,
                "periodo": self.etiqueta_periodo(), "hay_papelera": bool(self.papelera)}

    def _buscar(self, rid):
        for clave, lista in self.datos["periodos"].items():
            for r in lista:
                if r["id"] == rid:
                    return clave, r
        return None, None

    def marcar(self, ids, tipo):
        if tipo not in TIPOS_ORDEN:
            return _err("Estado no válido.")
        ids = set(ids)
        k = 0
        for lista in self.datos["periodos"].values():
            for r in lista:
                if r["id"] in ids:
                    r["tipo"] = tipo
                    k += 1
        self.guardar_todo()
        return {"ok": True, "n": k}

    def eliminar(self, ids):
        ids = set(ids)
        por = {}
        for clave, regs in self.datos["periodos"].items():
            b = [(i, r) for i, r in enumerate(regs) if r["id"] in ids]
            if b:
                por[clave] = b
        if not por:
            return {"ok": True, "n": 0}
        self.papelera = {"tipo": "registros", "regs": por}
        for clave in por:
            self.datos["periodos"][clave] = [r for r in self.datos["periodos"][clave] if r["id"] not in ids]
        self.guardar_todo()
        return {"ok": True, "n": sum(len(v) for v in por.values())}

    def deshacer(self):
        p = self.papelera
        if not p:
            return _err("No hay ninguna eliminación para deshacer.")
        if p["tipo"] == "vendedor":
            self.datos["vendedores"].insert(min(p["pos"], len(self.datos["vendedores"])), p["vend"])
            for c, m in p["metas"].items():
                self.datos["metas"].setdefault(c, {})[p["vend"]["id"]] = m
        total = 0
        for clave, borrados in p["regs"].items():
            lista = self.datos["periodos"].setdefault(clave, [])
            for i, r in borrados:
                lista.insert(min(i, len(lista)), r)
            total += len(borrados)
        self.papelera = None
        self.guardar_todo()
        return {"ok": True, "n": total, "vendedor": p["tipo"] == "vendedor"}

    def regresar(self, ids):
        k = n.regresar_a_seguimiento(self.datos, set(ids))
        self.guardar_todo()
        return {"ok": True, "n": k}

    def regresos(self):
        hist = sorted(self.datos.get("regresos", []), key=lambda h: h["regreso"], reverse=True)
        filas = []
        for h in hist:
            r = h["reg"]
            filas.append({"id": h["id"], "regreso": datetime.fromisoformat(h["regreso"]).strftime("%d/%m/%Y %H:%M"),
                          "vendedor": self.nombre(r["vend"]), "ci": next((v.get("ci", 0) for v in self.datos["vendedores"] if v["id"] == r["vend"]), 0),
                          "etq_id": n.etiqueta_id(r), "url": n.url_de(r), "campana": r["campana"] or "", "monto": r["monto"],
                          "tipo": r["tipo"], "periodo": n.nombre_periodo(h["periodo"])})
        return {"ok": True, "filas": filas}

    def restaurar_regresos(self, rids):
        k = n.restaurar_regresos(self.datos, set(rids))
        self.guardar_todo()
        return {"ok": True, "n": k}

    # ----------------------------------------------------------------- ingreso
    def ingreso(self):
        regs = self.registros
        por = {t: sum(r["monto"] for r in regs if r["tipo"] == t) for t in TIPOS_ORDEN}
        camps = sorted({r["campana"] for lista in self.datos["periodos"].values() for r in lista if r["campana"]})
        ult = [self._fila(i, r) for i, r in reversed(list(enumerate(regs, 1))[-10:])]
        return {"ok": True, "titulo_periodo": n.nombre_periodo(self.clave()), "ultimas": ult, "n": len(regs), "por": por,
                "total": sum(por.values()), "campanas": camps, "asesores": [v["nombre"] for v in self.datos["vendedores"]],
                "hoy": date.today().strftime("%d/%m/%Y"), "borrador": self.datos["config"].get("borrador"),
                "bitrix": bool(self.datos["config"].get("bitrix_webhook"))}

    def leer_bitrix(self, lead):
        """Lee la negociacion (puede tardar unos segundos; cada llamada corre en su propio hilo)."""
        did = n.extraer_id(n.limpiar_lead(lead or ""))
        cfg = self.datos["config"]
        if not did:
            return _err("Pega primero el enlace o el ID del lead.")
        if not cfg.get("bitrix_webhook"):
            return _err("Configura el webhook en Configuración → Conexión con Bitrix24.", "sin_webhook")
        try:
            d = n.leer_negociacion(cfg, did)
        except Exception as e:
            return _err("No se pudo leer: " + str(e).replace("\n", " "))
        vid = n.vendedor_por_nombre(self.datos, d["vendedor"])
        dup, _ = n.buscar_duplicados(self.datos, n.limpiar_lead(lead), vid, "", None)
        return {"ok": True, "id": did, "asesor": self.nombre(vid) if vid else "", "campana": d["campana"],
                "monto": "" if d["monto_vacio"] else "{:.2f}".format(d["monto"]), "monto_vacio": d["monto_vacio"],
                "aviso_campana": d.get("aviso_campana", ""), "vendedor_bitrix": d["vendedor"], "vendedor_conocido": bool(vid),
                "duplicado": ("{} ({})".format(n.nombre_periodo(dup[0]), TIPO_LABEL[dup[1]["tipo"]]) if dup else None)}

    def guardar_proyeccion(self, f):
        """f = {fecha, asesor, lead, campana, monto, tipo(label), editando, confirmar_nombre}."""
        if not self.datos["vendedores"]:
            return _err("Primero agrega al menos un vendedor en «Vendedores y metas».")
        try:
            fecha = n.parse_fecha(f.get("fecha", ""))
        except ValueError:
            return _err("La fecha no es válida. Usa el formato dd/mm/aaaa.", "fecha")
        vid = self.id_por_nombre(f.get("asesor", ""))
        if not vid:
            return _err("Elige el asesor (vendedor).", "asesor")
        lead = n.limpiar_lead(f.get("lead", ""))
        if not lead:
            return _err("Pega el enlace del lead (o su ID).", "lead")
        try:
            monto = n.parse_monto(f.get("monto", ""))
        except ValueError:
            return _err("El monto no es válido (ejemplo: 1300 o 1,300.50).", "monto")
        tipo = LABEL_TIPO.get(f.get("tipo", ""), f.get("tipo") if f.get("tipo") in TIPOS_ORDEN else "activa")
        editando = f.get("editando") or None
        dup_e, dup_n = n.buscar_duplicados(self.datos, lead, vid, f.get("campana", ""), editando)
        if dup_e:
            per, r = dup_e
            return {"error": "Este enlace ya está registrado (el monto puede repetirse, el enlace no):\n\n{} · {} · {} · {} · {}\n\n"
                             "Búscalo en el Historial para editarlo o cambiarle el estado.".format(
                                 n.nombre_periodo(per), self.nombre(r["vend"]), r["campana"] or "sin campaña", fm(r["monto"]),
                                 TIPO_LABEL[r["tipo"]]), "campo": "lead", "titulo": "Lead repetido"}
        if dup_n and not f.get("confirmar_nombre"):
            per, r = dup_n
            return {"pregunta": "{} ya tiene la campaña «{}» en {} con otro enlace ({}, {}).\n\n¿Es otra negociación distinta? ¿Guardar?".format(
                self.nombre(r["vend"]), r["campana"], n.nombre_periodo(per), n.extraer_id(r["lead"]), fm(r["monto"])),
                "titulo": "Posible repetido"}
        datos = {"fecha": fecha.isoformat(), "asesor": self.nombre(vid), "lead": lead,
                 "campana": n.canon_campana(f.get("campana", "")), "vend": vid, "monto": monto, "tipo": tipo}
        if editando:
            for r in self.registros:
                if r["id"] == editando:
                    r.update(datos)
        else:
            datos["id"] = uuid.uuid4().hex[:10]
            self.registros.append(datos)
        self.datos["config"].pop("borrador", None)
        self.guardar_todo()
        return {"ok": True}

    def editar_registro(self, rid):
        clave, r = self._buscar(rid)
        if not r:
            return _err("No se encontró la proyección.")
        self.mes_principal = int(clave[5:7]) - 1
        self.anio = int(clave[:4])
        if self.mes_principal not in self.meses_sel:
            self.meses_sel = {self.mes_principal}
        return {"ok": True, "vista": self._vista(), "reg": {
            "id": r["id"], "fecha": date.fromisoformat(r["fecha"]).strftime("%d/%m/%Y"), "asesor": self.nombre(r["vend"]),
            "campana": r["campana"], "monto": "{:.2f}".format(r["monto"]), "tipo": TIPO_LABEL[r["tipo"]], "lead": r["lead"]}}

    def guardar_borrador(self, b):
        if b and ((b.get("lead") or "").strip() or (b.get("monto") or "").strip()):
            self.datos["config"]["borrador"] = {k: str(b.get(k, "")) for k in ("fecha", "asesor", "campana", "monto", "tipo", "lead")}
        else:
            self.datos["config"].pop("borrador", None)
        self.guardar_todo()
        return {"ok": True}

    # --------------------------------------------------- vendedores y metas
    def vendedores_metas(self):
        filas = []
        todos = [r for regs in self.datos["periodos"].values() for r in regs]
        ms = []
        for v in self.datos["vendedores"]:
            m = n.meta_vigente(self.datos, self.clave(), v["id"])
            ms.append(m)
            filas.append({"id": v["id"], "nombre": v["nombre"], "ci": v.get("ci", 0), "mes": m["mes"], "sem": m["sem"],
                          "sem_auto": m["mes"] / 4.0, "n": sum(1 for r in todos if r["vend"] == v["id"])})
        tot = {"mes": sum(m["mes"] for m in ms), "sem": sum(m["sem"] or m["mes"] / 4.0 for m in ms), "n": len(todos)}
        return {"ok": True, "filas": filas, "total": tot, "titulo_periodo": n.nombre_periodo(self.clave())}

    def guardar_vendedor(self, vid, nombre, mes, sem):
        nombre = n.canon_vendedor(nombre or "")
        if not nombre:
            return _err("Escribe el nombre del vendedor.", "nombre")
        if any(norm(v["nombre"]) == norm(nombre) and v["id"] != vid for v in self.datos["vendedores"]):
            return _err("Ya existe un vendedor con ese nombre.", "nombre")
        try:
            m = n.parse_monto(mes) if str(mes or "").strip() else 0.0
            s = n.parse_monto(sem) if str(sem or "").strip() else None
        except ValueError:
            return _err("Las metas deben ser números (ejemplo: 20000).", "mes")
        if vid:
            if not any(v["id"] == vid for v in self.datos["vendedores"]):
                return _err("No se encontró al vendedor.")
            for v in self.datos["vendedores"]:
                if v["id"] == vid:
                    v["nombre"] = nombre
        else:
            vid = "V" + uuid.uuid4().hex[:6]
            self.datos["vendedores"].append({"id": vid, "nombre": nombre, "ci": n.siguiente_color(self.datos)})
        self.datos["metas"].setdefault(self.clave(), {})[vid] = {"mes": m, "sem": s}
        self.guardar_todo()
        return {"ok": True, "id": vid}

    def datos_vendedor(self, vid):
        v = next((x for x in self.datos["vendedores"] if x["id"] == vid), None)
        if not v:
            return _err("No se encontró al vendedor.")
        m = n.meta_vigente(self.datos, self.clave(), vid)
        return {"ok": True, "nombre": v["nombre"], "mes": "{:.2f}".format(m["mes"]) if m["mes"] else "",
                "sem": "{:.2f}".format(m["sem"]) if m["sem"] else "", "titulo_periodo": n.nombre_periodo(self.clave())}

    def eliminar_vendedor(self, vid):
        vs = self.datos["vendedores"]
        pos = next((i for i, v in enumerate(vs) if v["id"] == vid), None)
        if pos is None:
            return _err("No se encontró al vendedor.")
        regs = {}
        for clave, lista in self.datos["periodos"].items():
            borr = [(i, r) for i, r in enumerate(lista) if r["vend"] == vid]
            if borr:
                regs[clave] = borr
                self.datos["periodos"][clave] = [r for r in lista if r["vend"] != vid]
        metas = {c: m.pop(vid) for c, m in self.datos["metas"].items() if vid in m}
        self.papelera = {"tipo": "vendedor", "vend": vs.pop(pos), "pos": pos, "regs": regs, "metas": metas}
        self.guardar_todo()
        return {"ok": True}

    # ---------------------------------------------------------------- reportes
    def guardar_reporte(self, reemplazar=False):
        m = self.reporte()
        previos = [x for x in self.datos["reportes"] if x["clave"] == m["clave"] and x["vista"] == m["vista"] and x["semana"] == m["semana"]]
        if previos and not reemplazar:
            return {"pregunta": "Ya hay un reporte guardado de «{}».\n¿Reemplazarlo con los datos de ahora?".format(m["titulo"]),
                    "titulo": "Reporte repetido"}
        if previos:
            self.datos["reportes"] = [x for x in self.datos["reportes"] if x not in previos]
        m["id"] = uuid.uuid4().hex[:10]
        self.datos["reportes"].append(m)
        self.guardar_todo()
        return {"ok": True, "titulo": m["titulo"]}

    def reportes(self):
        filas = []
        for m in sorted(self.datos["reportes"], key=lambda x: x["creado"], reverse=True):
            e = m["equipo"]
            filas.append({"id": m["id"], "periodo": m["periodo"], "titulo": m["titulo"],
                          "vista": "Mes completo" if m["vista"] == "Mes" else "Semana {}".format(m["semana"]),
                          "meta": e["meta"], "neto": e["neto"], "proy": e["proy"], "falta": e["falta_neto"],
                          "creado": datetime.fromisoformat(m["creado"]).strftime("%d/%m/%Y %H:%M")})
        return {"ok": True, "filas": filas}

    def reporte_guardado(self, rid):
        m = next((x for x in self.datos["reportes"] if x["id"] == rid), None)
        if not m:
            return _err("No se encontró el reporte.")
        return {"ok": True, "modelo": m, "creado": datetime.fromisoformat(m["creado"]).strftime("%d/%m/%Y %H:%M"),
                "mes_total": sum(x["meta_mes"] for x in m["filas"]), "sem_total": sum(x["meta_sem"] for x in m["filas"])}

    def eliminar_reporte(self, rid):
        self.datos["reportes"] = [x for x in self.datos["reportes"] if x["id"] != rid]
        self.guardar_todo()
        return {"ok": True}

    def descargar_pdf(self, rid=None):
        if rid:
            m = next((x for x in self.datos["reportes"] if x["id"] == rid), None)
            if not m:
                return _err("No se encontró el reporte.")
        else:
            m = self.reporte()
        if not m["filas"]:
            return _err("Agrega al menos un vendedor para generar el reporte.")
        sugerido = "reporte_{}_{}.pdf".format(norm(m["periodo"]).replace(" ", "_"),
                                              "mes" if m["vista"] == "Mes" else "semana{}".format(m["semana"]))
        ruta = self.ui.guardar(sugerido, ".pdf", [("PDF", "*.pdf")])
        if not ruta:
            return {"ok": True, "cancelado": True}
        try:
            k = n.generar_pdf(m, ruta)
        except OSError as e:
            return _err("No se pudo crear el PDF:\n{}".format(e))
        self._pdfs.add(os.path.abspath(ruta))
        return {"ok": True, "ruta": ruta, "laminas": k}

    def abrir_ruta(self, ruta):
        """Solo abre lo que la propia app acaba de crear o la carpeta de datos."""
        ruta = os.path.abspath(ruta or "")
        carpeta = os.path.dirname(self.almacen.ruta)
        if ruta not in self._pdfs and ruta not in self._exportados() and ruta != os.path.abspath(carpeta):
            return _err("Ruta no permitida.")
        self.ui.externo(ruta)
        return {"ok": True}

    def _exportados(self):
        return getattr(self, "_expo", set())

    def abrir_url(self, url):
        url = (url or "").strip()
        if not URL_WEB.match(url):
            return _err("Este lead no tiene un enlace válido (solo tiene el ID).")
        webbrowser.open(url)
        return {"ok": True}

    def abrir_carpeta(self):
        carpeta = os.path.dirname(self.almacen.ruta)
        os.makedirs(carpeta, exist_ok=True)
        self.ui.externo(carpeta)
        return {"ok": True, "ruta": carpeta}

    # ----------------------------------------------------------- configuracion
    def config(self):
        c = self.datos["config"]
        return {"ok": True, "webhook": c.get("bitrix_webhook", ""), "campo": c.get("campo_campana", "auto"),
                "graficas": {a: self.grafica(a) for a, _ in n.GRAFICA_AREAS}, "n_regresos": len(self.datos.get("regresos", [])),
                "ruta": self.almacen.ruta, "version": VERSION_APP, "empaquetado": bool(getattr(sys, "frozen", False))}

    def cambiar_grafica(self, area, clave):
        if area not in n.GRAFICAS or clave not in [k for k, _ in n.GRAFICAS[area]]:
            return _err("Gráfica no válida.")
        self.datos["config"].setdefault("graficas", {})[area] = clave
        self.guardar_todo()
        return {"ok": True}

    def guardar_conexion(self, webhook, campo):
        try:
            base = n.bitrix_base(webhook)
        except ValueError as e:
            return _err(str(e), "webhook")
        self.datos["config"]["bitrix_webhook"] = base
        self.datos["config"]["campo_campana"] = (campo or "").strip() or "auto"
        self.guardar_todo()
        return {"ok": True, "webhook": base}

    def probar_conexion(self, webhook, lead):
        try:
            cfg = {"bitrix_webhook": n.bitrix_base(webhook)}
        except ValueError as e:
            return _err(str(e), "webhook")
        did = n.extraer_id(n.limpiar_lead(lead or ""))
        if not did:
            return _err("Escribe el enlace o el ID de un lead para probar.", "lead")
        try:
            _, deal = n.bitrix_negociacion(cfg, did)
        except Exception as e:
            return _err("No se pudo leer el lead:\n{}".format(e))
        filas = ["{}: {}".format(k, n.recortar(str(v), 50)) for k, v in deal.items() if v not in (None, "", "0", 0, [], {}, "N", "0.00")]
        return {"ok": True, "id": did, "campos": filas[:30]}

    def vaciar_periodo(self):
        regs = self.registros
        if not regs:
            return _err("Este periodo no tiene proyecciones.")
        return self.eliminar([r["id"] for r in regs])

    def borrar_todo(self):
        k = sum(len(v) for v in self.datos["periodos"].values())
        if not k:
            return _err("No hay proyecciones guardadas.")
        self.guardar_todo()
        copia = self.almacen.copia_seguridad("antes_de_borrar")
        if copia is None and os.path.exists(self.almacen.ruta):
            return _err("No se pudo hacer la copia de seguridad; no se borró nada.")
        self.datos["periodos"] = {}
        self.datos["config"].pop("borrador", None)
        self.papelera = None
        self.guardar_todo()
        return {"ok": True, "n": k, "copia": copia}

    def cuenta_periodo(self):
        return {"ok": True, "n": len(self.registros), "total": sum(len(v) for v in self.datos["periodos"].values()),
                "titulo_periodo": n.nombre_periodo(self.clave())}

    # -------------------------------------------------------------- importar
    def imp_plantilla(self):
        ruta = self.ui.guardar("plantilla_proyecciones.xlsx", ".xlsx", [("Excel", "*.xlsx")])
        if not ruta:
            return {"ok": True, "cancelado": True}
        try:
            n.escribir_plantilla(ruta)
        except OSError as e:
            return _err("No se pudo crear la plantilla:\n{}".format(e))
        return {"ok": True, "ruta": ruta}

    def imp_elegir(self):
        ruta = self.ui.abrir([("Excel, CSV o JSON", "*.xlsx *.csv *.json"), ("Todos", "*.*")])
        if not ruta:
            return {"ok": True, "cancelado": True}
        return self.imp_cargar(ruta)

    def imp_cargar(self, ruta):
        try:
            filas = n.leer_tabla(ruta)
        except Exception as e:
            return _err("No pude leer el archivo ({}).".format(e))
        if not filas:
            return _err("El archivo está vacío.")
        cab, mapa = n.detectar_columnas(filas)
        ancho = max(len(f) for f in filas)
        base = list(filas[cab]) + [""] * (ancho - len(filas[cab]))
        enc, usados = [], {}
        for i, c in enumerate(base):
            nombre = str(c).strip() or "Columna {}".format(i + 1)
            usados[nombre] = usados.get(nombre, 0) + 1
            enc.append(nombre if usados[nombre] == 1 else "{} ({})".format(nombre, usados[nombre]))
        self._imp = {"filas": filas, "cab": cab}
        return {"ok": True, "archivo": os.path.basename(ruta), "encabezados": enc, "mapa": {k: int(v) for k, v in mapa.items()},
                "campos": [{"id": k, "label": nm, "req": req} for k, nm, req in n.IMP_CAMPOS], "vista": self.imp_vista(mapa)}

    def imp_vista(self, mapa):
        if not self._imp:
            return _err("Primero elige un archivo.")
        mapa = {k: int(v) for k, v in (mapa or {}).items() if v is not None and str(v) != "" and int(v) >= 0}
        r = n.importar_filas(self.datos, self._imp["filas"], mapa=mapa, cab=self._imp["cab"])
        return {"ok": True, "vista": r["vista"], "nuevos": r["nuevos"], "total": r["total"], "repetidos": len(r["repetidos"]),
                "errores": [[a, b] for a, b in r["errores"][:50]], "n_errores": len(r["errores"]),
                "periodos": {n.nombre_periodo(k): v for k, v in sorted(r["periodos"].items())}}

    def imp_aplicar(self, mapa):
        if not self._imp:
            return _err("Primero elige un archivo con «Elegir archivo…».")
        mapa = {k: int(v) for k, v in (mapa or {}).items() if v is not None and str(v) != "" and int(v) >= 0}
        r = n.importar_filas(self.datos, self._imp["filas"], aplicar=True, mapa=mapa, cab=self._imp["cab"])
        self.guardar_todo()
        self._imp = None
        return {"ok": True, "nuevos": r["nuevos"], "total": r["total"]}

    # -------------------------------------------------------------- exportar
    def _exp_contenido(self, o):
        formato = int(o.get("formato", 0))
        claves = self.claves() if o.get("alcance", "elegidos") == "elegidos" else sorted(self.datos["periodos"])
        pedidos = o.get("tipos")
        tipos = [t for t in TIPOS_ORDEN if t in (TIPOS_ORDEN if pedidos is None else pedidos)]
        pre = int(o.get("preset", 0))
        if pre == 0:
            cols = [(c, nm) for c, _, nm in n.EXP_COLUMNAS if c in n.EXP_DEFECTO]
        elif pre == 1:
            cols = [(c, nm) for c, _, nm in n.EXP_COLUMNAS]
        else:
            elegidas, nombres = o.get("columnas") or [], o.get("nombres") or {}
            cols = [(c, (nombres.get(c) or "").strip() or nm) for c, _, nm in n.EXP_COLUMNAS if c in elegidas]
        extras = [k for k in (o.get("extras") or []) if k in ("vendedores", "reportes", "completo")]
        if formato == 2:
            obj = json_obj = n.json_exportar(self.datos, claves, tipos, cols, extras)
            k = len(obj["proyecciones"]) if "proyecciones" in obj else sum(len(v) for v in obj["periodos"].values())
            lineas = json.dumps(json_obj, ensure_ascii=False, indent=1).splitlines()
            return obj, "\n".join(lineas[:70] + (["…"] if len(lineas) > 70 else [])), k, claves, tipos, cols, extras
        tabla = n.tabla_exportar(self.datos, claves, tipos, cols)
        lineas = [" | ".join(str(x) for x in f)[:150] for f in tabla[:16]]
        return tabla, "\n".join(lineas + (["…"] if len(tabla) > 16 else [])), len(tabla) - 1, claves, tipos, cols, extras

    def exp_info(self):
        return {"ok": True, "formatos": ["Excel (.xlsx)", "CSV (.csv)", "JSON (.json)"],
                "periodo": self.etiqueta_periodo(),
                "columnas": [{"id": c, "prog": p, "nombre": nm, "defecto": c in n.EXP_DEFECTO} for c, p, nm in n.EXP_COLUMNAS],
                "presets": ["Básicas (fecha, asesor, enlace, campaña, monto, estado)", "Todas las columnas", "Elegir columnas…"]}

    def exp_vista(self, o):
        _, txt, k, claves, tipos, cols, _e = self._exp_contenido(o)
        total = sum(r["monto"] for c in claves for r in self.datos["periodos"].get(c, []) if r["tipo"] in tipos)
        return {"ok": True, "texto": txt, "n": k, "columnas": len(cols), "total": total}

    def exp_exportar(self, o):
        formato = int(o.get("formato", 0))
        datos, _t, k, claves, tipos, cols, extras = self._exp_contenido(o)
        completo = formato == 2 and "completo" in extras
        if not cols and not completo:
            return _err("Marca al menos una columna.")
        if not tipos and not completo:
            return _err("Marca al menos un estado.")
        if k == 0 and not completo:
            return _err("No hay filas con esa selección.")
        ext = (".xlsx", ".csv", ".json")[formato]
        tipo = [("Excel", "*.xlsx"), ("CSV", "*.csv"), ("JSON", "*.json")][formato]
        base = "proyecciones_" + (norm(self.etiqueta_periodo()).replace(" ", "_").replace("–", "-").replace(",", "")
                                  if o.get("alcance", "elegidos") == "elegidos" else "todos")
        ruta = self.ui.guardar(base + ext, ext, [tipo])
        if not ruta:
            return {"ok": True, "cancelado": True}
        try:
            if ext == ".xlsx":
                n.escribir_xlsx(ruta, datos)
            elif ext == ".csv":
                n.escribir_csv(ruta, datos)
            else:
                with open(ruta, "w", encoding="utf-8") as f:
                    json.dump(datos, f, ensure_ascii=False, indent=1)
        except OSError as e:
            return _err("No se pudo exportar:\n{}".format(e))
        self._expo = getattr(self, "_expo", set()) | {os.path.abspath(ruta)}
        return {"ok": True, "n": k, "ruta": ruta}

    # -------------------------------------------------------- actualizaciones
    def novedades_pendientes(self):
        if not getattr(sys, "frozen", False):
            return {"ok": True, "notas": None}
        notas = novedades.notas_a_mostrar(VERSION_APP, novedades.ARGUMENTO_ACTUALIZADO in sys.argv, novedades.leer_version_vista())
        novedades.guardar_version_vista(VERSION_APP)
        if not notas:
            return {"ok": True, "notas": None}
        sec = [{"titulo": t, "items": notas.get(c) or [], "vineta": v} for c, t, v in novedades.SECCIONES if notas.get(c)]
        return {"ok": True, "notas": sec, "version": VERSION_APP}

    def buscar_actualizacion(self, manual=False):
        if not getattr(sys, "frozen", False):
            return {"ok": True, "estado": "fuente"} if manual else {"ok": True, "estado": "omitido"}
        actualizador.limpiar_descargas()
        cola = queue.Queue()
        threading.Thread(target=actualizador.hilo_consultar, args=(cola,), daemon=True).start()
        try:
            info = cola.get(timeout=actualizador.TIEMPO_CONSULTA_S + 6)
        except queue.Empty:
            info = None
        if info and actualizador.es_mas_nueva(info["version"], VERSION_APP):
            self._info_act = info
            return {"ok": True, "estado": "nueva", "version": info["version"], "actual": VERSION_APP}
        return {"ok": True, "estado": "actual" if info else "error", "actual": VERSION_APP}

    def descargar_actualizacion(self):
        info = self._info_act
        if not info:
            return _err("Primero busca una actualización.")
        self.guardar_todo()
        self._prog_act = {"pct": 0, "fin": False, "error": None, "ruta": None}
        cola = queue.Queue()
        threading.Thread(target=actualizador.hilo_descargar, args=(info, cola), daemon=True).start()

        def vigilar():
            while True:
                m = cola.get()
                if m[0] == "progreso":
                    if m[2]:
                        self._prog_act["pct"] = m[1] * 100 / m[2]
                    continue
                if m[0] == "error":
                    self._prog_act.update(fin=True, error=str(m[1]))
                else:
                    self._prog_act.update(fin=True, ruta=m[1], pct=100)
                return
        threading.Thread(target=vigilar, daemon=True).start()
        return {"ok": True, "version": info["version"]}

    def progreso_actualizacion(self):
        p = self._prog_act
        return {"ok": True, "pct": p["pct"], "fin": p["fin"], "error": p["error"]}

    def instalar_actualizacion(self, salir=None):
        ruta = self._prog_act.get("ruta")
        if not ruta:
            return _err("La descarga no ha terminado.")
        self.guardar_todo()
        actualizador.lanzar_instalador(ruta)
        if salir:
            salir()
        return {"ok": True}
