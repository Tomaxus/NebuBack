from io import StringIO

from django.core.cache import cache
from django.core.management import call_command
from rest_framework.test import APITestCase

from devconfsite.usuarios.models import Usuario

CLAVE = "ClaveSegura123!"
ORIGEN = "http://localhost:3000"


class BaseAPITest(APITestCase):
    def setUp(self):
        cache.clear()

    def login(self, email, password=CLAVE, kind=None):
        if kind is None:
            es_admin = Usuario.objects.filter(email=email.lower(), role=Usuario.Role.ADMIN).exists()
            kind = "admin" if es_admin else "customer"
        return self.client.post("/api/auth/login/", {"email": email, "password": password, "kind": kind}, format="json")

    def renovar(self, kind="customer", origen=ORIGEN):
        return self.client.post("/api/auth/refresh/", {"kind": kind}, format="json", HTTP_ORIGIN=origen)

    def salir(self, kind="customer", origen=ORIGEN):
        return self.client.post("/api/auth/logout/", {"kind": kind}, format="json", HTTP_ORIGIN=origen)

    def autenticar(self, email, password=CLAVE):
        respuesta = self.login(email, password)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {respuesta.json()['access']}")
        return respuesta.json()


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
