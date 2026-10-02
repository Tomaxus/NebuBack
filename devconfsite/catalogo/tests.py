from io import StringIO

from django.core.management import call_command
from rest_framework.test import APITestCase

from devconfsite.usuarios.models import Usuario
from devconfsite.usuarios.tests import CLAVE, BaseAPITest

from .models import Categoria, Producto


class CatalogoAPITests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_catalog", stdout=StringIO())
        cls.oculto = Producto.objects.get(slug="magsafe-charger")
        cls.oculto.status = Producto.Status.DISABLED
        cls.oculto.save()
        cls.visibles = Producto.objects.filter(status=Producto.Status.LIVE).count()

    def test_categorias_sin_paginar(self):
        respuesta = self.client.get("/api/categories/")
        self.assertEqual(respuesta.status_code, 200)
        self.assertIsInstance(respuesta.json(), list)
        self.assertEqual(len(respuesta.json()), 7)
        self.assertEqual(respuesta.json()[0], {"id": 1, "name": "Iphone", "slug": "iphone"})

    def test_lista_paginada_de_9_solo_visibles(self):
        datos = self.client.get("/api/products/").json()
        self.assertEqual(set(datos), {"count", "next", "previous", "results"})
        self.assertEqual(datos["count"], self.visibles)
        self.assertEqual(len(datos["results"]), 9)
        self.assertNotIn(self.oculto.slug, [p["slug"] for p in datos["results"]])

    def test_formato_del_producto(self):
        producto = self.client.get("/api/products/iphone-18-pro-max/").json()
        self.assertEqual(
            list(producto),
            ["id", "slug", "name", "category", "price", "image", "isNew", "recommended",
             "options", "variants", "status", "stock", "priceMin", "priceMax", "description", "createdAt", "updatedAt"],
        )
        self.assertEqual(producto["category"], "Iphone")
        self.assertEqual(producto["price"], 1199)
        self.assertIsInstance(producto["price"], (int, float))
        self.assertTrue(producto["createdAt"].endswith("Z"))
        self.assertEqual(producto["options"][0]["name"], "Storage")
        self.assertEqual(producto["options"][0]["layout"], "stack")
        self.assertEqual((producto["variants"], producto["priceMin"], producto["priceMax"]), ([], 1199, 1199))

    def test_detalle_404_si_no_existe_o_esta_desactivado(self):
        for slug in ["no-existe", self.oculto.slug]:
            respuesta = self.client.get(f"/api/products/{slug}/")
            self.assertEqual(respuesta.status_code, 404)
            self.assertEqual(respuesta.json(), {"detail": "Not found."})

    def test_filtro_por_categoria(self):
        datos = self.client.get("/api/products/", {"category": "Apple Watch", "page_size": 50}).json()
        self.assertGreater(datos["count"], 0)
        self.assertTrue(all(p["category"] == "Apple Watch" for p in datos["results"]))

    def test_filtro_novedades_y_recomendados(self):
        nuevos = self.client.get("/api/products/", {"is_new": "true", "page_size": 50}).json()["results"]
        self.assertTrue(nuevos and all(p["isNew"] for p in nuevos))
        recomendados = self.client.get("/api/products/", {"recommended": "true", "page_size": 50}).json()["results"]
        self.assertTrue(recomendados and all(p["recommended"] for p in recomendados))

    def test_busqueda_sin_tildes_ni_mayusculas_y_todas_las_palabras(self):
        hermes = self.client.get("/api/products/", {"search": "HERMES"}).json()["results"]
        self.assertIn("Apple Watch Hermès", [p["name"] for p in hermes])
        air = self.client.get("/api/products/", {"search": "macbook air", "page_size": 50}).json()["results"]
        self.assertTrue(air)
        self.assertTrue(all("air" in p["name"].lower() for p in air))
        por_categoria = self.client.get("/api/products/", {"search": "airpods", "page_size": 50}).json()["count"]
        self.assertEqual(por_categoria, Producto.objects.filter(status="live", category__name="AirPods").count())

    def test_orden_por_precio(self):
        precios = [p["price"] for p in self.client.get("/api/products/", {"ordering": "price", "page_size": 100}).json()["results"]]
        self.assertEqual(precios, sorted(precios))
        precios = [p["price"] for p in self.client.get("/api/products/", {"ordering": "-price", "page_size": 100}).json()["results"]]
        self.assertEqual(precios, sorted(precios, reverse=True))

    def test_paginas_estables_sin_repetidos(self):
        vistos = []
        for pagina in range(1, 5):
            vistos += [p["slug"] for p in self.client.get("/api/products/", {"page": pagina}).json()["results"]]
        self.assertEqual(len(vistos), self.visibles)
        self.assertEqual(len(set(vistos)), self.visibles)

    def test_pagina_fuera_de_rango_y_tope_de_page_size(self):
        respuesta = self.client.get("/api/products/", {"page": 99})
        self.assertEqual(respuesta.status_code, 404)
        self.assertEqual(respuesta.json(), {"detail": "Invalid page."})
        self.assertLessEqual(len(self.client.get("/api/products/", {"page_size": 500}).json()["results"]), 100)

    def test_solo_lectura(self):
        self.assertEqual(self.client.post("/api/products/", {}, format="json").status_code, 405)
        self.assertEqual(self.client.delete("/api/products/iphone-18-pro-max/").status_code, 405)


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
