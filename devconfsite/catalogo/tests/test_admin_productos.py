from devconfsite.comun.pruebas import TiendaTest

from ..models import Producto


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
