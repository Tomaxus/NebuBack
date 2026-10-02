from devconfsite.carrito.models import Carrito, Pedido
from devconfsite.catalogo.models import Producto
from devconfsite.comun.pruebas import DIRECCION, TiendaTest
from devconfsite.usuarios.models import Usuario


class CheckoutTests(TiendaTest):
    def test_flujo_completo_del_contrato(self):
        item = self.agregar().json()["items"][0]["id"]
        self.client.patch(f"/api/cart/items/{item}/", {"quantity": 2}, format="json")
        stock_antes = Producto.objects.get(slug="iphone-18-pro-max").stock
        respuesta = self.pagar()
        self.assertEqual(respuesta.status_code, 201)
        pedido = respuesta.json()
        self.assertEqual(pedido["number"], f"NB-{1000 + pedido['id']}")
        self.assertEqual((pedido["status"], pedido["subtotal"], pedido["tax"], pedido["total"]), ("paid", 2398, 191.84, 2589.84))
        self.assertEqual(pedido["shippingAddress"], DIRECCION)
        self.assertEqual((pedido["customerId"], pedido["customerEmail"], pedido["cardLast4"]), (self.cliente.pk, "buyer@example.com", "4242"))
        self.assertEqual(pedido["lines"][0]["category"], "Iphone")
        self.assertNotIn("units", pedido)
        self.assertEqual(Producto.objects.get(slug="iphone-18-pro-max").stock, stock_antes - 2)
        self.assertEqual(self.client.get("/api/cart/").json()["items"], [])
        self.assertEqual(Carrito.objects.get(pk=Pedido.objects.get(pk=pedido["id"]).cart_id).status, "converted")

        self.como_admin()
        respuesta = self.client.patch(f"/api/admin/orders/{pedido['id']}/", {"status": "cancelled"}, format="json")
        self.assertEqual(respuesta.json()["status"], "cancelled")
        self.assertEqual(Producto.objects.get(slug="iphone-18-pro-max").stock, stock_antes)
        self.client.patch(f"/api/admin/orders/{pedido['id']}/", {"status": "shipped"}, format="json")
        self.assertEqual(Producto.objects.get(slug="iphone-18-pro-max").stock, stock_antes - 2)

    def test_carrito_vacio_y_doble_clic(self):
        respuesta = self.pagar()
        self.assertEqual((respuesta.status_code, respuesta.json()), (400, {"detail": "Your bag is empty."}))
        self.agregar()
        self.assertEqual(self.pagar().status_code, 201)
        self.assertEqual(self.pagar().json(), {"detail": "Your bag is empty."})

    def test_cliente_bloqueado(self):
        self.agregar()
        Usuario.objects.filter(pk=self.cliente.pk).update(status="blocked")
        respuesta = self.pagar()
        self.assertEqual((respuesta.status_code, respuesta.json()), (403, {"detail": "This account can't place orders. Contact support."}))

    def test_producto_desactivado_despues_de_agregar(self):
        item = self.agregar().json()["items"][0]["id"]
        Producto.objects.filter(slug="iphone-18-pro-max").update(status="disabled")
        respuesta = self.pagar()
        self.assertEqual(respuesta.status_code, 400)
        self.assertEqual(respuesta.json(), {"detail": "Some items are no longer available.", "items": [str(item)]})

    def test_datos_de_envio_obligatorios(self):
        self.agregar()
        respuesta = self.client.post("/api/orders/", {"shippingAddress": {**DIRECCION, "city": ""}, "cardLast4": "42a2"}, format="json")
        self.assertEqual(
            respuesta.json(),
            {"shippingAddress": {"city": ["Enter your city."]}, "cardLast4": ["Send the last 4 digits of the card."]},
        )
