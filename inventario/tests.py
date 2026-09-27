from unittest import mock

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from .forms import ProductoForm
from .models import ConsultaIA, Categoria, Producto
from .ollama_client import ModeloNoRegistrado, consultar_ollama
from .reportes import generar_reporte


class ProductoModelTests(TestCase):
    def test_crear_producto_con_campos_minimos(self):
        p = Producto.objects.create(
            codigo="P-100", nombre="Laptop Dell", categoria="Computación", precio=1500.50,
        )
        self.assertEqual(p.codigo, "P-100")
        self.assertEqual(p.cantidad_existente, 0)
        self.assertEqual(p.stock_minimo, 5)
        self.assertTrue(p.estado)
        self.assertIsNotNone(p.fecha_registro)

    def test_codigo_es_unico(self):
        Producto.objects.create(codigo="P-200", nombre="Mouse", categoria="Periféricos", precio=9.99)
        with self.assertRaises(ValidationError):
            Producto(codigo="P-200", nombre="Teclado", categoria="Periféricos", precio=19.99).full_clean()

    def test_no_acepta_negativos_a_nivel_modelo(self):
        for campo, valor, msg in [
            ("cantidad_existente", -1, "negativa"),
            ("stock_minimo", -3, "negativo"),
        ]:
            p = Producto(codigo=f"P-NEG-{campo}", nombre="X", categoria="Y", precio=1, **{campo: valor})
            with self.assertRaises(ValidationError) as ctx:
                p.full_clean()
            self.assertIn("no puede ser", str(ctx.exception))
        p2 = Producto(codigo="P-NEG2", nombre="X", categoria="Y", precio=-0.5)
        with self.assertRaises(ValidationError):
            p2.full_clean()


class ProductoFormTests(TestCase):
    def test_form_valido_con_datos_correctos(self):
        form = ProductoForm(data={
            "codigo": "P-300", "nombre": "Monitor 24\"", "categoria": "Periféricos",
            "precio": "120.00", "cantidad_existente": "10", "stock_minimo": "3", "estado": "on",
        })
        self.assertTrue(form.is_valid(), form.errors)

    def test_form_con_precio_negativo_invalido(self):
        form = ProductoForm(data={
            "codigo": "P-301", "nombre": "Monitor", "categoria": "Periféricos",
            "precio": "-5", "cantidad_existente": "1", "stock_minimo": "1",
        })
        self.assertFalse(form.is_valid())
        self.assertIn("precio", form.errors)

    def test_form_con_cantidad_negativa_invalida(self):
        form = ProductoForm(data={
            "codigo": "P-302", "nombre": "Monitor", "categoria": "Periféricos",
            "precio": "5", "cantidad_existente": "-2", "stock_minimo": "1",
        })
        self.assertFalse(form.is_valid())
        self.assertIn("cantidad_existente", form.errors)

    def test_form_con_codigo_duplicado_invalido(self):
        Producto.objects.create(codigo="P-400", nombre="Existente", categoria="X", precio=1)
        form = ProductoForm(data={
            "codigo": "p-400", "nombre": "Duplicado", "categoria": "X",
            "precio": "2", "cantidad_existente": "1", "stock_minimo": "1",
        })
        self.assertFalse(form.is_valid())
        self.assertIn("codigo", form.errors)

    def test_edicion_no_rechaza_su_propio_codigo(self):
        p = Producto.objects.create(codigo="P-500", nombre="Aceite", categoria="Alimentos", precio=3.5)
        form = ProductoForm(instance=p, data={
            "codigo": "P-500", "nombre": "Aceite de girasol", "categoria": "Alimentos",
            "precio": "3.5", "cantidad_existente": "8", "stock_minimo": "2",
        })
        self.assertTrue(form.is_valid(), form.errors)


class CrudApiTests(TestCase):
    def setUp(self):
        self.p = Producto.objects.create(
            codigo="P-600", nombre="Balón", categoria="Deportes", precio=10, cantidad_existente=5, stock_minimo=1,
        )

    def test_panel_renderiza_productos(self):
        resp = self.client.get(reverse("panel"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Balón")
        self.assertContains(resp, "P-600")

    def test_guardar_producto_nuevo(self):
        resp = self.client.post(reverse("guardar_producto"), {
            "codigo": "P-601", "nombre": "Raqueta", "categoria": "Deportes",
            "precio": "25", "cantidad_existente": "4", "stock_minimo": "1",
        })
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(Producto.objects.filter(codigo="P-601").exists())

    def test_guardar_producto_duplicado_rechazado(self):
        resp = self.client.post(reverse("guardar_producto"), {
            "codigo": "P-600", "nombre": "Copia", "categoria": "Deportes",
            "precio": "1", "cantidad_existente": "1", "stock_minimo": "1",
        })
        self.assertEqual(resp.status_code, 400)

    def test_guardar_producto_negativo_rechazado(self):
        resp = self.client.post(reverse("guardar_producto"), {
            "codigo": "P-602", "nombre": "Prueba", "categoria": "Deportes",
            "precio": "-1", "cantidad_existente": "1", "stock_minimo": "1",
        })
        self.assertEqual(resp.status_code, 400)
        self.assertIn("no puede", resp.json()["error"])

    def test_editar_producto(self):
        resp = self.client.post(reverse("guardar_producto"), {
            "id": str(self.p.id), "codigo": "P-600", "nombre": "Balón profesional",
            "categoria": "Deportes", "precio": "12", "cantidad_existente": "6", "stock_minimo": "2",
        })
        self.assertEqual(resp.status_code, 200)
        self.p.refresh_from_db()
        self.assertEqual(self.p.nombre, "Balón profesional")
        self.assertEqual(str(self.p.precio), "12.00")

    def test_eliminar_producto_es_logico_por_defecto(self):
        """RF-04: el borrado por defecto desactiva, no borra la fila."""
        resp = self.client.post(reverse("eliminar_producto", args=[self.p.id]))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["modo"], "logico")
        self.p.refresh_from_db()
        self.assertFalse(self.p.estado)
        self.assertTrue(Producto.objects.filter(id=self.p.id).exists())

    def test_eliminar_producto_fisico(self):
        resp = self.client.post(reverse("eliminar_producto", args=[self.p.id]), {"modo": "fisico"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["modo"], "fisico")
        self.assertFalse(Producto.objects.filter(id=self.p.id).exists())

    def test_eliminar_producto_modo_invalido(self):
        resp = self.client.post(reverse("eliminar_producto", args=[self.p.id]), {"modo": "volar"})
        self.assertEqual(resp.status_code, 400)
        self.assertTrue(Producto.objects.filter(id=self.p.id).exists())

    def test_el_producto_desactivado_no_aparece_en_el_panel(self):
        self.p.estado = False
        self.p.save()
        html = self.client.get(reverse("panel")).content.decode()
        self.assertNotIn(self.p.codigo, html)
        html_inactivos = self.client.get(reverse("panel"), {"mostrar": "inactivos"}).content.decode()
        self.assertIn(self.p.codigo, html_inactivos)

    def test_ajustar_stock_sumary_restar(self):
        self.client.post(reverse("ajustar_stock", args=[self.p.id]), {"operacion": "sumar"})
        self.client.post(reverse("ajustar_stock", args=[self.p.id]), {"operacion": "restar"})
        self.p.refresh_from_db()
        self.assertEqual(self.p.cantidad_existente, 5)

    def test_ajustar_stock_no_baja_de_cero(self):
        self.p.cantidad_existente = 0
        self.p.save()
        resp = self.client.post(reverse("ajustar_stock", args=[self.p.id]), {"operacion": "restar"})
        self.assertEqual(resp.status_code, 400)


class ReportesTests(TestCase):
    def setUp(self):
        Producto.objects.create(codigo="R-1", nombre="A", categoria="X", precio=100, cantidad_existente=10, stock_minimo=2)
        Producto.objects.create(codigo="R-2", nombre="B", categoria="Y", precio=1, cantidad_existente=5, stock_minimo=5)

    @mock.patch("inventario.reportes.consultar_ollama", return_value="Análisis OK.")
    def test_ocho_reportes_generan_salida_markdown(self, _m):
        tipos = ["todos", "mas_caro", "mas_barato", "pocas_existencias",
                 "agotados", "por_categoria", "valor_total", "mayor_cantidad"]
        for tipo in tipos:
            reporte = generar_reporte(tipo, categoria="X")
            self.assertIn("### Reporte:", reporte)
            self.assertIn("Análisis IA", reporte)
            self.assertTrue(ConsultaIA.objects.filter(pregunta__startswith="Reporte").exists())

    def test_reporte_desconocido_lanza_error(self):
        with self.assertRaises(ValueError):
            generar_reporte("inexistente")


class OllamaClientTests(TestCase):
    def test_404_levanta_modelo_no_registrado(self):
        fake = mock.MagicMock()
        fake.__enter__.return_value = fake
        fake.post.return_value.raise_for_status.side_effect = __import__("httpx").HTTPStatusError(
            "Not Found", request=mock.Mock(), response=mock.Mock(status_code=404)
        )
        with mock.patch("inventario.ollama_client.httpx.Client", return_value=fake):
            with self.assertRaises(ModeloNoRegistrado):
                consultar_ollama("¿cuántos productos hay?")

    def test_errores_de_conexion_devuelven_none(self):
        fake = mock.MagicMock()
        fake.__enter__.return_value = fake
        fake.post.side_effect = __import__("httpx").ConnectError("down")
        with mock.patch("inventario.ollama_client.httpx.Client", return_value=fake):
            self.assertIsNone(consultar_ollama("¿cuántos productos hay?"))

    @mock.patch("inventario.ollama_client.httpx.Client")
    def test_consulta_ok_retorna_respuesta(self, mock_client):
        fake = mock.MagicMock()
        fake.__enter__.return_value = fake
        fake.post.return_value.raise_for_status.return_value = None
        fake.post.return_value.json.return_value = {"response": "Hay 2 productos."}
        mock_client.return_value = fake
        self.assertEqual(consultar_ollama("¿cuántos productos hay?"), "Hay 2 productos.")


class RespuestaIAFallbackTests(TestCase):
    """Cubre la ruta determinista de alertas y el descarte de respuestas cortadas."""

    def setUp(self):
        Producto.objects.create(codigo="F-1", nombre="Sal", categoria="Abarrotes", precio=3, cantidad_existente=0, stock_minimo=2)
        Producto.objects.create(codigo="F-2", nombre="Azucar", categoria="Abarrotes", precio=4, cantidad_existente=1, stock_minimo=2)
        Producto.objects.create(codigo="F-3", nombre="Papa", categoria="Abarrotes", precio=5, cantidad_existente=20, stock_minimo=2)

    def test_alertas_stock_responde_sin_llm(self):
        from .ia import construir_contexto, _respuesta_deterministica
        contexto = construir_contexto("productos criticos y agotados")
        self.assertEqual(contexto["tipo"], "alertas_stock")
        respuesta = _respuesta_deterministica(contexto)
        self.assertIsNotNone(respuesta)  # responde sin llamar al modelo
        self.assertIn("reposición", respuesta)
        self.assertIn(str(contexto["total_afectados"]), respuesta)
        self.assertIn(str(contexto["agotados"]), respuesta)
        self.assertNotIn("$", respuesta)

    def test_detecta_respuesta_truncada(self):
        from .ia import _respuesta_truncada
        self.assertTrue(_respuesta_truncada("| Producto | Stock |\n| --- | --- |\n| Sal | 0 |"))
        self.assertTrue(_respuesta_truncada("| Codigo | Producto |"))
        self.assertTrue(_respuesta_truncada(None))
        self.assertTrue(_respuesta_truncada(""))
        self.assertFalse(_respuesta_truncada("Hay 41 productos agotados."))

    @mock.patch("inventario.ia.consultar_ollama")
    def test_chat_usa_fallback_si_el_modelo_corta_la_tabla(self, mock_ollama):
        from .ia import chat_consulta
        mock_ollama.return_value = "| Producto | Stock |\n| --- | --- |\n| Sal | 0 |"
        respuesta = chat_consulta("Resume el estado del inventario")
        # La tabla cortada del modelo se descarta y se usa la respuesta local.
        self.assertNotIn("| Sal | 0 |", respuesta)
        self.assertIn("Sal", respuesta)
        self.assertTrue(ConsultaIA.objects.filter(respuesta=respuesta).exists())

    def test_los_botones_responden_con_tabla_y_todos_los_datos(self):
        """Los atajos del chat deben devolver tabla Markdown con el detalle completo."""
        from .ia import construir_contexto, _respuesta_deterministica, _respuesta_fallback
        Producto.objects.create(codigo="X-1", nombre="Extra", categoria="Abarrotes", precio=1, cantidad_existente=0, stock_minimo=1)
        casos = [
            ("¿Qué productos están en estado crítico o agotados?", "alertas_stock"),
            ("¿Cuál es el producto más caro?", "precio_maximo"),
            ("¿Cuál es el producto más barato?", "precio_minimo"),
        ]
        for pregunta, tipo in casos:
            contexto = construir_contexto(pregunta)
            self.assertEqual(contexto["tipo"], tipo)
            items = contexto.get("productos") or contexto.get("ranking")
            for respuesta in (_respuesta_deterministica(contexto), _respuesta_fallback(contexto)):
                self.assertIn("| Código |", respuesta)
                # Cabecera + todas las filas: ningun recorte a 5.
                self.assertEqual(respuesta.count("\n| "), len(items) + 1)
                for p in items:
                    self.assertIn(p["codigo"], respuesta)
                    self.assertIn(p["nombre"], respuesta)

    def test_contexto_para_llm_se_recorta(self):
        from .ia import construir_contexto, _contexto_para_llm, MUESTRA_LLM
        for i in range(6):
            Producto.objects.create(codigo=f"Y-{i}", nombre=f"Critico {i}", categoria="Abarrotes",
                                    precio=1, cantidad_existente=0, stock_minimo=1)
        contexto = construir_contexto("productos agotados y criticos")
        compacto = _contexto_para_llm(contexto)
        # 2 criticos del setUp (F-3 tiene stock sano) + 6 nuevos = 8; al LLM solo 5.
        self.assertEqual(len(contexto["productos"]), 8)
        self.assertEqual(len(compacto["productos"]), MUESTRA_LLM)
        self.assertEqual(compacto["total_afectados"], contexto["total_afectados"])

    def test_reporte_descarta_explicacion_con_tabla(self):
        from .reportes import _explicacion_ollama
        with mock.patch("inventario.reportes.consultar_ollama", return_value="| Codigo | Producto |\n| --- | --- |"):
            self.assertIn("motor de IA no disponible", _explicacion_ollama("Prueba", "| a | b |"))


class ChatTests(TestCase):
    @mock.patch("inventario.views.chat_consulta", return_value="Respuesta de prueba.")
    def test_chat_ia_responde(self, _m):
        resp = self.client.post(reverse("chat_ia"), {"pregunta": "¿stock?"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["respuesta"], "Respuesta de prueba.")

    def test_chat_ia_pregunta_vacia_rechazada(self):
        resp = self.client.post(reverse("chat_ia"), {"pregunta": "   "})
        self.assertEqual(resp.status_code, 400)

class CategoriaCrudTests(TestCase):
    """RF-01 ampliado: el catalogo de categorias se administra desde el sistema."""

    def setUp(self):
        self.url_listar = reverse("listar_categorias")
        self.url_guardar = reverse("guardar_categoria")
        self.p1 = Producto.objects.create(
            codigo="CAT-001", nombre="Leche", categoria="Lácteos",
            precio=10, cantidad_existente=5, stock_minimo=2,
        )
        # En produccion el catalogo se llena al guardar el producto o por la migracion.
        Categoria.objects.get_or_create(nombre="Lácteos")

    def test_la_migracion_pobla_el_catalogo_desde_los_productos(self):
        # La migracion 0004 recorre los productos existentes y crea el catalogo.
        from django.apps import apps as django_apps
        from django.db import connection
        from importlib import import_module

        migracion = import_module("inventario.migrations.0004_categoria")
        migracion.poblar_categorias(django_apps, connection)
        self.assertTrue(Categoria.objects.filter(nombre="Lácteos").exists())

    def test_listar_categorias_devuelve_conteo_de_productos(self):
        Categoria.objects.get_or_create(nombre="Lácteos")
        resp = self.client.get(self.url_listar)
        self.assertEqual(resp.status_code, 200)
        datos = {c["nombre"]: c["total_productos"] for c in resp.json()["categorias"]}
        self.assertEqual(datos["Lácteos"], 1)

    def test_se_puede_agregar_una_categoria(self):
        resp = self.client.post(self.url_guardar, {"nombre": "Verduras"})
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()["ok"])
        self.assertTrue(Categoria.objects.filter(nombre="Verduras").exists())

    def test_no_se_puede_agregar_duplicada_ignorando_mayusculas(self):
        Categoria.objects.get_or_create(nombre="Lácteos")
        resp = self.client.post(self.url_guardar, {"nombre": "lácteos"})
        self.assertEqual(resp.status_code, 400)
        self.assertIn("ya existe", resp.json()["error"].lower())

    def test_nombre_vacio_es_rechazado(self):
        resp = self.client.post(self.url_guardar, {"nombre": "   "})
        self.assertEqual(resp.status_code, 400)

    def test_guardar_producto_registra_la_categoria_nueva(self):
        self.client.post(reverse("guardar_producto"), {
            "codigo": "CAT-002", "nombre": "Pan", "categoria": "Panadería",
            "precio": "5", "cantidad_existente": "3", "stock_minimo": "1",
        })
        self.assertTrue(Categoria.objects.filter(nombre="Panadería").exists())

    def test_renombrar_actualiza_los_productos(self):
        cat = Categoria.objects.get(nombre="Lácteos")
        resp = self.client.post(self.url_guardar, {"id": cat.id, "nombre": "Lacteos"})
        self.assertTrue(resp.json()["ok"])
        self.p1.refresh_from_db()
        self.assertEqual(self.p1.categoria, "Lacteos")

    def test_no_se_puede_eliminar_una_categoria_en_uso(self):
        cat = Categoria.objects.get(nombre="Lácteos")
        resp = self.client.post(reverse("eliminar_categoria", args=[cat.id]))
        self.assertEqual(resp.status_code, 400)
        self.assertIn("producto", resp.json()["error"].lower())
        self.assertTrue(Categoria.objects.filter(pk=cat.id).exists())

    def test_se_puede_eliminar_una_categoria_sin_productos(self):
        Categoria.objects.create(nombre="Temporal")
        cat = Categoria.objects.get(nombre="Temporal")
        resp = self.client.post(reverse("eliminar_categoria", args=[cat.id]))
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(Categoria.objects.filter(pk=cat.id).exists())

    def test_metodo_no_permitido_en_eliminar(self):
        resp = self.client.get(reverse("eliminar_categoria", args=[1]))
        self.assertEqual(resp.status_code, 405)


class BotonesRapidosTests(TestCase):
    """Los 4 botones de consulta rapida exigidos por la rubrica (RF-06)."""

    def setUp(self):
        Producto.objects.create(codigo="BR-1", nombre="Arroz", categoria="Abarrotes",
                                precio=25, cantidad_existente=0, stock_minimo=5)
        Producto.objects.create(codigo="BR-2", nombre="Leche", categoria="Lácteos",
                                precio=8, cantidad_existente=12, stock_minimo=4)
        Producto.objects.create(codigo="BR-3", nombre="Papel", categoria="Limpieza",
                                precio=15, cantidad_existente=3, stock_minimo=3)

    def test_chip_de_reporte_agotados_pinta_tabla(self):
        """El boton 'Reporte: agotados' va por AJAX a /api/reporte/ y pinta tabla."""
        with mock.patch("inventario.reportes.consultar_ollama", return_value="Analisis de prueba."):
            resp = self.client.get(reverse("reporte"), {"tipo": "agotados"})
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()["ok"])
        reporte = resp.json()["reporte"]
        self.assertIn("| Código |", reporte)
        self.assertIn("BR-1", reporte)
        # No debe incluir productos con existencias.
        self.assertNotIn("BR-2", reporte)

    def test_chip_stock_critico_pinta_todos_los_criticos(self):
        resp = self.client.post(reverse("chat_ia"),
                                {"pregunta": "¿Qué productos están en estado crítico o agotados?"})
        self.assertEqual(resp.status_code, 200)
        texto = resp.json()["respuesta"]
        self.assertIn("| Código |", texto)
        self.assertIn("BR-1", texto)   # agotado
        self.assertIn("BR-3", texto)   # bajo (<= stock_minimo)

    def test_chip_producto_mas_carro_responde_exacto(self):
        resp = self.client.post(reverse("chat_ia"), {"pregunta": "¿Cuál es el producto más caro?"})
        self.assertEqual(resp.status_code, 200)
        texto = resp.json()["respuesta"]
        self.assertIn("Arroz", texto)
        self.assertIn("25", texto)

    def test_chip_valor_total_responde_exacto(self):
        resp = self.client.post(reverse("chat_ia"), {"pregunta": "¿Cuál es el valor total del inventario?"})
        self.assertEqual(resp.status_code, 200)
        texto = resp.json()["respuesta"]
        # 0*25 + 12*8 + 3*15 = 141 Bs, 15 unidades.
        self.assertIn("141", texto)
        self.assertIn("15", texto)

    def test_los_cuatro_chips_existen_en_la_interfaz(self):
        html = self.client.get(reverse("panel")).content.decode()
        for etiqueta in ["Stock crítico", "Producto más caro", "Valor total", "Reporte: agotados"]:
            self.assertIn(etiqueta, html)
        self.assertIn("askReportChip('agotados'", html)

    def test_cada_boton_pide_datos_al_su_endpoint(self):
        html = self.client.get(reverse("panel")).content.decode()
        self.assertIn("fetch('/api/chat/'", html)
        self.assertIn("fetch(`/api/reporte/?tipo=", html)


class ReportesConsistenciaTests(TestCase):
    """Los 8 reportes deben usar el mismo criterio: solo productos activos."""

    def setUp(self):
        self.activo = Producto.objects.create(codigo="AC-1", nombre="Activo", categoria="Abarrotes",
                                             precio=10, cantidad_existente=2, stock_minimo=1)
        self.inactivo = Producto.objects.create(codigo="IN-1", nombre="Inactivo", categoria="Abarrotes",
                                                precio=999, cantidad_existente=50, stock_minimo=1,
                                                estado=False)

    def test_valor_total_ignora_productos_inactivos(self):
        """Regresion: el reporte sumaba unidades de productos desactivados."""
        from .reportes import generar_reporte
        with mock.patch("inventario.reportes.consultar_ollama", return_value="Analisis de prueba."):
            texto = generar_reporte("valor_total")
        self.assertIn("Bs. 20.00", texto)      # 2 unidades x 10 Bs del producto activo
        self.assertIn("**2**", texto)          # unidades: solo las del activo
        self.assertIn("**1**", texto)          # productos activos: 1
        self.assertNotIn("999", texto)
        self.assertNotIn("50", texto)          # no suma las unidades del inactivo

    def test_todos_los_reportes_excluyen_inactivos(self):
        from .reportes import generar_reporte
        for tipo in ["todos", "mas_caro", "mas_barato", "pocas_existencias",
                     "agotados", "por_categoria", "valor_total", "mayor_cantidad"]:
            with self.subTest(tipo=tipo):
                with mock.patch("inventario.reportes.consultar_ollama", return_value="Analisis de prueba."):
                    self.assertNotIn("IN-1", generar_reporte(tipo))

    def test_los_ocho_tipos_existen_en_el_diccionario_strategy(self):
        from .reportes import REPORTES
        self.assertEqual(
            set(REPORTES),
            {"todos", "mas_caro", "mas_barato", "pocas_existencias",
             "agotados", "por_categoria", "valor_total", "mayor_cantidad"},
        )


class ValorTotalConTablaTests(TestCase):
    """El boton 'Valor total' debe devolver la cifra Y la tabla completa."""

    def setUp(self):
        Producto.objects.create(codigo="VT-1", nombre="Arroz", categoria="Abarrotes",
                                precio=10, cantidad_existente=2, stock_minimo=1)
        Producto.objects.create(codigo="VT-2", nombre="Leche", categoria="Lácteos",
                                precio=5, cantidad_existente=3, stock_minimo=1)

    def test_valor_total_incluye_tabla_completa(self):
        resp = self.client.post(reverse("chat_ia"),
                                {"pregunta": "¿Cuál es el valor total del inventario?"})
        texto = resp.json()["respuesta"]
        # 2x10 + 3x5 = 35 Bs, 5 unidades
        self.assertIn("35", texto)
        self.assertIn("5 unidades", texto)
        self.assertIn("| Código |", texto)
        self.assertIn("VT-1", texto)
        self.assertIn("VT-2", texto)

    def test_el_fallback_de_valor_total_tambien_trae_tabla(self):
        from .ia import construir_contexto, _respuesta_fallback
        contexto = construir_contexto("¿Cuál es el valor total del inventario?")
        texto = _respuesta_fallback(contexto)
        self.assertIn("| Código |", texto)
        self.assertIn("VT-1", texto)
