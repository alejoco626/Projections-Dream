# -*- coding: utf-8 -*-
"""
Puente entre la ventana web y el Servicio.

pywebview expone a JavaScript los metodos publicos de este objeto (window.pywebview.api.<metodo>(...)).
Cada llamada corre en su propio hilo, asi que leer Bitrix24 o descargar una actualizacion no congela la ventana.
Los errores inesperados nunca llegan como excepcion a la pagina: se devuelven como {"error": "..."}.
"""
import functools
import traceback

import servicio

# Metodos del Servicio que la pagina puede llamar (lista cerrada: nada mas queda expuesto).
PUBLICOS = (
    "estado", "fijar_vista", "fijar_tema", "panel", "campanas", "embudos", "historial", "marcar", "eliminar",
    "deshacer", "regresar", "regresos", "restaurar_regresos", "ingreso", "leer_bitrix", "guardar_proyeccion",
    "editar_registro", "guardar_borrador", "vendedores_metas", "guardar_vendedor", "datos_vendedor",
    "eliminar_vendedor", "guardar_reporte", "reportes", "reporte_guardado", "eliminar_reporte", "descargar_pdf",
    "abrir_ruta", "abrir_url", "abrir_carpeta", "config", "cambiar_grafica", "guardar_conexion", "probar_conexion",
    "vaciar_periodo", "borrar_todo", "cuenta_periodo", "imp_plantilla", "imp_elegir", "imp_vista", "imp_aplicar",
    "exp_info", "exp_vista", "exp_exportar", "novedades_pendientes", "buscar_actualizacion",
    "descargar_actualizacion", "progreso_actualizacion", "instalar_actualizacion",
)


class Api:
    def __init__(self, svc, salir=None):
        self._svc = svc
        self._salir = salir
        for nombre in PUBLICOS:
            setattr(self, nombre, self._envolver(nombre))

    def _envolver(self, nombre):
        metodo = getattr(self._svc, nombre)

        @functools.wraps(metodo)
        def llamar(*args, **kw):
            try:
                if nombre == "instalar_actualizacion":
                    return metodo(salir=self._salir)
                return metodo(*args, **kw)
            except Exception as e:           # nunca dejar caer la pagina por un error de Python
                traceback.print_exc()
                return {"error": "Error inesperado: {}".format(e)}
        return llamar


def llamar_por_nombre(api, nombre, args):
    """Usado por el servidor de desarrollo y las pruebas: misma lista cerrada que la ventana real."""
    if nombre not in PUBLICOS:
        return {"error": "Metodo no permitido: {}".format(nombre)}
    return getattr(api, nombre)(*args)
