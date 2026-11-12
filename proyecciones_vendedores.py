# -*- coding: utf-8 -*-
"""
Proyecciones de Vendedores  (v4)
App local de escritorio (Tkinter + solo libreria estandar de Python; el PDF se genera sin librerias externas).

Identidad visual: azul #003D6B y corinto #960018, bordes redondeados y animaciones suaves y rapidas.

Secciones (menu lateral):
  - Panel principal     : dashboard por vendedor (anillo de meta, recibido, proyectado, falta/supero, semanas)
  - Ingresar reporte    : formulario (el asesor elegido es el vendedor al que cuenta el monto)
  - Historial           : tabla completa con buscador universal y filtros
  - Campañas            : que campaña se pidio mas y cuanto recaudo
  - Embudos             : embudo por vendedor
  - Reportes guardados  : fotos de semana/mes con la meta que tenian asignada (con PDF)
  - Vendedores y metas  : agregar / editar / eliminar vendedores y sus metas (mensual y semanal)
  - Configuración (⚙)   : conexión con Bitrix24, tipo de gráficas y manejo de los datos

Los datos se guardan solos en:  <carpeta de usuario>/ProyeccionesVendedores/datos.json
"""
import calendar
import csv
import json
import math
import os
import queue
import re
import sys
import threading
import time
import traceback
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import uuid
import webbrowser
import zlib
from datetime import date, datetime, timedelta

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from tkinter import font as tkfont

import actualizador

APP_NAME = "Proyecciones de Vendedores"
# El flujo de GitHub (publicar.yml) reescribe esta linea con la etiqueta de la version.
VERSION_APP = "1.0.0"

DATA_FILE = os.path.join(os.path.expanduser("~"), "ProyeccionesVendedores", "datos.json")
BITRIX_DEAL_URL = "https://dreamtravel.bitrix24.es/crm/deal/details/{}/"

MESES = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio",
         "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]

MESES_ABR = [m[:3] for m in MESES]

TIPOS_ORDEN = ["activa", "perdida", "exitosa"]
TIPO_LABEL = {"activa": "Activa", "perdida": "Perdida", "exitosa": "Exitosa"}
LABEL_TIPO = {v: k for k, v in TIPO_LABEL.items()}

# ---- identidad visual -------------------------------------------------------
# Azul 003D6B + corinto 960018. Cada rol tiene su valor claro y su valor oscuro (gris suave, colores tenues).
# PT/PS = color de cada vendedor (tinte, solido); GT/GS = el gris del equipo.
def _armar(base, vend, gris):
    d = dict(base)
    for i, (t, s) in enumerate(vend):
        d["PT%d" % i], d["PS%d" % i] = t, s
    d["GT"], d["GS"] = gris
    return d


LIGHT = _armar(dict(
    AZUL="#003D6B", AZUL_H="#002E50", AZUL_MED="#2F6FA3", AZUL_CLARO="#8DB4D6", AZUL_PALIDO="#E6EDF4", AZUL_PALIDO_H="#D5E1EC",
    CORINTO="#960018", CORINTO_H="#760013", CORINTO_MED="#B84A5C", CORINTO_PALIDO="#F5E6E9",
    BG="#F4F6F9", CARD="#FFFFFF", BORDE="#DDE3EA", TRACK="#E6EBF1", INK="#1B2733", MUTED="#5E6E7E", SELEC="#8EB5D7",
    SIDE_BG="#00355E", SIDE_SEL="#0A4F82", SIDE_HOV="#05447A", SIDE_FG="#D6E4F0", SIDE_MUTED="#8FB0CC", SIDE_TXT="#F8FAFC",
    BTN="#003D6B", BTN_H="#002E50", BTN_R="#960018", BTN_R_H="#760013", BLANCO="#FFFFFF", FIELD="#FFFFFF"),
    [("#E4EDF5", "#003D6B"), ("#F6E3E7", "#960018"), ("#E3F0FA", "#2F6FA3"), ("#F7E7EA", "#C4586B"),
     ("#E8ECF0", "#5F7080"), ("#FBF1DC", "#B7791F"), ("#E2F3EE", "#1B7F5B"), ("#EDE7F6", "#6B4EA3")],
    ("#E8ECF0", "#5F7080"))

DARK = _armar(dict(
    AZUL="#8FB1D3", AZUL_H="#7FA3C8", AZUL_MED="#6B97C0", AZUL_CLARO="#4B677F", AZUL_PALIDO="#34414E", AZUL_PALIDO_H="#3E4D5C",
    CORINTO="#E09AA7", CORINTO_H="#CF8A97", CORINTO_MED="#B96F7D", CORINTO_PALIDO="#43353A",
    BG="#22262B", CARD="#2C3137", BORDE="#444B54", TRACK="#3A414A", INK="#E8ECF0", MUTED="#A6B0BC", SELEC="#2F4A63",
    SIDE_BG="#1D2024", SIDE_SEL="#2F3A46", SIDE_HOV="#272E36", SIDE_FG="#C3CBD4", SIDE_MUTED="#7F8995", SIDE_TXT="#EEF1F4",
    BTN="#4D7AA6", BTN_H="#5D8AB6", BTN_R="#A24F5E", BTN_R_H="#B25F6E", BLANCO="#F3F6F9", FIELD="#262A30"),
    [("#34414E", "#7FA3C7"), ("#42353A", "#C9818F"), ("#34475A", "#6B97C0"), ("#463A3E", "#B6707E"),
     ("#363B42", "#8A96A3"), ("#463F2E", "#C49A55"), ("#2F443E", "#5FA88A"), ("#3B3750", "#9C86C9")],
    ("#363B42", "#8A96A3"))

# Aspecto de los PDF (no cambia con el tema de la pantalla; se rediseñara aparte)
PDF_PAL = _armar(dict(
    AZUL="#003D6B", AZUL_H="#002E50", AZUL_MED="#2F6FA3", AZUL_CLARO="#8DB4D6", AZUL_PALIDO="#E4EDF5", AZUL_PALIDO_H="#D2E1EE",
    CORINTO="#960018", CORINTO_H="#760013", CORINTO_MED="#C4586B", CORINTO_PALIDO="#F6E3E7",
    BG="#FFFFFF", CARD="#F5F8FC", BORDE="#DFE6EE", TRACK="#E3EAF2", INK="#0F1E2E", MUTED="#5F7080", SELEC="#8EB5D7",
    SIDE_BG="#003D6B", SIDE_SEL="#0B5A94", SIDE_HOV="#05487D", SIDE_FG="#D6E4F0", SIDE_MUTED="#8FB0CC", SIDE_TXT="#FFFFFF",
    BTN="#003D6B", BTN_H="#002E50", BTN_R="#960018", BTN_R_H="#760013", BLANCO="#FFFFFF", FIELD="#FFFFFF"),
    [("#E4EDF5", "#003D6B"), ("#F6E3E7", "#960018"), ("#E3F0FA", "#2F6FA3"), ("#F7E7EA", "#C4586B"),
     ("#E8ECF0", "#5F7080"), ("#FBF1DC", "#B7791F"), ("#E2F3EE", "#1B7F5B"), ("#EDE7F6", "#6B4EA3")], ("#E8ECF0", "#5F7080"))

PALETA, DONA_COLORES, TIPO_FG, GRIS = [], [], {}, None


def aplicar_paleta(P):
    """Pone la paleta P como colores vigentes (las constantes de modulo AZUL, CARD, INK... se leen al dibujar)."""
    g = globals()
    g.update(P)
    PALETA[:] = [(P["PT%d" % i], P["PS%d" % i]) for i in range(8)]
    g["GRIS"] = (P["GT"], P["GS"])
    g["TIPO_FG"] = {"activa": P["INK"], "perdida": P["CORINTO"], "exitosa": P["AZUL"]}
    DONA_COLORES[:] = [P["CORINTO"], P["AZUL"], P["AZUL_MED"], P["AZUL_CLARO"], P["CORINTO_MED"], P["MUTED"]]


class paleta_pdf:
    """Con 'with paleta_pdf():' los colores vuelven temporalmente a los del PDF."""

    def __enter__(self):
        self.antes = dict(TEMA.P)
        aplicar_paleta(PDF_PAL)

    def __exit__(self, *a):
        aplicar_paleta(self.antes)


aplicar_paleta(LIGHT)

# Tipos de grafica disponibles por seccion (se cambian en Configuración)
GRAFICAS = {
    "panel": [("anillo", "Anillo + semanas (actual)"), ("barra", "Barra de progreso (recomendada)"),
              ("acumulada", "Acumulada por semana (recomendada)"), ("dona", "Dona"), ("pastel", "Pastel")],
    "embudo": [("embudo", "Embudo (actual)"), ("barras", "Barras por etapa"),
               ("dona", "Dona de estados (recomendada)"), ("pastel", "Pastel de estados")],
    "rank": [("barras", "Barras (actual)"), ("pareto", "Acumulada · Pareto (recomendada)")],
    "dona": [("dona", "Dona (actual)"), ("pastel", "Pastel (recomendada)")],
}
GRAFICA_DEF = {"panel": "anillo", "embudo": "embudo", "rank": "barras", "dona": "dona"}
GRAFICA_AREAS = [("panel", "Panel principal · cada vendedor"), ("embudo", "Embudos"),
                 ("rank", "Campañas · ranking"), ("dona", "Campañas · participación")]

TODOS = "(Todos)"
TODAS = "(Todas)"
SIN_CAMP = "(sin campaña)"
MEDIDAS = ["Monto ($)", "Cantidad"]

VEND_DEFAULT = [{"id": "A", "nombre": "Lesly", "ci": 0}, {"id": "B", "nombre": "Susana", "ci": 1},
                {"id": "C", "nombre": "Debi", "ci": 2}]

DEAL_RE = re.compile(r"/deal/details/(\d+)", re.I)


# ----------------------------------------------------------------- utilidades
def norm(texto):
    """Minusculas y sin tildes, para buscar sin importar acentos."""
    t = unicodedata.normalize("NFD", str(texto))
    return "".join(c for c in t if unicodedata.category(c) != "Mn").lower()


def extraer_id(lead):
    """ID de la negociacion a partir del enlace de Bitrix24 (o '' si no hay)."""
    m = DEAL_RE.search(lead or "")
    if m:
        return m.group(1)
    t = (lead or "").strip()
    return t if t.isdigit() else ""


def limpiar_lead(texto):
    """Quita espacios/saltos/comillas sobrantes. Si solo es un numero, arma el enlace."""
    t = "".join((texto or "").split()).strip("'\"")
    if t.isdigit():
        return BITRIX_DEAL_URL.format(t)
    return t


def parse_monto(txt):
    """Acepta 1300, 1300.50, $1,300.00, 1.300,50 ..."""
    t = str(txt).strip().replace("$", "").replace(" ", "")
    if not t:
        raise ValueError("vacio")
    if "," in t and "." in t:
        if t.rfind(",") > t.rfind("."):
            t = t.replace(".", "").replace(",", ".")
        else:
            t = t.replace(",", "")
    elif "," in t:
        partes = t.split(",")
        if len(partes) == 2 and len(partes[1]) in (1, 2):
            t = t.replace(",", ".")
        else:
            t = t.replace(",", "")
    v = float(t)
    if v < 0 or v != v:
        raise ValueError("negativo")
    return round(v, 2)


def parse_fecha(txt):
    t = str(txt).strip().replace("-", "/").replace(".", "/")
    for fmt in ("%d/%m/%Y", "%d/%m/%y", "%Y/%m/%d"):
        try:
            return datetime.strptime(t, fmt).date()
        except ValueError:
            pass
    raise ValueError("fecha")


def fm(x):
    return "${:,.2f}".format(x)


def fm0(x):
    return "${:,.0f}".format(x)


def pct(v, base):
    return "{:.1f}%".format(v / base * 100) if base and base > 0 else "—"


def pct0(v, base):
    return "{:.0f}%".format(v / base * 100) if base and base > 0 else "—"


def recortar(s, n):
    return s if len(s) <= n else s[:n - 1] + "…"


def canon_vendedor(s):
    """Nombre de persona: cada palabra con su inicial en mayuscula (LESLY -> Lesly)."""
    return " ".join(p[:1].upper() + p[1:].lower() for p in str(s).split())


def canon_campana(s):
    """Campaña: solo la inicial en mayuscula (META ADS -> Meta ads)."""
    s = " ".join(str(s).split())
    return s[:1].upper() + s[1:].lower()


def clave_periodo(anio, mes_idx):
    return "{:04d}-{:02d}".format(anio, mes_idx + 1)


def nombre_periodo(clave):
    return "{} {}".format(MESES[int(clave[5:7]) - 1], clave[:4])


def dias_del_mes(clave):
    return calendar.monthrange(int(clave[:4]), int(clave[5:7]))[1]


def rangos_semanas(clave):
    """[(1,7),(8,14),(15,21),(22,28),(29,fin)] ; la 5ta solo si el mes tiene 29+ dias."""
    dias = dias_del_mes(clave)
    r = [(1, 7), (8, 14), (15, 21), (22, 28)]
    if dias >= 29:
        r.append((29, dias))
    return r


def semana_de(fecha_iso, clave):
    """Semana (1..5) de una fecha dentro del periodo. Antes del mes -> 1 ; despues -> ultima."""
    d = date.fromisoformat(fecha_iso)
    a, m = int(clave[:4]), int(clave[5:7])
    n = len(rangos_semanas(clave))
    if (d.year, d.month) < (a, m):
        return 1
    if (d.year, d.month) > (a, m):
        return n
    return min((d.day - 1) // 7 + 1, n)


def filtrar_tiempo(registros, clave, modo, semana):
    if modo == "Mes":
        return list(registros)
    return [r for r in registros if semana_de(r["fecha"], clave) == semana]


def lerp(a, b, t):
    return a + (b - a) * t


def ease_out(p):
    return 1 - (1 - p) ** 3


def ease_in_out(p):
    return p * p * (3 - 2 * p)


def _lum(c):
    def f(v):
        v /= 255.0
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = (f(int(c[i:i + 2], 16)) for i in (1, 3, 5))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def texto_sobre(fondo):
    """Texto blanco u oscuro, el que mejor se lea sobre ese color (sirve igual en claro y en oscuro)."""
    l = _lum(fondo)
    return "#FFFFFF" if 1.05 / (l + 0.05) >= (l + 0.05) / 0.06 else "#12161A"


def mezclar(c1, c2, t):
    """Mezcla dos colores #rrggbb (t=0 -> c1, t=1 -> c2)."""
    a = [int(c1[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(c2[i:i + 2], 16) for i in (1, 3, 5)]
    return "#{:02x}{:02x}{:02x}".format(*[int(round(lerp(x, y, t))) for x, y in zip(a, b)])


# ---- vendedores (sobre el dict de datos) -----------------------------------
def vend_ids(datos):
    return [v["id"] for v in datos["vendedores"]]


def vend_nombres(datos):
    return {v["id"]: v["nombre"] for v in datos["vendedores"]}


def siguiente_color(datos):
    usados = {v.get("ci", 0) % len(PALETA) for v in datos["vendedores"]}
    for i in range(len(PALETA)):
        if i not in usados:
            return i
    return len(datos["vendedores"]) % len(PALETA)


def texto_busqueda(r, nombres):
    d = date.fromisoformat(r["fecha"])
    partes = [
        d.strftime("%d/%m/%Y"), d.isoformat(), nombres.get(r["vend"], ""), r.get("asesor", ""), r["lead"],
        extraer_id(r["lead"]), r["campana"], "{:.2f}".format(r["monto"]), "{:,.2f}".format(r["monto"]),
        TIPO_LABEL[r["tipo"]],
    ]
    return norm(" ".join(partes))


def filtrar(registros, nombres, texto="", vend=TODOS, camp=TODAS, tipo=TODOS):
    """Devuelve [(posicion, registro)] que cumplen buscador + filtros (vend = id del vendedor)."""
    tokens = []
    for tok in norm(texto).split():
        m = DEAL_RE.search(tok)          # si pegan un enlace completo, se busca por su ID
        tokens.append(m.group(1) if m else tok)
    out = []
    for pos, r in enumerate(registros, 1):
        if vend != TODOS and r["vend"] != vend:
            continue
        if camp != TODAS:
            if camp == SIN_CAMP:
                if r["campana"]:
                    continue
            elif r["campana"] != camp:
                continue
        if tipo != TODOS and r["tipo"] != tipo:
            continue
        if tokens:
            h = texto_busqueda(r, nombres)
            if not all(t in h for t in tokens):
                continue
        out.append((pos, r))
    return out


def resumir(registros, vids):
    """{vend: {tipo: [cantidad, monto]}} + 'TOTAL'."""
    res = {k: {t: [0, 0.0] for t in TIPOS_ORDEN} for k in list(vids) + ["TOTAL"]}
    for r in registros:
        for k in (r["vend"], "TOTAL"):
            if k in res:
                res[k][r["tipo"]][0] += 1
                res[k][r["tipo"]][1] += r["monto"]
    return res


# ---- metas ---------------------------------------------------------------
def meta_vigente(datos, clave, vid):
    """Meta {'mes':x,'sem':y|None} valida para el periodo (hereda del ultimo periodo anterior que la definio)."""
    metas = datos.get("metas", {})
    for c in sorted((c for c in metas if c <= clave), reverse=True):
        m = metas[c].get(vid)
        if m is not None:
            return {"mes": float(m.get("mes") or 0), "sem": m.get("sem")}
    return {"mes": 0.0, "sem": None}


def meta_de(datos, clave, vid, modo):
    """Meta a usar segun la vista. Semanal vacia = mensual / 4. vid='TOTAL' suma todos los vendedores."""
    if vid == "TOTAL":
        return sum(meta_de(datos, clave, v, modo) for v in vend_ids(datos))
    m = meta_vigente(datos, clave, vid)
    if modo == "Mes":
        return m["mes"]
    return float(m["sem"]) if m["sem"] else m["mes"] / 4.0


def metas_semanales(datos, clave, vid, hoy=None):
    """Meta de cada semana con lo que arrastra la anterior: si la semana pasada la meta era 7k y se llego a 3k, esta
    sera 7k + 4k = 11k; si se vendieron 9k, sera 7k - 2k = 5k. Solo cuentan las semanas que ya terminaron."""
    hoy = hoy or date.today()
    a, m = int(clave[:4]), int(clave[5:7])
    base = meta_de(datos, clave, vid, "Semana")
    regs = datos["periodos"].get(clave, [])
    out, dif = [], 0.0
    for i, (a0, b0) in enumerate(rangos_semanas(clave), 1):
        meta = max(0.0, base + dif) if base > 0 else 0.0
        neto = sum(r["monto"] for r in regs
                   if r["vend"] == vid and r["tipo"] == "exitosa" and semana_de(r["fecha"], clave) == i)
        out.append({"semana": i, "base": base, "arrastre": meta - base, "meta": meta, "neto": neto})
        if base > 0 and hoy > date(a, m, b0):
            dif = meta - neto
    return out


def calcular_tarjeta(registros, meta):
    """Neto = exitosas ; proyeccion = activas (teorico) ; perdidas no cuentan."""
    ex = [r for r in registros if r["tipo"] == "exitosa"]
    ac = [r for r in registros if r["tipo"] == "activa"]
    pe = [r for r in registros if r["tipo"] == "perdida"]
    neto, proy = sum(r["monto"] for r in ex), sum(r["monto"] for r in ac)
    return {"meta": meta, "neto": neto, "proy": proy, "total": neto + proy,
            "perdidas": sum(r["monto"] for r in pe), "n_neto": len(ex), "n_proy": len(ac), "n_perdidas": len(pe),
            "falta_neto": meta - neto, "falta_total": meta - (neto + proy)}


def calcular_embudo(registros):
    """Etapas: ingresadas > en juego (activas+exitosas) > exitosas ; perdidas aparte."""
    def suma(tipos):
        rs = [r for r in registros if r["tipo"] in tipos]
        return len(rs), sum(r["monto"] for r in rs)
    return {"ingresadas": suma(TIPOS_ORDEN), "en_juego": suma(("activa", "exitosa")),
            "exitosas": suma(("exitosa",)), "perdidas": suma(("perdida",))}


def ranking_campanas(registros):
    """Campañas ordenadas por lo vendido (exitosas); a igualdad, por lo proyectado."""
    d = {}
    for r in registros:
        c = r["campana"] or SIN_CAMP
        e = d.setdefault(c, {"campana": c, "neto": 0.0, "n_neto": 0, "proy": 0.0, "n_proy": 0,
                             "perdidas": 0.0, "n_perdidas": 0})
        if r["tipo"] == "exitosa":
            e["neto"] += r["monto"]
            e["n_neto"] += 1
        elif r["tipo"] == "activa":
            e["proy"] += r["monto"]
            e["n_proy"] += 1
        else:
            e["perdidas"] += r["monto"]
            e["n_perdidas"] += 1
    for e in d.values():
        e["leads"] = e["n_neto"] + e["n_proy"] + e["n_perdidas"]
    return sorted(d.values(), key=lambda e: (-e["neto"], -e["proy"], norm(e["campana"])))


def campana_mas_solicitada(rank):
    """La campaña con mas leads (a igualdad, la que mas recaudo)."""
    return max(rank, key=lambda e: (e["leads"], e["neto"], e["proy"])) if rank else None


def fraccion_esperada(clave, modo, semana, hoy=None):
    """Que parte del periodo (mes o semana) ya paso: sirve para el ritmo teorico (ej. 3 de 7 dias = 43%)."""
    hoy = hoy or date.today()
    a, m = int(clave[:4]), int(clave[5:7])
    a0, b0 = (1, dias_del_mes(clave)) if modo == "Mes" else rangos_semanas(clave)[(semana or 1) - 1]
    ini, fin = date(a, m, a0), date(a, m, b0)
    if hoy < ini:
        return 0.0
    if hoy >= fin:
        return 1.0
    return ((hoy - ini).days + 1) / float(b0 - a0 + 1)


def con_ritmo(c, frac):
    """Agrega lo que deberia llevar segun el ritmo y la diferencia contra lo recibido."""
    esp = c["meta"] * frac
    c["esp_monto"] = esp
    c["ritmo"] = c["neto"] - esp
    return c


def con_necesaria(c):
    """Proyeccion que hace falta para llegar a la meta si se sigue cerrando al mismo ritmo:
    tasa = vendido / proyectado total; necesaria = meta / tasa; falta proyectar = necesaria - ya proyectado.
    (Ej.: 20,000 proyectados y 3,000 vendidos = 15%; para vender 20,000 hacen falta 133,333 de proyeccion.)"""
    ing = c["neto"] + c["proy"] + c["perdidas"]
    c["ingresado"] = ing
    c["tasa"] = c["neto"] / ing if ing > 0 else None
    c["nec_total"] = c["nec_falta"] = None
    if c["meta"] > 0 and 0 < c["neto"] < c["meta"]:
        c["nec_total"] = c["meta"] / c["tasa"]
        c["nec_falta"] = max(0.0, c["nec_total"] - ing)
    return c


def construir_reporte(datos, clave, modo, semana, hoy=None):
    """Modelo completo de un reporte (sirve para guardarlo y para el PDF). Solo contiene datos simples."""
    regs_all = datos["periodos"].get(clave, [])
    semana = semana if modo == "Semana" else None
    frac = fraccion_esperada(clave, modo, semana, hoy)
    regs = filtrar_tiempo(regs_all, clave, modo, semana)
    nombres = vend_nombres(datos)
    ms = {vid: metas_semanales(datos, clave, vid, hoy) for vid in vend_ids(datos)}
    filas = []
    for vid in vend_ids(datos):
        mv = meta_vigente(datos, clave, vid)
        meta = ms[vid][semana - 1]["meta"] if modo == "Semana" else meta_de(datos, clave, vid, modo)
        c = calcular_tarjeta([r for r in regs if r["vend"] == vid], meta)
        c.update({"id": vid, "nombre": nombres[vid], "ci": next(v.get("ci", 0) for v in datos["vendedores"] if v["id"] == vid),
                  "meta_mes": mv["mes"], "meta_sem": float(mv["sem"]) if mv["sem"] else mv["mes"] / 4.0,
                  "arrastre": ms[vid][semana - 1]["arrastre"] if modo == "Semana" else 0.0})
        filas.append(con_necesaria(con_ritmo(c, frac)))
    semanas = []
    for i, (a, b) in enumerate(rangos_semanas(clave), 1):
        sr = [r for r in regs_all if semana_de(r["fecha"], clave) == i]
        eq = calcular_tarjeta(sr, sum(ms[vid][i - 1]["meta"] for vid in ms))
        eq["arrastre"] = sum(ms[vid][i - 1]["arrastre"] for vid in ms)
        semanas.append({
            "semana": i, "rango": [a, b], "equipo": eq,
            "filas": {vid: calcular_tarjeta([r for r in sr if r["vend"] == vid], ms[vid][i - 1]["meta"])
                      for vid in vend_ids(datos)}})
    if modo == "Semana":
        a, b = rangos_semanas(clave)[semana - 1]
        titulo = "{} · Semana {} (días {}–{})".format(nombre_periodo(clave), semana, a, b)
    else:
        titulo = "{} · Mes completo".format(nombre_periodo(clave))
    meta_eq = sum(f["meta"] for f in filas)
    equipo = con_necesaria(con_ritmo(calcular_tarjeta(regs, meta_eq), frac))
    equipo["arrastre"] = sum(f["arrastre"] for f in filas)
    return {"version": 1, "clave": clave, "periodo": nombre_periodo(clave), "vista": modo, "semana": semana,
            "titulo": titulo, "creado": datetime.now().isoformat(timespec="seconds"),
            "filas": filas, "equipo": equipo, "esp": frac,
            "semanas": semanas, "campanas": ranking_campanas(regs)}


def etiqueta_meses(claves):
    """'Noviembre 2026', 'Ene–Mar 2026', 'Ene, Mar, Jun 2026' o 'Todo 2026' segun los meses elegidos."""
    claves = sorted(claves)
    if len(claves) == 1:
        return nombre_periodo(claves[0])
    anio = claves[0][:4]
    idx = [int(c[5:7]) - 1 for c in claves]
    if len(idx) == 12:
        return "Todo " + anio
    if idx == list(range(idx[0], idx[-1] + 1)):
        return "{}–{} {}".format(MESES_ABR[idx[0]], MESES_ABR[idx[-1]], anio)
    return "{} {}".format(", ".join(MESES_ABR[i] for i in idx), anio)


def construir_reporte_multi(datos, claves, hoy=None):
    """Reporte que une varios meses: metas, recibido y proyectado se suman; en lugar de semanas hay una columna por mes."""
    claves = sorted(claves)
    rs = [construir_reporte(datos, c, "Mes", None, hoy) for c in claves]
    ids = vend_ids(datos)
    regs = [r for c in claves for r in datos["periodos"].get(c, [])]
    n = float(len(claves))
    filas = []
    for k, vid in enumerate(ids):
        fs = [r["filas"][k] for r in rs]
        meta = sum(f["meta"] for f in fs)
        c = calcular_tarjeta([r for r in regs if r["vend"] == vid], meta)
        esp = sum(f["esp_monto"] for f in fs)
        c.update({"id": vid, "nombre": fs[0]["nombre"], "ci": fs[0]["ci"], "meta_mes": meta, "meta_sem": meta / n, "arrastre": 0.0})
        filas.append(con_necesaria(con_ritmo(c, esp / meta if meta > 0 else 0.0)))
        c["esp_monto"] = esp
        c["ritmo"] = c["neto"] - esp
    meta_eq = sum(f["meta"] for f in filas)
    esp_eq = sum(f["esp_monto"] for f in filas)
    frac = esp_eq / meta_eq if meta_eq > 0 else 0.0
    equipo = con_necesaria(con_ritmo(calcular_tarjeta(regs, meta_eq), frac))
    equipo["arrastre"] = 0.0
    meses = []
    for i, (c, r) in enumerate(zip(claves, rs), 1):
        meses.append({"semana": i, "rango": None, "etq": MESES_ABR[int(c[5:7]) - 1], "equipo": r["equipo"],
                      "filas": {f["id"]: f for f in r["filas"]}})
    etq = etiqueta_meses(claves)
    return {"version": 1, "clave": "+".join(claves), "claves": claves, "multi": True, "periodo": etq, "vista": "Mes",
            "semana": None, "titulo": "{} · Meses combinados".format(etq),
            "creado": datetime.now().isoformat(timespec="seconds"), "filas": filas, "equipo": equipo, "esp": frac,
            "semanas": meses, "campanas": ranking_campanas(regs)}


def buscar_duplicados(datos, lead, vid, campana, excluir_id=None):
    """(por_enlace, por_nombre): None o (clave_periodo, registro).
    Enlace = misma negociacion (ID) en CUALQUIER periodo: el monto puede repetirse, el enlace no.
    Nombre = mismo asesor y misma campaña pero con otro enlace (solo advertencia)."""
    did = extraer_id(lead)
    camp = norm(campana).strip()
    nombre = None
    for clave in sorted(datos["periodos"]):
        for r in datos["periodos"][clave]:
            if r["id"] == excluir_id:
                continue
            if did and extraer_id(r["lead"]) == did:
                return (clave, r), None
            if nombre is None and camp and r["vend"] == vid and norm(r["campana"]).strip() == camp:
                nombre = (clave, r)
    return None, nombre


def bitrix_base(url):
    """Normaliza la URL del webhook de entrada: https://portal.bitrix24.es/rest/1/xxxx/  ('' si esta vacia)."""
    u = (url or "").strip().split("?")[0].rstrip("/")
    if not u:
        return ""
    m = re.match(r"^(https://[^/\s]+/rest/\d+/[^/\s]+)", u, re.I)
    if not m:
        raise ValueError("La URL del webhook debe verse así:\nhttps://tu-portal.bitrix24.es/rest/1/xxxxxxxx/")
    return m.group(1) + "/"


def bitrix_llamar(base, metodo, params=None, abrir=None, timeout=12):
    abrir = abrir or urllib.request.urlopen
    req = urllib.request.Request(base + metodo + ".json", data=urllib.parse.urlencode(params or {}).encode("utf-8"),
                                 headers={"User-Agent": "ProyeccionesVendedores"})
    try:
        with abrir(req, timeout=timeout) as r:
            res = json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            res = json.loads(e.read().decode("utf-8"))
        except Exception:
            raise ValueError("Bitrix24 respondió con error {}".format(e.code))
    except urllib.error.URLError as e:
        raise ValueError("No se pudo conectar con Bitrix24 ({})".format(e.reason))
    if isinstance(res, dict) and res.get("error"):
        raise ValueError(res.get("error_description") or str(res["error"]))
    return res


def bitrix_negociacion(cfg, did, abrir=None):
    """Datos crudos de la negociacion (crm.deal.get)."""
    base = bitrix_base(cfg.get("bitrix_webhook"))
    if not base:
        raise ValueError("Falta el webhook de Bitrix24 (Configuración → Conexión con Bitrix24).")
    deal = bitrix_llamar(base, "crm.deal.get", {"id": did}, abrir).get("result") or {}
    if not deal:
        raise ValueError("Bitrix24 no devolvió la negociación {}.".format(did))
    return base, deal


def _campo_campana(base, abrir=None):
    """(codigo, detalle) del campo personalizado de negociaciones cuyo nombre es «Campaña»; ('TITLE', {}) si no existe."""
    try:
        campos = bitrix_llamar(base, "crm.deal.fields", {}, abrir).get("result") or {}
    except Exception:
        return "TITLE", {}
    for cod, inf in campos.items():
        if not cod.startswith("UF_") or not isinstance(inf, dict):
            continue
        if any(norm(inf.get(k) or "").strip() == "campana" for k in ("formLabel", "listLabel", "title", "editFormLabel")):
            return cod, inf
    return "TITLE", {}


def leer_negociacion(cfg, did, abrir=None):
    """Lee la negociacion y devuelve lo que llena el formulario: monto, campaña y vendedor (editables despues)."""
    base, deal = bitrix_negociacion(cfg, did, abrir)
    campo = (cfg.get("campo_campana") or "auto").strip()
    info = {}
    if campo.lower() in ("auto", "title"):          # busca el campo personalizado llamado «Campaña»
        campo, info = _campo_campana(base, abrir)
    valor = deal.get(campo) if campo else None
    items = info.get("items") or []
    if items and valor not in (None, "", []):       # lista desplegable: el valor viene como codigo
        nombres = {str(i.get("ID")): i.get("VALUE") for i in items}
        valor = [nombres.get(str(v), v) for v in valor] if isinstance(valor, (list, tuple)) else nombres.get(str(valor), valor)
    if campo == "SOURCE_ID" and valor:       # el origen viene como codigo: se traduce a su nombre
        try:
            lista = bitrix_llamar(base, "crm.status.list", {"filter[ENTITY_ID]": "SOURCE"}, abrir).get("result") or []
            valor = next((x["NAME"] for x in lista if x.get("STATUS_ID") == valor), valor)
        except Exception:
            pass
    if isinstance(valor, (list, tuple)):
        valor = ", ".join(str(v) for v in valor)
    vendedor = ""
    if deal.get("ASSIGNED_BY_ID"):
        try:
            us = bitrix_llamar(base, "user.get", {"ID": deal["ASSIGNED_BY_ID"]}, abrir).get("result") or []
            if us:
                vendedor = "{} {}".format(us[0].get("NAME") or "", us[0].get("LAST_NAME") or "").strip()
        except Exception:
            pass
    try:
        monto = round(float(deal.get("OPPORTUNITY") or 0), 2)
    except (TypeError, ValueError):
        monto = 0.0
    return {"monto": monto, "campana": canon_campana(valor or ""), "vendedor": vendedor,
            "titulo": str(deal.get("TITLE") or "")}


def vendedor_por_nombre(datos, nombre):
    """Id del vendedor cuyo nombre aparece completo entre las palabras del nombre de Bitrix24 (o None)."""
    palabras = set(norm(nombre).split())
    for v in datos["vendedores"]:
        vp = set(norm(v["nombre"]).split())
        if vp and vp <= palabras:
            return v["id"]
    return None


# ------------------------------------------------------------------ exportar
# (clave, nombre en el programa, nombre por defecto en el archivo)
EXP_COLUMNAS = [("fecha", "Fecha", "Fecha"), ("vend", "Vendedor", "Asesor de ventas"), ("lead", "Enlace", "Enlace"),
                ("id", "ID de la negociación", "ID negociación"), ("campana", "Campaña", "Campaña"),
                ("monto", "Monto", "Monto"), ("tipo", "Estado", "Estado"), ("periodo", "Periodo", "Periodo"),
                ("semana", "Semana", "Semana")]
EXP_DEFECTO = ("fecha", "vend", "lead", "campana", "monto", "tipo")


def _valor_exportar(datos, clave, r, col):
    if col == "fecha":
        return date.fromisoformat(r["fecha"]).strftime("%d/%m/%Y")
    if col == "vend":
        return vend_nombres(datos).get(r["vend"], r.get("asesor", ""))
    if col == "lead":
        return r["lead"]
    if col == "id":
        return extraer_id(r["lead"])
    if col == "campana":
        return r["campana"]
    if col == "monto":
        return r["monto"]
    if col == "tipo":
        return TIPO_LABEL[r["tipo"]]
    if col == "periodo":
        return nombre_periodo(clave)
    return semana_de(r["fecha"], clave)


def tabla_exportar(datos, claves, tipos, columnas):
    """columnas = [(clave_columna, encabezado)]. Devuelve [encabezados, fila, fila, ...] ordenadas por fecha."""
    regs = [(c, r) for c in claves for r in datos["periodos"].get(c, []) if r["tipo"] in tipos]
    regs.sort(key=lambda x: (x[1]["fecha"], x[1]["id"]))
    return [[enc for _, enc in columnas]] + [[_valor_exportar(datos, c, r, col) for col, _ in columnas] for c, r in regs]


def json_exportar(datos, claves, tipos, columnas, extras=()):
    """Estructura JSON: proyecciones con las columnas elegidas (y los nombres elegidos) + secciones opcionales.
    'completo' = copia de toda la app para respaldo (sin el webhook de Bitrix24)."""
    if "completo" in extras:
        copia = json.loads(json.dumps(datos))
        copia.get("config", {}).pop("bitrix_webhook", None)
        return copia
    tabla = tabla_exportar(datos, claves, tipos, columnas)
    enc, usados = [], {}
    for e in tabla[0]:
        usados[e] = usados.get(e, 0) + 1
        enc.append(e if usados[e] == 1 else "{} ({})".format(e, usados[e]))
    out = {"exportado": datetime.now().isoformat(timespec="seconds"),
           "periodos": [nombre_periodo(c) for c in claves],
           "proyecciones": [dict(zip(enc, fila)) for fila in tabla[1:]]}
    if "vendedores" in extras:
        out["vendedores"] = [{"id": v["id"], "nombre": v["nombre"]} for v in datos["vendedores"]]
        out["metas"] = {c: m for c, m in datos.get("metas", {}).items()}
    if "reportes" in extras:
        out["reportes"] = datos.get("reportes", [])
    return out


def escribir_csv(ruta, filas):
    with open(ruta, "w", newline="", encoding="utf-8-sig") as f:
        csv.writer(f).writerows(filas)


# ------------------------------------------------------------ importar desde Excel / CSV
IMP_COLUMNAS = ["Fecha", "Asesor", "Enlace", "Campaña", "Monto", "Estado"]
IMP_EJEMPLO = [["06/11/2026", "Lesly", "https://dreamtravel.bitrix24.es/crm/deal/details/472763/", "Personalizado boston", 1323.8, "Exitosa"],
               ["06/11/2026", "Susana", "474865", "Madrid", 18810, "Activa"],
               ["03/11/2026", "Debi", "https://dreamtravel.bitrix24.es/crm/deal/details/471002/", "Cancún", 2500, "Perdida"]]
IMP_ALIAS = {"fecha": ("fecha", "fecha de proyeccion"), "asesor": ("asesor", "vendedor", "asesor de ventas"),
             "lead": ("enlace", "lead", "link", "url", "enlace del lead", "id", "id negociacion", "id de la negociacion"), "campana": ("campana", "campana de bitrix"),
             "monto": ("monto", "importe", "valor"), "tipo": ("estado", "tipo")}
_XL = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"


def _col_idx(ref):
    n = 0
    for ch in re.match(r"[A-Za-z]+", ref).group(0).upper():
        n = n * 26 + ord(ch) - 64
    return n - 1


def leer_xlsx(ruta):
    """Filas (listas de texto) de la primera hoja de un .xlsx, solo con la libreria estandar."""
    import zipfile
    import xml.etree.ElementTree as ET
    with zipfile.ZipFile(ruta) as z:
        nombres = z.namelist()
        comp = []
        if "xl/sharedStrings.xml" in nombres:
            for si in ET.fromstring(z.read("xl/sharedStrings.xml")).iter(_XL + "si"):
                comp.append("".join(t.text or "" for t in si.iter(_XL + "t")))
        hojas = sorted((n for n in nombres if re.match(r"xl/worksheets/sheet\d+\.xml$", n)),
                       key=lambda n: int(re.findall(r"\d+", n)[-1]))
        if not hojas:
            raise ValueError("El archivo no tiene hojas.")
        hoja = ET.fromstring(z.read(hojas[0]))
    filas = []
    for row in hoja.iter(_XL + "row"):
        celdas = {}
        for c in row.iter(_XL + "c"):
            t, v = c.get("t"), c.find(_XL + "v")
            if t == "s":
                val = comp[int(v.text)] if v is not None and v.text else ""
            elif t == "inlineStr":
                val = "".join(x.text or "" for x in c.iter(_XL + "t"))
            else:
                val = v.text if v is not None and v.text else ""
            celdas[_col_idx(c.get("r") or "A1")] = val
        filas.append([celdas.get(i, "") for i in range(max(celdas) + 1)] if celdas else [])
    return filas


def leer_tabla(ruta):
    if ruta.lower().endswith(".json"):
        with open(ruta, "r", encoding="utf-8-sig") as f:
            return tabla_desde_json(json.load(f))
    if ruta.lower().endswith(".csv"):
        with open(ruta, "r", encoding="utf-8-sig", newline="") as f:
            muestra = f.read(4096)
            f.seek(0)
            sep = ";" if muestra.count(";") > muestra.count(",") else ","
            return [list(r) for r in csv.reader(f, delimiter=sep)]
    return leer_xlsx(ruta)


def _letra_col(i):
    s = ""
    i += 1
    while i:
        i, r = divmod(i - 1, 26)
        s = chr(65 + r) + s
    return s


def escribir_xlsx(ruta, filas, anchos=None):
    """Crea un .xlsx (primera fila = encabezados con color) solo con la libreria estandar."""
    import zipfile
    from xml.sax.saxutils import escape
    ncol = max(len(f) for f in filas) if filas else 1
    if not anchos:
        anchos = [min(60, max(10, max(len(str(f[j])) if j < len(f) else 0 for f in filas) + 3)) for j in range(ncol)]
    xs = []
    for i, fila in enumerate(filas, 1):
        cel = []
        for j, v in enumerate(fila):
            ref = _letra_col(j) + str(i)
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                cel.append('<c r="{}"><v>{}</v></c>'.format(ref, v))
            else:
                cel.append('<c r="{}" t="inlineStr"{}><is><t>{}</t></is></c>'.format(ref, ' s="1"' if i == 1 else "", escape(str(v))))
        xs.append('<row r="{}">{}</row>'.format(i, "".join(cel)))
    cols = "".join('<col min="{0}" max="{0}" width="{1}" customWidth="1"/>'.format(j + 1, a) for j, a in enumerate(anchos))
    hoja = ('<?xml version="1.0" encoding="UTF-8"?><worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            '<cols>{}</cols><sheetData>{}</sheetData></worksheet>').format(cols, "".join(xs))
    estilos = ('<?xml version="1.0" encoding="UTF-8"?><styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
               '<fonts count="2"><font><sz val="11"/><name val="Calibri"/></font><font><b/><color rgb="FFFFFFFF"/><sz val="11"/><name val="Calibri"/></font></fonts>'
               '<fills count="3"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill>'
               '<fill><patternFill patternType="solid"><fgColor rgb="FF003D6B"/></patternFill></fill></fills>'
               '<borders count="1"><border/></borders><cellStyleXfs count="1"><xf/></cellStyleXfs>'
               '<cellXfs count="2"><xf/><xf fontId="1" fillId="2" applyFont="1" applyFill="1"/></cellXfs></styleSheet>')
    with zipfile.ZipFile(ruta, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", '<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                   '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                   '<Default Extension="xml" ContentType="application/xml"/>'
                   '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
                   '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
                   '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/></Types>')
        z.writestr("_rels/.rels", '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                   '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>')
        z.writestr("xl/workbook.xml", '<?xml version="1.0" encoding="UTF-8"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
                   'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Proyecciones" sheetId="1" r:id="rId1"/></sheets></workbook>')
        z.writestr("xl/_rels/workbook.xml.rels", '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                   '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
                   '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/></Relationships>')
        z.writestr("xl/worksheets/sheet1.xml", hoja)
        z.writestr("xl/styles.xml", estilos)


def escribir_plantilla(ruta):
    """.xlsx con los encabezados y tres filas de ejemplo."""
    escribir_xlsx(ruta, [IMP_COLUMNAS] + IMP_EJEMPLO, [13, 12, 58, 24, 12, 12])


def _fecha_celda(v):
    t = str(v).strip()
    if re.fullmatch(r"\d{5}(\.\d+)?", t):                      # numero de serie de Excel
        return date(1899, 12, 30) + timedelta(days=int(float(t)))
    if re.match(r"\d{4}-\d{2}-\d{2}", t):
        return date.fromisoformat(t[:10])
    return parse_fecha(t)


def _tipo_celda(v):
    n = norm(v).strip()
    if not n or n.startswith("activ"):
        return "activa"
    if n.startswith(("perd", "baja")):
        return "perdida"
    if n.startswith(("exit", "cierre", "vendid")):
        return "exitosa"
    return None


IMP_CAMPOS = [("fecha", "Fecha", True), ("asesor", "Asesor (vendedor)", True), ("lead", "Enlace o ID", True),
              ("campana", "Campaña", False), ("monto", "Monto", True), ("tipo", "Estado", False)]


def tabla_desde_json(obj):
    """Convierte un JSON en tabla (encabezados + filas). Acepta una lista de objetos, el JSON exportado
    ({"proyecciones": [...]}) o una copia completa de la app ({"periodos": {...}})."""
    if isinstance(obj, dict) and isinstance(obj.get("periodos"), dict):
        nombres = {v.get("id"): v.get("nombre") for v in obj.get("vendedores", []) if isinstance(v, dict)}
        regs = []
        for clave in sorted(obj["periodos"]):
            for r in obj["periodos"][clave]:
                regs.append({"Fecha": r.get("fecha", ""), "Asesor": nombres.get(r.get("vend")) or r.get("asesor", ""),
                             "Enlace": r.get("lead", ""), "Campaña": r.get("campana", ""), "Monto": r.get("monto", 0),
                             "Estado": r.get("tipo", "")})
    elif isinstance(obj, dict) and isinstance(obj.get("proyecciones"), list):
        regs = obj["proyecciones"]
    elif isinstance(obj, list):
        regs = obj
    else:
        raise ValueError("El JSON no trae una lista de proyecciones.")
    regs = [r for r in regs if isinstance(r, dict)]
    enc = []
    for r in regs:
        for k in r:
            if k not in enc:
                enc.append(k)
    return [enc] + [["" if r.get(k) is None else r.get(k) for k in enc] for r in regs]


def detectar_columnas(filas):
    """(fila de encabezados, {campo: columna}). Revisa las primeras filas y toma la que mas encabezados reconoce."""
    mejor, mapa_mejor = 0, {}
    for i, f in enumerate(filas[:15]):
        m = {}
        for j, c in enumerate(f):
            n = norm(c).strip()
            for k, alias in IMP_ALIAS.items():
                if n in alias and k not in m:
                    m[k] = j
                    break
        if len(m) > len(mapa_mejor):
            mejor, mapa_mejor = i, m
    return mejor, mapa_mejor


def importar_filas(datos, filas, aplicar=False, mapa=None, cab=None):
    """Revisa (y con aplicar=True guarda) las filas segun el mapa {campo: columna}. Sin mapa, lo detecta por los
    encabezados. Devuelve {"nuevos", "repetidos", "errores", "periodos", "total", "vista"}.
    Un enlace que ya existe (o que se repite dentro del archivo) no se importa."""
    res = {"nuevos": 0, "repetidos": [], "errores": [], "periodos": {}, "total": 0.0, "vista": []}
    if mapa is None:
        cab, mapa = detectar_columnas(filas)
    cab = cab or 0
    faltan = [n for k, n, req in IMP_CAMPOS if req and k not in mapa]
    if faltan:
        res["errores"].append((cab + 1, "Elige la columna de: " + ", ".join(faltan) + "."))
        return res
    vistos = set()

    def celda(f, k):
        j = mapa.get(k)
        return str(f[j]).strip() if j is not None and j < len(f) else ""
    for n, f in enumerate(filas[cab + 1:], cab + 2):
        if not any(str(c).strip() for c in f):
            continue
        try:
            fecha = _fecha_celda(celda(f, "fecha"))
        except (ValueError, OverflowError):
            res["errores"].append((n, "fecha no válida «{}» (usa dd/mm/aaaa)".format(celda(f, "fecha"))))
            continue
        vid = vendedor_por_nombre(datos, celda(f, "asesor")) if celda(f, "asesor") else None
        if not vid:
            res["errores"].append((n, "asesor desconocido «{}»".format(celda(f, "asesor"))))
            continue
        lead = limpiar_lead(celda(f, "lead"))
        did = extraer_id(lead)
        if not did:
            res["errores"].append((n, "el enlace no trae el ID de la negociación"))
            continue
        try:
            monto = parse_monto(celda(f, "monto"))
        except ValueError:
            res["errores"].append((n, "monto no válido «{}»".format(celda(f, "monto"))))
            continue
        tipo = _tipo_celda(celda(f, "tipo"))
        if tipo is None:
            res["errores"].append((n, "estado no válido «{}» (Activa, Perdida o Exitosa)".format(celda(f, "tipo"))))
            continue
        if did in vistos or buscar_duplicados(datos, lead, vid, "")[0]:
            res["repetidos"].append((n, "negociación {} repetida".format(did)))
            continue
        vistos.add(did)
        clave = clave_periodo(fecha.year, fecha.month - 1)
        res["nuevos"] += 1
        res["total"] += monto
        res["periodos"][clave] = res["periodos"].get(clave, 0) + 1
        nombre = next(v["nombre"] for v in datos["vendedores"] if v["id"] == vid)
        camp = canon_campana(celda(f, "campana"))
        if len(res["vista"]) < 8:
            res["vista"].append([fecha.strftime("%d/%m/%Y"), nombre, did, camp or "—", fm(monto), TIPO_LABEL[tipo]])
        if aplicar:
            datos["periodos"].setdefault(clave, []).append({
                "id": uuid.uuid4().hex[:10], "fecha": fecha.isoformat(), "asesor": nombre, "lead": lead,
                "campana": camp, "vend": vid, "monto": monto, "tipo": tipo})
    return res



class Almacen:
    def __init__(self, ruta):
        self.ruta = ruta

    def cargar(self):
        datos, aviso = None, None
        if os.path.exists(self.ruta):
            try:
                with open(self.ruta, "r", encoding="utf-8") as f:
                    datos = json.load(f)
                if not isinstance(datos, dict) or not isinstance(datos.get("periodos"), dict):
                    raise ValueError("estructura")
            except Exception:
                copia = self.ruta + ".corrupto"
                try:
                    os.replace(self.ruta, copia)
                except OSError:
                    pass
                aviso = "No se pudo leer el archivo de datos. Se guardó una copia en:\n" + copia
                datos = None
        if datos is None:
            datos = {"version": 3, "vendedores": [dict(v) for v in VEND_DEFAULT], "periodos": {}, "metas": {}, "reportes": []}
        vend = datos.get("vendedores")
        if isinstance(vend, dict):          # formato anterior: {"A": "LESLY", ...}
            datos["vendedores"] = [{"id": k, "nombre": n, "ci": i} for i, (k, n) in enumerate(vend.items())]
        elif not isinstance(vend, list):
            datos["vendedores"] = [dict(v) for v in VEND_DEFAULT]
        datos["version"] = 3
        datos.setdefault("metas", {})
        datos.setdefault("reportes", [])
        if not isinstance(datos.get("config"), dict):
            datos["config"] = {}
        for v in datos["vendedores"]:
            v["nombre"] = canon_vendedor(v["nombre"])
        for regs in datos["periodos"].values():
            for r in regs:
                r["campana"] = canon_campana(r.get("campana") or "")
        return datos, aviso

    def respaldar(self, conservar=14):
        """Copia de seguridad una vez al dia (carpeta 'copias', junto al archivo de datos); guarda las ultimas 14."""
        try:
            if not os.path.exists(self.ruta):
                return
            carpeta = os.path.join(os.path.dirname(self.ruta), "copias")
            os.makedirs(carpeta, exist_ok=True)
            destino = os.path.join(carpeta, "datos_{}.json".format(date.today().isoformat()))
            if not os.path.exists(destino):
                with open(self.ruta, "rb") as o, open(destino, "wb") as d:
                    d.write(o.read())
            viejas = sorted(f for f in os.listdir(carpeta) if re.match(r"datos_\d{4}-\d{2}-\d{2}\.json$", f))
            for f in viejas[:-conservar]:
                os.remove(os.path.join(carpeta, f))
        except OSError:
            pass

    def copia_seguridad(self, etiqueta="manual"):
        """Copia el archivo de datos a la carpeta 'copias' con fecha y hora. Devuelve la ruta (o None)."""
        try:
            if not os.path.exists(self.ruta):
                return None
            carpeta = os.path.join(os.path.dirname(self.ruta), "copias")
            os.makedirs(carpeta, exist_ok=True)
            destino = os.path.join(carpeta, "datos_{}_{}.json".format(etiqueta, datetime.now().strftime("%Y-%m-%d_%H%M%S")))
            with open(self.ruta, "rb") as o, open(destino, "wb") as d:
                d.write(o.read())
            return destino
        except OSError:
            return None

    def guardar(self, datos):
        os.makedirs(os.path.dirname(self.ruta), exist_ok=True)
        tmp = self.ruta + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(datos, f, ensure_ascii=False, indent=1)
        os.replace(tmp, self.ruta)


# =============================================================== PDF (propio)
_W_REG = {" ": 278, "!": 278, '"': 355, "#": 556, "$": 556, "%": 889, "&": 667, "'": 191, "(": 333, ")": 333,
          "*": 389, "+": 584, ",": 278, "-": 333, ".": 278, "/": 278, ":": 278, ";": 278, "<": 584, "=": 584,
          ">": 584, "?": 556, "@": 1015, "·": 278, "–": 556, "—": 1000, "…": 1000}
_W_REG.update({c: 556 for c in "0123456789"})
_W_REG.update(dict(zip("ABCDEFGHIJKLMNOPQRSTUVWXYZ", [667, 667, 722, 722, 667, 611, 778, 722, 278, 500, 667, 556, 833,
                                                        722, 778, 667, 778, 722, 667, 611, 722, 667, 944, 667, 667, 611])))
_W_REG.update(dict(zip("abcdefghijklmnopqrstuvwxyz", [556, 556, 500, 556, 556, 278, 556, 556, 222, 222, 500, 222, 833,
                                                        556, 556, 556, 556, 333, 500, 278, 556, 500, 722, 500, 500, 500])))
_W_BOLD = dict(_W_REG)
_W_BOLD.update({":": 333, ";": 333, "?": 611, "!": 333})
_W_BOLD.update(dict(zip("ABCDEFGHIJKLMNOPQRSTUVWXYZ", [722, 722, 722, 722, 667, 611, 778, 722, 278, 556, 722, 611, 833,
                                                         722, 778, 667, 778, 722, 667, 611, 722, 667, 944, 667, 667, 611])))
_W_BOLD.update(dict(zip("abcdefghijklmnopqrstuvwxyz", [556, 611, 556, 611, 556, 333, 611, 611, 278, 278, 556, 278, 889,
                                                         611, 611, 611, 611, 389, 556, 333, 611, 556, 778, 556, 556, 500])))


def puntos_arco(cx, cy, r, a0, a1, paso=3.0):
    """Puntos [x,y,x,y,...] de un arco. Angulos en grados: 0 = arriba, sentido horario."""
    n = max(2, int(abs(a1 - a0) / paso) + 1)
    pts = []
    for i in range(n + 1):
        a = math.radians(lerp(a0, a1, i / float(n)) - 90.0)
        pts += [cx + r * math.cos(a), cy + r * math.sin(a)]
    return pts


class PDF:
    """Generador minimo de PDF (paginas 16:9, texto Helvetica, formas y lineas). Origen arriba-izquierda."""
    W, H = 960.0, 540.0

    def __init__(self):
        self.paginas = []
        self.ops = []

    @staticmethod
    def _n(v):
        return "{:.2f}".format(v)

    @staticmethod
    def _c(hexcol):
        h = hexcol.lstrip("#")
        return " ".join("{:.3f}".format(int(h[i:i + 2], 16) / 255.0) for i in (0, 2, 4))

    def nueva(self, fondo="#ffffff"):
        self.ops = []
        self.paginas.append(self.ops)
        self.rect(0, 0, self.W, self.H, fondo)

    def rect(self, x, y, w, h, fill=None, stroke=None, lw=1.0):
        if w > 0 and h > 0 and (fill or stroke):
            n = self._n
            p = ["q"]
            if fill:
                p.append("{} rg".format(self._c(fill)))
            if stroke:
                p.append("{} RG {} w".format(self._c(stroke), n(lw)))
            p.append("{} {} {} {} re".format(n(x), n(self.H - y - h), n(w), n(h)))
            p.append("B" if (fill and stroke) else ("f" if fill else "S"))
            p.append("Q")
            self.ops.append(" ".join(p))

    def rrect(self, x, y, w, h, r, fill=None, stroke=None, lw=1.0):
        if w <= 0 or h <= 0 or not (fill or stroke):
            return
        r = max(0.0, min(r, w / 2.0, h / 2.0))
        n, k = self._n, 0.5523 * r
        y0 = self.H - y - h
        p = ["q"]
        if fill:
            p.append("{} rg".format(self._c(fill)))
        if stroke:
            p.append("{} RG {} w".format(self._c(stroke), n(lw)))
        p.append("{} {} m {} {} l".format(n(x + r), n(y0), n(x + w - r), n(y0)))
        p.append("{} {} {} {} {} {} c".format(n(x + w - r + k), n(y0), n(x + w), n(y0 + r - k), n(x + w), n(y0 + r)))
        p.append("{} {} l".format(n(x + w), n(y0 + h - r)))
        p.append("{} {} {} {} {} {} c".format(n(x + w), n(y0 + h - r + k), n(x + w - r + k), n(y0 + h), n(x + w - r), n(y0 + h)))
        p.append("{} {} l".format(n(x + r), n(y0 + h)))
        p.append("{} {} {} {} {} {} c".format(n(x + r - k), n(y0 + h), n(x), n(y0 + h - r + k), n(x), n(y0 + h - r)))
        p.append("{} {} l".format(n(x), n(y0 + r)))
        p.append("{} {} {} {} {} {} c".format(n(x), n(y0 + r - k), n(x + r - k), n(y0), n(x + r), n(y0)))
        p.append("h " + ("B" if (fill and stroke) else ("f" if fill else "S")))
        p.append("Q")
        self.ops.append(" ".join(p))

    def line(self, x1, y1, x2, y2, color="#0F1E2E", lw=1.0, dash=None):
        n = self._n
        d = "[{} {}] 0 d".format(dash[0], dash[1]) if dash else "[] 0 d"
        self.ops.append("q {} RG {} w {} {} {} m {} {} l S Q".format(
            self._c(color), n(lw), d, n(x1), n(self.H - y1), n(x2), n(self.H - y2)))

    def arco(self, cx, cy, r, a0, a1, color, ancho, redondo=True):
        """Arco grueso (anillo / dona). 0 grados = arriba, sentido horario."""
        pts = puntos_arco(cx, cy, r, a0, a1, 2.0)
        n = self._n
        trazo = " ".join("{} {} {}".format(n(pts[i]), n(self.H - pts[i + 1]), "m" if i == 0 else "l")
                         for i in range(0, len(pts), 2))
        self.ops.append("q {} RG {} w {} J 1 j {} S Q".format(self._c(color), n(ancho), 1 if redondo else 0, trazo))

    @staticmethod
    def _wch(ch, bold):
        t = _W_BOLD if bold else _W_REG
        if ch in t:
            return t[ch]
        base = unicodedata.normalize("NFD", ch)[0]
        return t.get(base, 556)

    def ancho(self, s, size, bold=False):
        return sum(self._wch(c, bold) for c in s) * size / 1000.0

    def text(self, x, y, s, size=12, bold=False, color="#0F1E2E", align="l", maxw=None):
        s = str(s)
        if maxw and self.ancho(s, size, bold) > maxw:
            while len(s) > 1 and self.ancho(s + "...", size, bold) > maxw:
                s = s[:-1]
            s += "..."
        w = self.ancho(s, size, bold)
        if align == "c":
            x -= w / 2.0
        elif align == "r":
            x -= w
        b = s.encode("cp1252", "replace")
        esc = b.replace(b"\\", b"\\\\").replace(b"(", b"\\(").replace(b")", b"\\)").decode("latin-1")
        self.ops.append("BT /F{} {} Tf {} rg {} {} Td ({}) Tj ET".format(
            2 if bold else 1, self._n(size), self._c(color), self._n(x), self._n(self.H - y), esc))

    def guardar(self, ruta):
        out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
        offs = {}

        def add(num, cuerpo):
            offs[num] = len(out)
            out.extend(b"%d 0 obj\n" % num + cuerpo + b"\nendobj\n")

        n_pag = len(self.paginas)
        total = 4 + 2 * n_pag
        add(1, b"<< /Type /Catalog /Pages 2 0 R >>")
        kids = " ".join("%d 0 R" % (5 + 2 * i) for i in range(n_pag))
        add(2, ("<< /Type /Pages /Kids [%s] /Count %d >>" % (kids, n_pag)).encode("ascii"))
        add(3, b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>")
        add(4, b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>")
        for i, ops in enumerate(self.paginas):
            pn, cn = 5 + 2 * i, 6 + 2 * i
            add(pn, ("<< /Type /Page /Parent 2 0 R /MediaBox [0 0 %g %g] /Contents %d 0 R "
                     "/Resources << /Font << /F1 3 0 R /F2 4 0 R >> >> >>" % (self.W, self.H, cn)).encode("ascii"))
            data = zlib.compress("\n".join(ops).encode("latin-1"))
            add(cn, b"<< /Length %d /Filter /FlateDecode >>\nstream\n" % len(data) + data + b"\nendstream")
        pos = len(out)
        out.extend(b"xref\n0 %d\n0000000000 65535 f \n" % (total + 1))
        for i in range(1, total + 1):
            out.extend(b"%010d 00000 n \n" % offs[i])
        out.extend(b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (total + 1, pos))
        with open(ruta, "wb") as f:
            f.write(bytes(out))


# ---- diapositivas -----------------------------------------------------------
def _pie(pdf, m):
    pdf.text(48, 518, "Proyecciones de Vendedores  ·  " + m["titulo"], 9, False, MUTED)
    pdf.text(912, 518, str(len(pdf.paginas)), 9, False, MUTED, "r")


def _cabecera(pdf, titulo, sub=None, punto=None):
    pdf.nueva("#FFFFFF")
    pdf.rect(0, 0, PDF.W, 8, AZUL)
    pdf.rect(0, 0, 150, 8, CORINTO)
    x = 48
    if punto:
        pdf.rrect(48, 42, 18, 18, 9, punto)
        x = 76
    pdf.text(x, 64, titulo, 28, True, AZUL, maxw=830)
    if sub:
        pdf.text(48, 88, sub, 12.5, False, MUTED, maxw=860)


def _kpi(pdf, x, y, w, h, titulo, valor, sub="", color=INK, acento=AZUL):
    pdf.rrect(x, y, w, h, 14, CARD, BORDE)
    pdf.rrect(x + 14, y + 16, 5, 18, 2.5, acento)
    pdf.text(x + 28, y + 30, titulo, 10, False, MUTED, maxw=w - 40)
    pdf.text(x + 16, y + h * 0.66, valor, 22, True, color, maxw=w - 28)
    if sub:
        pdf.text(x + 16, y + h - 12, sub, 9.5, False, MUTED, maxw=w - 28)


def _anillo_pdf(pdf, cx, cy, r, ancho, fn, fp, esp=None):
    pdf.arco(cx, cy, r, 0, 359.9, TRACK, ancho, False)
    if fp > 0.003:
        pdf.arco(cx, cy, r, 0, 359.9 * fp, AZUL_CLARO, ancho)
    if fn > 0.003:
        pdf.arco(cx, cy, r, 0, 359.9 * fn, AZUL, ancho)
    if esp is not None and 0 < esp < 1:      # marca corinto = donde deberia ir segun el ritmo
        a = math.radians(360.0 * esp - 90.0)
        pdf.line(cx + (r - ancho / 2 - 3) * math.cos(a), cy + (r - ancho / 2 - 3) * math.sin(a),
                 cx + (r + ancho / 2 + 3) * math.cos(a), cy + (r + ancho / 2 + 3) * math.sin(a), CORINTO, 3)


def _falta_tile(c):
    """(titulo, valor, color, acento) para falta / supero."""
    if c["meta"] <= 0:
        return "Falta para la meta", "—", MUTED, TRACK
    if c["falta_neto"] > 0:
        return "Falta para la meta", fm0(c["falta_neto"]), CORINTO, CORINTO
    return "Superó la meta por", fm0(-c["falta_neto"]), AZUL_MED, AZUL_MED


def _grafico_semanas(pdf, x, y, w, h, semanas, getc, destacada, meta_sem, rotulo="Meta semanal"):
    """Barras apiladas por semana: recibido (azul) + proyectado (azul claro) y linea de meta semanal."""
    base = y + h - 24
    alto = h - 24 - 22
    mensual = rotulo != "Meta semanal"                 # vista de varios meses: la etiqueta de la meta va arriba, con espacio
    mx = max([getc(s)["neto"] + getc(s)["proy"] for s in semanas] + [meta_sem, 1.0]) * (1.34 if mensual else 1.12)
    n = len(semanas)
    gw = w / float(n)
    for i, s in enumerate(semanas):
        gx = x + i * gw
        c = getc(s)
        bw = min(gw * 0.42, 62)
        bx = gx + (gw - bw) / 2.0
        if destacada and s["semana"] == destacada:
            pdf.rrect(gx + 6, y - 2, gw - 12, h + 2, 12, AZUL_PALIDO)
        th = alto * (c["neto"] + c["proy"]) / mx
        nh = alto * c["neto"] / mx
        if th > 0:
            pdf.rrect(bx, base - th, bw, th, 6, AZUL_CLARO)
            if nh > 0:
                pdf.rrect(bx, base - nh, bw, nh, 6, AZUL)
                if th - nh > 6:
                    pdf.rect(bx, base - nh, bw, min(8, nh), AZUL)
            pdf.text(bx + bw / 2.0, base - th - 6, fm0(c["neto"] + c["proy"]), 8.5, True, INK, "c")
        pdf.text(gx + gw / 2.0, base + 16, s.get("etq") or "S{}".format(s["semana"]), 10, bool(destacada and s["semana"] == destacada), INK, "c")
    pdf.line(x, base, x + w, base, "#B8C4D0", 1)
    if meta_sem > 0:
        ym = base - alto * meta_sem / mx
        pdf.line(x, ym, x + w, ym, INK, 1.2, (5, 3))
        if mensual:
            pdf.line(x + w - 170, y + 7, x + w - 150, y + 7, INK, 1.2, (5, 3))
            pdf.text(x + w, y + 11, rotulo + " " + fm0(meta_sem), 9, True, INK, "r")
        else:
            pdf.text(x + w, ym - 5, rotulo + " " + fm0(meta_sem), 9, True, INK, "r")


def _leyenda(pdf, x, y):
    pdf.rrect(x, y - 8, 10, 10, 3, AZUL)
    pdf.text(x + 15, y, "Recibido", 9.5, False, MUTED)
    pdf.rrect(x + 74, y - 8, 10, 10, 3, AZUL_CLARO)
    pdf.text(x + 89, y, "Proyectado", 9.5, False, MUTED)


def _slide_portada(pdf, m):
    pdf.nueva(AZUL)
    pdf.rect(0, 0, 16, PDF.H, CORINTO)
    pdf.text(70, 150, "REPORTE DE PROYECCIONES", 14, True, AZUL_CLARO)
    pdf.text(70, 225, m["periodo"], 58, True, "#FFFFFF", maxw=820)
    sub = ("Meses combinados" if m.get("multi") else "Mes completo" if m["vista"] == "Mes" else
           "Semana {}  ·  días {} al {}".format(m["semana"], *m["semanas"][m["semana"] - 1]["rango"]))
    pdf.text(70, 265, sub, 22, False, "#D6E4F0")
    e = m["equipo"]
    chips = [("RECIBIDO", fm0(e["neto"]), "#FFFFFF"), ("PROYECTADO", fm0(e["proy"]), "#FFFFFF"),
             ("META", fm0(e["meta"]) if e["meta"] > 0 else "—", "#FFFFFF"),
             ("% DE LA META", pct0(e["neto"], e["meta"]), "#FFFFFF")]
    x = 70
    for t, v, col in chips:
        pdf.rrect(x, 330, 196, 84, 16, "#0B5A94")
        pdf.rrect(x + 16, 346, 5, 16, 2.5, CORINTO_MED)
        pdf.text(x + 30, 359, t, 9, True, "#A9C7E0")
        pdf.text(x + 16, 396, v, 22, True, col, maxw=170)
        x += 208
    pdf.text(70, 480, "Generado el " + datetime.now().strftime("%d/%m/%Y %H:%M"), 11, False, "#8FB0CC")


def _sub_meta(m, e):
    if abs(e.get("arrastre", 0.0)) >= 0.5:
        return "Incluye {}{} de semanas anteriores".format("+" if e["arrastre"] > 0 else "-", fm0(abs(e["arrastre"])))
    if e["meta"] > 0 and m.get("esp") is not None and "esp_monto" in e:
        return "Ritmo esperado {} · {}".format(pct0(m["esp"], 1.0), fm0(e["esp_monto"]))
    return ""


def _slide_resumen(pdf, m):
    cols = [("Vendedor", 66, "l"), ("Meta", 330, "r"), ("Recibido", 430, "r"), ("Proyectado", 535, "r"),
            ("Avance", 560, "l"), ("Ritmo", 790, "r"), ("Falta / Superó", 905, "r")]
    filas = list(m["filas"])
    por_slide = 6
    trozos = [filas[i:i + por_slide] for i in range(0, len(filas), por_slide)] or [[]]
    for idx, trozo in enumerate(trozos):
        _cabecera(pdf, "Resumen del equipo" + (" (cont.)" if idx else ""), m["titulo"])
        if idx == 0:
            e = m["equipo"]
            t = _falta_tile(e)
            w = (864 - 36) / 4.0
            _kpi(pdf, 48, 106, w, 88, "Meta del equipo", fm0(e["meta"]) if e["meta"] > 0 else "Sin meta",
                 sub=_sub_meta(m, e), acento=INK)
            _kpi(pdf, 48 + (w + 12), 106, w, 88, "Recibido", fm0(e["neto"]),
                 pct0(e["neto"], e["meta"]) + " de la meta" if e["meta"] > 0 else "", AZUL, AZUL)
            _kpi(pdf, 48 + 2 * (w + 12), 106, w, 88, "Proyectado", fm0(e["proy"]), "", INK, AZUL_CLARO)
            _kpi(pdf, 48 + 3 * (w + 12), 106, w, 88, t[0], t[1], "", t[2], t[3])
            y0 = 216
        else:
            y0 = 112
        pdf.rrect(48, y0, 864, 30, 10, AZUL)
        for nombre, x, al in cols:
            if nombre == "Proyectado":
                x = 538
                al = "r"
            pdf.text(x, y0 + 20, nombre, 10, True, "#FFFFFF", al)
        y = y0 + 34
        ultimo = idx == len(trozos) - 1
        for i, f in enumerate(trozo + ([None] if ultimo else [])):
            if f is None:
                f = dict(m["equipo"], nombre="EQUIPO", ci=None)
            equipo = f.get("ci") is None
            pdf.rrect(48, y, 864, 34, 10, CARD if i % 2 == 0 else "#FFFFFF")
            if not equipo:
                pdf.rrect(60, y + 12, 10, 10, 5, PALETA[f["ci"] % len(PALETA)][1])
                pdf.text(78, y + 22, f["nombre"], 11, True, INK, maxw=150)
            else:
                pdf.text(66, y + 22, "EQUIPO", 11, True, AZUL)
            pdf.text(330, y + 22, fm0(f["meta"]) if f["meta"] > 0 else "—", 11, equipo, INK, "r")
            pdf.text(430, y + 22, fm0(f["neto"]), 11, True, AZUL, "r")
            pdf.text(538, y + 22, fm0(f["proy"]), 11, equipo, INK, "r")
            # barra de avance
            bx, bw = 566, 120
            pdf.rrect(bx, y + 12, bw, 10, 5, TRACK)
            if f["meta"] > 0:
                fn = min(f["neto"] / f["meta"], 1.0)
                fp = min((f["neto"] + f["proy"]) / f["meta"], 1.0)
                if fp > 0:
                    pdf.rrect(bx, y + 12, max(bw * fp, 6), 10, 5, AZUL_CLARO)
                if fn > 0:
                    pdf.rrect(bx, y + 12, max(bw * fn, 6), 10, 5, AZUL)
                pdf.text(bx + bw + 8, y + 22, pct0(f["neto"], f["meta"]), 10, True, INK)
                esp = m.get("esp")
                if esp is not None and f.get("ritmo") is not None:
                    pdf.rrect(bx + bw * min(esp, 1.0) - 1.5, y + 8, 3, 18, 1.5, CORINTO)
                    rt = f["ritmo"]
                    pdf.text(790, y + 22, ("+" if rt >= 0 else "-") + fm0(abs(rt)), 10.5, True,
                             AZUL_MED if rt >= 0 else CORINTO, "r")
            if f["meta"] <= 0:
                pdf.text(905, y + 22, "—", 11, False, MUTED, "r")
            elif f["falta_neto"] > 0:
                pdf.text(905, y + 22, "Falta " + fm0(f["falta_neto"]), 11, True, CORINTO, "r")
            else:
                pdf.text(905, y + 22, "Superó " + fm0(-f["falta_neto"]), 11, True, AZUL_MED, "r")
            y += 36
        _leyenda(pdf, 48, 494)
        if m.get("esp") is not None:
            pdf.rrect(196, 486, 3, 12, 1.5, CORINTO)
            pdf.text(204, 494, "Ritmo esperado", 9.5, False, MUTED)
        _pie(pdf, m)


def _slide_necesaria(pdf, m):
    cols = [("Vendedor", 66, "l"), ("Meta", 290, "r"), ("Vendido", 385, "r"), ("Proyectado", 490, "r"),
            ("Tasa", 565, "r"), ("Necesaria", 700, "r"), ("Falta proyectar", 905, "r")]
    filas = list(m["filas"])
    trozos = [filas[i:i + 6] for i in range(0, len(filas), 6)] or [[]]
    for idx, trozo in enumerate(trozos):
        _cabecera(pdf, "Proyección necesaria" + (" (cont.)" if idx else ""), m["titulo"])
        e = m["equipo"]
        if idx == 0:
            pdf.rrect(48, 104, 864, 78, 14, CARD, BORDE)
            if e["meta"] > 0 and e["nec_total"] is not None:
                t1 = "Con {} proyectados y {} vendidos ({} de cierre),".format(fm0(e["ingresado"]), fm0(e["neto"]), pct0(e["tasa"], 1.0))
                t2 = "para llegar a la meta de {} hay que proyectar {} en total: faltan {} por proyectar.".format(
                    fm0(e["meta"]), fm0(e["nec_total"]), fm0(e["nec_falta"]))
            elif e["meta"] > 0 and e["neto"] >= e["meta"]:
                t1, t2 = "El equipo ya alcanzó la meta de {}.".format(fm0(e["meta"])), "No hace falta proyectar más para lograrla."
            else:
                t1, t2 = "Aún no hay ventas exitosas o no hay meta definida:", "no se puede calcular la proyección necesaria."
            pdf.text(66, 134, t1, 12.5, True, AZUL, maxw=830)
            pdf.text(66, 158, t2, 12.5, False, INK, maxw=830)
            y0 = 200
        else:
            y0 = 112
        pdf.rrect(48, y0, 864, 30, 10, AZUL)
        for nombre, x, al in cols:
            pdf.text(x, y0 + 20, nombre, 10, True, "#FFFFFF", al)
        y = y0 + 34
        ultimo = idx == len(trozos) - 1
        for i, f in enumerate(trozo + ([None] if ultimo else [])):
            if f is None:
                f = dict(m["equipo"], nombre="EQUIPO", ci=None)
            equipo = f.get("ci") is None
            pdf.rrect(48, y, 864, 34, 10, CARD if i % 2 == 0 else "#FFFFFF")
            if not equipo:
                pdf.rrect(60, y + 12, 10, 10, 5, PALETA[f["ci"] % len(PALETA)][1])
                pdf.text(78, y + 22, f["nombre"], 11, True, INK, maxw=150)
            else:
                pdf.text(66, y + 22, "EQUIPO", 11, True, AZUL)
            if f["meta"] <= 0:
                pdf.text(905, y + 22, "Sin meta", 10.5, False, MUTED, "r")
            else:
                pdf.text(290, y + 22, fm0(f["meta"]), 11, equipo, INK, "r")
                pdf.text(385, y + 22, fm0(f["neto"]), 11, True, AZUL, "r")
                pdf.text(490, y + 22, fm0(f["ingresado"]), 11, equipo, INK, "r")
                pdf.text(565, y + 22, pct0(f["tasa"], 1.0) if f["tasa"] is not None else "—", 11, equipo, INK, "r")
                if f["neto"] >= f["meta"]:
                    pdf.text(905, y + 22, "Meta lograda", 11, True, AZUL_MED, "r")
                elif f["nec_total"] is None:
                    pdf.text(905, y + 22, "Sin ventas aún", 10.5, False, MUTED, "r")
                else:
                    pdf.text(700, y + 22, fm0(f["nec_total"]), 11, equipo, INK, "r")
                    pdf.text(905, y + 22, fm0(f["nec_falta"]), 11, True, CORINTO, "r")
            y += 36
        if ultimo:
            pdf.text(48, 492, "Tasa = vendido ÷ proyectado total (activas + perdidas + exitosas). Necesaria = meta ÷ tasa. "
                              "Falta proyectar = necesaria - proyectado.", 9, False, MUTED, maxw=864)
        _pie(pdf, m)


def _slide_embudo(pdf, m):
    cols = [("Vendedor", 66, "l"), ("Ingresadas", 290, "r"), ("Activas", 420, "r"), ("Exitosas", 550, "r"),
            ("Perdidas", 680, "r"), ("% cierre", 790, "r"), ("% perdido", 905, "r")]
    filas = list(m["filas"])
    trozos = [filas[i:i + 6] for i in range(0, len(filas), 6)] or [[]]

    def celda(n, monto):
        return "{} · {}".format(n, fm0(monto))
    for idx, trozo in enumerate(trozos):
        _cabecera(pdf, "Embudo de conversión" + (" (cont.)" if idx else ""), m["titulo"])
        y0 = 112
        pdf.rrect(48, y0, 864, 30, 10, AZUL)
        for nombre, x, al in cols:
            pdf.text(x, y0 + 20, nombre, 10, True, "#FFFFFF", al)
        y = y0 + 34
        ultimo = idx == len(trozos) - 1
        for i, f in enumerate(trozo + ([None] if ultimo else [])):
            if f is None:
                f = dict(m["equipo"], nombre="EQUIPO", ci=None)
            equipo = f.get("ci") is None
            n = f["n_neto"] + f["n_proy"] + f["n_perdidas"]
            pdf.rrect(48, y, 864, 34, 10, CARD if i % 2 == 0 else "#FFFFFF")
            if not equipo:
                pdf.rrect(60, y + 12, 10, 10, 5, PALETA[f["ci"] % len(PALETA)][1])
                pdf.text(78, y + 22, f["nombre"], 11, True, INK, maxw=150)
            else:
                pdf.text(66, y + 22, "EQUIPO", 11, True, AZUL)
            pdf.text(290, y + 22, celda(n, f["neto"] + f["proy"] + f["perdidas"]), 10.5, equipo, INK, "r")
            pdf.text(420, y + 22, celda(f["n_proy"], f["proy"]), 10.5, equipo, INK, "r")
            pdf.text(550, y + 22, celda(f["n_neto"], f["neto"]), 10.5, True, AZUL, "r")
            pdf.text(680, y + 22, celda(f["n_perdidas"], f["perdidas"]), 10.5, equipo, CORINTO, "r")
            pdf.text(790, y + 22, pct0(f["n_neto"], n) if n else "—", 10.5, True, INK, "r")
            pdf.text(905, y + 22, pct0(f["n_perdidas"], n) if n else "—", 10.5, False, INK, "r")
            y += 36
        if ultimo and 470 - (y + 14) >= 150:      # hay espacio: embudo del equipo
            e = m["equipo"]
            ex, ac, pe = (e["n_neto"], e["neto"]), (e["n_proy"], e["proy"]), (e["n_perdidas"], e["perdidas"])
            etapas = [("Ingresadas", e["n_neto"] + e["n_proy"] + e["n_perdidas"], e["neto"] + e["proy"] + e["perdidas"], AZUL),
                      ("En juego (activas + exitosas)", ex[0] + ac[0], ex[1] + ac[1], AZUL_MED),
                      ("Exitosas", ex[0], ex[1], AZUL_CLARO), ("Perdidas", pe[0], pe[1], CORINTO)]
            top = y + 14
            pdf.text(48, top + 8, "Embudo del equipo", 12, True, AZUL)
            vmax = max(etapas[0][2], 1.0)
            yy = top + 24
            for nombre, cant, monto, col in etapas:
                if yy + 28 > 478:
                    break
                pdf.text(48, yy + 17, nombre, 10, False, MUTED)
                pdf.rrect(250, yy + 2, 480, 20, 10, TRACK)
                if monto > 0:
                    pdf.rrect(250, yy + 2, max(480 * monto / vmax, 12), 20, 10, col)
                pdf.text(745, yy + 17, "{} · {}".format(cant, fm0(monto)), 10.5, True, INK)
                yy += 32
        if ultimo:
            pdf.text(48, 492, "Cada celda: cantidad de negociaciones · monto. % cierre = exitosas ÷ ingresadas; "
                              "% perdido = perdidas ÷ ingresadas (por cantidad).", 9, False, MUTED, maxw=864)
        _pie(pdf, m)


def _slide_vendedor(pdf, m, f):
    _, oscuro = PALETA[f["ci"] % len(PALETA)]
    _cabecera(pdf, f["nombre"], m["titulo"], oscuro)
    esp = m.get("esp")
    ritmo = f.get("ritmo")
    tiene = esp is not None and ritmo is not None and f["meta"] > 0
    pdf.rrect(48, 106, 262, 226, 16, CARD, BORDE)
    fn = min(f["neto"] / f["meta"], 1.0) if f["meta"] > 0 else 0.0
    fp = min((f["neto"] + f["proy"]) / f["meta"], 1.0) if f["meta"] > 0 else 0.0
    _anillo_pdf(pdf, 179, 200, 64, 17, fn, fp, esp if tiene else None)
    pdf.text(179, 209, pct0(f["neto"], f["meta"]), 30, True, AZUL, "c")
    pdf.text(179, 227, "de la meta", 10, False, MUTED, "c")
    pdf.text(179, 296, ("Meta " + fm0(f["meta"])) if f["meta"] > 0 else "Sin meta", 11, True, INK, "c")
    if tiene:
        pdf.rrect(120, 308, 3, 12, 1.5, CORINTO)
        pdf.text(128, 318, "Ritmo esperado: " + pct0(esp, 1.0), 9, False, MUTED)
    x0, w = 326, (912 - 326 - 24) / 3.0
    t = _falta_tile(f)
    _kpi(pdf, x0, 106, w, 106, "Recibido", fm0(f["neto"]), "{} ventas".format(f["n_neto"]), AZUL, AZUL)
    _kpi(pdf, x0 + (w + 12), 106, w, 106, "Proyectado", fm0(f["proy"]), "{} negociaciones".format(f["n_proy"]), INK, AZUL_CLARO)
    _kpi(pdf, x0 + 2 * (w + 12), 106, w, 106, t[0], t[1], "", t[2], t[3])
    if tiene:
        _kpi(pdf, x0, 226, w, 106, "Debería llevar", fm0(f["esp_monto"]), "{} del periodo".format(pct0(esp, 1.0)), INK, CORINTO)
        adelante = ritmo >= 0
        _kpi(pdf, x0 + (w + 12), 226, w, 106, "Ritmo vs esperado", ("+" if adelante else "-") + fm0(abs(ritmo)),
             "por encima del ritmo" if adelante else "por debajo del ritmo", AZUL_MED if adelante else CORINTO,
             AZUL_MED if adelante else CORINTO)
    else:
        _kpi(pdf, x0, 226, w, 106, "Meta mensual", fm0(f["meta_mes"]) if f["meta_mes"] > 0 else "—", "", INK, INK)
        _kpi(pdf, x0 + (w + 12), 226, w, 106, "Meta semanal", fm0(f["meta_sem"]) if f["meta_sem"] > 0 else "—", "", INK, INK)
    _kpi(pdf, x0 + 2 * (w + 12), 226, w, 106, "Perdidas", fm0(f["perdidas"]), "{} negociaciones".format(f["n_perdidas"]), CORINTO, CORINTO)
    pdf.text(48, 358, "Mes por mes" if m.get("multi") else "Semana por semana", 12, True, AZUL)
    if f["meta"] > 0:
        if f["neto"] >= f["meta"]:
            nota = "Meta lograda"
        elif f.get("nec_total") is not None:
            nota = "Para la meta: proyectar {} en total (faltan {}) · cierre {}".format(
                fm0(f["nec_total"]), fm0(f["nec_falta"]), pct0(f["tasa"], 1.0))
        else:
            nota = "Aún sin ventas: no se puede calcular la proyección necesaria"
        pdf.text(190, 358, nota, 9.5, False, MUTED, maxw=540)
    _leyenda(pdf, 740, 358)
    pdf.rrect(48, 368, 864, 134, 16, CARD, BORDE)
    _grafico_semanas(pdf, 64, 378, 832, 120, m["semanas"], lambda s, vid=f["id"]: s["filas"][vid], m["semana"], f["meta_sem"],
                     "Meta mensual (prom.)" if m.get("multi") else "Meta semanal")
    _pie(pdf, m)


def _slide_semanas(pdf, m):
    multi = m.get("multi")
    _cabecera(pdf, "Mes por mes" if multi else "Semana por semana", m["titulo"] + "  ·  equipo")
    meta_sem = (sum(s["equipo"]["meta"] for s in m["semanas"]) / len(m["semanas"])) if multi else m["semanas"][0]["equipo"]["meta"]
    _leyenda(pdf, 740, 112)
    pdf.rrect(48, 122, 864, 178, 16, CARD, BORDE)
    _grafico_semanas(pdf, 64, 128, 832, 166, m["semanas"], lambda s: s["equipo"], m["semana"], meta_sem,
                     "Meta mensual (prom.)" if multi else "Meta semanal")
    n = len(m["semanas"])
    x0, cw = 48 + 140, (864 - 140) / float(n)
    y = 312
    pdf.rrect(48, y, 864, 28, 10, AZUL)
    pdf.text(62, y + 19, "Mes" if multi else "Semana", 10, True, "#FFFFFF")
    for i, s in enumerate(m["semanas"]):
        pdf.text(x0 + cw * (i + 0.5), y + 19, s["etq"] if multi else "S{}  ({}–{})".format(s["semana"], *s["rango"]), 10, True, "#FFFFFF", "c")
    filas = [("Meta del mes" if multi else "Meta de la semana", lambda c: fm0(c["meta"]) if c["meta"] > 0 else "—", INK),
             ("Arrastre", lambda c: ("+" if c["arrastre"] > 0 else "-") + fm0(abs(c["arrastre"])) if abs(c["arrastre"]) >= 0.5 else "—", MUTED),
             ("Recibido", lambda c: fm0(c["neto"]), AZUL), ("Proyectado", lambda c: fm0(c["proy"]), INK),
             ("% de la meta", lambda c: pct0(c["neto"], c["meta"]), INK)]
    y += 32
    for j, (nombre, fn, col) in enumerate(filas):
        pdf.rrect(48, y, 864, 27, 10, CARD if j % 2 == 0 else "#FFFFFF")
        pdf.text(62, y + 18, nombre, 10.5, True, col)
        for i, s in enumerate(m["semanas"]):
            pdf.text(x0 + cw * (i + 0.5), y + 18, fn(s["equipo"]), 10.5, bool(m["semana"] == s["semana"]), INK, "c")
        y += 28
    _pie(pdf, m)


def _slide_campanas(pdf, m):
    _cabecera(pdf, "Campañas: qué se pidió y qué se recaudó", m["titulo"])
    rank = m["campanas"]
    if not rank:
        pdf.rrect(48, 106, 864, 80, 16, CARD, BORDE)
        pdf.text(70, 154, "Aún no hay proyecciones registradas en esta vista.", 14, False, MUTED)
        _pie(pdf, m)
        return
    top = campana_mas_solicitada(rank)
    total_neto = sum(e["neto"] for e in rank)
    # lider
    pdf.rrect(48, 106, 864, 80, 16, CORINTO_PALIDO)
    pdf.rrect(66, 124, 6, 44, 3, CORINTO)
    pdf.text(86, 134, "CAMPAÑA MÁS SOLICITADA", 9.5, True, CORINTO)
    pdf.text(86, 166, top["campana"], 24, True, CORINTO, maxw=520)
    pdf.text(894, 140, fm0(top["neto"]), 22, True, CORINTO, "r")
    pdf.text(894, 164, "recaudado en {} leads · {} ventas".format(top["leads"], top["n_neto"]), 10.5, False, MUTED, "r")
    # ranking
    vmax = max([e["neto"] + e["proy"] for e in rank[:6]] + [1.0])
    pdf.rrect(48, 200, 580, 300, 16, CARD, BORDE)
    y = 214
    bx, bw = 250, 250
    for i, e in enumerate(rank[:6]):
        pdf.rrect(64, y + 9, 20, 20, 10, CORINTO if i == 0 else AZUL_PALIDO)
        pdf.text(74, y + 23, str(i + 1), 10, True, "#FFFFFF" if i == 0 else AZUL, "c")
        pdf.text(94, y + 24, e["campana"], 11, i == 0, INK, maxw=145)
        pdf.rrect(bx, y + 12, bw, 14, 7, TRACK)
        wt, wn = bw * (e["neto"] + e["proy"]) / vmax, bw * e["neto"] / vmax
        if wt > 0:
            pdf.rrect(bx, y + 12, max(wt, 8), 14, 7, AZUL_CLARO)
        if wn > 0:
            pdf.rrect(bx, y + 12, max(wn, 8), 14, 7, CORINTO if i == 0 else AZUL)
        pdf.text(612, y + 22, fm0(e["neto"]), 11, True, CORINTO if i == 0 else AZUL, "r")
        pdf.text(612, y + 36, "{} leads".format(e["leads"]), 8.5, False, MUTED, "r")
        y += 46
    if len(rank) > 6:
        pdf.text(64, 494, "+ {} campañas más en la app".format(len(rank) - 6), 9, False, MUTED)
    # dona
    pdf.rrect(644, 200, 268, 300, 16, CARD, BORDE)
    pdf.text(660, 224, "Participación de lo recibido", 10, True, AZUL)
    cx, cy, r, ancho = 778, 322, 60, 20
    pdf.arco(cx, cy, r, 0, 359.9, TRACK, ancho, False)
    if total_neto > 0:
        a = 0.0
        for i, e in enumerate(rank[:5] + ([dict(campana="Otras", neto=sum(x["neto"] for x in rank[5:]))] if len(rank) > 5 else [])):
            fr = e["neto"] / total_neto
            if fr > 0.004:
                pdf.arco(cx, cy, r, a + 1.2, a + 360 * fr - 1.2, DONA_COLORES[min(i, 5)], ancho, False)
            a += 360 * fr
        pdf.text(cx, cy + 4, fm0(total_neto), 14, True, INK, "c")
        pdf.text(cx, cy + 20, "recibido", 9, False, MUTED, "c")
        yl = 412
        for i, e in enumerate(rank[:3]):
            pdf.rrect(664, yl - 8, 10, 10, 3, DONA_COLORES[i])
            pdf.text(680, yl, e["campana"], 9.5, False, INK, maxw=150)
            pdf.text(896, yl, pct0(e["neto"], total_neto), 9.5, True, INK, "r")
            yl += 18
    else:
        pdf.text(cx, cy + 4, "Sin ventas", 12, True, MUTED, "c")
    _pie(pdf, m)


def generar_pdf(m, ruta):
    """Presentacion PDF: portada, resumen del equipo, proyeccion necesaria, embudo, una lamina por vendedor, semana por semana y campañas."""
    pdf = PDF()
    with paleta_pdf():
        _slide_portada(pdf, m)
        _slide_resumen(pdf, m)
        _slide_necesaria(pdf, m)
        _slide_embudo(pdf, m)
        for f in m["filas"]:
            _slide_vendedor(pdf, m, f)
        _slide_semanas(pdf, m)
        _slide_campanas(pdf, m)
    pdf.guardar(ruta)
    return len(pdf.paginas)


# ===================================================== tema y sistema de diseño (Tk)
F = {}       # fuentes; se crean al abrir la app
ESC = 1.0    # factor de pantalla (DPI / 96); todo lo dibujado con medidas fijas pasa por E()


def E(n):
    return int(round(n * ESC))


def alto_texto(fuente):
    """Alto real de una linea de texto con esa fuente (en pixeles de pantalla)."""
    try:
        return int(fuente.metrics("linespace"))
    except Exception:
        return E(16)


def ajustar(texto, fuente, ancho):
    """Recorta con «…» para que el texto quepa en 'ancho' (medido en unidades logicas, es decir sin escala)."""
    texto = str(texto)
    if fuente.measure(texto) <= ancho * ESC:
        return texto
    lo, hi = 0, len(texto)
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if fuente.measure(texto[:mid] + "…") <= ancho * ESC:
            lo = mid
        else:
            hi = mid - 1
    return texto[:lo].rstrip() + "…"


def crear_fuentes(root):
    global ESC
    try:
        ESC = max(1.0, min(3.0, root.winfo_fpixels("1i") / 96.0))
    except Exception:
        ESC = 1.0
    base = tkfont.nametofont("TkDefaultFont")
    try:
        fams = set(tkfont.families(root))
    except Exception:
        fams = set()

    def elige(*c):
        return next((x for x in c if x in fams), None)
    txt = elige("Segoe UI Variable Text", "Segoe UI", "SF Pro Text", "Helvetica Neue", "DejaVu Sans") or base.cget("family")
    semi = elige("Segoe UI Semibold")
    cifra = elige("Bahnschrift SemiBold", "Bahnschrift", "Segoe UI Semibold")
    base.configure(family=txt, size=10)
    for n in ("TkTextFont", "TkMenuFont", "TkHeadingFont", "TkCaptionFont", "TkSmallCaptionFont", "TkTooltipFont"):
        try:
            tkfont.nametofont(n).configure(family=txt)
        except Exception:
            pass

    def mk(size, fuerte=False, fam=None):
        if fam:
            return tkfont.Font(family=fam, size=size)
        if fuerte and semi:
            return tkfont.Font(family=semi, size=size)
        return tkfont.Font(family=txt, size=size, weight="bold" if fuerte else "normal")
    F.update(base=mk(10), bold=mk(10, True), peq=mk(9), peq_b=mk(9, True), mini=mk(8), h2=mk(11, True),
             kpi=mk(22, fam=cifra or txt), titulo=mk(19, True), num=mk(21, fam=cifra or txt))


def rrect(cv, x1, y1, x2, y2, r, **kw):
    """Rectangulo redondeado dibujado como poligono suavizado."""
    r = max(0, min(r, (x2 - x1) / 2.0, (y2 - y1) / 2.0))
    pts = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2, x2 - r, y2, x1 + r, y2,
           x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
    return cv.create_polygon(pts, smooth=True, **kw)


def _bg_de(w):
    try:
        return w.cget("bg")
    except Exception:
        return BG


class Tema:
    """Paleta activa y cambio claro <-> oscuro. Los widgets de Tk se recolorean por rol (el color que tienen hoy se
    traduce al rol que ocupa en la paleta); los dibujados a mano se registran y se repintan solos con retema()."""
    OPC = ("bg", "fg", "activebackground", "activeforeground", "insertbackground", "highlightbackground",
           "highlightcolor", "troughcolor", "selectbackground", "selectforeground", "selectcolor")

    def __init__(self):
        self.app, self.nombre, self.P, self.vivos = None, "claro", dict(LIGHT), []

    def fijar(self, nombre):
        self.nombre = "oscuro" if nombre == "oscuro" else "claro"
        self.P = dict(DARK if self.nombre == "oscuro" else LIGHT)
        aplicar_paleta(self.P)

    def registrar(self, w):
        self.vivos.append(w)

    def _instantanea(self, A):
        inv = {}
        for k, v in A.items():
            inv.setdefault(v.upper(), k)
        propios = {id(w) for w in self.vivos}
        res, pila = [], [self.app]
        while pila:
            w = pila.pop()
            try:
                pila.extend(w.winfo_children())
            except tk.TclError:
                continue
            if isinstance(w, ttk.Widget) or id(w) in propios:
                continue
            for o in self.OPC:
                try:
                    rol = inv.get(str(w.cget(o)).upper())
                except tk.TclError:
                    continue
                if rol:
                    res.append((w, o, rol))
        return res

    def poner(self, nombre, ms=900):
        if nombre == self.nombre:
            return
        A, B = dict(self.P), (DARK if nombre == "oscuro" else LIGHT)
        self.nombre = nombre
        snap = self._instantanea(A)

        def paso(p):
            P = dict(B) if p >= 1.0 else {k: mezclar(A[k], B[k], p) for k in B}
            self.P = P
            aplicar_paleta(P)
            for w, o, rol in snap:
                try:
                    w.configure(**{o: P[rol]})
                except tk.TclError:
                    pass
            vivos = []
            for w in self.vivos:
                try:
                    w.retema()
                    vivos.append(w)
                except tk.TclError:
                    pass
            self.vivos = vivos
            self.app.retema_global()
        self.app.motor.correr("tema", ms, paso, ease_in_out)


TEMA = Tema()


class Motor:
    """Animaciones cortas (300-450 ms; el cambio de tema dura 900 ms) con suavizado."""

    def __init__(self, root):
        self.root, self.act, self.animar = root, {}, True

    def correr(self, clave, ms, fn, ease=ease_out):
        self.cancelar(clave)
        if not self.animar:
            fn(1.0)
            return
        t0 = time.perf_counter()

        def paso():
            p = min(1.0, (time.perf_counter() - t0) * 1000.0 / ms)
            try:
                fn(ease(p))
            except tk.TclError:
                self.act.pop(clave, None)
                return
            except Exception:
                self.act.pop(clave, None)
                traceback.print_exc()
                return
            if p < 1.0:
                self.act[clave] = self.root.after(16, paso)
            else:
                self.act.pop(clave, None)
        paso()

    def cancelar(self, clave):
        i = self.act.pop(clave, None)
        if i is not None:
            try:
                self.root.after_cancel(i)
            except Exception:
                pass


class Tarjeta(tk.Frame):
    """Contenedor de bordes redondeados: un Frame con un canvas de fondo detras. Los hijos van en self.interior."""

    def __init__(self, master, radio=14, pad=14, rol="CARD", borde="BORDE"):
        super().__init__(master, bg=_bg_de(master), bd=0, highlightthickness=0)
        self.radio, self.pad, self.rol, self.borde = E(radio), E(pad), rol, borde
        self.fondo = tk.Canvas(self, bg=_bg_de(master), highlightthickness=0, bd=0)
        self.fondo.place(x=0, y=0, relwidth=1, relheight=1)
        self.interior = tk.Frame(self, bg=globals()[rol])
        self.interior.pack(fill="both", expand=True, padx=self.pad, pady=self.pad)
        self.fondo.bind("<Configure>", lambda e: self._dibujar())
        TEMA.registrar(self)

    def _dibujar(self):
        w, h = self.fondo.winfo_width(), self.fondo.winfo_height()
        if w < 8 or h < 8:
            return
        self.fondo.delete("all")
        rrect(self.fondo, 1, 1, w - 2, h - 2, self.radio, fill=globals()[self.rol], outline=globals()[self.borde], width=1)

    def retema(self):
        fondo = _bg_de(self.master)
        self.configure(bg=fondo)
        self.fondo.configure(bg=fondo)
        self.interior.configure(bg=globals()[self.rol])
        self._dibujar()


class Boton(tk.Canvas):
    """Boton redondeado con transicion de color al pasar el mouse."""
    ESTILOS = {"primario": ("BTN", "BTN_H", "BLANCO"), "peligro": ("BTN_R", "BTN_R_H", "BLANCO"),
               "suave": ("AZUL_PALIDO", "AZUL_PALIDO_H", "AZUL"), "suave_rojo": ("CORINTO_PALIDO", None, "CORINTO")}

    def __init__(self, master, app, texto="", comando=None, estilo="suave", textvariable=None, ancho=None, alto=34, bg=None):
        self.app, self.cmd, self.fijo, self.estilo = app, comando, E(ancho) if ancho else None, estilo
        self.texto = textvariable.get() if textvariable is not None else texto
        self._ancho, self._alto, self.sobre = self._medir(), max(E(alto), alto_texto(F["bold"]) + E(14)), False
        super().__init__(master, width=self._ancho, height=self._alto, bg=_bg_de(master), highlightthickness=0, bd=0,
                         cursor="hand2")
        self.actual = self._colores()[0]
        self.bind("<Enter>", lambda e: self._ir_a(True))
        self.bind("<Leave>", lambda e: self._ir_a(False))
        self.bind("<ButtonPress-1>", lambda e: self._pintar(mezclar(self._colores()[1], "#000000", 0.12)))
        self.bind("<ButtonRelease-1>", self._soltar)
        if textvariable is not None:
            textvariable.trace_add("write", lambda *a: self.poner_texto(textvariable.get()))
        TEMA.registrar(self)
        self._pintar(self.actual)

    def _colores(self):
        b, h, f = self.ESTILOS[self.estilo]
        g = globals()
        base = g[b]
        return base, (g[h] if h else mezclar(base, g["CORINTO"], 0.14)), g[f]

    def _medir(self):
        return self.fijo or max(F["bold"].measure(self.texto) + E(36), E(72))

    def poner_texto(self, t):
        self.texto = t
        self._ancho = self._medir()
        self.configure(width=self._ancho)
        self._pintar(self.actual)

    def _pintar(self, color):
        self.actual = color
        self.delete("all")
        rrect(self, 1, 1, self._ancho - 1, self._alto - 1, E(10), fill=color, outline="")
        self.create_text(self._ancho / 2.0, self._alto / 2.0, text=self.texto, fill=self._colores()[2], font=F["bold"])

    def _ir_a(self, sobre):
        self.sobre = sobre
        origen, destino = self.actual, self._colores()[1 if sobre else 0]
        self.app.motor.correr(("btn", id(self)), 140, lambda p: self._pintar(mezclar(origen, destino, p)))

    def _soltar(self, e):
        self._pintar(self._colores()[1])
        if 0 <= e.x <= self._ancho and 0 <= e.y <= self._alto and self.cmd:
            self.cmd()

    def retema(self):
        self.configure(bg=_bg_de(self.master))
        self._pintar(self._colores()[1 if self.sobre else 0])


class Campo(tk.Canvas):
    """Campo redondeado: entrada de texto, o selector (con lista desplegable) si se dan 'valores' / solo_lectura.
    Imita la API de ttk.Combobox: cb['values'], bind('<<ComboboxSelected>>')."""

    def __init__(self, master, app, variable, ancho=180, valores=None, solo_lectura=False, placeholder="", bg=None, alto=34):
        self._ancho, self._alto = E(ancho), max(E(alto), alto_texto(F["base"]) + E(18))
        super().__init__(master, width=self._ancho, height=self._alto, bg=_bg_de(master), highlightthickness=0, bd=0)
        self.app, self.var = app, variable
        self._valores = list(valores) if valores is not None else None
        self.solo_lectura, self.placeholder = solo_lectura, placeholder
        self.foco = self.hover = False
        self.chev = self._valores is not None or solo_lectura
        self.entry = self.ventana = self.menu = None
        if not solo_lectura:
            self.entry = tk.Entry(self, textvariable=variable, bd=0, relief="flat", bg=FIELD, fg=INK, font=F["base"],
                                  highlightthickness=0, insertbackground=AZUL)
            self.ventana = self.create_window(E(12), self._alto // 2, window=self.entry, anchor="w",
                                              width=max(self._ancho - E(24) - (E(22) if self.chev else 0), 10),
                                              height=min(self._alto - E(8), alto_texto(F["base"]) + E(6)))
            self.entry.bind("<FocusIn>", lambda e: self._foco(True))
            self.entry.bind("<FocusOut>", lambda e: self._foco(False))
        if self.chev:
            self.menu = tk.Menu(self, tearoff=0, font=F["base"], bg=CARD, fg=INK, activebackground=BTN,
                                activeforeground=BLANCO, bd=0, relief="flat")
        tk.Canvas.bind(self, "<Configure>", self._conf)      # los eventos del propio canvas (no los de la entrada)
        tk.Canvas.bind(self, "<Enter>", lambda e: self._hov(True))
        tk.Canvas.bind(self, "<Leave>", lambda e: self._hov(False))
        tk.Canvas.bind(self, "<Button-1>", self._click)
        variable.trace_add("write", lambda *a: self._dibujar())
        TEMA.registrar(self)
        self._dibujar()

    # --- API compatible con Combobox
    def __setitem__(self, k, v):
        if k == "values":
            self._valores = list(v)
        else:
            super().__setitem__(k, v)

    def __getitem__(self, k):
        return tuple(self._valores or ()) if k == "values" else super().__getitem__(k)

    def bind(self, seq=None, func=None, add=None):
        if seq and seq != "<<ComboboxSelected>>" and self.entry is not None:
            return self.entry.bind(seq, func, add)
        return super().bind(seq, func, add)

    def focus_set(self):
        if self.entry is not None:
            self.itemconfigure(self.ventana, state="normal")
            self.entry.focus_set()
        else:
            super().focus_set()

    def select_range(self, a, b):
        if self.entry is not None:
            self.entry.select_range(a, b)

    # --- interno
    def _foco(self, v):
        self.foco = v
        self._dibujar()

    def _hov(self, v):
        self.hover = v
        self._dibujar()

    def _conf(self, e):
        if e.width > 20 and e.width != self._ancho:
            self._ancho = e.width
            if self.ventana is not None:
                self.itemconfigure(self.ventana, width=max(self._ancho - E(24) - (E(22) if self.chev else 0), 10))
            self._dibujar()

    def _dibujar(self):
        w, h = self._ancho, self._alto
        self.delete("fondo", "txt", "chev", "ph")
        borde = AZUL if self.foco else (AZUL_CLARO if self.hover else BORDE)
        rrect(self, 1, 1, w - 1, h - 1, E(9), fill=FIELD, outline=borde, width=2 if self.foco else 1, tags="fondo")
        self.tag_lower("fondo")
        if self.solo_lectura:
            self.create_text(E(13), h / 2.0, text=ajustar(str(self.var.get()), F["base"], (w - E(40)) / ESC), anchor="w",
                             font=F["base"], fill=INK, tags="txt")
        if self.chev:
            self.create_text(w - E(14), h / 2.0, text="▾", font=F["base"], fill=MUTED, tags="chev")
        if self.entry is not None:
            vacio = (not self.var.get()) and (not self.foco) and self.placeholder
            self.itemconfigure(self.ventana, state="hidden" if vacio else "normal")
            if vacio:
                self.create_text(E(13), h / 2.0, text=self.placeholder, anchor="w", font=F["base"], fill=MUTED, tags="ph")

    def _click(self, e):
        if self.chev and (self.solo_lectura or e.x > self._ancho - E(34)):
            self._abrir_menu()
        elif self.entry is not None:
            self.focus_set()

    def _abrir_menu(self):
        vals = self._valores or []
        if not vals:
            return
        self.menu.delete(0, "end")
        actual = self.var.get()
        for v in vals:
            marca = v == actual
            self.menu.add_command(label=("✓  " if marca else "     ") + v, font=F["bold"] if marca else F["base"],
                                  command=lambda v=v: self._elegir(v))
        try:
            self.menu.tk_popup(self.winfo_rootx(), self.winfo_rooty() + self._alto)
        finally:
            self.menu.grab_release()

    def _elegir(self, v):
        self.var.set(v)
        self.event_generate("<<ComboboxSelected>>")

    def retema(self):
        self.configure(bg=_bg_de(self.master))
        if self.entry is not None:
            self.entry.configure(bg=FIELD, fg=INK, insertbackground=AZUL)
        if self.menu is not None:
            self.menu.configure(bg=CARD, fg=INK, activebackground=BTN, activeforeground=BLANCO)
        self._dibujar()


class NavItem(tk.Canvas):
    def __init__(self, master, app, texto, comando):
        super().__init__(master, height=E(40), bg=SIDE_BG, highlightthickness=0, bd=0, cursor="hand2")
        self.app, self.texto, self.cmd, self.sel, self.sobre = app, texto, comando, False, False
        self.actual = SIDE_BG
        self.bind("<Configure>", lambda e: self._pintar(self.actual))
        self.bind("<Enter>", lambda e: self._ir(True))
        self.bind("<Leave>", lambda e: self._ir(False))
        self.bind("<Button-1>", lambda e: self.cmd())
        TEMA.registrar(self)

    def _color(self):
        return SIDE_SEL if self.sel else (SIDE_HOV if self.sobre else SIDE_BG)

    def _pintar(self, color):
        self.actual = color
        self.delete("all")
        w = max(self.winfo_width(), E(100))
        rrect(self, E(12), E(2), w - E(12), self._alto() - E(2), E(9), fill=color, outline="")
        self.create_text(E(30), self._alto() / 2.0, text=self.texto, anchor="w",
                         fill=SIDE_TXT if self.sel else SIDE_FG, font=F["bold"] if self.sel else F["base"])

    def _alto(self):
        return E(40)

    def _ir(self, sobre):
        if self.sel:
            return
        self.sobre = sobre
        origen, destino = self.actual, self._color()
        self.app.motor.correr(("nav", id(self)), 130, lambda p: self._pintar(mezclar(origen, destino, p)))

    def poner_seleccion(self, v):
        self.sel = v
        self.app.motor.cancelar(("nav", id(self)))
        self._pintar(self._color())

    def retema(self):
        self.configure(bg=SIDE_BG)
        self._pintar(self._color())


class Interruptor(tk.Canvas):
    """Claro / Oscuro: pastilla con una perilla que se desliza despacio junto con el cambio de tema."""

    def __init__(self, master, app):
        self._ancho, self._alto = E(184), E(34)
        super().__init__(master, width=self._ancho, height=self._alto, bg=SIDE_BG, highlightthickness=0, bd=0, cursor="hand2")
        self.app, self.pos = app, 1.0 if TEMA.nombre == "oscuro" else 0.0
        self.bind("<Button-1>", lambda e: app.alternar_tema())
        TEMA.registrar(self)
        self._pintar()

    def _pintar(self):
        w, h, m = self._ancho, self._alto, E(3)
        self.delete("all")
        rrect(self, 1, 1, w - 1, h - 1, h / 2.0, fill=SIDE_HOV, outline="")
        kw = w / 2.0 - m
        x0 = m + (w - 2 * m - kw) * self.pos
        rrect(self, x0, m, x0 + kw, h - m, (h - 2 * m) / 2.0, fill=SIDE_SEL, outline="")
        self.create_text(w / 4.0, h / 2.0, text="Claro", font=F["peq_b"], fill=mezclar(SIDE_TXT, SIDE_MUTED, self.pos))
        self.create_text(w * 0.75, h / 2.0, text="Oscuro", font=F["peq_b"], fill=mezclar(SIDE_MUTED, SIDE_TXT, self.pos))

    def ir_a(self, oscuro, ms=900):
        origen, destino = self.pos, 1.0 if oscuro else 0.0

        def paso(p):
            self.pos = lerp(origen, destino, p)
            self._pintar()
        self.app.motor.correr(("sw", id(self)), ms, paso, ease_in_out)

    def retema(self):
        self.configure(bg=SIDE_BG)
        self._pintar()


class ScrollFrame(tk.Frame):
    def __init__(self, master, bg=None):
        bg = bg or BG
        super().__init__(master, bg=bg)
        self.cv = tk.Canvas(self, bg=bg, highlightthickness=0)
        self.sb = ttk.Scrollbar(self, orient="vertical", command=self.cv.yview)
        self.cv.configure(yscrollcommand=self.sb.set)
        self.sb.pack(side="right", fill="y")
        self.cv.pack(side="left", fill="both", expand=True)
        self.inner = tk.Frame(self.cv, bg=bg)
        self.win = self.cv.create_window((0, 0), window=self.inner, anchor="nw")
        self.inner.bind("<Configure>", lambda e: self.cv.configure(scrollregion=self.cv.bbox("all")))
        self.cv.bind("<Configure>", lambda e: self.cv.itemconfigure(self.win, width=e.width))
        self.cv.bind("<Enter>", lambda e: self.cv.bind_all("<MouseWheel>", self._rueda))
        self.cv.bind("<Leave>", lambda e: self.cv.unbind_all("<MouseWheel>"))

    def _rueda(self, e):
        self.cv.yview_scroll(int(-e.delta / 120), "units")

    def vaciar(self):
        for w in self.inner.winfo_children():
            w.destroy()


# ============================================================ graficas (Canvas)
def anillo(cv, cx, cy, r, ancho, fn, fp, esp=None):
    """Anillo de avance: azul = recibido, azul claro = proyectado (acumulado), pista gris,
    marca corinto = donde deberia ir segun el ritmo del periodo."""
    cv.create_oval(cx - r, cy - r, cx + r, cy + r, outline=TRACK, width=ancho)
    if fp > 0.003:
        cv.create_line(*puntos_arco(cx, cy, r, 0, 359.9 * fp), fill=AZUL_CLARO, width=ancho, capstyle="round", joinstyle="round")
    if fn > 0.003:
        cv.create_line(*puntos_arco(cx, cy, r, 0, 359.9 * fn), fill=AZUL, width=ancho, capstyle="round", joinstyle="round")
    if esp is not None and 0 < esp < 1:
        a = math.radians(360.0 * esp - 90.0)
        cv.create_line(cx + (r - ancho / 2 - 3) * math.cos(a), cy + (r - ancho / 2 - 3) * math.sin(a),
                       cx + (r + ancho / 2 + 3) * math.cos(a), cy + (r + ancho / 2 + 3) * math.sin(a),
                       fill=CORINTO, width=3, capstyle="round")


def dibujar_semanas(cv, x, y, w, h, sem, destacada, meta_sem, etq=None):
    """Mini columnas por semana: neto (azul) + proyectado (azul claro) apilados y linea de meta semanal."""
    n = len(sem)
    if n == 0:
        return
    zona = h - 16
    base = y + zona
    mx = max([a + b for a, b in sem] + [meta_sem, 1.0]) * 1.12
    cw = w / float(n)
    bw = min(cw * 0.46, 30)
    for i, (neto, proy) in enumerate(sem):
        gx = x + i * cw
        bx = gx + (cw - bw) / 2.0
        if destacada and destacada == i + 1:
            rrect(cv, gx + 3, y - 4, gx + cw - 3, y + h + 2, 10, fill=AZUL_PALIDO, outline="")
        th, nh = zona * (neto + proy) / mx, zona * neto / mx
        if th > 1:
            rrect(cv, bx, base - th, bx + bw, base, min(5, bw / 2.0), fill=AZUL_CLARO, outline="")
        if nh > 1:
            rrect(cv, bx, base - nh, bx + bw, base, min(5, bw / 2.0), fill=AZUL, outline="")
            if th - nh > 5:
                cv.create_rectangle(bx, base - nh, bx + bw, base - max(nh - 5, 0), fill=AZUL, outline="")
        cv.create_text(gx + cw / 2.0, base + 9, text=etq[i] if etq else "S{}".format(i + 1), font=F["mini"],
                       fill=AZUL if destacada == i + 1 else MUTED)
    if meta_sem > 0:
        ym = base - zona * meta_sem / mx
        cv.create_line(x, ym, x + w, ym, fill=INK, width=1, dash=(4, 3))


def _partes_meta(neto, proy, meta):
    """Reparto de la meta: recibido, proyectado (sin pasarse de la meta) y lo que falta."""
    if meta <= 0:
        return None
    rec = min(neto, meta)
    pro = max(min(proy, meta - rec), 0.0)
    return [(rec / meta, AZUL), (pro / meta, AZUL_CLARO), (max(meta - rec - pro, 0.0) / meta, CORINTO)]


def segmentos(cv, cx, cy, r, ancho, partes, k=1.0, gap=1.5):
    """Dona dividida en partes [(fraccion, color)]."""
    cv.create_oval(cx - r, cy - r, cx + r, cy + r, outline=TRACK, width=ancho)
    a = 0.0
    for fr, col in partes:
        if fr * k > 0.003:
            a1 = a + 360.0 * fr * k
            cv.create_line(*puntos_arco(cx, cy, r, a + gap, max(a1 - gap, a + gap + 0.5)), fill=col, width=ancho, capstyle="butt")
        a += 360.0 * fr * k


def pastel(cv, cx, cy, r, partes, k=1.0):
    """Pastel solido dividido en partes [(fraccion, color)]."""
    a = 0.0
    for fr, col in partes:
        if fr * k > 0.003:
            a1 = a + 360.0 * fr * k
            cv.create_polygon([cx, cy] + puntos_arco(cx, cy, r, a, min(a1, a + 359.9), 3.0), fill=col, outline=CARD, width=2)
        a += 360.0 * fr * k


def dibujar_acumulada(cv, x, y, w, h, sem, meta, destacada=None, etq=None):
    """Lineas acumuladas por semana: recibido (azul) y recibido + proyectado (azul claro) contra el ritmo de la meta (corinto)."""
    n = len(sem)
    if n == 0:
        return
    base, alto = y + h - 14, h - 14 - 8
    x0, ancho = x + 8, w - 16
    cn, ct = [0.0], [0.0]
    for a, b in sem:
        cn.append(cn[-1] + a)
        ct.append(ct[-1] + a + b)
    ultima = max([i + 1 for i, (a, b) in enumerate(sem) if a + b > 0], default=0)
    mx = max(meta, ct[ultima], 1.0) * 1.12
    px = lambda k: x0 + ancho * k / float(n)
    py = lambda v: base - alto * v / mx
    cv.create_line(x, base, x + w, base, fill="#B8C4D0")
    for k in range(1, n + 1):
        cv.create_text(px(k), base + 8, text=etq[k - 1] if etq else "S{}".format(k), font=F["mini"], fill=AZUL if destacada == k else MUTED)
    if meta > 0:
        cv.create_line(px(0), base, px(n), py(meta), fill=CORINTO, width=2, dash=(4, 3))
        cv.create_text(px(n), py(meta) - 8, text="Meta " + fm0(meta), anchor="e", font=F["mini"], fill=CORINTO)
    if ultima >= 1:
        cv.create_line(*[v for k in range(ultima + 1) for v in (px(k), py(ct[k]))], fill=AZUL_CLARO, width=3,
                       capstyle="round", joinstyle="round")
        cv.create_line(*[v for k in range(ultima + 1) for v in (px(k), py(cn[k]))], fill=AZUL, width=3,
                       capstyle="round", joinstyle="round")
        for k in range(1, ultima + 1):
            cv.create_oval(px(k) - 3, py(cn[k]) - 3, px(k) + 3, py(cn[k]) + 3, fill=CARD, outline=AZUL, width=2)
        lx = min(max(px(ultima), 24), w - 24)
        cv.create_text(lx, py(cn[ultima]) + 12, text=fm0(cn[ultima]), font=F["peq_b"], fill=AZUL)


def _tercera(vis, meta):
    falta = meta - vis["neto"]
    if meta <= 0:
        return ("Falta", "—", TRACK, MUTED)
    if falta > 0:
        return ("Falta", fm0(falta), CORINTO, CORINTO)
    return ("Superó por", fm0(-falta), AZUL_MED, AZUL_MED)


def _stats(cv, vis, meta):
    return [("Recibido", fm0(vis["neto"]), AZUL, INK), ("Proyectado", fm0(vis["proy"]), AZUL_CLARO, INK), _tercera(vis, meta)]


def bloque_ritmo(cv, w, y0, esp, neto, esp_monto, meta, grande=False):
    """Tres cifras: porcentaje estimado (lo que deberia llevar segun los dias transcurridos), porcentaje real y
    la diferencia (faltante si va atras, de mas si va adelante), mas una barra con la marca del ritmo."""
    real = neto / meta if meta > 0 else 0.0
    pe, pr = esp * 100.0, real * 100.0
    atras = pr < pe - 1e-9
    dif = abs(pr - pe)
    f_val = F["num"] if grande else F["h2"]
    cols = [("Estimado", "{:.0f}%".format(pe), INK, fm0(esp_monto)),
            ("Real", "{:.0f}%".format(pr), AZUL, fm0(neto)),
            ("Faltante" if atras else "De más", "{:.0f}%".format(dif), CORINTO if atras else AZUL_MED,
             fm0(abs(neto - esp_monto)))]
    cw = w / 3.0
    alto_v = 26 if grande else 17
    for i, (lab, val, col, monto) in enumerate(cols):
        x = i * cw
        cv.create_text(x, y0 + 5, text=lab, anchor="w", font=F["peq"], fill=MUTED)
        cv.create_text(x, y0 + 16 + alto_v / 2.0, text=val, anchor="w", font=f_val, fill=col)
        cv.create_text(x, y0 + 20 + alto_v + 6, text=monto, anchor="w", font=F["mini"], fill=MUTED)
    yb = y0 + 20 + alto_v + 22
    rrect(cv, 0, yb, w, yb + 8, 4, fill=TRACK, outline="")
    xr, xe = w * min(real, 1.0), w * min(esp, 1.0)
    if atras and xe - xr > 2:
        rrect(cv, 0, yb, max(xe, 8), yb + 8, 4, fill=CORINTO_MED, outline="")
    if xr > 1:
        rrect(cv, 0, yb, max(xr, 8), yb + 8, 4, fill=AZUL, outline="")
    if 0 < esp < 1:
        cv.create_line(xe, yb - 4, xe, yb + 12, fill=INK, width=2, capstyle="round")


def dibujar_necesaria(cv, w, filas, equipo):
    """Tabla: por vendedor y para el equipo, cuanta proyeccion hace falta para llegar a la meta con la tasa actual."""
    cv.create_text(0, 9, text="Proyección necesaria para la meta", anchor="w", font=F["h2"], fill=INK)
    cv.create_text(0, 28, text="Con la tasa de cierre actual: vendido ÷ proyectado.", anchor="w", font=F["peq"], fill=MUTED)
    xt, xp, xn, xf = w * 0.42, w * 0.60, w * 0.80, w
    y = 56
    cv.create_text(0, y, text="Vendedor", anchor="w", font=F["peq"], fill=MUTED)
    for x, t in ((xt, "Tasa de cierre"), (xp, "Proyectado"), (xn, "Necesaria"), (xf, "Falta proyectar")):
        cv.create_text(x, y, text=t, anchor="e", font=F["peq"], fill=MUTED)
    for k, f in enumerate(list(filas) + [equipo]):
        y += 24
        total = k == len(filas)
        cv.create_line(0, y - 12, w, y - 12, fill=BORDE)
        fb = F["bold"] if total else F["base"]
        cv.create_text(0, y, text=ajustar(f["nombre"], fb, w * 0.30), anchor="w", font=fb, fill=INK)
        if f["meta"] <= 0:
            cv.create_text(xf, y, text="Sin meta", anchor="e", font=F["peq"], fill=MUTED)
            continue
        cv.create_text(xt, y, text=pct0(f["tasa"], 1.0) if f["tasa"] is not None else "—", anchor="e", font=fb, fill=INK)
        cv.create_text(xp, y, text=fm0(f["ingresado"]), anchor="e", font=fb, fill=INK)
        if f["neto"] >= f["meta"]:
            cv.create_text(xf, y, text="Meta lograda", anchor="e", font=F["bold"], fill=AZUL_MED)
        elif f["nec_total"] is None:
            cv.create_text(xf, y, text="Sin ventas aún", anchor="e", font=F["peq"], fill=MUTED)
        else:
            cv.create_text(xn, y, text=fm0(f["nec_total"]), anchor="e", font=fb, fill=INK)
            cv.create_text(xf, y, text=fm0(f["nec_falta"]), anchor="e", font=F["bold"], fill=CORINTO)


def dibujar_vendedor(cv, w, h, d, vis):
    """Tarjeta de vendedor segun el tipo de grafica elegido (d['tipo']): cabecera, cuerpo, ritmo y semanas."""
    cv.delete("all")
    meta = d["meta"]
    tipo = d.get("tipo", "anillo")
    esp = d.get("esp")
    cv.create_oval(0, 8, 10, 18, fill=d["colores"][1], outline="")
    cv.create_text(18, 13, text=ajustar(d["nombre"], F["h2"], w - 190), anchor="w", font=F["h2"], fill=INK)
    arr = d.get("arrastre", 0.0)
    cv.create_text(w, 13, text=("Meta {}{}".format(fm0(meta), " ({}{})".format("+" if arr > 0 else "−", fm0(abs(arr)))
                                                  if abs(arr) >= 0.5 else "")) if meta > 0 else "Sin meta",
                   anchor="e", font=F["peq"], fill=MUTED)
    partes = _partes_meta(vis["neto"], vis["proy"], meta)
    fn = min(vis["neto"] / meta, 1.0) if meta > 0 else 0.0
    fp = min((vis["neto"] + vis["proy"]) / meta, 1.0) if meta > 0 else 0.0
    stats = _stats(cv, vis, meta)
    cx, cy, r, gw = 62, 92, 46, 13
    if tipo in ("anillo", "dona", "pastel"):
        if tipo == "anillo":
            anillo(cv, cx, cy, r, gw, fn, fp, esp if meta > 0 else None)
        elif tipo == "dona":
            if partes:
                segmentos(cv, cx, cy, r, gw, partes)
                if esp is not None and 0 < esp < 1:
                    a = math.radians(360.0 * esp - 90.0)
                    cv.create_line(cx + (r - gw / 2 - 3) * math.cos(a), cy + (r - gw / 2 - 3) * math.sin(a),
                                   cx + (r + gw / 2 + 3) * math.cos(a), cy + (r + gw / 2 + 3) * math.sin(a),
                                   fill=INK, width=3, capstyle="round")
            else:
                cv.create_oval(cx - r, cy - r, cx + r, cy + r, outline=TRACK, width=gw)
        else:
            if partes:
                pastel(cv, cx, cy, r + 6, partes)
            else:
                cv.create_oval(cx - r, cy - r, cx + r, cy + r, fill=TRACK, outline="")
        if tipo != "pastel":
            cv.create_text(cx, cy - 4, text=pct0(vis["neto"], meta), font=F["num"], fill=AZUL)
            cv.create_text(cx, cy + 16, text="de la meta", font=F["mini"], fill=MUTED)
        x0 = 136
        for i, (lab, val, marca, col) in enumerate(stats):
            y = 44 + i * 38
            cv.create_oval(x0, y + 2, x0 + 8, y + 10, fill=marca, outline="")
            cv.create_text(x0 + 16, y + 6, text=lab, anchor="w", font=F["peq"], fill=MUTED)
            cv.create_text(x0 + 16, y + 22, text=val, anchor="w", font=F["h2"], fill=col)
    else:
        if tipo == "barra":
            cv.create_text(0, 44, text=pct0(vis["neto"], meta), anchor="w", font=F["num"], fill=AZUL)
            cv.create_text(w - 2, 48, text="de la meta", anchor="e", font=F["peq"], fill=MUTED)
            rrect(cv, 0, 66, w, 84, 9, fill=TRACK, outline="")
            if fp > 0:
                rrect(cv, 0, 66, max(w * fp, 18), 84, 9, fill=AZUL_CLARO, outline="")
            if fn > 0:
                rrect(cv, 0, 66, max(w * fn, 18), 84, 9, fill=AZUL, outline="")
            if meta > 0 and esp is not None and 0 < esp < 1:
                rrect(cv, w * esp - 1.5, 60, w * esp + 1.5, 90, 1.5, fill=CORINTO, outline="")
            ytxt = 108
        else:   # acumulada
            dibujar_acumulada(cv, 0, 28, w, 88, vis["sem"], d.get("meta_mes", meta), d["destacada"], d.get("etq"))
            ytxt = 124
        cw = w / 3.0
        for i, (lab, val, marca, col) in enumerate(stats):
            xx = i * cw
            cv.create_oval(xx, ytxt + 2, xx + 8, ytxt + 10, fill=marca, outline="")
            cv.create_text(xx + 16, ytxt + 6, text=lab, anchor="w", font=F["peq"], fill=MUTED)
            cv.create_text(xx + 16, ytxt + 22, text=val, anchor="w", font=F["h2"], fill=col)
    if meta > 0 and esp is not None:           # estimado / real / faltante o de mas
        bloque_ritmo(cv, w, 158, esp, vis["neto"], d.get("esp_monto", 0.0), meta)
    cv.create_line(0, 242, w, 242, fill=BORDE)
    cv.create_text(0, 254, text="Por semana", anchor="w", font=F["peq"], fill=MUTED)
    dibujar_semanas(cv, 0, 266, w, 56, vis["sem"], d["destacada"], d["meta_sem"], d.get("etq"))


def _embudo_barras(cv, w, h, etapas, perdidas, por_monto, k):
    """Barras horizontales por etapa, una debajo de otra."""
    filas = [(n, v, c) for (n, v), c in zip(etapas, (AZUL, AZUL_MED, AZUL_CLARO))] + [("Perdidas", perdidas, CORINTO)]
    idx = 1 if por_monto else 0
    vmax = max([f[1][idx] for f in filas] + [1])
    for i, (nombre, (cant, monto), col) in enumerate(filas):
        y = 4 + i * 50
        cv.create_text(6, y + 7, text=nombre, anchor="w", font=F["peq"], fill=MUTED)
        v = monto if por_monto else cant
        ancho = max((w - 12) * v / vmax * k, 0)
        if v > 0:
            rrect(cv, 6, y + 16, 6 + max(ancho, 14), y + 40, 12, fill=col, outline="")
        if k > 0.85:
            cv.create_text(12 + max(ancho, 14), y + 28, text="{} · {}".format(cant, fm0(monto)), anchor="w", font=F["bold"],
                           fill=INK) if ancho < w * 0.55 else cv.create_text(
                6 + ancho / 2.0, y + 28, text="{} · {}".format(cant, fm0(monto)), font=F["bold"], fill=texto_sobre(col))


def _embudo_estados(cv, w, h, etapas, perdidas, por_monto, k, tipo):
    """Como terminaron las negociaciones: exitosas, activas y perdidas (dona o pastel)."""
    exi, juego = etapas[2][1], etapas[1][1]
    act = (juego[0] - exi[0], juego[1] - exi[1])
    estados = [("Exitosas", exi, AZUL), ("Activas", act, AZUL_CLARO), ("Perdidas", perdidas, CORINTO)]
    idx = 1 if por_monto else 0
    total = sum(e[1][idx] for e in estados)
    cx, cy, r = 84, 100, 64
    if total <= 0:
        cv.create_oval(cx - r, cy - r, cx + r, cy + r, outline=TRACK, width=22)
        cv.create_text(cx, cy, text="Sin datos", font=F["bold"], fill=MUTED)
        return
    partes = [(e[1][idx] / total, e[2]) for e in estados]
    if tipo == "pastel":
        pastel(cv, cx, cy, r + 6, partes, k)
    else:
        segmentos(cv, cx, cy, r - 8, 22, partes, k)
        cv.create_text(cx, cy - 6, text=fm0(total) if por_monto else str(int(total)), font=F["h2"], fill=INK)
        cv.create_text(cx, cy + 12, text="ingresadas", font=F["mini"], fill=MUTED)
    for i, (nombre, (cant, monto), col) in enumerate(estados):
        y = 34 + i * 58
        rrect(cv, 190, y, 196, y + 40, 3, fill=col, outline="")
        cv.create_text(208, y + 8, text=nombre, anchor="w", font=F["peq"], fill=MUTED)
        cv.create_text(208, y + 28, text="{} · {}".format(cant, fm0(monto)), anchor="w", font=F["bold"], fill=INK)
        cv.create_text(w - 4, y + 20, text=pct0(monto if por_monto else cant, total), anchor="e", font=F["h2"], fill=col)


def dibujar_embudo(cv, w, h, etapas, perdidas, por_monto, k, tipo="embudo"):
    if w < 120:
        cv.delete("all")
        return
    if tipo == "barras":
        cv.delete("all")
        return _embudo_barras(cv, w, h, etapas, perdidas, por_monto, k)
    if tipo in ("dona", "pastel"):
        cv.delete("all")
        return _embudo_estados(cv, w, h, etapas, perdidas, por_monto, k, tipo)
    return _embudo_clasico(cv, w, h, etapas, perdidas, por_monto, k)


def _embudo_clasico(cv, w, h, etapas, perdidas, por_monto, k):
    """Embudo: barras centradas cuyo ancho es proporcional al valor; % de conversion entre etapas."""
    cv.delete("all")
    if w < 120:
        return
    vals = [(m if por_monto else n) for _, (n, m) in etapas]
    vmax = max(vals[0], 1)
    colores = [AZUL, AZUL_MED, AZUL_CLARO]
    fg = [texto_sobre(c) for c in colores]
    fila = 50
    for i, ((nombre, (n, m)), v) in enumerate(zip(etapas, vals)):
        y = 4 + i * fila
        cv.create_text(6, y + 7, text=nombre, anchor="w", font=F["peq"], fill=MUTED)
        ancho = max((w - 12) * (v / vmax) * k, 0)
        ancho = max(ancho, 110 * k) if v > 0 else 0
        x0 = (w - ancho) / 2.0
        if ancho > 0:
            rrect(cv, x0, y + 16, x0 + ancho, y + 40, 12, fill=colores[i], outline="")
            if k > 0.85:
                cv.create_text(w / 2.0, y + 28, text="{} · {}".format(n, fm0(m)), font=F["bold"], fill=fg[i])
        if i > 0 and vals[i - 1] > 0 and k > 0.85:
            cv.create_text(w - 6, y + 7, text="▼ " + pct0(v, vals[i - 1]), anchor="e", font=F["peq_b"], fill=AZUL_MED)
    y = 4 + len(etapas) * fila
    pn, pm = perdidas
    pv = pm if por_monto else pn
    cv.create_text(6, y + 7, text="Perdidas", anchor="w", font=F["peq"], fill=MUTED)
    ancho = max((w - 12) * (pv / vmax) * k, 0)
    if pv > 0:
        ancho = max(ancho, 110 * k)
        rrect(cv, 6, y + 16, 6 + ancho, y + 40, 12, fill=CORINTO, outline="")
        if k > 0.85:
            cv.create_text(6 + ancho / 2.0, y + 28, text="{} · {}".format(pn, fm0(pm)), font=F["bold"], fill=texto_sobre(CORINTO))
    else:
        cv.create_text(6, y + 28, text="—", anchor="w", font=F["base"], fill=MUTED)


def _ranking_barras(cv, w, rank, total_neto, k):
    """Ranking de campañas: barras redondeadas; la lider en corinto, el resto en azul; proyectado en azul claro."""
    cv.delete("all")
    if w < 240:
        return
    rank = rank[:10]
    if not rank:
        cv.create_text(w / 2.0, 60, text="Sin proyecciones en esta vista", fill=MUTED, font=F["base"])
        return
    vmax = max(e["neto"] + e["proy"] for e in rank) or 1.0
    x_bar, ancho = 230, max(w - 230 - 150, 100)
    for i, e in enumerate(rank):
        y = 8 + i * 40
        lider = i == 0 and e["neto"] > 0
        cv.create_oval(6, y + 4, 28, y + 26, fill=CORINTO if lider else AZUL_PALIDO, outline="")
        cv.create_text(17, y + 15, text=str(i + 1), font=F["peq_b"], fill=texto_sobre(CORINTO) if lider else AZUL)
        cv.create_text(38, y + 15, text=ajustar(e["campana"], F["bold"] if lider else F["base"], 184), anchor="w", font=F["bold"] if lider else F["base"], fill=INK)
        rrect(cv, x_bar, y + 7, x_bar + ancho, y + 23, 8, fill=TRACK, outline="")
        wt, wn = ancho * (e["neto"] + e["proy"]) / vmax * k, ancho * e["neto"] / vmax * k
        if wt > 1:
            rrect(cv, x_bar, y + 7, x_bar + max(wt, 10), y + 23, 8, fill=AZUL_CLARO, outline="")
        if wn > 1:
            rrect(cv, x_bar, y + 7, x_bar + max(wn, 10), y + 23, 8, fill=CORINTO if lider else AZUL, outline="")
        cv.create_text(w - 4, y + 11, text=fm0(e["neto"]), anchor="e", font=F["bold"], fill=CORINTO if lider else AZUL)
        cv.create_text(w - 4, y + 25, text="{} ventas".format(e["n_neto"]), anchor="e", font=F["mini"], fill=MUTED)


def _ranking_pareto(cv, w, h, rank, total_neto, k):
    """Columnas por campaña (recibido + proyectado) y linea acumulada del % de lo recibido (Pareto)."""
    cv.delete("all")
    rank = rank[:8]
    if not rank:
        cv.create_text(w / 2.0, 60, text="Sin proyecciones en esta vista", fill=MUTED, font=F["base"])
        return
    n = len(rank)
    base, alto = h - 40, h - 40 - 30
    x0, ancho = 8, w - 8 - 44
    vmax = max(e["neto"] + e["proy"] for e in rank) or 1.0
    ref = [e["neto"] if total_neto > 0 else e["proy"] for e in rank]
    ref_total = sum(e["neto"] if total_neto > 0 else e["proy"] for e in rank) or 1.0
    bw = min(ancho / n * 0.56, 62)
    cv.create_line(0, base, w, base, fill=BORDE)
    pts, cum = [], 0.0
    for i, e in enumerate(rank):
        cx = x0 + ancho * (i + 0.5) / n
        lider = i == 0 and e["neto"] > 0
        th, nh = alto * (e["neto"] + e["proy"]) / vmax * k, alto * e["neto"] / vmax * k
        if th > 1:
            rrect(cv, cx - bw / 2, base - th, cx + bw / 2, base, 7, fill=AZUL_CLARO, outline="")
        if nh > 1:
            rrect(cv, cx - bw / 2, base - nh, cx + bw / 2, base, 7, fill=CORINTO if lider else AZUL, outline="")
        cv.create_text(cx, base + 14, text=ajustar(e["campana"], F["mini"], ancho / n - 4), font=F["mini"], fill=INK)
        cv.create_text(cx, base + 28, text=fm0(e["neto"]), font=F["mini"], fill=CORINTO if lider else AZUL)
        cum += ref[i]
        pts += [cx, base - alto * (cum / ref_total) * k]
    if n >= 2:
        cv.create_line(*pts, fill=CORINTO_MED, width=2, capstyle="round", joinstyle="round")
    for i in range(n):
        cv.create_oval(pts[2 * i] - 4, pts[2 * i + 1] - 4, pts[2 * i] + 4, pts[2 * i + 1] + 4, fill=CARD, outline=CORINTO_MED, width=2)
        if k > 0.9:
            cv.create_text(pts[2 * i], pts[2 * i + 1] - 13, text=pct0(sum(ref[:i + 1]), ref_total), font=F["mini"], fill=CORINTO)
    cv.create_text(w - 2, base - alto, text="100%", anchor="e", font=F["mini"], fill=CORINTO)
    cv.create_text(w - 2, base, text="0%", anchor="e", font=F["mini"], fill=CORINTO)


def dibujar_ranking(cv, w, rank, total_neto, k, tipo="barras", h=400):
    if tipo == "pareto":
        return _ranking_pareto(cv, w, h, rank, total_neto, k)
    return _ranking_barras(cv, w, rank, total_neto, k)


def dibujar_dona(cv, w, h, rank, total_neto, k, tipo="dona"):
    """Participacion de cada campaña en lo recibido (top 5 + otras)."""
    cv.delete("all")
    if w < 120:
        return
    cx, cy, r, gw = w / 2.0, 92, 62, 20
    cv.create_oval(cx - r, cy - r, cx + r, cy + r, outline=TRACK, width=gw)
    partes = [(e["campana"], e["neto"]) for e in rank[:5]]
    if len(rank) > 5:
        partes.append(("Otras", sum(e["neto"] for e in rank[5:])))
    partes = [p for p in partes if p[1] > 0]
    if total_neto <= 0:
        cv.create_text(cx, cy, text="Sin ventas", font=F["bold"], fill=MUTED)
        return
    if tipo == "pastel":
        pastel(cv, cx, cy, r + 8, [(v / total_neto, DONA_COLORES[min(i, 5)]) for i, (nombre, v) in enumerate(partes)], k)
    else:
        segmentos(cv, cx, cy, r, gw, [(v / total_neto, DONA_COLORES[min(i, 5)]) for i, (nombre, v) in enumerate(partes)], k)
        cv.create_text(cx, cy - 6, text=fm0(total_neto * k), font=F["h2"], fill=INK)
        cv.create_text(cx, cy + 12, text="recibido", font=F["mini"], fill=MUTED)
    y = 180
    for i, (nombre, v) in enumerate(partes):
        cv.create_oval(10, y - 5, 20, y + 5, fill=DONA_COLORES[min(i, 5)], outline="")
        cv.create_text(28, y, text=ajustar(nombre, F["peq"], w - 70), anchor="w", font=F["peq"], fill=INK)
        cv.create_text(w - 10, y, text=pct0(v, total_neto), anchor="e", font=F["peq_b"], fill=INK)
        y += 22


# ============================================================ componentes de pagina
class Pagina(tk.Frame):
    def __init__(self, master, app):
        super().__init__(master, bg=BG)
        self.app = app

    def refrescar(self):
        pass

    def al_mostrar(self):
        self.refrescar()

    def encabezado(self, titulo):
        cab = tk.Frame(self, bg=BG)
        cab.pack(fill="x", padx=E(26), pady=(E(20), E(10)))
        izq = tk.Frame(cab, bg=BG)
        izq.pack(side="left")
        tk.Label(izq, text=titulo, bg=BG, fg=INK, font=F["titulo"], anchor="w").pack(anchor="w")
        sub = tk.Label(izq, bg=BG, fg=MUTED, font=F["base"], anchor="w")
        sub.pack(anchor="w")
        der = tk.Frame(cab, bg=BG)
        der.pack(side="right")
        return sub, der


class FiltroTiempo(tk.Frame):
    """Boton Mes/Semana (muestra la vista actual; al presionarlo cambia) + selector de semana.
    Con varios meses elegidos solo hay vista de mes, asi que el boton se cambia por una nota."""

    def __init__(self, master, app):
        super().__init__(master, bg=BG)
        self.app = app
        self.lbl = tk.Label(self, text="Ver por", bg=BG, fg=MUTED, font=F["base"])
        self.btn = Boton(self, app, "", app.toggle_modo, "primario", textvariable=app.var_modo, ancho=100)
        self.cb = Campo(self, app, app.var_sem, ancho=178, valores=[], solo_lectura=True)
        self.cb.bind("<<ComboboxSelected>>", lambda e: app.notificar(guardar=False))
        self.nota = tk.Label(self, bg=BG, fg=AZUL, font=F["bold"])

    def sincronizar(self):
        a = self.app
        for w in (self.lbl, self.btn, self.cb, self.nota):
            w.pack_forget()
        if a.es_multi:
            a.var_modo.set("Mes")
            self.nota.config(text="Meses combinados · {}".format(a.resumen_meses()))
            self.nota.pack(side="left")
            return
        self.lbl.pack(side="left", padx=(0, E(8)))
        self.btn.pack(side="left")
        self.cb["values"] = a.etiquetas_semanas()
        if a.var_modo.get() == "Semana":
            self.cb.pack(side="left", padx=(E(8), 0))


class SelectorMeses(Campo):
    """Lista de meses con casillas: se pueden marcar varios, o todos de una vez. Se ve como un campo mas."""

    def __init__(self, master, app, ancho=188):
        self.var_txt = tk.StringVar(value=app.resumen_meses())
        super().__init__(master, app, self.var_txt, ancho=ancho, valores=[], solo_lectura=True)
        self.pop = None

    def refrescar_texto(self):
        self.var_txt.set(self.app.resumen_meses())

    def _abrir_menu(self):
        if self.pop is not None:
            return self._cerrar()
        app = self.app
        p = self.pop = tk.Toplevel(self)
        p.overrideredirect(True)
        p.configure(bg=BORDE)
        cuerpo = tk.Frame(p, bg=CARD)
        cuerpo.pack(padx=1, pady=1)
        tk.Label(cuerpo, text="Meses de " + app.var_anio.get(), bg=CARD, fg=MUTED, font=F["peq_b"]).grid(
            row=0, column=0, columnspan=2, sticky="w", padx=E(14), pady=(E(10), E(2)))
        self.v_todos = tk.BooleanVar(value=len(app.meses_sel) == 12)
        self.v_mes = [tk.BooleanVar(value=i in app.meses_sel) for i in range(12)]
        ck = _check(cuerpo, "Todos los meses", self.v_todos, bg=CARD)
        ck.configure(font=F["bold"], command=self._todos)
        ck.grid(row=1, column=0, columnspan=2, sticky="we", padx=E(10), pady=(0, E(4)))
        for i, nombre in enumerate(MESES):
            c = _check(cuerpo, nombre, self.v_mes[i], bg=CARD)
            c.configure(command=self._cambio, width=11)
            c.grid(row=2 + i % 6, column=i // 6, sticky="we", padx=(E(10), E(4)), pady=E(1))
        fila = tk.Frame(cuerpo, bg=CARD)
        fila.grid(row=8, column=0, columnspan=2, sticky="we", padx=E(12), pady=(E(8), E(10)))
        Boton(fila, app, "Solo el mes actual", self._hoy, "suave", bg=CARD, alto=30).pack(side="left")
        Boton(fila, app, "Listo", self._cerrar, "primario", bg=CARD, alto=30).pack(side="right")
        p.update_idletasks()
        p.geometry("+{}+{}".format(self.winfo_rootx(), self.winfo_rooty() + self._alto + E(4)))
        p.bind("<Escape>", lambda e: self._cerrar())
        p.bind("<Button-1>", self._fuera)
        try:
            p.grab_set()
            p.focus_force()
        except tk.TclError:
            pass

    def _fuera(self, e):
        p = self.pop
        if p is not None and not (0 <= e.x_root - p.winfo_rootx() <= p.winfo_width()
                                  and 0 <= e.y_root - p.winfo_rooty() <= p.winfo_height()):
            self._cerrar()

    def _cerrar(self):
        p, self.pop = self.pop, None
        if p is not None:
            try:
                p.grab_release()
            except tk.TclError:
                pass
            p.destroy()

    def _todos(self):
        marcar = self.v_todos.get()
        for i, v in enumerate(self.v_mes):
            v.set(marcar or i == self._primario())
        self._cambio()

    def _primario(self):
        return MESES.index(self.app.var_mes.get())

    def _hoy(self):
        hoy = date.today()
        self.app.var_anio.set(str(hoy.year))
        for i, v in enumerate(self.v_mes):
            v.set(i == hoy.month - 1)
        self._cambio()

    def _cambio(self):
        sel = {i for i, v in enumerate(self.v_mes) if v.get()}
        if not sel:                                  # siempre debe quedar al menos un mes
            sel = {self._primario()}
            self.v_mes[self._primario()].set(True)
        self.v_todos.set(len(sel) == 12)
        self.app.poner_meses(sel)
        self.refrescar_texto()


class KpiTile(Tarjeta):
    def __init__(self, master, app):
        super().__init__(master, radio=12, pad=14)
        self.app, self.num = app, 0.0
        self.t = tk.Label(self.interior, bg=CARD, fg=MUTED, font=F["peq"], anchor="w")
        self.t.pack(fill="x")
        self.v = tk.Label(self.interior, bg=CARD, fg=INK, font=F["kpi"], anchor="w")
        self.v.pack(fill="x", pady=(E(2), 0))
        self.s = tk.Label(self.interior, bg=CARD, fg=MUTED, font=F["peq"], anchor="w")
        self.s.pack(fill="x")

    def set(self, titulo, valor, sub="", color=None, sub_color=None):
        """valor = numero (se anima como contador) o texto."""
        color, sub_color = color or INK, sub_color or MUTED
        self.t.config(text=titulo)
        self.s.config(text=sub, fg=sub_color)
        if isinstance(valor, (int, float)):
            desde = self.num
            self.v.config(fg=color)
            if self.winfo_viewable():
                self.app.motor.correr(("kpi", id(self)), 420, lambda p: self.v.config(text=fm0(lerp(desde, valor, p))))
            else:
                self.v.config(text=fm0(valor))
            self.num = float(valor)
        else:
            self.v.config(text=valor, fg=color)


class Off:
    """Proxy de canvas: desplaza (y escala, solo el exterior) todo lo que se dibuja. Las graficas se piensan en
    unidades de 96 dpi; el proxy exterior las multiplica por ESC para que se vean igual en cualquier pantalla."""

    def __init__(self, cv, dx, dy, s=1.0):
        self.cv, self.dx, self.dy, self.s = cv, dx, dy, s

    def _p(self, c):
        return [v * self.s + (self.dx if i % 2 == 0 else self.dy) for i, v in enumerate(c)]

    def _k(self, k):
        if self.s != 1.0:
            if "width" in k:
                k["width"] = k["width"] * self.s
            if "dash" in k:
                k["dash"] = tuple(max(1, int(round(d * self.s))) for d in k["dash"])
        return k

    def delete(self, *a):
        pass

    def create_oval(self, *c, **k):
        return self.cv.create_oval(*self._p(c), **self._k(k))

    def create_rectangle(self, *c, **k):
        return self.cv.create_rectangle(*self._p(c), **self._k(k))

    def create_line(self, *c, **k):
        return self.cv.create_line(*self._p(c), **self._k(k))

    def create_text(self, x, y, **k):
        return self.cv.create_text(x * self.s + self.dx, y * self.s + self.dy, **k)

    def create_polygon(self, pts, **k):
        return self.cv.create_polygon(self._p(pts), **self._k(k))


class TarjetaGrafica(tk.Canvas):
    """Tarjeta redondeada que es UN solo canvas: dibuja su fondo y la grafica, y anima entre un estado y otro."""
    PAD = 16

    def __init__(self, master, app, alto, radio=14):
        super().__init__(master, height=E(alto), bg=_bg_de(master), highlightthickness=0, bd=0)
        self.app, self.alto, self.radio, self.vis, self.d = app, E(alto), E(radio), None, None
        self.bind("<Configure>", lambda e: self.dibujar())
        TEMA.registrar(self)

    def animar(self, hasta, ms=430):
        """hasta: dict de numeros / listas; interpola desde el estado visible actual."""
        desde = self.vis if self.vis is not None else self.cero(hasta)
        if not self.winfo_viewable():
            self.vis = hasta
            self.dibujar()
            return

        def paso(p):
            self.vis = self.mezcla(desde, hasta, p)
            self.dibujar()
        self.app.motor.correr(("g", id(self)), ms, paso)

    def cero(self, hasta):
        return hasta

    def mezcla(self, a, b, p):
        return b

    def retema(self):
        self.configure(bg=_bg_de(self.master))
        self.dibujar()

    def dibujar(self):
        w, h = self.winfo_width(), max(self.winfo_height(), self.alto)
        if w < 60:
            return
        self.delete("all")
        rrect(self, 1, 1, w - 2, h - 2, self.radio, fill=CARD, outline=BORDE, width=1)
        if self.d is None or self.vis is None:
            return
        try:
            m = E(self.PAD)
            self.pintar(Off(self, m, m, ESC), (w - 2 * m) / ESC, (h - 2 * m) / ESC)
        except Exception:
            traceback.print_exc()

    def pintar(self, cv, w, h):
        pass


class _AnimaK:
    def cero(self, h):
        return {"k": 0.0}

    def mezcla(self, a, b, p):
        return {"k": p}


def _colores_de(ci):
    return GRIS if ci is None else PALETA[ci % len(PALETA)]


class TarjetaVendedor(TarjetaGrafica):
    def __init__(self, master, app):
        super().__init__(master, app, 352)

    def cero(self, h):
        return {"neto": 0.0, "proy": 0.0, "sem": [(0.0, 0.0)] * len(h["sem"])}

    def mezcla(self, a, b, p):
        sa = a["sem"] if len(a["sem"]) == len(b["sem"]) else [(0.0, 0.0)] * len(b["sem"])
        return {"neto": lerp(a["neto"], b["neto"], p), "proy": lerp(a["proy"], b["proy"], p),
                "sem": [(lerp(x0, x1, p), lerp(y0, y1, p)) for (x0, y0), (x1, y1) in zip(sa, b["sem"])]}

    def actualizar(self, nombre, ci, c, semanas, destacada, meta_sem, esp=None, etq=None):
        self.d = {"nombre": nombre, "ci": ci, "meta": c["meta"], "destacada": destacada, "meta_sem": meta_sem,
                  "esp": esp if c["meta"] > 0 else None, "esp_monto": c.get("esp_monto", 0.0),
                  "meta_mes": c.get("meta_mes", c["meta"]), "tipo": self.app.grafica("panel"),
                  "arrastre": c.get("arrastre", 0.0), "etq": etq}
        self.animar({"neto": c["neto"], "proy": c["proy"], "sem": [(n, p) for n, p in semanas]})

    def pintar(self, cv, w, h):
        self.d["colores"] = _colores_de(self.d["ci"])
        dibujar_vendedor(cv, w, h, self.d, self.vis)


class TarjetaRitmo(TarjetaGrafica):
    """Resumen del equipo: porcentaje estimado (ritmo), real y faltante / de mas, con barra y marca del ritmo."""

    def __init__(self, master, app):
        super().__init__(master, app, 150)

    def cero(self, h):
        return {"neto": 0.0}

    def mezcla(self, a, b, p):
        return {"neto": lerp(a["neto"], b["neto"], p)}

    def actualizar(self, titulo, meta, neto, esp, esp_monto):
        self.d = {"titulo": titulo, "meta": meta, "esp": esp, "esp_monto": esp_monto}
        self.animar({"neto": neto})

    def pintar(self, cv, w, h):
        d = self.d
        cv.create_text(0, 9, text=d["titulo"], anchor="w", font=F["h2"], fill=INK)
        if d["meta"] <= 0 or d["esp"] is None:
            cv.create_text(w, 9, text="Define la meta para ver el ritmo", anchor="e", font=F["peq"], fill=MUTED)
            return
        bloque_ritmo(cv, w, 30, d["esp"], self.vis["neto"], d["esp_monto"], d["meta"], grande=True)


class TarjetaNecesaria(TarjetaGrafica):
    def __init__(self, master, app):
        super().__init__(master, app, 150)

    def actualizar(self, filas, equipo):
        self.d = {"filas": filas, "equipo": dict(equipo, nombre="Equipo")}
        self.alto = E(max(150, 100 + 24 * (len(filas) + 1)))
        self.configure(height=self.alto)
        self.vis = {"k": 1.0}
        self.dibujar()

    def pintar(self, cv, w, h):
        dibujar_necesaria(cv, w, self.d["filas"], self.d["equipo"])


class TarjetaEmbudo(_AnimaK, TarjetaGrafica):
    def __init__(self, master, app):
        super().__init__(master, app, 280)

    def actualizar(self, titulo, ci, e):
        self.d = {"titulo": titulo, "ci": ci, "e": e}
        self.animar({"k": 1.0}, 520)

    def pintar(self, cv, w, h):
        e = self.d["e"]
        cv.create_oval(0, 4, 10, 14, fill=_colores_de(self.d["ci"])[1], outline="")
        cv.create_text(18, 9, text=ajustar(self.d["titulo"], F["h2"], w - 20), anchor="w", font=F["h2"], fill=INK)
        dibujar_embudo(Off(cv, 0, 30), w, h - 30, [("Ingresadas", e["ingresadas"]), ("En juego (activas + exitosas)", e["en_juego"]),
                                                   ("Exitosas", e["exitosas"])], e["perdidas"],
                       self.app.var_medida.get() == MEDIDAS[0], self.vis["k"], self.app.grafica("embudo"))


class TarjetaRanking(_AnimaK, TarjetaGrafica):
    def __init__(self, master, app, pag):
        super().__init__(master, app, 470)
        self.pag = pag

    def pintar(self, cv, w, h):
        cv.create_text(0, 9, text="Ranking de campañas", anchor="w", font=F["h2"], fill=INK)
        dibujar_ranking(Off(cv, 0, 28), w, self.pag.rank, self.pag.total, self.vis["k"], self.app.grafica("rank"), h - 28)


class TarjetaDona(_AnimaK, TarjetaGrafica):
    def __init__(self, master, app, pag):
        super().__init__(master, app, 470)
        self.pag = pag

    def pintar(self, cv, w, h):
        cv.create_text(0, 9, text="Participación", anchor="w", font=F["h2"], fill=INK)
        dibujar_dona(Off(cv, 0, 28), w, h - 28, self.pag.rank, self.pag.total, self.vis["k"], self.app.grafica("dona"))


# ============================================================ secciones
class PaginaPanel(Pagina):
    def __init__(self, master, app):
        super().__init__(master, app)
        self.sub, der = self.encabezado("Panel principal")
        self.ft = FiltroTiempo(der, app)
        self.ft.pack(side="left", padx=(0, E(14)))
        Boton(der, app, "Guardar reporte", app.guardar_reporte_actual, "primario").pack(side="left", padx=E(3))
        Boton(der, app, "Descargar PDF", app.descargar_pdf, "suave").pack(side="left", padx=E(3))

        self.kpis = tk.Frame(self, bg=BG)
        self.kpis.pack(fill="x", padx=E(20), pady=(E(4), E(2)))
        self.k = []
        for i in range(5):
            self.kpis.columnconfigure(i, weight=1, uniform="k")
            t = KpiTile(self.kpis, app)
            t.grid(row=0, column=i, sticky="nsew", padx=E(6))
            self.k.append(t)
        fila2 = tk.Frame(self, bg=BG)
        fila2.pack(fill="x", padx=E(20), pady=(E(8), E(2)))
        fila2.columnconfigure(0, weight=5, uniform="r")
        fila2.columnconfigure(1, weight=6, uniform="r")
        self.ritmo = TarjetaRitmo(fila2, app)
        self.ritmo.grid(row=0, column=0, sticky="nsew", padx=E(6))
        self.necesaria = TarjetaNecesaria(fila2, app)
        self.necesaria.grid(row=0, column=1, sticky="nsew", padx=E(6))
        self.scroll = ScrollFrame(self)
        self.scroll.pack(fill="both", expand=True, padx=E(14), pady=(E(2), E(10)))
        self.cards, self.orden = {}, None

    def _reconstruir(self, vids):
        self.scroll.vaciar()
        self.cards = {}
        self.orden = tuple(vids)
        if not vids:
            tk.Label(self.scroll.inner, bg=BG, fg=MUTED, font=F["base"], pady=E(40),
                     text="Aún no hay vendedores. Agrégalos en «Vendedores y metas».").pack()
            return
        cols = columnas_para(len(vids))
        for i in range(4):
            self.scroll.inner.columnconfigure(i, weight=1 if i < cols else 0, uniform="c" if i < cols else "")
        for i, vid in enumerate(vids):
            c = TarjetaVendedor(self.scroll.inner, self.app)
            c.grid(row=i // cols, column=i % cols, sticky="nsew", padx=E(6), pady=E(6))
            self.cards[vid] = c

    def al_mostrar(self):
        for c in list(self.cards.values()) + [self.ritmo]:
            c.vis = None            # el anillo vuelve a "llenarse" al entrar
        self.k_reset()
        self.refrescar()

    def k_reset(self):
        for t in self.k:
            t.num = 0.0

    def refrescar(self):
        a = self.app
        self.ft.sincronizar()
        modo, sem = a.var_modo.get(), a.semana_num()
        m = a.reporte(modo, sem)
        self.sub.config(text=m["titulo"])
        if tuple(a.vend_ids()) != self.orden:
            self._reconstruir(a.vend_ids())
        e = m["equipo"]
        top = m["campanas"][0] if m["campanas"] and m["campanas"][0]["neto"] > 0 else None
        arr = e.get("arrastre", 0.0)
        sub_meta = "de los meses elegidos" if m.get("multi") else "mensual" if modo == "Mes" else "semanal"
        if abs(arr) >= 0.5:
            sub_meta += " · {}{} de semanas anteriores".format("+" if arr > 0 else "−", fm0(abs(arr)))
        self.k[0].set("Meta del equipo", e["meta"] if e["meta"] > 0 else "Sin meta", sub_meta)
        self.k[1].set("Recibido", e["neto"], (pct0(e["neto"], e["meta"]) + " de la meta") if e["meta"] > 0 else "", AZUL)
        self.k[2].set("Proyectado", e["proy"], "{} activas".format(e["n_proy"]))
        if e["meta"] <= 0:
            self.k[3].set("Falta", "—", "")
        elif e["falta_neto"] > 0:
            self.k[3].set("Falta", e["falta_neto"], "para la meta", CORINTO)
        else:
            self.k[3].set("Superó por", -e["falta_neto"], "la meta", AZUL_MED)
        self.k[4].set("Campaña líder", ajustar(top["campana"], F["kpi"], 150) if top else "—",
                      "{} · {} ventas".format(fm0(top["neto"]), top["n_neto"]) if top else "sin ventas", CORINTO if top else MUTED)
        self.ritmo.actualizar("Ritmo del equipo", e["meta"], e["neto"], m["esp"], e["esp_monto"])
        self.necesaria.actualizar(m["filas"], e)
        for f in m["filas"]:
            card = self.cards.get(f["id"])
            if card:
                semanas = [(s["filas"][f["id"]]["neto"], s["filas"][f["id"]]["proy"]) for s in m["semanas"]]
                card.actualizar(f["nombre"], f["ci"], f, semanas, m["semana"], f["meta_sem"], m["esp"],
                                [x["etq"] for x in m["semanas"]] if m.get("multi") else None)


def columnas_para(n):
    if n <= 3:
        return max(n, 1)
    return 2 if n == 4 else 3


class PaginaCampanas(Pagina):
    def __init__(self, master, app):
        super().__init__(master, app)
        self.sub, der = self.encabezado("Campañas")
        self.ft = FiltroTiempo(der, app)
        self.ft.pack(side="left", padx=(0, E(14)))
        tk.Label(der, text="Vendedor", bg=BG, fg=MUTED, font=F["base"]).pack(side="left", padx=(0, E(8)))
        self.var_v = tk.StringVar(value=TODOS)
        self.cb = Campo(der, app, self.var_v, ancho=170, valores=[TODOS], solo_lectura=True, bg=BG)
        self.cb.pack(side="left")
        self.cb.bind("<<ComboboxSelected>>", lambda e: self.refrescar())

        self.lider = Tarjeta(self, radio=14, pad=16, rol="CORINTO_PALIDO", borde="CORINTO_PALIDO")
        self.lider.pack(fill="x", padx=E(24), pady=(E(6), E(8)))
        fila = tk.Frame(self.lider.interior, bg=CORINTO_PALIDO)
        fila.pack(fill="x")
        izq = tk.Frame(fila, bg=CORINTO_PALIDO)
        izq.pack(side="left")
        tk.Label(izq, text="Campaña más solicitada", bg=CORINTO_PALIDO, fg=CORINTO, font=F["peq_b"]).pack(anchor="w")
        self.l_nom = tk.Label(izq, bg=CORINTO_PALIDO, fg=CORINTO, font=F["titulo"], anchor="w")
        self.l_nom.pack(anchor="w")
        der2 = tk.Frame(fila, bg=CORINTO_PALIDO)
        der2.pack(side="right")
        self.l_val = tk.Label(der2, bg=CORINTO_PALIDO, fg=CORINTO, font=F["kpi"], anchor="e")
        self.l_val.pack(anchor="e")
        self.l_det = tk.Label(der2, bg=CORINTO_PALIDO, fg=MUTED, font=F["peq"], anchor="e")
        self.l_det.pack(anchor="e")

        cuerpo = tk.Frame(self, bg=BG)
        cuerpo.pack(fill="both", expand=True, padx=E(18), pady=(0, E(14)))
        cuerpo.columnconfigure(0, weight=3)
        cuerpo.columnconfigure(1, weight=1, minsize=E(270))
        cuerpo.rowconfigure(0, weight=1)
        self.rank = []
        self.total = 0.0
        self.t_rank = TarjetaRanking(cuerpo, app, self)
        self.t_rank.grid(row=0, column=0, sticky="nsew", padx=E(6))
        self.t_dona = TarjetaDona(cuerpo, app, self)
        self.t_dona.grid(row=0, column=1, sticky="nsew", padx=E(6))
        self.t_rank.d = self.t_dona.d = {}

    def al_mostrar(self):
        self.t_rank.vis = self.t_dona.vis = None
        self.refrescar()

    def refrescar(self):
        a = self.app
        self.ft.sincronizar()
        nombres = [TODOS] + a.nombres_lista()
        self.cb["values"] = nombres
        if self.var_v.get() not in nombres:
            self.var_v.set(TODOS)
        modo, sem = a.var_modo.get(), a.semana_num()
        regs = a.registros_filtrados(modo, sem)
        if self.var_v.get() != TODOS:
            vid = a.id_por_nombre(self.var_v.get())
            regs = [r for r in regs if r["vend"] == vid]
        self.rank = ranking_campanas(regs)
        self.total = sum(e["neto"] for e in self.rank)
        cuando = a.etiqueta_periodo() + (" · Semana {}".format(sem) if modo == "Semana" else " · Meses combinados" if a.es_multi else " · Mes completo")
        self.sub.config(text=cuando + ("" if self.var_v.get() == TODOS else " · " + self.var_v.get()))
        top = campana_mas_solicitada(self.rank)
        if top is None:
            self.l_nom.config(text="—")
            self.l_val.config(text="")
            self.l_det.config(text="sin proyecciones en esta vista")
        else:
            self.l_nom.config(text=ajustar(top["campana"], F["titulo"], 520))
            self.l_val.config(text=fm0(top["neto"]))
            self.l_det.config(text="recaudado en {} leads · {} ventas".format(top["leads"], top["n_neto"]))
        self.t_rank.animar({"k": 1.0}, 520)
        self.t_dona.animar({"k": 1.0}, 620)


class PaginaEmbudos(Pagina):
    def __init__(self, master, app):
        super().__init__(master, app)
        self.sub, der = self.encabezado("Embudos")
        self.ft = FiltroTiempo(der, app)
        self.ft.pack(side="left", padx=(0, E(14)))
        tk.Label(der, text="Medir por", bg=BG, fg=MUTED, font=F["base"]).pack(side="left", padx=(0, E(8)))
        cm = Campo(der, app, app.var_medida, ancho=130, valores=MEDIDAS, solo_lectura=True, bg=BG)
        cm.pack(side="left")
        cm.bind("<<ComboboxSelected>>", lambda e: app.notificar(guardar=False))
        self.scroll = ScrollFrame(self)
        self.scroll.pack(fill="both", expand=True, padx=E(12), pady=(E(6), E(10)))
        self.cards, self.orden = {}, None

    def al_mostrar(self):
        for c in self.cards.values():
            c.vis = None
        self.refrescar()

    def refrescar(self):
        a = self.app
        self.ft.sincronizar()
        modo, sem = a.var_modo.get(), a.semana_num()
        self.sub.config(text=a.etiqueta_periodo() + (" · Semana {}".format(sem) if modo == "Semana" else " · Meses combinados" if a.es_multi else " · Mes completo"))
        vids = ["TOTAL"] + a.vend_ids()
        if tuple(vids) != self.orden:
            self.scroll.vaciar()
            self.orden = tuple(vids)
            self.cards = {}
            for i in range(4):
                self.scroll.inner.columnconfigure(i, weight=1 if i < 2 else 0, uniform="c" if i < 2 else "")
            for i, vid in enumerate(vids):
                c = TarjetaEmbudo(self.scroll.inner, a)
                c.grid(row=i // 2, column=i % 2, sticky="nsew", padx=E(6), pady=E(6))
                self.cards[vid] = c
        regs = a.registros_filtrados(modo, sem)
        for vid, card in self.cards.items():
            vr = regs if vid == "TOTAL" else [r for r in regs if r["vend"] == vid]
            nombre = "Equipo (todos)" if vid == "TOTAL" else a.nombre(vid)
            ci = None if vid == "TOTAL" else next(v.get("ci", 0) for v in a.datos["vendedores"] if v["id"] == vid)
            card.actualizar(nombre, ci, calcular_embudo(vr))


class DialogoVendedor(tk.Toplevel):
    """Agregar o editar un vendedor y su meta (mensual y semanal) desde el periodo actual."""

    def __init__(self, app, vid=None):
        super().__init__(app)
        self.app, self.vid = app, vid
        self.title("Editar vendedor" if vid else "Agregar vendedor")
        self.configure(bg=BG)
        self.transient(app)
        self.resizable(False, False)
        m = meta_vigente(app.datos, app.clave(), vid) if vid else {"mes": 0.0, "sem": None}
        self.var_nom = tk.StringVar(value=app.nombre(vid) if vid else "")
        self.var_mes = tk.StringVar(value="{:.2f}".format(m["mes"]) if m["mes"] else "")
        self.var_sem = tk.StringVar(value="{:.2f}".format(m["sem"]) if m["sem"] else "")
        cuerpo = tk.Frame(self, bg=BG)
        cuerpo.pack(padx=E(24), pady=E(20))
        tk.Label(cuerpo, text="Editar vendedor" if vid else "Agregar vendedor", bg=BG, fg=AZUL, font=F["titulo"]).grid(
            row=0, column=0, sticky="w", pady=(0, E(10)))
        for i, (t, v) in enumerate((("Nombre del vendedor", self.var_nom), ("Meta mensual ($)", self.var_mes),
                                    ("Meta semanal ($)  ·  vacío = mensual ÷ 4", self.var_sem))):
            tk.Label(cuerpo, text=t, bg=BG, fg=MUTED, font=F["peq"]).grid(row=1 + i * 2, column=0, sticky="w", pady=(E(8), E(2)))
            c = Campo(cuerpo, app, v, ancho=330, bg=BG)
            c.grid(row=2 + i * 2, column=0, sticky="ew")
            c.bind("<Return>", lambda ev: self.guardar())
            if i == 0:
                c.focus_set()
        tk.Label(cuerpo, text="La meta vale desde {} en adelante.".format(nombre_periodo(app.clave())), bg=BG, fg=MUTED,
                 font=F["peq"]).grid(row=7, column=0, sticky="w", pady=(E(10), 0))
        bt = tk.Frame(cuerpo, bg=BG)
        bt.grid(row=8, column=0, sticky="e", pady=(E(16), 0))
        Boton(bt, app, "Cancelar", self.destroy, "suave", bg=BG).pack(side="left", padx=E(4))
        Boton(bt, app, "Guardar", self.guardar, "primario", bg=BG).pack(side="left")
        self.grab_set()

    def guardar(self):
        a = self.app
        nombre = canon_vendedor(self.var_nom.get())
        if not nombre:
            return messagebox.showwarning(APP_NAME, "Escribe el nombre del vendedor.", parent=self)
        if any(norm(v["nombre"]) == norm(nombre) and v["id"] != self.vid for v in a.datos["vendedores"]):
            return messagebox.showwarning(APP_NAME, "Ya existe un vendedor con ese nombre.", parent=self)
        try:
            mes = parse_monto(self.var_mes.get()) if self.var_mes.get().strip() else 0.0
            sem = parse_monto(self.var_sem.get()) if self.var_sem.get().strip() else None
        except ValueError:
            return messagebox.showwarning(APP_NAME, "Las metas deben ser números (ejemplo: 20000).", parent=self)
        vid = self.vid
        if vid:
            for v in a.datos["vendedores"]:
                if v["id"] == vid:
                    v["nombre"] = nombre
        else:
            vid = "V" + uuid.uuid4().hex[:6]
            a.datos["vendedores"].append({"id": vid, "nombre": nombre, "ci": siguiente_color(a.datos)})
        a.datos["metas"].setdefault(a.clave(), {})[vid] = {"mes": mes, "sem": sem}
        self.destroy()
        a.notificar()


def tabla_en_tarjeta(master, app, cols, **kw):
    """Treeview dentro de una tarjeta redondeada. cols = [(id, titulo, ancho, ancla)]."""
    box = Tarjeta(master, radio=14, pad=10)
    tree = ttk.Treeview(box.interior, columns=[c[0] for c in cols], show="headings", **kw)
    for cid, t, w, an in cols:
        tree.heading(cid, text=t, anchor=an)
        tree.column(cid, width=E(w), anchor=an)
    app.configurar_tags(tree)
    tree.pack(fill="both", expand=True)
    return box, tree


class PaginaAjustes(Pagina):
    """Vendedores y sus metas."""

    def __init__(self, master, app):
        super().__init__(master, app)
        self.sub, der = self.encabezado("Vendedores y metas")
        Boton(der, app, "Agregar vendedor", self.agregar, "primario").pack(side="left", padx=E(3))
        Boton(der, app, "Editar", self.editar, "suave").pack(side="left", padx=E(3))
        Boton(der, app, "Eliminar", self.eliminar, "suave_rojo").pack(side="left", padx=E(3))
        Boton(der, app, "Deshacer eliminación", app.deshacer_eliminacion, "suave").pack(side="left", padx=(E(12), 0))
        box, self.tree = tabla_en_tarjeta(self, app, [
            ("vend", "Vendedor", 220, "w"), ("mes", "Meta mensual", 140, "e"), ("sem", "Meta semanal", 160, "e"),
            ("n", "Proyecciones", 130, "center")], selectmode="browse", height=8)
        box.pack(fill="both", expand=True, padx=E(24), pady=(E(8), E(8)))
        self.tree.bind("<Double-1>", lambda e: self.editar())
        tk.Label(self, justify="left", bg=BG, fg=MUTED, font=F["peq"], text=(
            "Doble clic para editar. La meta vale desde el periodo elegido y se hereda a los siguientes.")).pack(
            anchor="w", padx=E(26), pady=(0, E(12)))

    def refrescar(self):
        a = self.app
        self.sub.config(text="Metas de " + nombre_periodo(a.clave()))
        a.configurar_tags(self.tree)
        self.tree.delete(*self.tree.get_children())
        for v in a.datos["vendedores"]:
            m = meta_vigente(a.datos, a.clave(), v["id"])
            n = sum(1 for regs in a.datos["periodos"].values() for r in regs if r["vend"] == v["id"])
            self.tree.insert("", "end", iid=v["id"], values=(
                v["nombre"], fm(m["mes"]), fm(m["sem"]) if m["sem"] else "auto ({})".format(fm(m["mes"] / 4.0)), n))
        a.zebra(self.tree)
        vs = a.datos["vendedores"]
        if vs:
            ms = [meta_vigente(a.datos, a.clave(), v["id"]) for v in vs]
            self.tree.insert("", "end", iid="__total__", tags=("total",), values=(
                "TOTAL", fm(sum(m["mes"] for m in ms)), fm(sum(m["sem"] or m["mes"] / 4.0 for m in ms)),
                sum(1 for regs in a.datos["periodos"].values() for r in regs)))

    def _sel(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo(APP_NAME, "Selecciona un vendedor de la lista.", parent=self.app)
            return None
        if sel[0] == "__total__":
            messagebox.showinfo(APP_NAME, "Esa fila es el total. Selecciona un vendedor.", parent=self.app)
            return None
        return sel[0]

    def agregar(self):
        DialogoVendedor(self.app)

    def editar(self):
        vid = self._sel()
        if vid:
            DialogoVendedor(self.app, vid)

    def eliminar(self):
        vid = self._sel()
        if not vid:
            return
        a = self.app
        n = sum(1 for regs in a.datos["periodos"].values() for r in regs if r["vend"] == vid)
        if messagebox.askyesno(APP_NAME, "¿Eliminar a {}?\n\nTambién se eliminarán sus {} proyección(es) y sus metas.\n"
                                         "(Podrás deshacerlo.)".format(a.nombre(vid), n), parent=a):
            a.eliminar_vendedor(vid)


class PaginaConfig(Pagina):
    """⚙ Configuración: conexión con Bitrix24, tipo de gráficas y manejo de los datos."""

    def __init__(self, master, app):
        super().__init__(master, app)
        self.sub, _ = self.encabezado("Configuración")
        self.sub.config(text="Conexión, gráficas y datos")
        sf = ScrollFrame(self)
        sf.pack(fill="both", expand=True, padx=E(12), pady=(0, E(10)))
        i = sf.inner

        def seccion(titulo, ayuda):
            t = Tarjeta(i, radio=14, pad=16)
            t.pack(fill="x", padx=E(12), pady=(E(4), E(8)))
            tk.Label(t.interior, text=titulo, bg=CARD, fg=AZUL, font=F["h2"]).pack(anchor="w")
            tk.Label(t.interior, text=ayuda, bg=CARD, fg=MUTED, font=F["peq"], justify="left", anchor="w").pack(anchor="w", pady=(0, E(8)))
            return t.interior

        # --- Bitrix24
        ci = seccion("Conexión con Bitrix24", "Con el webhook, al pegar un lead se llenan solos el monto, la campaña y el vendedor.")
        self.var_hook = tk.StringVar(value=app.datos["config"].get("bitrix_webhook", ""))
        self.var_campo = tk.StringVar(value=app.datos["config"].get("campo_campana", "auto"))
        tk.Label(ci, text="Webhook de entrada", bg=CARD, fg=MUTED, font=F["peq"]).pack(anchor="w")
        Campo(ci, app, self.var_hook, ancho=560, placeholder="https://tuempresa.bitrix24.es/rest/1/clave/").pack(anchor="w", pady=(E(2), E(8)))
        tk.Label(ci, text="Campo de Bitrix24 con la campaña", bg=CARD, fg=MUTED, font=F["peq"]).pack(anchor="w")
        Campo(ci, app, self.var_campo, ancho=250).pack(anchor="w", pady=(E(2), E(2)))
        tk.Label(ci, text="Déjalo en «auto» para usar el campo «Campaña». Si no la encuentra, usa «Probar con un lead».",
                 bg=CARD, fg=MUTED, font=F["mini"]).pack(anchor="w", pady=(0, E(8)))
        bc = tk.Frame(ci, bg=CARD)
        bc.pack(anchor="w")
        Boton(bc, app, "Guardar", self.guardar_conexion, "primario", bg=CARD).pack(side="left", padx=(0, E(6)))
        Boton(bc, app, "Probar con un lead", self.probar_conexion, "suave", bg=CARD).pack(side="left")

        # --- graficas
        gi = seccion("Gráficas", "Elige cómo se dibuja cada sección.")
        gi.columnconfigure(0, weight=1)
        rejilla = tk.Frame(gi, bg=CARD)
        rejilla.pack(fill="x")
        rejilla.columnconfigure(0, weight=1)
        self.var_graf = {}
        for n, (area, titulo) in enumerate(GRAFICA_AREAS):
            tk.Label(rejilla, text=titulo, bg=CARD, fg=INK, font=F["base"]).grid(row=n, column=0, sticky="w", pady=E(3))
            var = tk.StringVar()
            self.var_graf[area] = var
            cb = Campo(rejilla, app, var, ancho=330, valores=[l for _, l in GRAFICAS[area]], solo_lectura=True)
            cb.grid(row=n, column=1, padx=(E(20), 0), pady=E(3), sticky="e")
            cb.bind("<<ComboboxSelected>>", lambda e, a=area, v=var: self.cambiar_grafica(a, v.get()))

        # --- datos
        di = seccion("Mis datos", "Todo se guarda solo en tu computadora, en esta carpeta:")
        tk.Label(di, text=app.almacen.ruta, bg=CARD, fg=INK, font=F["peq"], anchor="w").pack(anchor="w", pady=(0, E(8)))
        b1 = tk.Frame(di, bg=CARD)
        b1.pack(anchor="w")
        Boton(b1, app, "Importar datos", lambda: DialogoImportar(app), "suave", bg=CARD).pack(side="left", padx=(0, E(6)))
        Boton(b1, app, "Exportar datos", lambda: DialogoExportar(app), "suave", bg=CARD).pack(side="left", padx=(0, E(6)))
        Boton(b1, app, "Abrir carpeta de datos", self.abrir_carpeta, "suave", bg=CARD).pack(side="left")
        tk.Label(di, text="Zona de borrado (se hace una copia de seguridad antes de borrar todo)", bg=CARD, fg=MUTED,
                 font=F["peq"]).pack(anchor="w", pady=(E(14), E(6)))
        b2 = tk.Frame(di, bg=CARD)
        b2.pack(anchor="w")
        Boton(b2, app, "Vaciar este periodo", self.vaciar_periodo, "suave_rojo", bg=CARD).pack(side="left", padx=(0, E(6)))
        Boton(b2, app, "Borrar TODAS las proyecciones…", self.borrar_todo, "suave_rojo", bg=CARD).pack(side="left")

        vi = seccion("Versión", "Versión {}. Cuando se publica una nueva, el programa instalado te avisa al abrirlo.".format(VERSION_APP))
        Boton(vi, app, "Buscar actualización", lambda: app.buscar_actualizacion(True), "suave", bg=CARD).pack(anchor="w")

    def refrescar(self):
        for area, var in self.var_graf.items():
            var.set(next(l for k, l in GRAFICAS[area] if k == self.app.grafica(area)))

    def cambiar_grafica(self, area, etiqueta):
        k = next((k for k, l in GRAFICAS[area] if l == etiqueta), None)
        if k:
            self.app.datos["config"].setdefault("graficas", {})[area] = k
            self.app.notificar()

    def guardar_conexion(self):
        a = self.app
        try:
            base = bitrix_base(self.var_hook.get())
        except ValueError as e:
            return messagebox.showwarning(APP_NAME, str(e), parent=a)
        a.datos["config"]["bitrix_webhook"] = base
        a.datos["config"]["campo_campana"] = self.var_campo.get().strip() or "auto"
        self.var_hook.set(base)
        a.notificar()
        messagebox.showinfo(APP_NAME, "Conexión guardada." if base else "Conexión desactivada (webhook vacío).", parent=a)

    def probar_conexion(self):
        """Lee un lead y muestra sus campos con valor, para saber cual usar como campo de campaña."""
        from tkinter import simpledialog
        a = self.app
        try:
            cfg = {"bitrix_webhook": bitrix_base(self.var_hook.get())}
        except ValueError as e:
            return messagebox.showwarning(APP_NAME, str(e), parent=a)
        txt = simpledialog.askstring(APP_NAME, "Enlace o ID de un lead para probar:", parent=a)
        did = extraer_id(limpiar_lead(txt or ""))
        if not did:
            return
        a.config(cursor="watch")
        a.update_idletasks()
        try:
            _, deal = bitrix_negociacion(cfg, did)
            filas = ["{}: {}".format(k, recortar(str(v), 50)) for k, v in deal.items() if v not in (None, "", "0", 0, [], {}, "N", "0.00")]
            messagebox.showinfo(APP_NAME, "Conexión correcta. Campos con valor en el lead {}:\n\n{}\n\nEscribe en «Campo de la campaña» "
                                          "el nombre del que trae la campaña.".format(did, "\n".join(filas[:30])), parent=a)
        except Exception as e:
            messagebox.showerror(APP_NAME, "No se pudo leer el lead:\n{}".format(e), parent=a)
        finally:
            a.config(cursor="")

    def abrir_carpeta(self):
        carpeta = os.path.dirname(self.app.almacen.ruta)
        os.makedirs(carpeta, exist_ok=True)
        try:
            if hasattr(os, "startfile"):
                os.startfile(carpeta)
            else:
                webbrowser.open("file://" + carpeta)
        except Exception as e:
            messagebox.showinfo(APP_NAME, "La carpeta es:\n{}\n({})".format(carpeta, e), parent=self.app)

    def borrar_todo(self):
        """Borra todas las proyecciones de todos los periodos (conserva vendedores, metas, reportes y conexión)."""
        a = self.app
        n = sum(len(v) for v in a.datos["periodos"].values())
        if not n:
            return messagebox.showinfo(APP_NAME, "No hay proyecciones guardadas.", parent=a)
        if not messagebox.askyesno(APP_NAME, "Se borrarán las {} proyecciones de TODOS los periodos.\n\nSe conservan vendedores, metas, "
                                             "reportes guardados y la conexión con Bitrix24.\nAntes se hace una copia de seguridad en la "
                                             "carpeta «copias».\n\n¿Continuar?".format(n), icon="warning", parent=a):
            return
        a.guardar_todo()
        copia = a.almacen.copia_seguridad("antes_de_borrar")
        if copia is None and os.path.exists(a.almacen.ruta):
            return messagebox.showerror(APP_NAME, "No se pudo hacer la copia de seguridad; no se borró nada.", parent=a)
        a.datos["periodos"] = {}
        a.datos["config"].pop("borrador", None)
        a.papelera = None
        a.notificar()
        a.guardar_todo()
        messagebox.showinfo(APP_NAME, "Listo: se borraron {} proyecciones.{}".format(
            n, "\nCopia de seguridad:\n" + copia if copia else ""), parent=a)

    def vaciar_periodo(self):
        a = self.app
        n = len(a.registros)
        if not n:
            return messagebox.showinfo(APP_NAME, "Este periodo no tiene proyecciones.", parent=a)
        if messagebox.askyesno(APP_NAME, "Se eliminarán las {} proyecciones de {}.\n(Podrás deshacerlo con «Deshacer eliminación».)\n\n¿Continuar?".format(
                n, nombre_periodo(a.clave())), parent=a):
            a.eliminar_registros([r["id"] for r in a.registros])


class VentanaReporte(tk.Toplevel):
    def __init__(self, app, m):
        super().__init__(app)
        self.title("Reporte guardado — " + m["titulo"])
        self.configure(bg=BG)
        self.geometry("{}x{}".format(E(1000), E(560)))
        self.transient(app)
        tk.Label(self, text=m["titulo"], bg=BG, fg=AZUL, font=F["titulo"]).pack(anchor="w", padx=E(22), pady=(E(16), 0))
        tk.Label(self, text="Guardado el " + datetime.fromisoformat(m["creado"]).strftime("%d/%m/%Y %H:%M") +
                 " · las metas son las que estaban asignadas en ese momento", bg=BG, fg=MUTED, font=F["base"]).pack(anchor="w", padx=E(22))
        box, t = tabla_en_tarjeta(self, app, [
            ("v", "Vendedor", 150, "w"), ("mm", "Meta mensual", 105, "e"), ("ms", "Meta semanal", 105, "e"),
            ("ma", "Meta aplicada", 105, "e"), ("n", "Recibido", 100, "e"), ("p", "Proyectado", 100, "e"),
            ("pc", "% meta", 70, "e"), ("f", "Falta / Superó", 130, "e")], height=8)
        box.pack(fill="x", padx=E(22), pady=E(12))
        for f in m["filas"] + [dict(m["equipo"], nombre="Equipo", meta_mes=sum(x["meta_mes"] for x in m["filas"]),
                                    meta_sem=sum(x["meta_sem"] for x in m["filas"]))]:
            fs = ("Falta " + fm(f["falta_neto"])) if f["falta_neto"] > 0 else "Superó " + fm(-f["falta_neto"])
            t.insert("", "end", tags=("total",) if f["nombre"] == "Equipo" else (), values=(
                f["nombre"], fm(f["meta_mes"]), fm(f["meta_sem"]), fm(f["meta"]), fm(f["neto"]), fm(f["proy"]),
                pct(f["neto"], f["meta"]), fs if f["meta"] > 0 else "—"))
        app.zebra(t)
        top = m["campanas"][0] if m["campanas"] else None
        tk.Label(self, bg=BG, fg=CORINTO, font=F["bold"], text=(
            "Campaña más vendida: {}  ·  {} en {} ventas".format(top["campana"], fm(top["neto"]), top["n_neto"])
            if top and top["neto"] > 0 else "Sin ventas exitosas")).pack(anchor="w", padx=E(22))
        Boton(self, app, "Cerrar", self.destroy, "suave", bg=BG).pack(anchor="e", padx=E(22), pady=E(14))


class PaginaReportes(Pagina):
    def __init__(self, master, app):
        super().__init__(master, app)
        self.sub, der = self.encabezado("Reportes guardados")
        Boton(der, app, "Ver detalle", self.ver, "suave").pack(side="left", padx=E(3))
        Boton(der, app, "Descargar PDF", self.pdf, "primario").pack(side="left", padx=E(3))
        Boton(der, app, "Eliminar", self.eliminar, "suave_rojo").pack(side="left", padx=E(3))
        box, self.tree = tabla_en_tarjeta(self, app, [
            ("per", "Periodo", 130, "w"), ("vista", "Vista", 120, "w"), ("meta", "Meta equipo", 110, "e"),
            ("neto", "Recibido", 110, "e"), ("proy", "Proyectado", 110, "e"), ("pc", "% meta", 70, "e"),
            ("f", "Falta / Superó", 130, "e"), ("cre", "Guardado", 130, "center")], selectmode="browse")
        box.pack(fill="both", expand=True, padx=E(24), pady=(E(8), E(8)))
        self.tree.bind("<Double-1>", lambda e: self.ver())
        tk.Label(self, bg=BG, fg=MUTED, font=F["peq"], text=(
            "Cada reporte guarda la vista (semana o mes) con la meta mensual y semanal de cada vendedor en ese momento.  "
            "Se crean desde Panel principal → Guardar reporte.")).pack(anchor="w", padx=E(26), pady=(0, E(12)))

    def refrescar(self):
        a = self.app
        self.sub.config(text="{} reporte(s) guardado(s)".format(len(a.datos["reportes"])))
        self.tree.delete(*self.tree.get_children())
        for m in sorted(a.datos["reportes"], key=lambda x: x["creado"], reverse=True):
            e = m["equipo"]
            fs = "—" if e["meta"] <= 0 else (("Falta " + fm(e["falta_neto"])) if e["falta_neto"] > 0 else "Superó " + fm(-e["falta_neto"]))
            vista = "Mes completo" if m["vista"] == "Mes" else "Semana {}".format(m["semana"])
            self.tree.insert("", "end", iid=m["id"], values=(
                m["periodo"], vista, fm(e["meta"]), fm(e["neto"]), fm(e["proy"]), pct(e["neto"], e["meta"]), fs,
                datetime.fromisoformat(m["creado"]).strftime("%d/%m/%Y %H:%M")))

    def _sel(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo(APP_NAME, "Selecciona un reporte de la lista.", parent=self.app)
            return None
        return next((m for m in self.app.datos["reportes"] if m["id"] == sel[0]), None)

    def ver(self):
        m = self._sel()
        if m:
            VentanaReporte(self.app, m)

    def pdf(self):
        m = self._sel()
        if m:
            self.app.descargar_pdf(m)

    def eliminar(self):
        m = self._sel()
        if m and messagebox.askyesno(APP_NAME, "¿Eliminar el reporte «{}»?\nEsta acción no se puede deshacer.".format(m["titulo"]), parent=self.app):
            self.app.datos["reportes"] = [x for x in self.app.datos["reportes"] if x["id"] != m["id"]]
            self.app.notificar()


class Referencia(tk.Canvas):
    """Imagen de referencia: como debe verse la hoja de Excel que se va a importar."""
    ANCHO, ALTO = 660, 150

    def __init__(self, master):
        super().__init__(master, width=E(self.ANCHO), height=E(self.ALTO), bg=_bg_de(master), highlightthickness=0, bd=0)
        TEMA.registrar(self)
        self.retema()

    def retema(self):
        self.configure(bg=_bg_de(self.master))
        self.delete("all")
        o = Off(self, 0, 0, ESC)
        anchos = [86, 74, 212, 130, 70, 70]
        x0, h = 26, 28
        rrect(o, 0, 0, self.ANCHO - 1, self.ALTO - 1, 8, fill=FIELD, outline=BORDE)
        for j, (ancho, letra) in enumerate(zip(anchos, "ABCDEF")):
            x = x0 + sum(anchos[:j])
            o.create_rectangle(x, 1, x + ancho, h - 6, fill=AZUL_PALIDO, outline=BORDE)
            o.create_text(x + ancho / 2.0, h / 2.0 - 3, text=letra, font=F["peq"], fill=MUTED)
        filas = [IMP_COLUMNAS] + [[f[0], f[1], f[2], f[3], "{:,.2f}".format(f[4]), f[5]] for f in IMP_EJEMPLO]
        for i, fila in enumerate(filas):
            y = h - 6 + i * 28
            o.create_rectangle(1, y, x0, y + 28, fill=AZUL_PALIDO, outline=BORDE)
            o.create_text(x0 / 2.0, y + 14, text=str(i + 1), font=F["peq"], fill=MUTED)
            for j, (ancho, v) in enumerate(zip(anchos, fila)):
                x = x0 + sum(anchos[:j])
                o.create_rectangle(x, y, x + ancho, y + 28, fill=BTN if i == 0 else FIELD, outline=BORDE)
                o.create_text(x + 6, y + 14, text=ajustar(v, F["peq_b"] if i == 0 else F["peq"], ancho - 10), anchor="w",
                              font=F["peq_b"] if i == 0 else F["peq"], fill=BLANCO if i == 0 else INK)


class DialogoEjemplo(tk.Toplevel):
    """Imagen de referencia + instructivo de la hoja de Excel que se puede importar."""

    def __init__(self, app):
        super().__init__(app)
        self.title("Ejemplo de archivo")
        self.configure(bg=BG)
        self.transient(app)
        c = tk.Frame(self, bg=BG)
        c.pack(padx=E(24), pady=E(20))
        tk.Label(c, text="Así debe verse tu archivo", bg=BG, fg=INK, font=F["titulo"]).pack(anchor="w")
        tk.Label(c, text="Primera hoja de Excel (o una tabla CSV). Los encabezados pueden llamarse distinto: "
                         "luego eliges qué columna es cuál.", bg=BG, fg=MUTED, font=F["base"], wraplength=E(640),
                 justify="left").pack(anchor="w", pady=(E(4), E(10)))
        Referencia(c).pack(anchor="w")
        tk.Label(c, justify="left", anchor="w", bg=BG, fg=INK, font=F["peq"], text=(
            "•  Fecha como dd/mm/aaaa.   •  Enlace de Bitrix24 o solo el ID.   •  Monto como número.\n"
            "•  Estado: Activa, Perdida (o Baja) o Exitosa.   •  El asesor debe ser uno de tus vendedores.\n"
            "•  JSON: una lista de objetos con esos mismos nombres, o un archivo exportado desde esta app.")).pack(
            anchor="w", pady=(E(10), E(12)))
        Boton(c, app, "Cerrar", self.destroy, "suave").pack(anchor="e")


class DialogoImportar(tk.Toplevel):
    """Importar desde Excel, CSV o JSON: eliges el archivo, ves una vista previa y dices que columna es cual."""
    NINGUNA = "(no importar)"

    def __init__(self, app):
        super().__init__(app)
        self.app, self.filas, self.cab, self.enc, self._carga = app, None, 0, [], False
        self.title("Importar datos")
        self.configure(bg=BG)
        self.transient(app)
        an, al = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry("{}x{}".format(min(E(1060), an - 60), min(E(640), al - 100)))
        self.v_map = {k: tk.StringVar(value=self.NINGUNA) for k, _, _ in IMP_CAMPOS}
        tk.Label(self, text="Importar datos", bg=BG, fg=INK, font=F["titulo"]).pack(anchor="w", padx=E(24), pady=(E(16), 0))
        tk.Label(self, text="Excel (.xlsx), CSV o JSON. Elige el archivo, revisa la vista previa y confirma las columnas.",
                 bg=BG, fg=MUTED, font=F["base"]).pack(anchor="w", padx=E(24))
        pie = tk.Frame(self, bg=BG)
        pie.pack(side="bottom", fill="x", padx=E(24), pady=E(14))
        Boton(pie, app, "Cerrar", self.destroy, "suave").pack(side="right")
        self.btn = Boton(pie, app, "Importar", self.aplicar, "primario")
        self.btn.pack(side="right", padx=(0, E(8)))
        self.lbl = tk.Label(pie, bg=BG, fg=MUTED, font=F["peq"], text="Aún no has elegido un archivo.")
        self.lbl.pack(side="left")
        fila = tk.Frame(self, bg=BG)
        fila.pack(anchor="w", padx=E(24), pady=(E(10), E(6)))
        Boton(fila, app, "Elegir archivo…", self.elegir, "primario").pack(side="left")
        Boton(fila, app, "Descargar plantilla", self.plantilla, "suave").pack(side="left", padx=(E(8), 0))
        Boton(fila, app, "Ver ejemplo", lambda: DialogoEjemplo(app), "suave").pack(side="left", padx=(E(8), 0))
        self.lbl_arch = tk.Label(fila, bg=BG, fg=MUTED, font=F["peq"])
        self.lbl_arch.pack(side="left", padx=E(12))
        cuerpo = tk.Frame(self, bg=BG)
        cuerpo.pack(fill="both", expand=True, padx=E(18))
        cuerpo.columnconfigure(1, weight=1)
        cuerpo.rowconfigure(0, weight=1)
        izq = tk.Frame(cuerpo, bg=BG)
        izq.grid(row=0, column=0, sticky="n")
        tk.Label(izq, text="Qué columna es cuál", bg=BG, fg=MUTED, font=F["peq"]).pack(anchor="w", padx=E(6), pady=(0, E(4)))
        self.cbs = {}
        for k, nombre, req in IMP_CAMPOS:
            tk.Label(izq, text=nombre + (" *" if req else ""), bg=BG, fg=INK, font=F["peq"]).pack(anchor="w", padx=E(6), pady=(E(6), E(2)))
            cb = Campo(izq, app, self.v_map[k], ancho=250, valores=[self.NINGUNA], solo_lectura=True)
            cb.pack(anchor="w", padx=E(6))
            cb.bind("<<ComboboxSelected>>", lambda e: self.vista())
            self.cbs[k] = cb
        tk.Label(izq, text="* obligatorias", bg=BG, fg=MUTED, font=F["mini"]).pack(anchor="w", padx=E(6), pady=(E(8), 0))
        der = Tarjeta(cuerpo, radio=14, pad=12)
        der.grid(row=0, column=1, sticky="nsew", padx=(E(12), 0))
        tk.Label(der.interior, text="Vista previa de lo que se importaría", bg=CARD, fg=INK, font=F["h2"]).pack(anchor="w")
        self.txt = tk.Text(der.interior, bg=CARD, fg=INK, font=("Consolas", 9), bd=0, highlightthickness=0, wrap="none",
                           state="disabled", relief="flat", height=10, width=40)
        self.txt.pack(fill="both", expand=True, pady=(E(6), 0))
        self.grab_set()

    def plantilla(self):
        ruta = filedialog.asksaveasfilename(parent=self, defaultextension=".xlsx", filetypes=[("Excel", "*.xlsx")],
                                            initialfile="plantilla_proyecciones.xlsx")
        if not ruta:
            return
        try:
            escribir_plantilla(ruta)
        except OSError as e:
            return messagebox.showerror(APP_NAME, "No se pudo crear la plantilla:\n{}".format(e), parent=self)
        self.lbl.config(text="Plantilla guardada. Llénala y luego elige el archivo.")

    def elegir(self):
        ruta = filedialog.askopenfilename(parent=self, filetypes=[("Excel, CSV o JSON", "*.xlsx *.csv *.json"), ("Todos", "*.*")])
        if not ruta:
            return
        try:
            filas = leer_tabla(ruta)
        except Exception as e:
            return messagebox.showwarning(APP_NAME, "No pude leer el archivo ({}).".format(e), parent=self)
        if not filas:
            return messagebox.showwarning(APP_NAME, "El archivo está vacío.", parent=self)
        self.filas = filas
        self.cab, mapa = detectar_columnas(filas)
        ancho = max(len(f) for f in filas)
        base = list(filas[self.cab]) + [""] * (ancho - len(filas[self.cab]))
        self.enc, usados = [], {}
        for i, c in enumerate(base):
            nombre = str(c).strip() or "Columna {}".format(i + 1)
            usados[nombre] = usados.get(nombre, 0) + 1
            self.enc.append(nombre if usados[nombre] == 1 else "{} ({})".format(nombre, usados[nombre]))
        self.lbl_arch.config(text=os.path.basename(ruta))
        self._carga = True
        for k, cb in self.cbs.items():
            cb["values"] = [self.NINGUNA] + self.enc
            self.v_map[k].set(self.enc[mapa[k]] if k in mapa else self.NINGUNA)
        self._carga = False
        self.vista()

    def _mapa(self):
        return {k: self.enc.index(v.get()) for k, v in self.v_map.items() if v.get() in self.enc}

    def vista(self):
        if self._carga or not self.filas:
            return
        r = importar_filas(self.app.datos, self.filas, mapa=self._mapa(), cab=self.cab)
        lineas = []
        if r["vista"]:
            lineas.append(" | ".join(["Fecha", "Asesor", "ID", "Campaña", "Monto", "Estado"]))
            lineas += [" | ".join(f)[:150] for f in r["vista"]]
            if r["nuevos"] > len(r["vista"]):
                lineas.append("…")
        if r["repetidos"]:
            lineas += ["", "{} repetidas (ya registradas; se omiten).".format(len(r["repetidos"]))]
        if r["errores"]:
            lineas += ["", "{} filas con problemas (no se importan):".format(len(r["errores"]))]
            lineas += ["  Fila {}: {}".format(n, m) for n, m in r["errores"][:8]]
            if len(r["errores"]) > 8:
                lineas.append("  … y {} más".format(len(r["errores"]) - 8))
        self.txt.configure(state="normal")
        self.txt.delete("1.0", "end")
        self.txt.insert("end", "\n".join(lineas))
        self.txt.configure(state="disabled")
        porper = ", ".join("{}: {}".format(nombre_periodo(k), v) for k, v in sorted(r["periodos"].items()))
        self.lbl.config(text="{} nuevas · total {}{}".format(r["nuevos"], fm(r["total"]), " · " + porper if porper else ""))
        self.btn.poner_texto("Importar {}".format(r["nuevos"]) if r["nuevos"] else "Importar")

    def aplicar(self):
        if not self.filas:
            return messagebox.showinfo(APP_NAME, "Primero elige un archivo con «Elegir archivo…».", parent=self)
        r = importar_filas(self.app.datos, self.filas, aplicar=True, mapa=self._mapa(), cab=self.cab)
        self.app.notificar()
        messagebox.showinfo(APP_NAME, "Se importaron {} proyecciones ({}).".format(r["nuevos"], fm(r["total"])), parent=self.app)
        self.destroy()


def _check(master, texto, var, bg=None):
    return tk.Checkbutton(master, text=texto, variable=var, bg=bg or BG, fg=INK, activebackground=bg or BG,
                          activeforeground=INK, selectcolor=FIELD, font=F["base"], anchor="w", bd=0,
                          highlightthickness=0, cursor="hand2")


class DialogoExportar(tk.Toplevel):
    """Exportar a Excel, CSV o JSON: eliges periodos, estados, columnas y como se llamara cada una en el archivo."""
    FORMATOS = ["Excel (.xlsx)", "CSV (.csv)", "JSON (.json)"]

    def __init__(self, app):
        super().__init__(app)
        self.app = app
        self.title("Exportar datos")
        self.configure(bg=BG)
        self.transient(app)
        an, al = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry("{}x{}".format(min(E(1060), an - 60), min(E(690), al - 100)))
        self.alcances = ["Periodos elegidos ({})".format(app.etiqueta_periodo()), "Todos los periodos"]
        self.var_fmt = tk.StringVar(value=self.FORMATOS[0])
        self.var_alc = tk.StringVar(value=self.alcances[0])
        self.v_tipo = {t: tk.BooleanVar(value=True) for t in TIPOS_ORDEN}
        self.v_col = {c: tk.BooleanVar(value=c in EXP_DEFECTO) for c, _, _ in EXP_COLUMNAS}
        self.v_nom = {c: tk.StringVar(value=n) for c, _, n in EXP_COLUMNAS}
        self.v_ext = {k: tk.BooleanVar(value=False) for k in ("vendedores", "reportes", "completo")}
        self.PRESETS = ["Básicas (fecha, asesor, enlace, campaña, monto, estado)", "Todas las columnas", "Elegir columnas…"]
        self.var_pre = tk.StringVar(value=self.PRESETS[0])

        tk.Label(self, text="Exportar datos", bg=BG, fg=INK, font=F["titulo"]).pack(anchor="w", padx=E(24), pady=(E(16), 0))
        tk.Label(self, text="Elige formato y periodos; abajo ves cómo quedará el archivo.", bg=BG, fg=MUTED,
                 font=F["base"]).pack(anchor="w", padx=E(24))
        pie = tk.Frame(self, bg=BG)
        pie.pack(side="bottom", fill="x", padx=E(24), pady=E(14))
        Boton(pie, app, "Cerrar", self.destroy, "suave").pack(side="right")
        Boton(pie, app, "Exportar", self.exportar, "primario").pack(side="right", padx=(0, E(8)))
        self.lbl = tk.Label(pie, bg=BG, fg=MUTED, font=F["peq"])
        self.lbl.pack(side="left")
        cuerpo = tk.Frame(self, bg=BG)
        cuerpo.pack(fill="both", expand=True, padx=E(18), pady=(E(8), 0))
        cuerpo.columnconfigure(1, weight=1)
        cuerpo.rowconfigure(0, weight=1)
        sf = ScrollFrame(cuerpo)
        sf.cv.configure(width=E(470))
        sf.grid(row=0, column=0, sticky="ns")
        i = sf.inner
        tk.Label(i, text="Formato", bg=BG, fg=MUTED, font=F["peq"]).pack(anchor="w", padx=E(6), pady=(0, E(3)))
        self.cb_fmt = Campo(i, app, self.var_fmt, ancho=250, valores=self.FORMATOS, solo_lectura=True)
        self.cb_fmt.pack(anchor="w", padx=E(6))
        tk.Label(i, text="Periodos", bg=BG, fg=MUTED, font=F["peq"]).pack(anchor="w", padx=E(6), pady=(E(10), E(3)))
        self.cb_alc = Campo(i, app, self.var_alc, ancho=250, valores=self.alcances, solo_lectura=True)
        self.cb_alc.pack(anchor="w", padx=E(6))
        tk.Label(i, text="Estados", bg=BG, fg=MUTED, font=F["peq"]).pack(anchor="w", padx=E(6), pady=(E(10), 0))
        fe = tk.Frame(i, bg=BG)
        fe.pack(anchor="w")
        for t in TIPOS_ORDEN:
            _check(fe, TIPO_LABEL[t], self.v_tipo[t]).pack(side="left", padx=(E(2), E(10)))
        tk.Label(i, text="Columnas", bg=BG, fg=MUTED, font=F["peq"]).pack(anchor="w", padx=E(6), pady=(E(10), E(3)))
        self.cb_pre = Campo(i, app, self.var_pre, ancho=420, valores=self.PRESETS, solo_lectura=True)
        self.cb_pre.pack(anchor="w", padx=E(6))
        self.f_cols = tk.Frame(i, bg=BG)
        tb = tk.Frame(self.f_cols, bg=BG)
        tb.pack(anchor="w", fill="x", pady=(E(6), 0))
        tk.Label(tb, text="En el programa", bg=BG, fg=MUTED, font=F["peq_b"]).grid(row=0, column=0, sticky="w", padx=E(6))
        tk.Label(tb, text="Nombre en el archivo", bg=BG, fg=MUTED, font=F["peq_b"]).grid(row=0, column=2, sticky="w", padx=E(6))
        for k, (c, prog, _) in enumerate(EXP_COLUMNAS, 1):
            _check(tb, prog, self.v_col[c]).grid(row=k, column=0, sticky="w", pady=E(2))
            tk.Label(tb, text="→", bg=BG, fg=MUTED, font=F["base"]).grid(row=k, column=1, padx=E(6))
            Campo(tb, app, self.v_nom[c], ancho=200).grid(row=k, column=2, pady=E(2), padx=E(6))
        self.f_json = tk.Frame(i, bg=BG)
        tk.Label(self.f_json, text="Además, en el JSON", bg=BG, fg=MUTED, font=F["peq"]).pack(anchor="w", padx=E(6), pady=(E(10), 0))
        _check(self.f_json, "Vendedores y sus metas", self.v_ext["vendedores"]).pack(anchor="w")
        _check(self.f_json, "Reportes guardados", self.v_ext["reportes"]).pack(anchor="w")
        _check(self.f_json, "Copia completa de la app (respaldo, sin el webhook)", self.v_ext["completo"]).pack(anchor="w")
        # lector / vista previa
        der = Tarjeta(cuerpo, radio=14, pad=12)
        der.grid(row=0, column=1, sticky="nsew", padx=(E(12), 0))
        tk.Label(der.interior, text="Vista previa", bg=CARD, fg=INK, font=F["h2"]).pack(anchor="w")
        self.txt = tk.Text(der.interior, bg=CARD, fg=INK, font=("Consolas", 9), bd=0, highlightthickness=0, wrap="none",
                           state="disabled", relief="flat", height=10, width=40)
        self.txt.pack(fill="both", expand=True, pady=(E(6), 0))
        for v in list(self.v_tipo.values()) + list(self.v_col.values()) + list(self.v_ext.values()) + list(self.v_nom.values()):
            v.trace_add("write", lambda *a: self.vista())
        for cb in (self.cb_fmt, self.cb_alc, self.cb_pre):
            cb.bind("<<ComboboxSelected>>", lambda e: self.vista())
        self.grab_set()
        self.vista()

    # ---- datos elegidos
    def _fmt(self):
        return self.FORMATOS.index(self.var_fmt.get()) if self.var_fmt.get() in self.FORMATOS else 0

    def _claves(self):
        if self.var_alc.get() == self.alcances[0]:
            return self.app.claves()
        return sorted(self.app.datos["periodos"])

    def _tipos(self):
        return [t for t in TIPOS_ORDEN if self.v_tipo[t].get()]

    def _columnas(self):
        p = self.PRESETS.index(self.var_pre.get()) if self.var_pre.get() in self.PRESETS else 0
        if p == 0:
            return [(c, n) for c, _, n in EXP_COLUMNAS if c in EXP_DEFECTO]
        if p == 1:
            return [(c, n) for c, _, n in EXP_COLUMNAS]
        return [(c, self.v_nom[c].get().strip() or n) for c, _, n in EXP_COLUMNAS if self.v_col[c].get()]

    def _extras(self):
        return [k for k, v in self.v_ext.items() if v.get()]

    def _contenido(self):
        """(filas o estructura json, texto de vista previa, cuantas filas)."""
        a, claves, tipos, cols = self.app.datos, self._claves(), self._tipos(), self._columnas()
        if self._fmt() == 2:
            obj = json_exportar(a, claves, tipos, cols, self._extras())
            n = len(obj.get("proyecciones", [])) if "proyecciones" in obj else sum(len(v) for v in obj["periodos"].values())
            txt = json.dumps(obj, ensure_ascii=False, indent=1).splitlines()
            return obj, "\n".join(txt[:70] + (["…"] if len(txt) > 70 else [])), n
        tabla = tabla_exportar(a, claves, tipos, cols)
        lineas = [" | ".join(str(x) for x in f)[:150] for f in tabla[:16]]
        return tabla, "\n".join(lineas + (["…"] if len(tabla) > 16 else [])), len(tabla) - 1

    def vista(self):
        if self._fmt() == 2:
            self.f_json.pack(anchor="w", fill="x")
        else:
            self.f_json.pack_forget()
        if self.var_pre.get() == self.PRESETS[2]:
            self.f_cols.pack(anchor="w", fill="x")
        else:
            self.f_cols.pack_forget()
        _, txt, n = self._contenido()
        self.txt.configure(state="normal")
        self.txt.delete("1.0", "end")
        self.txt.insert("end", txt)
        self.txt.configure(state="disabled")
        total = sum(r["monto"] for k in self._claves() for r in self.app.datos["periodos"].get(k, []) if r["tipo"] in self._tipos())
        self.lbl.config(text="{} filas · {} columnas · total {}".format(n, len(self._columnas()), fm(total)))

    def exportar(self):
        a = self.app
        completo = self._fmt() == 2 and "completo" in self._extras()
        if not self._columnas() and not completo:
            return messagebox.showwarning(APP_NAME, "Marca al menos una columna.", parent=self)
        if not self._tipos() and not completo:
            return messagebox.showwarning(APP_NAME, "Marca al menos un estado.", parent=self)
        datos, _, n = self._contenido()
        if n == 0 and not completo:
            return messagebox.showinfo(APP_NAME, "No hay filas con esa selección.", parent=self)
        ext = (".xlsx", ".csv", ".json")[self._fmt()]
        tipo = [("Excel", "*.xlsx"), ("CSV", "*.csv"), ("JSON", "*.json")][self._fmt()]
        base = "proyecciones_" + (norm(a.etiqueta_periodo()).replace(" ", "_").replace("–", "-").replace(",", "") if self.var_alc.get() == self.alcances[0] else "todos")
        ruta = filedialog.asksaveasfilename(parent=self, defaultextension=ext, filetypes=[tipo], initialfile=base + ext)
        if not ruta:
            return
        try:
            if ext == ".xlsx":
                escribir_xlsx(ruta, datos)
            elif ext == ".csv":
                escribir_csv(ruta, datos)
            else:
                with open(ruta, "w", encoding="utf-8") as f:
                    json.dump(datos, f, ensure_ascii=False, indent=1)
        except OSError as e:
            return messagebox.showerror(APP_NAME, "No se pudo exportar:\n{}".format(e), parent=self)
        messagebox.showinfo(APP_NAME, "Exportado: {} filas.\n{}".format(n, ruta), parent=self)


class PaginaIngreso(Pagina):
    def __init__(self, master, app):
        super().__init__(master, app)
        self.editando = None
        self.sub, der = self.encabezado("Ingresar reporte")
        Boton(der, app, "Importar datos", lambda: DialogoImportar(app), "suave").pack(side="left")
        Boton(der, app, "Exportar datos", lambda: DialogoExportar(app), "suave").pack(side="left", padx=(E(8), 0))

        f = Tarjeta(self, radio=14, pad=16)
        f.pack(fill="x", padx=E(24), pady=(E(6), E(10)))
        fi = f.interior
        for c in range(5):
            fi.columnconfigure(c, weight=1 if c in (1, 2) else 0)
        self.var_fecha = tk.StringVar(value=date.today().strftime("%d/%m/%Y"))
        self.var_asesor = tk.StringVar()
        self.var_camp = tk.StringVar()
        self.var_monto = tk.StringVar()
        self.var_tipo = tk.StringVar(value=TIPO_LABEL["activa"])
        self.var_lead = tk.StringVar()
        for i, t in enumerate(["Fecha", "Vendedor", "Campaña", "Monto ($)", "Estado"]):
            tk.Label(fi, text=t, bg=CARD, fg=MUTED, font=F["peq"]).grid(row=0, column=i, sticky="w", padx=E(6), pady=(0, E(3)))
        self.e_fecha = Campo(fi, app, self.var_fecha, ancho=130)
        self.cb_asesor = Campo(fi, app, self.var_asesor, ancho=180, valores=[], solo_lectura=True)
        self.cb_camp = Campo(fi, app, self.var_camp, ancho=220, valores=[])
        self.e_monto = Campo(fi, app, self.var_monto, ancho=120)
        self.cb_tipo = Campo(fi, app, self.var_tipo, ancho=130, valores=[TIPO_LABEL[t] for t in TIPOS_ORDEN], solo_lectura=True)
        for i, w in enumerate([self.e_fecha, self.cb_asesor, self.cb_camp, self.e_monto, self.cb_tipo]):
            w.grid(row=1, column=i, sticky="ew", padx=E(6), pady=(0, E(8)))
        tk.Label(fi, text="Enlace o ID del lead (Bitrix24)", bg=CARD, fg=MUTED, font=F["peq"]).grid(
            row=2, column=0, columnspan=4, sticky="w", padx=E(6), pady=(0, E(3)))
        self.e_lead = Campo(fi, app, self.var_lead, ancho=600)
        self.e_lead.grid(row=3, column=0, columnspan=4, sticky="ew", padx=E(6), pady=(0, E(10)))
        Boton(fi, app, "Leer de Bitrix24", lambda: self.leer_bitrix(manual=True), "suave", bg=CARD).grid(
            row=3, column=4, sticky="e", padx=E(6), pady=(0, E(10)))
        self.lbl_auto = tk.Label(fi, text="", bg=CARD, fg=MUTED, font=F["peq"], anchor="w")
        self.lbl_auto.grid(row=4, column=0, columnspan=3, sticky="w", padx=E(6))
        b = app.datos["config"].get("borrador")       # lo que quedo a medias la ultima vez
        if isinstance(b, dict) and (b.get("lead") or b.get("monto")):
            self.var_fecha.set(b.get("fecha") or self.var_fecha.get())
            self.var_asesor.set(b.get("asesor") or "")
            self.var_camp.set(b.get("campana") or "")
            self.var_monto.set(b.get("monto") or "")
            self.var_lead.set(b.get("lead") or "")
            if b.get("tipo") in LABEL_TIPO:
                self.var_tipo.set(b["tipo"])
            self.lbl_auto.config(text="Borrador recuperado: se queda aquí hasta que lo guardes o lo borres.")
        self._auto_job = None
        self._borrador_job = None
        self.var_lead.trace_add("write", lambda *x: self._programar_lectura())
        for v in (self.var_fecha, self.var_asesor, self.var_camp, self.var_monto, self.var_tipo, self.var_lead):
            v.trace_add("write", lambda *x: self._programar_borrador())
        bt = tk.Frame(fi, bg=CARD)
        bt.grid(row=4, column=3, columnspan=2, sticky="e", padx=E(6))
        self.btn_guardar = Boton(bt, app, "Agregar", self.guardar_form, "primario", ancho=120)
        self.btn_guardar.pack(side="left", padx=E(3))
        self.btn_cancelar = Boton(bt, app, "Cancelar edición", self.cancelar_edicion, "suave")
        self.btn_limpiar = Boton(bt, app, "Limpiar", self.limpiar_form, "suave")
        self.btn_limpiar.pack(side="left", padx=E(3))
        for w in (self.e_fecha, self.cb_camp, self.e_monto, self.e_lead):
            w.bind("<Return>", lambda e: self.guardar_form())

        tk.Label(self, text="Últimas 10 del periodo  ·  doble clic para editar", bg=BG, fg=MUTED, font=F["peq"]).pack(anchor="w", padx=E(28))
        box, self.tree = tabla_en_tarjeta(self, app, [
            ("fecha", "Fecha", 90, "w"), ("vend", "Vendedor", 130, "w"), ("id", "ID", 80, "w"),
            ("campana", "Campaña", 190, "w"), ("monto", "Monto", 100, "e"), ("tipo", "Tipo", 100, "w")],
            height=8, selectmode="extended")
        box.pack(fill="both", expand=True, padx=E(24), pady=(E(4), E(6)))
        self.tree.bind("<Double-1>", lambda e: self.editar_seleccion())
        self.tree.bind("<Delete>", lambda e: self.eliminar_seleccion())
        self.lbl_tot = tk.Label(self, bg=BG, fg=INK, font=F["peq_b"], anchor="w")
        self.lbl_tot.pack(fill="x", padx=E(28))
        bl = tk.Frame(self, bg=BG)
        bl.pack(fill="x", padx=E(24), pady=(E(4), E(14)))
        Boton(bl, app, "Editar", self.editar_seleccion, "suave").pack(side="left", padx=E(3))
        Boton(bl, app, "Eliminar", self.eliminar_seleccion, "suave_rojo").pack(side="left", padx=E(3))
        Boton(bl, app, "Deshacer eliminación", app.deshacer_eliminacion, "suave").pack(side="left", padx=(E(12), E(3)))

    def refrescar(self):
        a = self.app
        self.sub.config(text="Se guarda en " + nombre_periodo(a.clave()))
        campanas = {r["campana"] for regs in a.datos["periodos"].values() for r in regs if r["campana"]}
        self.cb_camp["values"] = sorted(campanas)
        nombres = a.nombres_lista()
        self.cb_asesor["values"] = nombres
        if self.var_asesor.get() not in nombres:
            self.var_asesor.set(nombres[0] if nombres else "")
        a.configurar_tags(self.tree)
        self.tree.delete(*self.tree.get_children())
        for r in reversed(a.registros[-10:]):
            self.tree.insert("", "end", iid=r["id"], tags=("t" + r["tipo"],), values=(
                date.fromisoformat(r["fecha"]).strftime("%d/%m/%Y"), a.nombre(r["vend"]), extraer_id(r["lead"]),
                r["campana"] or "—", fm(r["monto"]), TIPO_LABEL[r["tipo"]]))
        a.zebra(self.tree)
        por = {t: sum(r["monto"] for r in a.registros if r["tipo"] == t) for t in TIPOS_ORDEN}
        self.lbl_tot.config(text="Total del periodo ({} proyecciones): {}   ·   ".format(len(a.registros), fm(sum(por.values()))) +
                            "   ·   ".join("{}: {}".format(TIPO_LABEL[t], fm(por[t])) for t in TIPOS_ORDEN))

    # ---- lectura automatica del lead desde Bitrix24 (webhook); todo queda editable
    def _programar_lectura(self):
        if self._auto_job:
            try:
                self.after_cancel(self._auto_job)
            except Exception:
                pass
            self._auto_job = None
        did = extraer_id(limpiar_lead(self.var_lead.get()))
        if not did or self.editando or not self.app.datos["config"].get("bitrix_webhook"):
            return
        self._auto_job = self.after(500, lambda: self.leer_bitrix(did))

    def leer_bitrix(self, did=None, manual=False):
        a = self.app
        did = did or extraer_id(limpiar_lead(self.var_lead.get()))
        cfg = a.datos["config"]
        if not did:
            return self.lbl_auto.config(text="Pega primero el enlace o el ID del lead.", fg=MUTED) if manual else None
        if not cfg.get("bitrix_webhook"):
            if manual:
                messagebox.showinfo(APP_NAME, "Configura el webhook en ⚙ Configuración → Conexión con Bitrix24.", parent=a)
            return
        self.lbl_auto.config(text="Leyendo el lead {} en Bitrix24…".format(did), fg=MUTED)
        res = {}

        def trabajo():
            try:
                res["ok"] = leer_negociacion(cfg, did)
            except Exception as e:
                res["error"] = str(e)
        hilo = threading.Thread(target=trabajo, daemon=True)
        hilo.start()

        def esperar():
            if hilo.is_alive():
                self.after(120, esperar)
            else:
                self.aplicar_lectura(did, res)
        self.after(120, esperar)

    def aplicar_lectura(self, did, res):
        a = self.app
        if extraer_id(limpiar_lead(self.var_lead.get())) != did:      # ya cambio de lead mientras leia
            return
        if "error" in res:
            return self.lbl_auto.config(text="No se pudo leer: " + res["error"].replace("\n", " "), fg=CORINTO)
        d = res["ok"]
        vid = vendedor_por_nombre(a.datos, d["vendedor"])
        if vid:
            self.var_asesor.set(a.nombre(vid))
        if d["campana"]:
            self.var_camp.set(d["campana"])
        if d["monto"] > 0:
            self.var_monto.set("{:.2f}".format(d["monto"]))
        msg = "Leído de Bitrix24 · puedes editar los datos"
        if d["vendedor"] and not vid:
            msg += " · «{}» no está en tu lista de vendedores".format(d["vendedor"])
        dup, _ = buscar_duplicados(a.datos, limpiar_lead(self.var_lead.get()), vid, "", self.editando)
        if dup:
            msg = "Este lead ya está registrado en {} ({}).".format(nombre_periodo(dup[0]), TIPO_LABEL[dup[1]["tipo"]])
        self.lbl_auto.config(text=msg, fg=CORINTO if dup else AZUL_MED)

    def _error(self, msg, widget):
        messagebox.showwarning(APP_NAME, msg, parent=self.app)
        widget.focus_set()

    def guardar_form(self):
        a = self.app
        if not a.datos["vendedores"]:
            return messagebox.showwarning(APP_NAME, "Primero agrega al menos un vendedor en «Vendedores y metas».", parent=a)
        try:
            fecha = parse_fecha(self.var_fecha.get())
        except ValueError:
            return self._error("La fecha no es válida. Usa el formato dd/mm/aaaa.", self.e_fecha)
        vid = a.id_por_nombre(self.var_asesor.get())
        if not vid:
            return self._error("Elige el asesor (vendedor).", self.cb_asesor)
        lead = limpiar_lead(self.var_lead.get())
        if not lead:
            return self._error("Pega el enlace del lead (o su ID).", self.e_lead)
        try:
            monto = parse_monto(self.var_monto.get())
        except ValueError:
            return self._error("El monto no es válido (ejemplo: 1300 o 1,300.50).", self.e_monto)

        dup_enlace, dup_nombre = buscar_duplicados(a.datos, lead, vid, self.var_camp.get(), self.editando)
        if dup_enlace:
            per, r = dup_enlace
            messagebox.showwarning(
                "Lead repetido", "Este enlace ya está registrado (el monto puede repetirse, el enlace no):\n\n"
                                 "{} · {} · {} · {} · {}\n\nBúscalo en el Historial para editarlo o cambiarle el estado.".format(
                                     nombre_periodo(per), a.nombre(r["vend"]), r["campana"] or "sin campaña", fm(r["monto"]),
                                     TIPO_LABEL[r["tipo"]]), parent=a)
            return self.e_lead.focus_set()
        if dup_nombre:
            per, r = dup_nombre
            if not messagebox.askyesno(
                    "Posible repetido",
                    "{} ya tiene la campaña «{}» en {} con otro enlace ({}, {}).\n\n¿Es otra negociación distinta? ¿Guardar?".format(
                        a.nombre(r["vend"]), r["campana"], nombre_periodo(per), extraer_id(r["lead"]), fm(r["monto"])), parent=a):
                return
        datos = {"fecha": fecha.isoformat(), "asesor": a.nombre(vid), "lead": lead,
                 "campana": canon_campana(self.var_camp.get()), "vend": vid,
                 "monto": monto, "tipo": LABEL_TIPO[self.var_tipo.get()]}
        if self.editando:
            for r in a.registros:
                if r["id"] == self.editando:
                    r.update(datos)
            self.cancelar_edicion()
        else:
            datos["id"] = uuid.uuid4().hex[:10]
            a.registros.append(datos)
        self.var_lead.set("")
        self.var_monto.set("")
        a.notificar()
        self.e_lead.focus_set()

    def cargar(self, r):
        a = self.app
        self.editando = r["id"]
        self.var_fecha.set(date.fromisoformat(r["fecha"]).strftime("%d/%m/%Y"))
        self.var_asesor.set(a.nombre(r["vend"]))
        self.var_camp.set(r["campana"])
        self.var_monto.set("{:.2f}".format(r["monto"]))
        self.var_tipo.set(TIPO_LABEL[r["tipo"]])
        self.var_lead.set(r["lead"])
        self.btn_guardar.poner_texto("Guardar cambios")
        self.btn_cancelar.pack(side="left", padx=E(3), before=self.btn_limpiar)
        self.e_lead.focus_set()

    def editar_seleccion(self):
        sel = self.tree.selection()
        if not sel:
            return messagebox.showinfo(APP_NAME, "Selecciona una proyección de la lista.", parent=self.app)
        r = next((x for x in self.app.registros if x["id"] == sel[0]), None)
        if r:
            self.cargar(r)

    def eliminar_seleccion(self):
        sel = self.tree.selection()
        if not sel:
            return messagebox.showinfo(APP_NAME, "Selecciona una o varias proyecciones de la lista.", parent=self.app)
        if messagebox.askyesno(APP_NAME, "¿Eliminar {} proyección(es) seleccionada(s)?\n(Podrás deshacerlo.)".format(len(sel)), parent=self.app):
            self.app.eliminar_registros(sel)

    def _programar_borrador(self):
        if self._borrador_job:
            self.after_cancel(self._borrador_job)
        self._borrador_job = self.after(600, self.guardar_borrador)

    def guardar_borrador(self):
        """Guarda el formulario tal como esta (si hay enlace o monto escrito) para no perderlo al cerrar."""
        if self._borrador_job:
            self.after_cancel(self._borrador_job)
        self._borrador_job = None
        if self.editando:
            return
        a = self.app
        b = {"fecha": self.var_fecha.get(), "asesor": self.var_asesor.get(), "campana": self.var_camp.get(),
             "monto": self.var_monto.get(), "tipo": self.var_tipo.get(), "lead": self.var_lead.get()}
        if b["lead"].strip() or b["monto"].strip():
            a.datos["config"]["borrador"] = b
        else:
            a.datos["config"].pop("borrador", None)
        a.guardar_todo()

    def cancelar_edicion(self):
        self.editando = None
        self.btn_guardar.poner_texto("Agregar")
        self.btn_cancelar.pack_forget()

    def limpiar_form(self):
        self.cancelar_edicion()
        self.var_lead.set("")
        self.var_monto.set("")
        self.e_lead.focus_set()


class PaginaHistorial(Pagina):
    COLS = [  # id, titulo, ancho, ancla, estira
        ("n", "#", 40, "center", False), ("fecha", "Fecha", 90, "center", False),
        ("vend", "Vendedor", 120, "w", False), ("id", "ID", 75, "center", False),
        ("lead", "Lead", 330, "w", True), ("campana", "Campaña", 160, "w", False),
        ("monto", "Monto", 100, "e", False), ("tipo", "Tipo", 95, "w", False),
    ]

    def __init__(self, master, app):
        super().__init__(master, app)
        self.sort_col, self.sort_rev = "n", False
        self.sub, der = self.encabezado("Historial")
        Boton(der, app, "Exportar datos", lambda: DialogoExportar(app), "suave").pack(side="left")

        b = Tarjeta(self, radio=14, pad=12)
        b.pack(fill="x", padx=E(24), pady=(E(4), E(8)))
        bi = b.interior
        bi.columnconfigure(0, weight=1)
        self.var_busca = tk.StringVar()
        self.e_busca = Campo(bi, app, self.var_busca, ancho=300, placeholder="Buscar por referencia")
        self.e_busca.grid(row=0, column=0, sticky="ew", padx=(0, E(10)))
        self.var_busca.trace_add("write", lambda *x: self.refrescar())
        self.var_fvend = tk.StringVar(value=TODOS)
        self.var_fcamp = tk.StringVar(value=TODAS)
        self.var_ftipo = tk.StringVar(value=TODOS)
        self.cb_fvend = Campo(bi, app, self.var_fvend, ancho=150, valores=[TODOS], solo_lectura=True)
        self.cb_fcamp = Campo(bi, app, self.var_fcamp, ancho=190, valores=[TODAS], solo_lectura=True)
        self.cb_ftipo = Campo(bi, app, self.var_ftipo, ancho=130, valores=[TODOS] + [TIPO_LABEL[t] for t in TIPOS_ORDEN], solo_lectura=True)
        for i, w in enumerate((self.cb_fvend, self.cb_fcamp, self.cb_ftipo), 1):
            w.grid(row=0, column=i, padx=E(4))
            w.bind("<<ComboboxSelected>>", lambda e: self.refrescar())
        Boton(bi, app, "Limpiar filtros", self.limpiar_filtros, "suave").grid(row=0, column=4, padx=(E(8), 0))
        app.bind("<Control-f>", lambda e: (app.ir("historial"), self.e_busca.focus_set(), self.e_busca.select_range(0, "end")))

        box = Tarjeta(self, radio=14, pad=10)
        box.pack(fill="both", expand=True, padx=E(24), pady=(0, E(6)))
        self.tree = ttk.Treeview(box.interior, columns=[c[0] for c in self.COLS], show="headings", selectmode="extended")
        for cid, titulo, ancho, ancla, estira in self.COLS:
            self.tree.heading(cid, text=titulo, anchor=ancla, command=lambda c=cid: self.ordenar(c))
            self.tree.column(cid, width=E(ancho), anchor=ancla, stretch=estira, minwidth=E(40))
        sb = ttk.Scrollbar(box.interior, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        self.tree.bind("<Double-1>", lambda e: self.editar_seleccion())
        self.tree.bind("<Delete>", lambda e: self.eliminar_seleccion())
        self.tree.bind("<Button-3>", self.menu_contextual)
        self.menu = tk.Menu(self, tearoff=0)
        for t in ("perdida", "exitosa"):
            self.menu.add_command(label="Marcar " + TIPO_LABEL[t], command=lambda t=t: self.marcar(t))
        self.menu.add_separator()
        self.menu.add_command(label="Editar", command=self.editar_seleccion)
        self.menu.add_command(label="Abrir lead en el navegador", command=self.abrir_lead)
        self.menu.add_command(label="Eliminar", command=self.eliminar_seleccion)

        ac = tk.Frame(self, bg=BG)
        ac.pack(fill="x", padx=E(24), pady=(0, E(6)))
        for t in ("perdida", "exitosa"):
            Boton(ac, app, "Marcar " + TIPO_LABEL[t], lambda t=t: self.marcar(t), "suave").pack(side="left", padx=E(3))
        Boton(ac, app, "Editar", self.editar_seleccion, "suave").pack(side="left", padx=(E(12), E(3)))
        Boton(ac, app, "Abrir lead", self.abrir_lead, "suave").pack(side="left", padx=E(3))
        Boton(ac, app, "Eliminar", self.eliminar_seleccion, "suave_rojo").pack(side="left", padx=E(3))
        Boton(ac, app, "Deshacer eliminación", app.deshacer_eliminacion, "suave").pack(side="left", padx=(E(12), E(3)))
        self.lbl_estado = tk.Label(ac, text="", bg=BG, fg=MUTED, font=F["peq"])
        self.lbl_estado.pack(side="right")

        rs = Tarjeta(self, radio=14, pad=10)
        rs.pack(fill="x", padx=E(24), pady=(0, E(14)))
        cols = [("vend", "Vendedor", 130, "w"), ("an", "Activas", 60, "center"), ("am", "Monto activas", 110, "e"),
                ("pn", "Perdidas", 65, "center"), ("pm", "Monto perdidas", 110, "e"),
                ("en", "Exitosas", 65, "center"), ("em", "Monto exitosas", 110, "e"),
                ("tn", "Total", 55, "center"), ("tm", "Monto total", 110, "e"), ("pp", "% perdido", 80, "e")]
        self.res = ttk.Treeview(rs.interior, columns=[c[0] for c in cols], show="headings", height=4, selectmode="none")
        for cid, titulo, ancho, ancla in cols:
            self.res.heading(cid, text=titulo, anchor=ancla)
            self.res.column(cid, width=E(ancho), anchor=ancla, stretch=True)
        self.res.pack(fill="x")

    def filtros_actuales(self):
        a = self.app
        v = self.var_fvend.get()
        return (self.var_busca.get(), TODOS if v == TODOS else a.id_por_nombre(v), self.var_fcamp.get(),
                LABEL_TIPO.get(self.var_ftipo.get(), TODOS))

    def refrescar(self):
        a = self.app
        self.sub.config(text=a.etiqueta_periodo())
        regs_v = a.registros_vista
        self.cb_fvend["values"] = [TODOS] + a.nombres_lista()
        if self.var_fvend.get() not in self.cb_fvend["values"]:
            self.var_fvend.set(TODOS)
        vals = [TODAS] + sorted({r["campana"] for r in regs_v if r["campana"]})
        if any(not r["campana"] for r in regs_v):
            vals.append(SIN_CAMP)
        self.cb_fcamp["values"] = vals
        if self.var_fcamp.get() not in vals:
            self.var_fcamp.set(TODAS)

        a.configurar_tags(self.tree)
        a.configurar_tags(self.res)
        sel_previa = set(self.tree.selection())
        texto, vend, camp, tipo = self.filtros_actuales()
        filas = self._ordenar(filtrar(regs_v, a.nombres, texto, vend, camp, tipo))
        self.tree.delete(*self.tree.get_children())
        suma = 0.0
        for pos, r in filas:
            d = date.fromisoformat(r["fecha"])
            self.tree.insert("", "end", iid=r["id"], tags=("t" + r["tipo"],), values=(
                pos, d.strftime("%d/%m/%Y"), a.nombre(r["vend"]), extraer_id(r["lead"]), r["lead"],
                r["campana"] or "—", fm(r["monto"]), TIPO_LABEL[r["tipo"]]))
            suma += r["monto"]
        a.zebra(self.tree)
        vivos = [i for i in sel_previa if self.tree.exists(i)]
        if vivos:
            self.tree.selection_set(vivos)
        for cid, titulo, *_ in self.COLS:
            flecha = (" ▼" if self.sort_rev else " ▲") if cid == self.sort_col else ""
            self.tree.heading(cid, text=titulo + flecha)
        por = {t: sum(r["monto"] for _, r in filas if r["tipo"] == t) for t in TIPOS_ORDEN}
        self.lbl_estado.config(text="Mostrando {} de {}  ·  Total {}  ({})".format(
            len(filas), len(regs_v), fm(suma), " · ".join("{} {}".format(TIPO_LABEL[t], fm(por[t])) for t in TIPOS_ORDEN)))

        res = resumir(regs_v, a.vend_ids())
        a.configurar_tags(self.res)
        self.res.delete(*self.res.get_children())
        for k in a.vend_ids() + ["TOTAL"]:
            d = res[k]
            tn = sum(d[t][0] for t in TIPOS_ORDEN)
            tm = sum(d[t][1] for t in TIPOS_ORDEN)
            self.res.insert("", "end", tags=("total",) if k == "TOTAL" else (), values=(
                "Total" if k == "TOTAL" else a.nombre(k), d["activa"][0], fm(d["activa"][1]), d["perdida"][0],
                fm(d["perdida"][1]), d["exitosa"][0], fm(d["exitosa"][1]), tn, fm(tm), pct(d["perdida"][1], tm)))
        a.zebra(self.res)

    def _ordenar(self, filas):
        a = self.app
        claves = {
            "n": lambda p, r: p, "fecha": lambda p, r: r["fecha"],
            "vend": lambda p, r: norm(a.nombre(r["vend"])), "id": lambda p, r: int(extraer_id(r["lead"]) or 0),
            "lead": lambda p, r: norm(r["lead"]), "campana": lambda p, r: norm(r["campana"]),
            "monto": lambda p, r: r["monto"], "tipo": lambda p, r: TIPOS_ORDEN.index(r["tipo"]),
        }
        f = claves[self.sort_col]
        return sorted(filas, key=lambda pr: f(*pr), reverse=self.sort_rev)

    def ordenar(self, col):
        if self.sort_col == col:
            self.sort_rev = not self.sort_rev
        else:
            self.sort_col, self.sort_rev = col, False
        self.refrescar()

    def limpiar_filtros(self):
        self.var_busca.set("")
        self.var_fvend.set(TODOS)
        self.var_fcamp.set(TODAS)
        self.var_ftipo.set(TODOS)
        self.refrescar()

    def _seleccion(self, aviso=True):
        sel = self.tree.selection()
        if not sel and aviso:
            messagebox.showinfo(APP_NAME, "Selecciona una o varias proyecciones de la tabla.", parent=self.app)
        return sel

    def marcar(self, tipo):
        sel = set(self._seleccion())
        if not sel:
            return
        for r in self.app.registros_vista:
            if r["id"] in sel:
                r["tipo"] = tipo
        self.app.notificar()

    def eliminar_seleccion(self):
        sel = set(self._seleccion(aviso=False))
        if not sel:
            return
        a = self.app
        if not messagebox.askyesno(APP_NAME, "¿Eliminar {} proyección(es) seleccionada(s)?\n(Podrás deshacerlo.)".format(len(sel)), parent=a):
            return
        a.eliminar_registros(sel)

    def editar_seleccion(self):
        sel = self._seleccion()
        if not sel:
            return
        r = next((x for x in self.app.registros_vista if x["id"] == sel[0]), None)
        if r:
            clave = next((c for c, lst in self.app.datos["periodos"].items() if r in lst), None)
            if clave:
                self.app.var_mes.set(MESES[int(clave[5:7]) - 1])     # el formulario guarda en el mes principal
            self.app.ir("ingreso")
            self.app.pages["ingreso"].cargar(r)

    def abrir_lead(self):
        sel = self._seleccion()
        if not sel:
            return
        r = next((x for x in self.app.registros_vista if x["id"] == sel[0]), None)
        if r and r["lead"].lower().startswith("http"):
            webbrowser.open(r["lead"])
        else:
            messagebox.showinfo(APP_NAME, "Este lead no tiene un enlace válido.", parent=self.app)

    def menu_contextual(self, event):
        fila = self.tree.identify_row(event.y)
        if fila:
            if fila not in self.tree.selection():
                self.tree.selection_set(fila)
            self.menu.tk_popup(event.x_root, event.y_root)


# ------------------------------------------------------------------------ app
class App(tk.Tk):
    NAV = [("panel", "Panel principal"), ("ingreso", "Ingresar reporte"), ("historial", "Historial"),
           ("campanas", "Campañas"), ("embudos", "Embudos"), ("reportes", "Reportes guardados"),
           ("ajustes", "Vendedores y metas"), ("config", "⚙  Configuración")]

    def __init__(self, ruta=DATA_FILE):
        super().__init__()
        self.title(APP_NAME)
        crear_fuentes(self)
        an, al = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry("{}x{}".format(min(E(1240), an - 60), min(E(800), al - 90)))
        self.minsize(min(E(1080), an - 60), min(E(680), al - 90))
        try:                                    # siempre inicia en pantalla completa (maximizada)
            self.state("zoomed")
        except tk.TclError:
            try:
                self.attributes("-zoomed", True)
            except tk.TclError:
                pass
        self.motor = Motor(self)
        TEMA.app = self

        self.almacen = Almacen(ruta)
        self.datos, aviso = self.almacen.cargar()
        self.almacen.respaldar()
        self._guardado = json.dumps(self.datos, ensure_ascii=False, indent=1)
        TEMA.fijar(self.datos["config"].get("tema", "claro"))
        self.configure(bg=BG)
        self.arboles = []
        self.papelera = None   # ultima eliminacion, para poder deshacerla

        hoy = date.today()
        self.var_mes = tk.StringVar(value=MESES[hoy.month - 1])      # mes "principal": donde se ingresa y se ponen metas
        self.meses_sel = {hoy.month - 1}                              # meses que se miran (uno o varios)
        self.var_anio = tk.StringVar(value=str(hoy.year))
        self.var_modo = tk.StringVar(value="Mes")
        self.var_sem = tk.StringVar()
        self.var_medida = tk.StringVar(value=MEDIDAS[0])
        self.var_sem.set(self.semana_defecto())

        self._estilos()
        self._menu_lateral()
        self.cont = tk.Frame(self, bg=BG)
        self.cont.pack(side="right", fill="both", expand=True)
        self.pages = {}
        for clave, cls in (("panel", PaginaPanel), ("ingreso", PaginaIngreso), ("historial", PaginaHistorial),
                           ("campanas", PaginaCampanas), ("embudos", PaginaEmbudos), ("reportes", PaginaReportes),
                           ("ajustes", PaginaAjustes), ("config", PaginaConfig)):
            self.pages[clave] = cls(self.cont, self)
            self.pages[clave].place(x=0, y=0, relwidth=1, relheight=1)
        self.actual = "panel"
        self.ir("panel", animar=False)
        self.after(350, self.pages["panel"].al_mostrar)     # primer "llenado" de los anillos
        self.protocol("WM_DELETE_WINDOW", self.cerrar)
        self.after(20000, self._auto_guardar)
        self.after(4000, self.buscar_actualizacion)      # solo el programa instalado se actualiza
        if aviso:
            self.after(300, lambda: messagebox.showwarning(APP_NAME, aviso, parent=self))

    # -------------------------------------------------------------- estado
    @property
    def nombres(self):
        return vend_nombres(self.datos)

    def vend_ids(self):
        return vend_ids(self.datos)

    def nombres_lista(self):
        return [v["nombre"] for v in self.datos["vendedores"]]

    def nombre(self, vid):
        return self.nombres.get(vid, "(eliminado)")

    def id_por_nombre(self, nombre):
        for v in self.datos["vendedores"]:
            if v["nombre"] == nombre:
                return v["id"]
        return None

    def grafica(self, area):
        """Tipo de grafica elegido en Configuración para cada seccion."""
        v = self.datos.get("config", {}).get("graficas", {}).get(area)
        return v if v in [k for k, _ in GRAFICAS[area]] else GRAFICA_DEF[area]

    def clave(self):
        return clave_periodo(int(self.var_anio.get()), MESES.index(self.var_mes.get()))

    @property
    def registros(self):
        return self.datos["periodos"].setdefault(self.clave(), [])

    # ---- meses elegidos (uno o varios)
    @property
    def es_multi(self):
        return len(self.meses_sel) > 1

    def claves(self):
        a = int(self.var_anio.get())
        return [clave_periodo(a, i) for i in sorted(self.meses_sel)]

    def etiqueta_periodo(self):
        return etiqueta_meses(self.claves())

    def resumen_meses(self):
        if len(self.meses_sel) == 12:
            return "Todos los meses"
        nombres = [MESES[i] if len(self.meses_sel) == 1 else MESES_ABR[i] for i in sorted(self.meses_sel)]
        return ", ".join(nombres) if len(nombres) <= 3 else "{} meses".format(len(nombres))

    def poner_meses(self, sel):
        self.meses_sel = set(sel)
        if MESES.index(self.var_mes.get()) not in self.meses_sel:
            self.var_mes.set(MESES[min(self.meses_sel)])
        self.cambiar_periodo()

    @property
    def registros_vista(self):
        """Proyecciones de todos los meses elegidos (las mismas listas de siempre, sin copiar los registros)."""
        return [r for c in self.claves() for r in self.datos["periodos"].get(c, [])]

    def registros_filtrados(self, modo, sem):
        if self.es_multi:
            return self.registros_vista
        return filtrar_tiempo(self.registros, self.clave(), modo, sem)

    def reporte(self, modo, sem):
        if self.es_multi:
            return construir_reporte_multi(self.datos, self.claves())
        return construir_reporte(self.datos, self.clave(), modo, sem if modo == "Semana" else None)

    def etiquetas_semanas(self):
        return ["Semana {} ({}–{})".format(i, a, b) for i, (a, b) in enumerate(rangos_semanas(self.clave()), 1)]

    def semana_defecto(self):
        hoy = date.today()
        et = self.etiquetas_semanas()
        if clave_periodo(hoy.year, hoy.month - 1) == self.clave():
            return et[min((hoy.day - 1) // 7, len(et) - 1)]
        return et[0]

    def semana_num(self):
        if self.var_sem.get() not in self.etiquetas_semanas():
            self.var_sem.set(self.semana_defecto())
        return int(self.var_sem.get().split()[1])

    def toggle_modo(self):
        self.var_modo.set("Semana" if self.var_modo.get() == "Mes" else "Mes")
        self.notificar(guardar=False)

    def cambiar_periodo(self):
        self.pages["ingreso"].cancelar_edicion()
        if hasattr(self, "sel_meses"):
            self.sel_meses.refrescar_texto()
        self.var_sem.set(self.semana_defecto())
        self.notificar(guardar=False)

    def guardar_todo(self, avisar=False):
        """Guarda solo si algo cambio desde la ultima vez (incluye el borrador del formulario)."""
        try:
            s = json.dumps(self.datos, ensure_ascii=False, indent=1)
        except (TypeError, ValueError):
            return False
        if s == self._guardado:
            return True
        try:
            self.almacen.guardar(self.datos)
        except OSError as e:
            if avisar:
                messagebox.showerror(APP_NAME, "No se pudo guardar:\n{}".format(e), parent=self)
            return False
        self._guardado = s
        self.lbl_guardado.config(text="Guardado a las " + datetime.now().strftime("%H:%M"))
        return True

    def _auto_guardar(self):
        self.guardar_todo()
        self.after(20000, self._auto_guardar)

    def cerrar(self):
        """Al cerrar: guarda el borrador pendiente y todo lo demas."""
        try:
            self.pages["ingreso"].guardar_borrador()
        except Exception:
            traceback.print_exc()
        self.guardar_todo(avisar=True)
        self.destroy()

    def notificar(self, guardar=True):
        """Cada cambio refresca todas las secciones para que el dashboard siempre este al dia."""
        if guardar:
            self.guardar_todo(avisar=True)
        for p in self.pages.values():
            p.refrescar()

    # ---- eliminar / deshacer
    def eliminar_registros(self, ids):
        """Elimina de cualquier periodo y guarda copia para 'Deshacer'. Devuelve cuantas elimino."""
        ids = set(ids)
        borrados_por = {}
        for clave, regs in self.datos["periodos"].items():
            borrados = [(i, r) for i, r in enumerate(regs) if r["id"] in ids]
            if borrados:
                borrados_por[clave] = borrados
        if not borrados_por:
            return 0
        self.papelera = {"tipo": "registros", "regs": borrados_por}
        for clave in borrados_por:
            self.datos["periodos"][clave] = [r for r in self.datos["periodos"][clave] if r["id"] not in ids]
        if self.pages["ingreso"].editando in ids:
            self.pages["ingreso"].cancelar_edicion()
        self.notificar()
        return sum(len(v) for v in borrados_por.values())

    def eliminar_vendedor(self, vid):
        """Elimina al vendedor con sus proyecciones y metas (todo recuperable con 'Deshacer')."""
        vs = self.datos["vendedores"]
        pos = next((i for i, v in enumerate(vs) if v["id"] == vid), None)
        if pos is None:
            return
        regs = {}
        for clave, lista in self.datos["periodos"].items():
            borr = [(i, r) for i, r in enumerate(lista) if r["vend"] == vid]
            if borr:
                regs[clave] = borr
                self.datos["periodos"][clave] = [r for r in lista if r["vend"] != vid]
        metas = {c: m.pop(vid) for c, m in self.datos["metas"].items() if vid in m}
        self.papelera = {"tipo": "vendedor", "vend": vs.pop(pos), "pos": pos, "regs": regs, "metas": metas}
        ing = self.pages["ingreso"]
        if ing.editando and not any(r["id"] == ing.editando for r in self.registros):
            ing.cancelar_edicion()
        self.notificar()

    def deshacer_eliminacion(self):
        p = self.papelera
        if not p:
            return messagebox.showinfo(APP_NAME, "No hay ninguna eliminación para deshacer.", parent=self)
        if p["tipo"] == "vendedor":
            self.datos["vendedores"].insert(min(p["pos"], len(self.datos["vendedores"])), p["vend"])
            for c, m in p["metas"].items():
                self.datos["metas"].setdefault(c, {})[p["vend"]["id"]] = m
        total = 0
        for clave, borrados in p["regs"].items():
            lista = self.datos["periodos"].setdefault(clave, [])
            for i, r in borrados:                    # en orden ascendente se recupera la posicion original
                lista.insert(min(i, len(lista)), r)
            total += len(borrados)
        self.papelera = None
        self.notificar()
        messagebox.showinfo(APP_NAME, "Se restauró {}{} proyección(es).".format(
            "al vendedor y sus " if p["tipo"] == "vendedor" else "", total), parent=self)

    # ---- reportes
    def modelo_actual(self):
        modo = self.var_modo.get()
        return self.reporte(modo, self.semana_num() if modo == "Semana" else None)

    def guardar_reporte_actual(self):
        m = self.modelo_actual()
        previos = [x for x in self.datos["reportes"]
                   if x["clave"] == m["clave"] and x["vista"] == m["vista"] and x["semana"] == m["semana"]]
        if previos:
            if not messagebox.askyesno(APP_NAME, "Ya hay un reporte guardado de «{}».\n¿Reemplazarlo con los datos de ahora?".format(m["titulo"]), parent=self):
                return
            self.datos["reportes"] = [x for x in self.datos["reportes"] if x not in previos]
        m["id"] = uuid.uuid4().hex[:10]
        self.datos["reportes"].append(m)
        self.notificar()
        messagebox.showinfo(APP_NAME, "Reporte guardado: {}\n(con la meta mensual y semanal de cada vendedor).\n"
                                      "Lo encuentras en «Reportes guardados».".format(m["titulo"]), parent=self)

    def descargar_pdf(self, modelo=None):
        m = modelo or self.modelo_actual()
        if not m["filas"]:
            return messagebox.showinfo(APP_NAME, "Agrega al menos un vendedor para generar el reporte.", parent=self)
        sugerido = "reporte_{}_{}.pdf".format(
            norm(m["periodo"]).replace(" ", "_"), "mes" if m["vista"] == "Mes" else "semana{}".format(m["semana"]))
        ruta = filedialog.asksaveasfilename(parent=self, defaultextension=".pdf", filetypes=[("PDF", "*.pdf")], initialfile=sugerido)
        if not ruta:
            return
        try:
            n = generar_pdf(m, ruta)
        except OSError as e:
            return messagebox.showerror(APP_NAME, "No se pudo crear el PDF:\n{}".format(e), parent=self)
        if messagebox.askyesno(APP_NAME, "PDF creado ({} láminas).\n¿Abrirlo ahora?".format(n), parent=self):
            try:
                if hasattr(os, "startfile"):
                    os.startfile(ruta)
                else:
                    webbrowser.open("file://" + os.path.abspath(ruta))
            except OSError:
                pass

    # --------------------------------------------------------------- estilo
    def _estilos(self):
        st = ttk.Style(self)
        if st.theme_use() != "clam":
            st.theme_use("clam")
        st.configure(".", background=BG, foreground=INK, font=F["base"], bordercolor=BORDE)
        st.configure("Treeview", background=CARD, fieldbackground=CARD, foreground=INK, rowheight=E(32), borderwidth=0,
                     bordercolor=CARD)
        st.configure("Treeview.Heading", background=CARD, foreground=MUTED, font=F["bold"], relief="flat",
                     padding=(E(8), E(8)), borderwidth=0)
        st.map("Treeview.Heading", background=[("active", AZUL_PALIDO)])
        st.map("Treeview", background=[("selected", SELEC)], foreground=[("selected", INK)])
        st.configure("Vertical.TScrollbar", background=BORDE, troughcolor=BG, bordercolor=BG, arrowcolor=MUTED,
                     relief="flat", gripcount=0)
        st.map("Vertical.TScrollbar", background=[("active", AZUL_CLARO)])

    def configurar_tags(self, tree):
        if tree not in self.arboles:
            self.arboles.append(tree)
        for t in TIPOS_ORDEN:
            tree.tag_configure("t" + t, foreground=TIPO_FG[t])
        tree.tag_configure("par", background=BG)
        tree.tag_configure("total", font=F["bold"], background=AZUL_PALIDO)

    def zebra(self, tree):
        """Filas alternadas (en lugar de pintar cada fila con el color del vendedor)."""
        for i, iid in enumerate(tree.get_children()):
            if i % 2:
                tree.item(iid, tags=tuple(tree.item(iid, "tags")) + ("par",))

    def retema_global(self):
        self._estilos()
        for t in list(self.arboles):
            try:
                self.configurar_tags(t)
            except tk.TclError:
                self.arboles.remove(t)

    def alternar_tema(self):
        nuevo = "claro" if TEMA.nombre == "oscuro" else "oscuro"
        self.datos["config"]["tema"] = nuevo
        try:
            self.almacen.guardar(self.datos)
        except OSError:
            pass
        self.switch.ir_a(nuevo == "oscuro")
        TEMA.poner(nuevo)

    def _menu_lateral(self):
        side = tk.Frame(self, bg=SIDE_BG, width=E(236))
        side.pack(side="left", fill="y")
        side.pack_propagate(False)
        tk.Label(side, text="Proyecciones", bg=SIDE_BG, fg=SIDE_TXT, font=F["titulo"]).pack(anchor="w", padx=E(24), pady=(E(26), 0))
        tk.Label(side, text="de vendedores", bg=SIDE_BG, fg=SIDE_MUTED, font=F["base"]).pack(anchor="w", padx=E(24))
        pie = tk.Frame(side, bg=SIDE_BG)
        pie.pack(side="bottom", fill="x", padx=E(24), pady=(0, E(22)))
        self.lbl_guardado = tk.Label(pie, text="Guardado automático", bg=SIDE_BG, fg=SIDE_MUTED, font=F["mini"], anchor="w")
        self.lbl_guardado.pack(side="bottom", anchor="w", pady=(E(10), 0))
        tk.Label(pie, text="Apariencia", bg=SIDE_BG, fg=SIDE_MUTED, font=F["peq_b"]).pack(anchor="w", pady=(0, E(6)))
        self.switch = Interruptor(pie, self)
        self.switch.pack(anchor="w")
        tk.Label(side, text="Periodo", bg=SIDE_BG, fg=SIDE_MUTED, font=F["peq_b"]).pack(anchor="w", padx=E(24), pady=(E(26), E(6)))
        self.sel_meses = SelectorMeses(side, self, 188)
        self.sel_meses.pack(padx=E(24), pady=E(3), anchor="w")
        anios = sorted({str(y) for y in range(2024, 2036)} | {k[:4] for k in self.datos["periodos"]})
        cb_anio = Campo(side, self, self.var_anio, ancho=188, valores=anios, solo_lectura=True)
        cb_anio.pack(padx=E(24), pady=E(3), anchor="w")
        cb_anio.bind("<<ComboboxSelected>>", lambda e: self.cambiar_periodo())
        tk.Label(side, text="Menú", bg=SIDE_BG, fg=SIDE_MUTED, font=F["peq_b"]).pack(anchor="w", padx=E(24), pady=(E(26), E(6)))
        self.nav = {}
        for clave, texto in self.NAV:
            it = NavItem(side, self, texto, lambda c=clave: self.ir(c))
            it.pack(fill="x")
            self.nav[clave] = it

    # ---- actualizacion automatica desde GitHub Releases
    def buscar_actualizacion(self, manual=False):
        if not getattr(sys, "frozen", False):
            if manual:
                messagebox.showinfo(APP_NAME, "Estás usando el código fuente; solo el programa instalado se actualiza solo.", parent=self)
            return
        actualizador.limpiar_descargas()
        cola = queue.Queue()
        threading.Thread(target=actualizador.hilo_consultar, args=(cola,), daemon=True).start()
        self.after(300, lambda: self._revisar_actualizacion(cola, manual))

    def _revisar_actualizacion(self, cola, manual):
        try:
            info = cola.get_nowait()
        except queue.Empty:
            return self.after(300, lambda: self._revisar_actualizacion(cola, manual))
        if info and actualizador.es_mas_nueva(info["version"], VERSION_APP):
            if messagebox.askyesno("Actualización disponible", "Hay una versión nueva ({}).\nTu versión es la {}.\n\n"
                                   "Tus datos no se tocan. ¿Actualizar ahora?".format(info["version"], VERSION_APP), parent=self):
                self._descargar_actualizacion(info)
        elif manual:
            messagebox.showinfo(APP_NAME, "Ya tienes la última versión ({}).".format(VERSION_APP) if info else
                                "No se pudo consultar las versiones (revisa tu conexión).", parent=self)

    def _descargar_actualizacion(self, info):
        self.guardar_todo()
        cola = queue.Queue()
        d = tk.Toplevel(self)
        d.title("Actualizando")
        d.configure(bg=BG)
        d.resizable(False, False)
        d.transient(self)
        d.protocol("WM_DELETE_WINDOW", lambda: None)
        tk.Label(d, text="Descargando la versión {}…".format(info["version"]), bg=BG, fg=INK, font=F["bold"]).pack(padx=E(28), pady=E(18))
        barra = ttk.Progressbar(d, mode="determinate", length=E(320), maximum=100)
        barra.pack(padx=E(28), pady=(0, E(24)))
        d.grab_set()
        threading.Thread(target=actualizador.hilo_descargar, args=(info, cola), daemon=True).start()

        def revisar():
            res = None
            while res is None and not cola.empty():
                m = cola.get_nowait()
                if m[0] != "progreso":
                    res = m
                elif m[2]:
                    barra["value"] = m[1] * 100 / m[2]
            if res is None:
                return self.after(150, revisar)
            d.grab_release()
            d.destroy()
            if res[0] == "error":
                return messagebox.showerror(APP_NAME, "No se pudo descargar la actualización.\n{}".format(res[1]), parent=self)
            actualizador.lanzar_instalador(res[1])
            self.destroy()
        self.after(150, revisar)

    def ir(self, clave, animar=True):
        self.actual = clave
        for c, it in self.nav.items():
            it.poner_seleccion(c == clave)
        pag = self.pages[clave]
        pag.tkraise()
        if animar and self.motor.animar:
            pag.place_configure(x=26)                       # entra deslizando suavemente (180 ms)
            self.motor.correr(("pag",), 180, lambda p: pag.place_configure(x=int(26 * (1 - p))))
        else:
            pag.place_configure(x=0)
        pag.al_mostrar()


def main():
    try:  # nitidez en Windows con pantallas de alta resolucion
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass
    App().mainloop()


if __name__ == "__main__":
    main()
