"""Notas de cada versión, que se muestran en una ventana al terminar de actualizar.

Antes de publicar una versión, agrega aquí su entrada con el mismo número del release.
"cambios" se muestran con guion (-) y "correcciones" con asterisco (*); una sección
vacía no aparece. Si la versión no tiene entrada, no se muestra ninguna ventana.
"""

import os

from actualizador import es_mas_nueva

NOVEDADES = {
    "1.0.5": {
        "cambios": ["Aviso en rojo bajo el monto cuando el vendedor no lo colocó en la negociación"],
        "correcciones": ["Al leer una negociación ya no se quedan el monto, la campaña ni el vendedor de la anterior"],
    },
    "1.0.6": {
        "cambios": ["La campaña se toma de UTM PROMO y, si no hay, de «Seleccione Promoción»",
                    "Aviso en rojo bajo la campaña cuando la seleccionada y la del UTM no coinciden"],
        "correcciones": ["La campaña ya no se toma del título de la negociación"],
    },
    "1.0.7": {
        "cambios": ["Ventana con los cambios y correcciones al terminar de actualizar"],
        "correcciones": [],
    },
    "1.1.0": {
        "cambios": ["Interfaz nueva con pywebview: diseño renovado, tema claro y oscuro, animaciones suaves y rápidas",
                    "Esqueletos de carga mientras se llena cada pantalla",
                    "Gráficas que se ajustan al tamaño de la ventana"],
        "correcciones": ["Tus datos y copias se conservan igual: siguen en la misma carpeta"],
    },
}

SECCIONES = (("cambios", "Cambios", "-"), ("correcciones", "Correcciones", "*"))
ARGUMENTO_ACTUALIZADO = "--actualizado"  # lo pasa el instalador al reabrir el programa
ARCHIVO_VERSION_VISTA = os.path.join(
    os.environ.get("LOCALAPPDATA") or os.path.expanduser("~"),
    "DreamTravel",
    "proyecciones_ultima_version.txt",
)


def leer_version_vista():
    try:
        with open(ARCHIVO_VERSION_VISTA, encoding="utf-8") as archivo:
            return archivo.read().strip() or None
    except OSError:
        return None


def guardar_version_vista(version):
    try:
        os.makedirs(os.path.dirname(ARCHIVO_VERSION_VISTA), exist_ok=True)
        with open(ARCHIVO_VERSION_VISTA, "w", encoding="utf-8") as archivo:
            archivo.write(version)
    except OSError:
        pass


def notas_a_mostrar(version_actual, recien_actualizado, version_vista):
    """{'cambios': [...], 'correcciones': [...]} a mostrar ahora, o None.

    Si se sabe cuál fue la última versión abierta, junta las notas de todas las versiones
    posteriores hasta la actual (por si se saltó alguna). Si no se sabe, pero el instalador
    avisa que acaba de actualizar, muestra solo las de la versión actual.
    """
    if version_vista is not None:
        if not es_mas_nueva(version_actual, version_vista):
            return None
        versiones = [v for v in NOVEDADES
                     if es_mas_nueva(v, version_vista) and not es_mas_nueva(v, version_actual)]
    elif recien_actualizado:
        versiones = [version_actual] if version_actual in NOVEDADES else []
    else:
        return None
    versiones.sort(key=lambda v: tuple(int(p) for p in v.split(".")), reverse=True)
    notas = {clave: [n for v in versiones for n in NOVEDADES[v].get(clave) or []] for clave, _, _ in SECCIONES}
    return notas if any(notas.values()) else None
