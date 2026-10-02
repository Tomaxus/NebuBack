from devconfsite.catalogo.models import Producto
from devconfsite.comun.pruebas import CLAVE, IPHONE, TiendaTest
from devconfsite.usuarios.models import Usuario


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
        self.assertEqual(set(item), {"id", "slug", "name", "price", "image", "options", "quantity", "variantId", "stock"})
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
