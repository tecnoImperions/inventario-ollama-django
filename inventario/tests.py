from unittest import mock

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from .forms import ProductoForm
from .models import ConsultaIA, Producto
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

    def test_eliminar_producto(self):
        resp = self.client.post(reverse("eliminar_producto", args=[self.p.id]))
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(Producto.objects.filter(id=self.p.id).exists())

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


class ChatTests(TestCase):
    @mock.patch("inventario.views.chat_consulta", return_value="Respuesta de prueba.")
    def test_chat_ia_responde(self, _m):
        resp = self.client.post(reverse("chat_ia"), {"pregunta": "¿stock?"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["respuesta"], "Respuesta de prueba.")

    def test_chat_ia_pregunta_vacia_rechazada(self):
        resp = self.client.post(reverse("chat_ia"), {"pregunta": "   "})
        self.assertEqual(resp.status_code, 400)