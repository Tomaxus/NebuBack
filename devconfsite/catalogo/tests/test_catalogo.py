from io import StringIO

from django.core.management import call_command
from rest_framework.test import APITestCase

from ..models import Producto


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
