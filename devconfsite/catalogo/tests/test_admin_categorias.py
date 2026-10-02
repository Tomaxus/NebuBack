from io import StringIO

from django.core.management import call_command

from devconfsite.comun.pruebas import BaseAPITest, CLAVE
from devconfsite.usuarios.models import Usuario

from ..models import Categoria, Producto


class AdminCategoriasTests(BaseAPITest):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_catalog", stdout=StringIO())
        Usuario.objects.create_superuser("admin@nebulab.com", "Nebulab Admin", CLAVE)
        Usuario.objects.create_user("buyer@example.com", "Buyer Test", CLAVE)

    def setUp(self):
        super().setUp()
        self.autenticar("admin@nebulab.com")

    def crear(self, **datos):
        return self.client.post("/api/admin/categories/", {"name": "HomePod", **datos}, format="json")

    def test_solo_admins(self):
        self.client.credentials()
        self.assertEqual(self.client.get("/api/admin/categories/").status_code, 401)
        self.autenticar("buyer@example.com")
        self.assertEqual(self.client.get("/api/admin/categories/").status_code, 403)
        self.assertEqual(self.crear().status_code, 403)

    def test_listar_con_conteo_de_productos(self):
        datos = self.client.get("/api/admin/categories/").json()
        self.assertEqual(set(datos), {"count", "next", "previous", "results"})
        self.assertEqual(datos["count"], 7)
        iphone = datos["results"][0]
        self.assertEqual(list(iphone), ["id", "name", "slug", "productsCount"])
        self.assertEqual(iphone["productsCount"], Producto.objects.filter(category__name="Iphone").count())
        buscados = self.client.get("/api/admin/categories/", {"search": "watch"}).json()["results"]
        self.assertEqual([c["name"] for c in buscados], ["Apple Watch"])

    def test_crear_con_slug_automatico_y_aparece_en_el_catalogo(self):
        respuesta = self.crear(name="  Apple   TV ")
        self.assertEqual(respuesta.status_code, 201)
        self.assertEqual(respuesta.json(), {"id": respuesta.json()["id"], "name": "Apple TV", "slug": "apple-tv", "productsCount": 0})
        self.assertIn("Apple TV", [c["name"] for c in self.client.get("/api/categories/").json()])

    def test_errores_al_crear(self):
        self.assertEqual(self.crear(name="").json(), {"name": ["The category needs a name."]})
        self.assertEqual(self.crear(name="iphone").json(), {"name": ["Another category already uses this name."]})
        self.assertEqual(self.crear(slug="Home Pod").json(), {"slug": ["Use only lowercase letters, numbers and hyphens."]})
        self.assertEqual(self.crear(slug="ipad").json(), {"slug": ["Another category already uses this slug."]})

    def test_renombrar_actualiza_los_productos(self):
        categoria = Categoria.objects.get(name="Accesories")
        respuesta = self.client.patch(f"/api/admin/categories/{categoria.id}/", {"name": "Accessories"}, format="json")
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual((respuesta.json()["name"], respuesta.json()["slug"]), ("Accessories", categoria.slug))
        productos = self.client.get("/api/products/", {"category": "Accessories", "page_size": 50}).json()["results"]
        self.assertTrue(productos and all(p["category"] == "Accessories" for p in productos))
        self.assertEqual(self.client.get("/api/products/", {"search": "accessories"}).json()["count"], len(productos))

    def test_no_se_borra_una_categoria_con_productos(self):
        categoria = Categoria.objects.get(name="Iphone")
        respuesta = self.client.delete(f"/api/admin/categories/{categoria.id}/")
        self.assertEqual(respuesta.status_code, 400)
        self.assertEqual(set(respuesta.json()), {"detail"})
        self.assertTrue(Categoria.objects.filter(pk=categoria.pk).exists())

    def test_borrar_categoria_vacia_y_usarla_en_un_producto(self):
        nueva = self.crear().json()
        producto = {"name": "HomePod mini", "category": "HomePod", "price": 99, "stock": 5, "image": "https://cdn.example.com/homepod.png"}
        self.assertEqual(self.client.post("/api/admin/products/", producto, format="json").status_code, 201)
        self.assertEqual(self.client.get(f"/api/admin/categories/{nueva['id']}/").json()["productsCount"], 1)
        Producto.objects.filter(category_id=nueva["id"]).delete()
        self.assertEqual(self.client.delete(f"/api/admin/categories/{nueva['id']}/").status_code, 204)
        self.assertEqual(self.client.get(f"/api/admin/categories/{nueva['id']}/").status_code, 404)

    def test_put_no_permitido(self):
        categoria = Categoria.objects.first()
        self.assertEqual(self.client.put(f"/api/admin/categories/{categoria.id}/", {"name": "X"}, format="json").status_code, 405)
