from django.core import mail

from devconfsite.comun.pruebas import CLAVE, BaseAPITest

from ..models import Usuario


class AuthTests(BaseAPITest):
    def test_registro_devuelve_sesion_y_rol_cliente(self):
        respuesta = self.client.post(
            "/api/auth/register/", {"name": "Camila Rojas", "email": "Camila@Example.com", "password": CLAVE, "role": "admin"}, format="json"
        )
        self.assertEqual(respuesta.status_code, 201)
        datos = respuesta.json()
        self.assertEqual(set(datos), {"access", "refresh", "user"})
        self.assertEqual(datos["user"]["email"], "camila@example.com")
        self.assertEqual(datos["user"]["role"], "cliente")
        self.assertEqual(set(datos["user"]), {"id", "name", "email", "role"})

    def test_registro_email_repetido_y_clave_corta(self):
        Usuario.objects.create_user("camila@example.com", "Camila", CLAVE)
        respuesta = self.client.post("/api/auth/register/", {"name": "Otra", "email": "camila@example.com", "password": CLAVE}, format="json")
        self.assertEqual(respuesta.status_code, 400)
        self.assertEqual(respuesta.json(), {"email": ["An account with this email already exists."]})
        respuesta = self.client.post("/api/auth/register/", {"name": "Otra", "email": "otra@example.com", "password": "123"}, format="json")
        self.assertEqual(respuesta.status_code, 400)
        self.assertIn("password", respuesta.json())

    def test_registro_reclama_cliente_creado_por_admin(self):
        cliente = Usuario.objects.create_user("porreclamar@example.com", "Sin clave", None)
        respuesta = self.client.post("/api/auth/register/", {"name": "Ya con clave", "email": "porreclamar@example.com", "password": CLAVE}, format="json")
        self.assertEqual(respuesta.status_code, 201)
        cliente.refresh_from_db()
        self.assertTrue(cliente.check_password(CLAVE))
        self.assertEqual(Usuario.objects.filter(email="porreclamar@example.com").count(), 1)

    def test_login_y_me(self):
        Usuario.objects.create_user("ana@example.com", "Ana", CLAVE)
        self.assertEqual(self.login("ANA@example.com").status_code, 200)
        self.autenticar("ana@example.com")
        self.assertEqual(self.client.get("/api/auth/me/").json()["name"], "Ana")

    def test_login_incorrecto_mismo_mensaje(self):
        Usuario.objects.create_user("ana@example.com", "Ana", CLAVE)
        for email, clave in [("ana@example.com", "mala"), ("noexiste@example.com", CLAVE)]:
            respuesta = self.login(email, clave)
            self.assertEqual(respuesta.status_code, 401)
            self.assertEqual(respuesta.json(), {"detail": "Wrong email or password."})

    def test_me_sin_token_es_401(self):
        self.assertEqual(self.client.get("/api/auth/me/").status_code, 401)

    def test_refresh_rota_y_logout_invalida(self):
        Usuario.objects.create_user("ana@example.com", "Ana", CLAVE)
        sesion = self.autenticar("ana@example.com")
        nuevo = self.client.post("/api/auth/refresh/", {"refresh": sesion["refresh"]}, format="json")
        self.assertEqual(nuevo.status_code, 200)
        self.assertEqual(set(nuevo.json()), {"access", "refresh"})
        self.assertEqual(self.client.post("/api/auth/refresh/", {"refresh": sesion["refresh"]}, format="json").status_code, 401)
        refresh = nuevo.json()["refresh"]
        self.assertEqual(self.client.post("/api/auth/logout/", {"refresh": refresh}, format="json").status_code, 204)
        self.assertEqual(self.client.post("/api/auth/refresh/", {"refresh": refresh}, format="json").status_code, 401)

    def test_refresh_de_usuario_borrado_es_401(self):
        usuario = Usuario.objects.create_user("ana@example.com", "Ana", CLAVE)
        refresh = self.login("ana@example.com").json()["refresh"]
        usuario.delete()
        respuesta = self.client.post("/api/auth/refresh/", {"refresh": refresh}, format="json")
        self.assertEqual(respuesta.status_code, 401)

    def test_password_reset_siempre_204(self):
        Usuario.objects.create_user("ana@example.com", "Ana", CLAVE)
        for email in ["ana@example.com", "noexiste@example.com"]:
            self.assertEqual(self.client.post("/api/auth/password-reset/", {"email": email}, format="json").status_code, 204)
        self.assertEqual(len(mail.outbox), 1)

    def test_limite_de_intentos(self):
        codigos = [self.login("x@example.com", "mala").status_code for _ in range(11)]
        self.assertEqual(codigos[-1], 429)
