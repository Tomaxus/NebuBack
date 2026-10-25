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
        self.assertEqual(set(datos), {"access", "user"})
        self.assertTrue(respuesta.cookies["nebulab-refresh-customer"]["httponly"])
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

    def test_registro_no_reclama_cliente_creado_por_admin(self):
        cliente = Usuario.objects.create_user("porreclamar@example.com", "Sin clave", None)
        respuesta = self.client.post("/api/auth/register/", {"name": "Intruso", "email": "porreclamar@example.com", "password": CLAVE}, format="json")
        self.assertEqual(respuesta.status_code, 400)
        cliente.refresh_from_db()
        self.assertFalse(cliente.has_usable_password())
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
        self.login("ana@example.com")
        viejo = self.client.cookies["nebulab-refresh-customer"].value
        nuevo = self.renovar()
        self.assertEqual(nuevo.status_code, 200)
        self.assertEqual(set(nuevo.json()), {"access", "user"})
        self.assertEqual(nuevo.json()["user"]["email"], "ana@example.com")
        self.assertIn("no-store", nuevo["Cache-Control"])
        self.assertNotEqual(self.client.cookies["nebulab-refresh-customer"].value, viejo)
        self.assertEqual(self.salir().status_code, 204)
        self.assertEqual(self.client.cookies["nebulab-refresh-customer"].value, "")
        self.assertEqual(self.renovar().status_code, 401)
        self.assertEqual(self.salir().status_code, 204)

    def test_refresh_viejo_no_se_reutiliza_y_revoca_la_familia(self):
        Usuario.objects.create_user("ana@example.com", "Ana", CLAVE)
        self.login("ana@example.com")
        viejo = self.client.cookies["nebulab-refresh-customer"].value
        self.assertEqual(self.renovar().status_code, 200)
        vigente = self.client.cookies["nebulab-refresh-customer"].value
        self.client.cookies["nebulab-refresh-customer"] = viejo
        self.assertEqual(self.renovar().status_code, 401)
        with self.settings(AUTH_REFRESH_GRACIA_SEGUNDOS=-1):
            self.client.cookies["nebulab-refresh-customer"] = viejo
            self.assertEqual(self.renovar().status_code, 401)
        self.client.cookies["nebulab-refresh-customer"] = vigente
        self.assertEqual(self.renovar().status_code, 401)

    def test_sesiones_de_cliente_y_admin_independientes(self):
        Usuario.objects.create_user("ana@example.com", "Ana", CLAVE)
        Usuario.objects.create_superuser("admin@nebulab.com", "Admin", CLAVE)
        self.login("ana@example.com")
        self.login("admin@nebulab.com")
        self.assertEqual(self.salir("customer").status_code, 204)
        self.assertEqual(self.renovar("customer").status_code, 401)
        respuesta = self.renovar("admin")
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.json()["user"]["role"], "admin")

    def test_login_rechaza_rol_de_otra_sesion(self):
        Usuario.objects.create_user("ana@example.com", "Ana", CLAVE)
        respuesta = self.login("ana@example.com", kind="admin")
        self.assertEqual(respuesta.status_code, 403)
        self.assertNotIn("nebulab-refresh-admin", respuesta.cookies)
        self.login("ana@example.com")
        self.client.cookies["nebulab-refresh-admin"] = self.client.cookies["nebulab-refresh-customer"].value
        self.assertEqual(self.renovar("admin").status_code, 401)

    def test_refresh_y_logout_exigen_origen_permitido(self):
        Usuario.objects.create_user("ana@example.com", "Ana", CLAVE)
        self.login("ana@example.com")
        self.assertEqual(self.renovar(origen="https://malo.example").status_code, 403)
        self.assertEqual(self.client.post("/api/auth/refresh/", {"kind": "customer"}, format="json").status_code, 403)
        self.assertEqual(self.salir(origen="https://malo.example").status_code, 403)
        self.assertEqual(self.renovar().status_code, 200)

    def test_cors_con_credenciales_solo_para_el_frontend(self):
        respuesta = self.client.options(
            "/api/auth/refresh/", HTTP_ORIGIN="http://localhost:3000", HTTP_ACCESS_CONTROL_REQUEST_METHOD="POST"
        )
        self.assertEqual(respuesta["Access-Control-Allow-Origin"], "http://localhost:3000")
        self.assertEqual(respuesta["Access-Control-Allow-Credentials"], "true")
        self.assertIn("origin", respuesta["Vary"].lower())
        otra = self.client.options("/api/auth/refresh/", HTTP_ORIGIN="https://malo.example", HTTP_ACCESS_CONTROL_REQUEST_METHOD="POST")
        self.assertNotIn("Access-Control-Allow-Origin", otra)

    def test_refresh_de_usuario_borrado_o_bloqueado_es_401(self):
        usuario = Usuario.objects.create_user("ana@example.com", "Ana", CLAVE)
        self.login("ana@example.com")
        usuario.delete()
        self.assertEqual(self.renovar().status_code, 401)

    def test_bloquear_cliente_cierra_sus_sesiones(self):
        Usuario.objects.create_superuser("admin@nebulab.com", "Admin", CLAVE)
        cliente = Usuario.objects.create_user("ana@example.com", "Ana", CLAVE)
        self.login("ana@example.com")
        cookie = self.client.cookies["nebulab-refresh-customer"].value
        self.autenticar("admin@nebulab.com")
        self.assertEqual(self.client.patch(f"/api/admin/customers/{cliente.pk}/", {"status": "blocked"}, format="json").status_code, 200)
        self.client.cookies["nebulab-refresh-customer"] = cookie
        self.assertEqual(self.renovar().status_code, 401)

    def test_password_reset_siempre_204(self):
        Usuario.objects.create_user("ana@example.com", "Ana", CLAVE)
        for email in ["ana@example.com", "noexiste@example.com"]:
            self.assertEqual(self.client.post("/api/auth/password-reset/", {"email": email}, format="json").status_code, 204)
        self.assertEqual(len(mail.outbox), 1)

    def test_limite_de_intentos(self):
        codigos = [self.login("x@example.com", "mala").status_code for _ in range(11)]
        self.assertEqual(codigos[-1], 429)
