from django.test import Client, override_settings

from devconfsite.catalogo.models import Categoria
from devconfsite.usuarios.models import Usuario
from devconfsite.usuarios.tests import CLAVE, BaseAPITest

from .seguridad import MENSAJE_HTML

PRODUCTO = {
    "name": "Funda de prueba", "category": "Accesories", "price": 49, "stock": 3,
    "image": "https://cdn.example.com/funda.png",
}


class SeguridadTest(BaseAPITest):
    @classmethod
    def setUpTestData(cls):
        Categoria.objects.create(name="Accesories", slug="accesories")
        cls.admin = Usuario.objects.create_superuser("admin@nebulab.com", "Nebulab Admin", CLAVE)


class HTTPSTests(SeguridadTest):
    @override_settings(SECURE_SSL_REDIRECT=True)
    def test_http_redirige_a_https(self):
        respuesta = self.client.get("/api/categories/")
        self.assertEqual(respuesta.status_code, 301)
        self.assertEqual(respuesta["Location"], "https://testserver/api/categories/")

    @override_settings(SECURE_SSL_REDIRECT=True, SECURE_HSTS_SECONDS=31536000, SECURE_HSTS_INCLUDE_SUBDOMAINS=True, SECURE_HSTS_PRELOAD=True)
    def test_https_detras_del_proxy_responde_con_hsts(self):
        respuesta = self.client.get("/api/categories/", HTTP_X_FORWARDED_PROTO="https")
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta["Strict-Transport-Security"], "max-age=31536000; includeSubDomains; preload")


class XSSTests(SeguridadTest):
    def setUp(self):
        super().setUp()
        self.autenticar("admin@nebulab.com")

    def crear_producto(self, **cambios):
        return self.client.post("/api/admin/products/", {**PRODUCTO, **cambios}, format="json")

    def test_rechaza_script_en_la_descripcion(self):
        respuesta = self.crear_producto(description="<script>alert('xss')</script>")
        self.assertEqual(respuesta.status_code, 400)
        self.assertEqual(respuesta.json(), {"description": [MENSAJE_HTML]})

    def test_rechaza_html_anidado_y_eventos(self):
        respuesta = self.crear_producto(options=[{"name": "Color", "values": ['<img src=x onerror="alert(1)">']}])
        self.assertEqual(respuesta.json(), {"options": [MENSAJE_HTML]})
        respuesta = self.client.post("/api/auth/register/", {"name": "<b onmouseover=alert(1)>Ana</b>", "email": "ana@example.com", "password": CLAVE}, format="json")
        self.assertEqual(respuesta.json(), {"name": [MENSAJE_HTML]})

    def test_texto_normal_con_simbolos_se_guarda_igual(self):
        respuesta = self.crear_producto(description="Pantalla < 7 pulgadas & carga > 20 W")
        self.assertEqual(respuesta.status_code, 201)
        self.assertEqual(respuesta.json()["description"], "Pantalla < 7 pulgadas & carga > 20 W")

    def test_la_contrasena_puede_tener_simbolos(self):
        respuesta = self.client.post("/api/auth/register/", {"name": "Ana", "email": "ana@example.com", "password": "<b>Clave-Segura-1</b>"}, format="json")
        self.assertEqual(respuesta.status_code, 201)

    def test_cabeceras_contra_xss(self):
        respuesta = self.client.get("/api/categories/")
        self.assertEqual(respuesta["Content-Type"], "application/json")
        self.assertEqual(respuesta["X-Content-Type-Options"], "nosniff")
        self.assertEqual(respuesta["X-Frame-Options"], "DENY")
        self.assertIn("default-src 'none'", respuesta["Content-Security-Policy"])
        self.assertIn("script-src 'self' https://cdn.jsdelivr.net", self.client.get("/api/docs/")["Content-Security-Policy"])


class CSRFTests(SeguridadTest):
    def test_la_api_no_acepta_la_cookie_de_sesion(self):
        navegador = Client(enforce_csrf_checks=True)
        navegador.force_login(self.admin)
        respuesta = navegador.post("/api/admin/products/", PRODUCTO, content_type="application/json")
        self.assertEqual(respuesta.status_code, 401)

    def test_el_admin_de_django_exige_token_csrf(self):
        navegador = Client(enforce_csrf_checks=True)
        respuesta = navegador.post("/admin/login/", {"username": "admin@nebulab.com", "password": CLAVE})
        self.assertEqual(respuesta.status_code, 403)

    @override_settings(CORS_ALLOWED_ORIGINS=["https://nebulab.digital"])
    def test_cors_solo_para_el_frontend(self):
        preflight = {"HTTP_ACCESS_CONTROL_REQUEST_METHOD": "POST", "HTTP_ACCESS_CONTROL_REQUEST_HEADERS": "authorization,content-type"}
        propio = self.client.options("/api/cart/items/", HTTP_ORIGIN="https://nebulab.digital", **preflight)
        self.assertEqual(propio["Access-Control-Allow-Origin"], "https://nebulab.digital")
        ajeno = self.client.options("/api/cart/items/", HTTP_ORIGIN="https://sitio-malicioso.com", **preflight)
        self.assertNotIn("Access-Control-Allow-Origin", ajeno)
        self.assertNotIn("Access-Control-Allow-Credentials", propio)
