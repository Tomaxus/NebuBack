from devconfsite.comun.pruebas import TiendaTest

from ..models import Producto


def combinacion(storage, color, price, stock, **extra):
    return {"options": [{"name": "Storage", "value": storage}, {"name": "Color", "value": color}], "price": price, "stock": stock, **extra}


class VariantesTests(TiendaTest):
    def setUp(self):
        super().setUp()
        self.iphone = Producto.objects.get(slug="iphone-18-pro-max")
        self.cliente_headers = self.client._credentials
        self.como_admin()

    def guardar_variantes(self, variantes):
        return self.client.patch(f"/api/admin/products/{self.iphone.pk}/", {"variants": variantes}, format="json")

    def como_cliente(self):
        self.client.credentials(**self.cliente_headers)

    def test_crear_variantes_recalcula_precio_y_stock(self):
        respuesta = self.guardar_variantes([
            combinacion("256GB", "Silver", 1199, 3, sku="IP18PM-256-SLV"),
            combinacion("1TB", "Deep Blue", 1599, 0),
        ])
        self.assertEqual(respuesta.status_code, 200, respuesta.json())
        datos = respuesta.json()
        self.assertEqual((datos["price"], datos["stock"], datos["priceMin"], datos["priceMax"]), (1199, 3, 1199, 1599))
        self.assertEqual([v["sku"] for v in datos["variants"]], ["IP18PM-256-SLV", ""])
        self.assertEqual(set(datos["variants"][0]), {"id", "options", "price", "stock", "sku"})
        publico = self.client.get("/api/products/iphone-18-pro-max/").json()
        self.assertEqual(len(publico["variants"]), 2)

    def test_precio_y_stock_enviados_se_ignoran_con_variantes(self):
        respuesta = self.client.patch(
            f"/api/admin/products/{self.iphone.pk}/",
            {"price": 1, "stock": 999, "variants": [combinacion("256GB", "Silver", 1300, 4)]},
            format="json",
        )
        self.assertEqual((respuesta.json()["price"], respuesta.json()["stock"]), (1300, 4))

    def test_reemplazo_total(self):
        ids = [v["id"] for v in self.guardar_variantes([
            combinacion("256GB", "Silver", 1199, 3), combinacion("512GB", "Silver", 1399, 2),
        ]).json()["variants"]]
        datos = self.guardar_variantes([
            {"id": ids[0], **combinacion("256GB", "Silver", 1100, 5)},
            combinacion("2TB", "Deep Blue", 1999, 1),
        ]).json()
        self.assertEqual(datos["variants"][0]["id"], ids[0])
        self.assertNotIn(ids[1], [v["id"] for v in datos["variants"]])
        self.assertEqual((datos["price"], datos["stock"]), (1100, 6))
        sin_variantes = self.client.patch(
            f"/api/admin/products/{self.iphone.pk}/", {"variants": [], "price": 1250, "stock": 7}, format="json"
        ).json()
        self.assertEqual((sin_variantes["variants"], sin_variantes["price"], sin_variantes["stock"]), ([], 1250, 7))

    def test_intercambiar_opciones_entre_variantes(self):
        a, b = self.guardar_variantes([
            combinacion("256GB", "Silver", 1199, 3), combinacion("512GB", "Silver", 1399, 2),
        ]).json()["variants"]
        respuesta = self.guardar_variantes([
            {"id": a["id"], **combinacion("512GB", "Silver", 1199, 3)},
            {"id": b["id"], **combinacion("256GB", "Silver", 1399, 2)},
        ])
        self.assertEqual(respuesta.status_code, 200, respuesta.json())

    def test_validaciones_bajo_variants(self):
        casos = [
            ([combinacion("256GB", "Silver", 1, 1), combinacion("256gb", " silver ", 2, 1)], "another combination already has these options."),
            ([{"options": [{"name": "Storage", "value": "256GB"}], "price": 1, "stock": 1}], "choose exactly one value for every attribute."),
            ([combinacion("9TB", "Silver", 1, 1)], '"9TB" is not a value of Storage.'),
            ([combinacion("256GB", "Silver", -1, 1)], "Enter a price of 0 or more."),
            ([combinacion("256GB", "Silver", 1, 1.5)], "Stock must be a whole number, 0 or more."),
            ([{"id": 999999, **combinacion("256GB", "Silver", 1, 1)}], "this combination does not belong to the product."),
        ]
        for variantes, mensaje in casos:
            respuesta = self.guardar_variantes(variantes)
            self.assertEqual(respuesta.status_code, 400)
            self.assertIn("variants", respuesta.json())
            self.assertTrue(respuesta.json()["variants"][0].endswith(mensaje), respuesta.json())

    def test_producto_sin_atributos_no_admite_variantes(self):
        airpods = Producto.objects.get(slug="airpods-pro-2-gen")
        respuesta = self.client.patch(
            f"/api/admin/products/{airpods.pk}/", {"variants": [{"options": [], "price": 1, "stock": 1}]}, format="json"
        )
        self.assertEqual(respuesta.json(), {"variants": ["This product has no attributes, so it can't have combinations."]})

    def test_cambiar_atributos_sin_actualizar_variantes(self):
        self.guardar_variantes([combinacion("256GB", "Silver", 1199, 3)])
        respuesta = self.client.patch(
            f"/api/admin/products/{self.iphone.pk}/", {"options": [{"name": "Color", "values": ["Silver"]}]}, format="json"
        )
        self.assertEqual(respuesta.json(), {"variants": ["Update the combinations so they match the new attributes."]})

    def test_crear_producto_con_variantes_sin_precio(self):
        respuesta = self.client.post("/api/admin/products/", {
            "name": "iPhone 19", "category": "Iphone", "status": "live", "image": "/a.png",
            "options": [{"name": "Storage", "values": ["128GB", "256GB"]}],
            "variants": [{"options": [{"name": "Storage", "value": "128GB"}], "price": 799, "stock": 2},
                         {"options": [{"name": "Storage", "value": "256GB"}], "price": 899, "stock": 0}],
        }, format="json")
        self.assertEqual(respuesta.status_code, 201, respuesta.json())
        self.assertEqual((respuesta.json()["price"], respuesta.json()["stock"]), (799, 2))
        sin_variantes = self.client.post("/api/admin/products/", {
            "name": "Otro", "category": "Iphone", "image": "/a.png",
        }, format="json")
        self.assertEqual(sin_variantes.json(), {"price": ["Enter a price of 0 or more."], "stock": ["Stock must be a whole number, 0 or more."]})

    def test_carrito_resuelve_variante_y_su_precio(self):
        self.guardar_variantes([combinacion("256GB", "Silver", 1299, 2), combinacion("1TB", "Deep Blue", 1699, 0)])
        self.como_cliente()
        datos = self.agregar({"slug": "iphone-18-pro-max", "options": [{"name": "Color", "value": "silver".title()}, {"name": "Storage", "value": "256GB"}]}).json()
        item = datos["items"][0]
        self.assertEqual((item["price"], item["stock"], datos["subtotal"]), (1299, 2, 1299))
        self.assertIsNotNone(item["variantId"])
        self.assertEqual(self.agregar(combinacion("1TB", "Deep Blue", 0, 0) | {"slug": "iphone-18-pro-max"}).json(), {"detail": "Sold out."})
        self.assertEqual(
            self.agregar({"slug": "iphone-18-pro-max", "options": [{"name": "Storage", "value": "512GB"}, {"name": "Color", "value": "Silver"}]}).json(),
            {"detail": "That combination is not available."},
        )
        self.agregar()
        self.assertEqual(self.agregar().json(), {"detail": "Only 2 left in stock."})
        self.assertEqual(
            self.client.patch(f"/api/cart/items/{item['id']}/", {"quantity": 3}, format="json").json(),
            {"quantity": ["Only 2 left in stock."]},
        )

    def test_checkout_descuenta_y_cancelar_devuelve_a_la_variante(self):
        variantes = self.guardar_variantes([combinacion("256GB", "Silver", 1299, 2), combinacion("512GB", "Silver", 1499, 5)]).json()["variants"]
        self.como_cliente()
        self.agregar()
        self.agregar()
        pedido = self.pagar().json()
        self.assertEqual(pedido["lines"][0]["variantId"], variantes[0]["id"])
        self.assertEqual((pedido["lines"][0]["price"], pedido["subtotal"]), (1299, 2598))
        self.iphone.refresh_from_db()
        self.assertEqual(self.iphone.stock, 5)
        self.assertEqual(self.iphone.variants.get(pk=variantes[0]["id"]).stock, 0)

        self.como_admin()
        self.client.patch(f"/api/admin/orders/{pedido['id']}/", {"status": "cancelled"}, format="json")
        self.iphone.refresh_from_db()
        self.assertEqual((self.iphone.variants.get(pk=variantes[0]["id"]).stock, self.iphone.stock), (2, 7))

    def test_variante_borrada_no_rompe_el_pedido(self):
        variante = self.guardar_variantes([combinacion("256GB", "Silver", 1299, 2)]).json()["variants"][0]
        self.como_cliente()
        self.agregar()
        pedido = self.pagar().json()
        self.como_admin()
        self.guardar_variantes([combinacion("512GB", "Silver", 1499, 1)])
        linea = self.client.get(f"/api/admin/orders/{pedido['id']}/").json()["lines"][0]
        self.assertEqual((linea["variantId"], linea["price"], linea["options"][0]["value"]), (None, 1299, "256GB"))
        self.assertNotEqual(variante["id"], None)

    def test_orden_por_precio_usa_el_minimo(self):
        self.guardar_variantes([combinacion("256GB", "Silver", 9, 1), combinacion("2TB", "Silver", 9999, 1)])
        primero = self.client.get("/api/products/", {"ordering": "price", "page_size": 1}).json()["results"][0]
        self.assertEqual((primero["slug"], primero["price"], primero["priceMax"]), ("iphone-18-pro-max", 9, 9999))
