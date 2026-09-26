from io import StringIO

from django.core.management import call_command

from devconfsite.catalogo.models import Producto
from devconfsite.usuarios.models import Usuario
from devconfsite.usuarios.tests import CLAVE, BaseAPITest

from .models import Carrito, Pedido

IPHONE = {"slug": "iphone-18-pro-max", "options": [{"name": "Storage", "value": "256GB"}, {"name": "Color", "value": "Silver"}]}
DIRECCION = {"address": "Calle 10 #20-30", "city": "Bogota", "postalCode": "110111", "country": "Colombia"}


class TiendaTest(BaseAPITest):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_catalog", stdout=StringIO())

    def setUp(self):
        super().setUp()
        self.admin = Usuario.objects.create_superuser("admin@nebulab.com", "Nebulab Admin", CLAVE)
        self.cliente = Usuario.objects.create_user("buyer@example.com", "Buyer Test", CLAVE)
        self.autenticar("buyer@example.com")

    def agregar(self, datos=IPHONE):
        return self.client.post("/api/cart/items/", datos, format="json")

    def pagar(self):
        return self.client.post("/api/orders/", {"shippingAddress": DIRECCION, "cardLast4": "4242"}, format="json")

    def como_admin(self):
        self.client.credentials()
        self.autenticar("admin@nebulab.com")


class CarritoTests(TiendaTest):
    def test_carrito_vacio(self):
        self.assertEqual(
            self.client.get("/api/cart/").json(),
            {"items": [], "subtotal": 0, "taxRate": 0.08, "tax": 0, "total": 0},
        )

    def test_carrito_requiere_login(self):
        self.client.credentials()
        self.assertEqual(self.client.get("/api/cart/").status_code, 401)

    def test_agregar_devuelve_carrito_calculado(self):
        datos = self.agregar().json()
        self.assertEqual((datos["subtotal"], datos["tax"], datos["total"]), (1199, 95.92, 1294.92))
        item = datos["items"][0]
        self.assertEqual(set(item), {"id", "slug", "name", "price", "image", "options", "quantity"})
        self.assertEqual(item["options"], IPHONE["options"])

    def test_mismas_opciones_suman_y_distintas_crean_linea(self):
        self.agregar()
        self.assertEqual(self.agregar().json()["items"][0]["quantity"], 2)
        otra = {**IPHONE, "options": [{"name": "Color", "value": "Silver"}, {"name": "Storage", "value": "512GB"}]}
        self.assertEqual(len(self.agregar(otra).json()["items"]), 2)

    def test_opciones_invalidas(self):
        mensaje = {"options": ["Choose a valid value for every attribute of this product."]}
        for opciones in [[], [{"name": "Storage", "value": "256GB"}], [{"name": "Storage", "value": "9TB"}, {"name": "Color", "value": "Silver"}], IPHONE["options"] + [{"name": "Size", "value": "M"}]]:
            respuesta = self.agregar({**IPHONE, "options": opciones})
            self.assertEqual((respuesta.status_code, respuesta.json()), (400, mensaje))

    def test_producto_sin_opciones_y_producto_no_disponible(self):
        self.assertEqual(self.agregar({"slug": "airpods-pro-2-gen", "options": []}).status_code, 200)
        Producto.objects.filter(slug="airtag").update(status="disabled")
        respuesta = self.agregar({"slug": "airtag", "options": []})
        self.assertEqual(respuesta.json(), {"slug": ["This product is not available."]})

    def test_stock(self):
        Producto.objects.filter(slug="iphone-18-pro-max").update(stock=1)
        self.agregar()
        respuesta = self.agregar()
        self.assertEqual((respuesta.status_code, respuesta.json()), (400, {"quantity": ["Only 1 left in stock."]}))
        item = self.client.get("/api/cart/").json()["items"][0]["id"]
        self.assertEqual(self.client.patch(f"/api/cart/items/{item}/", {"quantity": 3}, format="json").json(), {"quantity": ["Only 1 left in stock."]})

    def test_cambiar_cantidad_y_quitar(self):
        item = self.agregar().json()["items"][0]["id"]
        self.assertEqual(self.client.patch(f"/api/cart/items/{item}/", {"quantity": 3}, format="json").json()["items"][0]["quantity"], 3)
        self.assertEqual(self.client.patch(f"/api/cart/items/{item}/", {"quantity": 0}, format="json").json()["items"], [])
        item = self.agregar().json()["items"][0]["id"]
        self.assertEqual(self.client.delete(f"/api/cart/items/{item}/").json()["items"], [])

    def test_no_se_toca_el_carrito_de_otro(self):
        item = self.agregar().json()["items"][0]["id"]
        Usuario.objects.create_user("otro@example.com", "Otro", CLAVE)
        self.client.credentials()
        self.autenticar("otro@example.com")
        self.assertEqual(self.client.patch(f"/api/cart/items/{item}/", {"quantity": 5}, format="json").status_code, 404)
        self.assertEqual(self.client.delete(f"/api/cart/items/{item}/").status_code, 404)

    def test_precio_copiado_al_agregar(self):
        self.agregar()
        Producto.objects.filter(slug="iphone-18-pro-max").update(price=1500)
        self.assertEqual(self.client.get("/api/cart/").json()["items"][0]["price"], 1199)


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


class AdminPedidosTests(TiendaTest):
    def setUp(self):
        super().setUp()
        self.agregar()
        self.pagar()
        self.agregar({"slug": "airpods-pro-2-gen", "options": []})
        self.pedido_cancelado = self.pagar().json()["id"]
        self.como_admin()
        self.client.patch(f"/api/admin/orders/{self.pedido_cancelado}/", {"status": "cancelled"}, format="json")

    def test_lista_con_summary_y_status_counts(self):
        datos = self.client.get("/api/admin/orders/").json()
        self.assertEqual(list(datos), ["count", "next", "previous", "summary", "statusCounts", "results"])
        self.assertEqual(datos["summary"], {"revenue": 1294.92, "orders": 2, "avgOrder": 1294.92})
        self.assertEqual(datos["statusCounts"], {"all": 2, "paid": 1, "shipped": 0, "delivered": 0, "cancelled": 1, "refunded": 0})
        self.assertEqual(datos["results"][0]["units"], 1)

    def test_filtros_de_pedidos(self):
        datos = self.client.get("/api/admin/orders/", {"status": "cancelled"}).json()
        self.assertEqual((datos["count"], datos["statusCounts"]["all"]), (1, 2))
        self.assertEqual(self.client.get("/api/admin/orders/", {"search": "airpods"}).json()["count"], 1)
        self.assertEqual(self.client.get("/api/admin/orders/", {"customer": self.cliente.pk, "days": 7}).json()["count"], 2)
        self.assertEqual(self.client.get("/api/admin/orders/", {"customer": self.admin.pk}).json()["count"], 0)
        totales = [p["total"] for p in self.client.get("/api/admin/orders/", {"ordering": "total"}).json()["results"]]
        self.assertEqual(totales, sorted(totales))

    def test_estado_invalido(self):
        respuesta = self.client.patch(f"/api/admin/orders/{self.pedido_cancelado}/", {"status": "lost"}, format="json")
        self.assertEqual(respuesta.status_code, 400)

    def test_historial_del_cliente(self):
        cliente = self.client.get("/api/admin/customers/").json()["results"][0]
        self.assertEqual((cliente["ordersCount"], cliente["totalSpent"]), (2, 1294.92))
        self.assertIsNotNone(cliente["lastOrderAt"])

    def test_borrar_producto_vendido_conserva_el_pedido(self):
        producto = Producto.objects.get(slug="iphone-18-pro-max")
        self.assertEqual(self.client.delete(f"/api/admin/products/{producto.pk}/").status_code, 204)
        pedido = [p for p in self.client.get("/api/admin/orders/").json()["results"] if p["id"] != self.pedido_cancelado][0]
        self.assertEqual((pedido["lines"][0]["productId"], pedido["lines"][0]["name"]), (None, "iPhone 18 Pro Max"))

    def test_dashboard(self):
        datos = self.client.get("/api/admin/dashboard/", {"days": 7}).json()
        self.assertEqual(datos["days"], 7)
        self.assertEqual((datos["revenue"], datos["orders"], datos["avgOrder"]), (1294.92, 2, 1294.92))
        self.assertEqual(len(datos["series"]), 7)
        self.assertEqual(sum(p["orders"] for p in datos["series"]), 2)
        self.assertEqual([e["status"] for e in datos["byStatus"]], ["paid", "shipped", "delivered", "cancelled", "refunded"])
        self.assertEqual(datos["byCategory"], [{"category": "Iphone", "revenue": 1199, "units": 1}])
        self.assertEqual(datos["topProducts"][0]["slug"], "iphone-18-pro-max")
        self.assertEqual(datos["revenueDelta"], {"pct": None})
        self.assertEqual(datos["totals"], {"customers": 1, "blocked": 0, "orders": 2})
        self.assertEqual(datos["catalog"]["live"], 31)
        self.assertEqual(len(datos["recent"]), 2)
        self.assertIn("units", datos["recent"][0])


class AdminProductosTests(TiendaTest):
    def setUp(self):
        super().setUp()
        self.como_admin()

    def producto(self, **cambios):
        datos = {
            "name": "iPhone 19 Pro", "slug": "", "category": "Iphone", "status": "live", "price": 1299, "stock": 4,
            "isNew": True, "recommended": False, "description": "", "image": "https://cdn.example.com/iphone-19.png",
            "options": [{"name": "Storage", "values": ["256GB", "512GB"], "layout": "stack"}],
        }
        datos.update(cambios)
        return self.client.post("/api/admin/products/", datos, format="json")

    def test_crear_con_slug_automatico(self):
        respuesta = self.producto()
        self.assertEqual(respuesta.status_code, 201)
        self.assertEqual((respuesta.json()["slug"], respuesta.json()["isNew"]), ("iphone-19-pro", True))

    def test_mensajes_de_validacion(self):
        respuesta = self.producto(
            name="", slug="iphone-18-pro-max", category="Android", price=-1, stock=1.5,
            image="http://inseguro.com/a.png", options=[{"name": "", "values": []}],
        )
        self.assertEqual(
            respuesta.json(),
            {
                "name": ["The product needs a name."],
                "category": ["Choose a valid category."],
                "price": ["Enter a price of 0 or more."],
                "stock": ["Stock must be a whole number, 0 or more."],
                "image": ["Enter an image URL starting with https:// (or a path of this site, like /images/catalog/photo.png)."],
                "options": ["Every attribute needs a name and at least one value."],
            },
        )
        self.assertEqual(self.producto(slug="iphone-18-pro-max").json(), {"slug": ["Another product already uses this slug."]})

    def test_editar_parcial_y_desactivar(self):
        producto = Producto.objects.get(slug="airtag")
        respuesta = self.client.patch(f"/api/admin/products/{producto.pk}/", {"status": "disabled"}, format="json")
        self.assertEqual((respuesta.status_code, respuesta.json()["status"], respuesta.json()["name"]), (200, "disabled", producto.name))
        self.assertEqual(self.client.get("/api/products/airtag/").status_code, 404)

    def test_lista_admin_incluye_desactivados_y_filtros(self):
        Producto.objects.filter(slug="airtag").update(status="disabled", stock=2)
        self.assertEqual(self.client.get("/api/admin/products/").json()["count"], 31)
        self.assertEqual(len(self.client.get("/api/admin/products/").json()["results"]), 10)
        self.assertEqual(self.client.get("/api/admin/products/", {"status": "disabled"}).json()["count"], 1)
        bajos = self.client.get("/api/admin/products/", {"low_stock": "true", "page_size": 100}).json()["results"]
        self.assertTrue(bajos and all(p["stock"] <= 5 for p in bajos))
        self.assertIn("airtag", [p["slug"] for p in bajos])
        categorias = [p["category"] for p in self.client.get("/api/admin/products/", {"ordering": "category", "page_size": 100}).json()["results"]]
        self.assertEqual(categorias, sorted(categorias))
