# -*- coding: utf-8 -*-
"""
Nucleo de Proyecciones de Vendedores: toda la logica, sin interfaz (ni Tkinter ni web).
La interfaz es HTML/CSS/JS dentro de una ventana pywebview (ver app_web.py y la carpeta web/).

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

import actualizador
import novedades

ICONO = "Proyecciones_Dream.ico"


def ruta_recurso(nombre):
    """Funciona tanto desde el codigo fuente como dentro del .exe de PyInstaller."""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, nombre)


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
_ACTUAL = {}


def aplicar_paleta(P):
    """Pone la paleta P como colores vigentes (las constantes de modulo AZUL, CARD, INK... se leen al dibujar)."""
    g = globals()
    g.update(P)
    _ACTUAL.clear()
    _ACTUAL.update(P)
    PALETA[:] = [(P["PT%d" % i], P["PS%d" % i]) for i in range(8)]
    g["GRIS"] = (P["GT"], P["GS"])
    g["TIPO_FG"] = {"activa": P["INK"], "perdida": P["CORINTO"], "exitosa": P["AZUL"]}
    DONA_COLORES[:] = [P["CORINTO"], P["AZUL"], P["AZUL_MED"], P["AZUL_CLARO"], P["CORINTO_MED"], P["MUTED"]]


class paleta_pdf:
    """Con 'with paleta_pdf():' los colores vuelven temporalmente a los del PDF."""

    def __enter__(self):
        self.antes = dict(_ACTUAL)
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


def con_necesaria(c, meta_mes=None):
    """Proyeccion que hace falta para llegar a la meta si se sigue cerrando al mismo ritmo.
    tasa de cierre = vendido / proyectado total (activas + perdidas + exitosas).
    % faltante = meta del periodo / meta mensual - vendido / meta mensual
      (en vista mensual la meta del periodo ES la mensual: 100% - vendido / meta).
    Falta vender = % faltante x meta mensual; falta proyectar = falta vender / tasa de cierre.
    (Ej.: meta mensual 1,000 y semanal 250; vendido 100 de 1,000 = 10%; faltante 25% - 10% = 15% = 150 por vender;
    con 20% de cierre hay que proyectar 750 mas.)"""
    ing = c["neto"] + c["proy"] + c["perdidas"]
    base = meta_mes if meta_mes and meta_mes > 0 else c["meta"]
    c["ingresado"] = ing
    c["tasa"] = c["neto"] / ing if ing > 0 else None
    c["pct_real"] = c["neto"] / base if base > 0 else None
    c["pct_falta"] = max(0.0, c["meta"] / base - c["neto"] / base) if base > 0 else None
    c["nec_total"] = c["nec_falta"] = None
    if c["meta"] > 0 and 0 < c["neto"] < c["meta"]:
        c["nec_falta"] = max(0.0, c["pct_falta"] * base / c["tasa"])
        c["nec_total"] = ing + c["nec_falta"]
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
        filas.append(con_necesaria(con_ritmo(c, frac), c["meta_mes"]))
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
    equipo = con_necesaria(con_ritmo(calcular_tarjeta(regs, meta_eq), frac), sum(f["meta_mes"] for f in filas))
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


def _campos_campana(base, abrir=None):
    """Campos personalizados de campaña [(codigo, detalle)], del mas confiable al menos.

    Primero la lista que llena el vendedor («Seleccione Campaña»), luego el texto «Campaña».
    Se ignoran los historicos. Lista vacia si no hay ninguno."""
    try:
        campos = bitrix_llamar(base, "crm.deal.fields", {}, abrir).get("result") or {}
    except Exception:
        return []
    hallados = []
    for cod, inf in campos.items():
        if not cod.startswith("UF_") or not isinstance(inf, dict):
            continue
        nombres = [norm(inf.get(k) or "").strip() for k in ("formLabel", "listLabel", "editFormLabel")]
        if not any("campana" in n for n in nombres) or any("historic" in n for n in nombres):
            continue
        if any(n.startswith("seleccione") for n in nombres):
            prioridad = 0
        elif "campana" in nombres:
            prioridad = 1
        else:
            prioridad = 2
        hallados.append((prioridad, cod, inf))
    return [(cod, inf) for _, cod, inf in sorted(hallados, key=lambda h: h[0])]


def _valor_campo(deal, campo, info):
    """Valor legible de un campo: las listas desplegables vienen como codigo y se traducen a su nombre."""
    valor = deal.get(campo) if campo else None
    items = (info or {}).get("items") or []
    if items and valor not in (None, "", []):
        nombres = {str(i.get("ID")): i.get("VALUE") for i in items}
        valor = [nombres.get(str(v), v) for v in valor] if isinstance(valor, (list, tuple)) else nombres.get(str(valor), valor)
    if isinstance(valor, (list, tuple)):
        valor = ", ".join(str(v) for v in valor if v not in (None, ""))
    return valor if valor not in (None, False) else ""


TIPO_PROMOCIONES = 1040     # proceso inteligente «Promociones» de Bitrix24 (respaldo si no se detecta)


def _id_entero(v):
    """ID numerico de un campo que puede venir como '79', 79, 79.0, '79.00' o [79]; None si no hay."""
    if isinstance(v, (list, tuple)):
        v = v[0] if v else None
    try:
        n = int(float(str(v).strip()))
    except (TypeError, ValueError):
        return None
    return n if n > 0 else None


def _campos_promocion(base, abrir=None):
    """Codigos de los campos de promocion: {'utm': [...], 'seleccion': [...], 'tipo': id del proceso}."""
    try:
        campos = bitrix_llamar(base, "crm.deal.fields", {}, abrir).get("result") or {}
    except Exception:
        campos = {}
    res = {"utm": [], "seleccion": [], "tipo": TIPO_PROMOCIONES}
    padre, id_spa = [], []
    for cod, inf in campos.items():
        if not isinstance(inf, dict):
            continue
        nombres = [norm(inf.get(k) or "").strip() for k in ("formLabel", "listLabel", "editFormLabel", "title")]
        if not any("promocion" in n for n in nombres):
            continue
        if cod.startswith("PARENT_ID_"):                # «PROMOCIONES» (UTM promo): enlace al proceso
            padre.append(cod)
            res["tipo"] = (inf.get("settings") or {}).get("parentEntityTypeId") or int(cod.rsplit("_", 1)[1])
        elif any(n.startswith("seleccione") for n in nombres):
            res["seleccion"].append(cod)                # «Seleccione Promoción»
        elif any(n.startswith("id ") for n in nombres):
            id_spa.append(cod)                          # «ID SPA Promocion» (UTM promo)
    res["utm"] = padre + id_spa
    return res


def _nombre_promocion(base, tipo, pid, abrir=None, cache=None):
    cache = {} if cache is None else cache
    if pid not in cache:
        try:
            item = (bitrix_llamar(base, "crm.item.get", {"entityTypeId": tipo, "id": pid}, abrir).get("result") or {}).get("item") or {}
            cache[pid] = str(item.get("title") or "").strip()
        except Exception:
            cache[pid] = ""
    return cache[pid]


def leer_promocion(base, deal, abrir=None):
    """(campaña, aviso). Se usa la promocion del UTM; si no hay, la seleccionada.
    El aviso dice si la seleccionada y la del UTM no coinciden."""
    c = _campos_promocion(base, abrir)
    utm = next((p for p in (_id_entero(deal.get(k)) for k in c["utm"]) if p), None)
    sel = next((p for p in (_id_entero(deal.get(k)) for k in c["seleccion"]) if p), None)
    if not utm and not sel:
        return "", ""
    cache = {}
    nombre_utm = _nombre_promocion(base, c["tipo"], utm, abrir, cache) if utm else ""
    nombre_sel = _nombre_promocion(base, c["tipo"], sel, abrir, cache) if sel else ""
    aviso = ""
    if utm and sel and utm != sel and norm(nombre_utm) != norm(nombre_sel):
        aviso = "La campaña y el UTM no coinciden. Se usó el UTM; la seleccionada es «{}».".format(
            canon_campana(nombre_sel) or sel)
    return (nombre_utm or nombre_sel), aviso


def leer_negociacion(cfg, did, abrir=None):
    """Lee la negociacion y devuelve lo que llena el formulario: monto, campaña y vendedor (editables despues)."""
    base, deal = bitrix_negociacion(cfg, did, abrir)
    campo = (cfg.get("campo_campana") or "auto").strip()
    valor, aviso_campana = leer_promocion(base, deal, abrir)
    if valor:                                     # la promocion manda; los demas campos son de negociaciones viejas
        campo = "PROMOCION"
    elif campo.lower() in ("auto", "title"):          # el primer campo de campaña que tenga valor
        campo = ""
        for cod, inf in _campos_campana(base, abrir):
            valor = _valor_campo(deal, cod, inf)
            if valor:
                campo = cod
                break
        if not campo and campo_es_title(cfg):
            campo, valor = "TITLE", deal.get("TITLE") or ""
    else:
        info = {}
        if campo.startswith("UF_"):
            info = next((inf for cod, inf in _campos_campana(base, abrir) if cod == campo), {})
        valor = _valor_campo(deal, campo, info)
    if campo == "SOURCE_ID" and valor:       # el origen viene como codigo: se traduce a su nombre
        try:
            lista = bitrix_llamar(base, "crm.status.list", {"filter[ENTITY_ID]": "SOURCE"}, abrir).get("result") or []
            valor = next((x["NAME"] for x in lista if x.get("STATUS_ID") == valor), valor)
        except Exception:
            pass
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
    return {"monto": monto, "monto_vacio": monto <= 0, "campana": canon_campana(valor or ""),
            "aviso_campana": aviso_campana,
            "vendedor": vendedor, "titulo": str(deal.get("TITLE") or "")}


def campo_es_title(cfg):
    """Solo se usa el titulo como campaña si el usuario lo escribio a proposito en Configuración."""
    return (cfg.get("campo_campana") or "").strip().upper() == "TITLE"


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
def regresar_a_seguimiento(datos, ids, ahora=None):
    """Saca las proyecciones de sus periodos (dejan de contar en tablas y totales) y las anota en datos['regresos'].
    Devuelve cuantas movio."""
    ids = set(ids)
    ahora = ahora or datetime.now()
    movidos = []
    for clave in list(datos["periodos"]):
        quedan = []
        for r in datos["periodos"][clave]:
            if r["id"] in ids:
                movidos.append({"id": uuid.uuid4().hex[:10], "regreso": ahora.isoformat(timespec="seconds"),
                                "periodo": clave, "reg": dict(r)})
            else:
                quedan.append(r)
        datos["periodos"][clave] = quedan
    datos.setdefault("regresos", []).extend(movidos)
    return len(movidos)


def restaurar_regresos(datos, rids):
    """Devuelve a su periodo original las proyecciones que habian regresado a Seguimiento. Devuelve cuantas restauro."""
    rids = set(rids)
    resto, n = [], 0
    for h in datos.get("regresos", []):
        if h["id"] not in rids:
            resto.append(h)
            continue
        lista = datos["periodos"].setdefault(h["periodo"], [])
        if all(x["id"] != h["reg"]["id"] for x in lista):
            lista.append(dict(h["reg"]))
            n += 1
    datos["regresos"] = resto
    return n


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


def _sin_formula(v):
    """Excel ejecuta como formula lo que empieza con = + - @ : se antepone un apostrofo a los textos (no a los numeros)."""
    if isinstance(v, str) and v[:1] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + v
    return v


def escribir_csv(ruta, filas):
    with open(ruta, "w", newline="", encoding="utf-8-sig") as f:
        csv.writer(f).writerows([[_sin_formula(v) for v in fila] for fila in filas])


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
        if len(z.infolist()) > 2000 or sum(i.file_size for i in z.infolist()) > 150 * 1024 * 1024:
            raise ValueError("El archivo de Excel es demasiado grande o no es válido.")      # protege de archivos comprimidos maliciosos
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
            datos = {"version": 3, "vendedores": [dict(v) for v in VEND_DEFAULT], "periodos": {}, "metas": {}, "reportes": [], "regresos": []}
        vend = datos.get("vendedores")
        if isinstance(vend, dict):          # formato anterior: {"A": "LESLY", ...}
            datos["vendedores"] = [{"id": k, "nombre": n, "ci": i} for i, (k, n) in enumerate(vend.items())]
        elif not isinstance(vend, list):
            datos["vendedores"] = [dict(v) for v in VEND_DEFAULT]
        datos["version"] = 3
        datos.setdefault("metas", {})
        datos.setdefault("reportes", [])
        if not isinstance(datos.get("regresos"), list):
            datos["regresos"] = []
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
    cols = [("Vendedor", 66, "l"), ("Meta", 275, "r"), ("Vendido", 365, "r"), ("Proyectado", 465, "r"),
            ("Tasa", 540, "r"), ("Necesaria", 650, "r"), ("% faltante", 775, "r"), ("Falta proyectar", 905, "r")]
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
                pdf.text(275, y + 22, fm0(f["meta"]), 11, equipo, INK, "r")
                pdf.text(365, y + 22, fm0(f["neto"]), 11, True, AZUL, "r")
                pdf.text(465, y + 22, fm0(f["ingresado"]), 11, equipo, INK, "r")
                pdf.text(540, y + 22, pct0(f["tasa"], 1.0) if f["tasa"] is not None else "—", 11, equipo, INK, "r")
                if f["neto"] >= f["meta"]:
                    pdf.text(905, y + 22, "Meta lograda", 11, True, AZUL_MED, "r")
                elif f["nec_total"] is None:
                    pdf.text(905, y + 22, "Sin ventas aún", 10.5, False, MUTED, "r")
                else:
                    pdf.text(650, y + 22, fm0(f["nec_total"]), 11, equipo, INK, "r")
                    pdf.text(775, y + 22, pct0(f["pct_falta"], 1.0), 11, equipo, INK, "r")
                    pdf.text(905, y + 22, fm0(f["nec_falta"]), 11, True, CORINTO, "r")
            y += 36
        if ultimo:
            pdf.text(48, 484, "Tasa = vendido ÷ proyectado total (activas + perdidas + exitosas). % faltante = meta del período ÷ meta mensual - "
                              "vendido ÷ meta mensual (en vista mensual: 100% - vendido ÷ meta).", 9, False, MUTED, maxw=864)
            pdf.text(48, 497, "Falta proyectar = (% faltante x meta mensual) ÷ tasa. Necesaria = proyectado + falta proyectar.", 9, False, MUTED, maxw=864)
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
            nota = "Para la meta: proyectar {} en total (faltan {}) · falta {} · cierre {}".format(
                fm0(f["nec_total"]), fm0(f["nec_falta"]), pct0(f["pct_falta"], 1.0), pct0(f["tasa"], 1.0))
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


# ------------------------------------------------------------ enlaces de leads
def url_de(r):
    """Enlace del lead si es una direccion web; si solo tiene el ID, None."""
    l = (r.get("lead") or "").strip()
    return l if re.match(r"https?://[^\s]+$", l, re.I) else None       # solo web: nunca file:// ni otros esquemas


def etiqueta_id(r):
    """ID para mostrar en tablas; lleva una flecha si el lead tiene enlace."""
    i = extraer_id(r["lead"])
    return ("\u2197 " + i) if i and url_de(r) else i
