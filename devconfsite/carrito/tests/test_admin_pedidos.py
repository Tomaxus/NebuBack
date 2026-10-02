from devconfsite.catalogo.models import Producto
from devconfsite.comun.pruebas import TiendaTest


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
