import unittest

import novedades as N


class PruebaNovedades(unittest.TestCase):
    def test_recien_actualizado_sin_registro_muestra_solo_la_actual(self):
        notas = N.notas_a_mostrar("1.0.7", True, None)
        self.assertEqual(notas["cambios"], N.NOVEDADES["1.0.7"]["cambios"])
        self.assertEqual(notas["correcciones"], [])

    def test_junta_las_versiones_saltadas(self):
        notas = N.notas_a_mostrar("1.0.7", True, "1.0.4")
        esperadas = N.NOVEDADES["1.0.7"]["cambios"] + N.NOVEDADES["1.0.6"]["cambios"] + N.NOVEDADES["1.0.5"]["cambios"]
        self.assertEqual(notas["cambios"], esperadas)
        self.assertEqual(len(notas["correcciones"]), 2)

    def test_no_se_repite(self):
        self.assertIsNone(N.notas_a_mostrar("1.0.7", False, "1.0.7"))
        self.assertIsNone(N.notas_a_mostrar("1.0.7", True, "1.0.7"))

    def test_primera_instalacion_no_muestra_nada(self):
        self.assertIsNone(N.notas_a_mostrar("1.0.7", False, None))

    def test_version_sin_notas(self):
        self.assertIsNone(N.notas_a_mostrar("9.9.9", True, None))

    def test_vinetas(self):
        self.assertEqual(dict((c, v) for c, _, v in N.SECCIONES), {"cambios": "-", "correcciones": "*"})

    def test_la_version_actual_tiene_notas(self):
        ultima = max(N.NOVEDADES, key=lambda v: tuple(int(p) for p in v.split(".")))
        self.assertTrue(N.NOVEDADES[ultima]["cambios"] or N.NOVEDADES[ultima]["correcciones"])


if __name__ == "__main__":
    unittest.main()
