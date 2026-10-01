import re
from datetime import timedelta
from unittest import mock

from django.core import mail
from django.core.cache import cache
from django.utils import timezone
from rest_framework.test import APITestCase

from .models import Usuario

CLAVE = "ClaveSegura123!"


class BaseAPITest(APITestCase):
    def setUp(self):
        cache.clear()

    def login(self, email, password=CLAVE):
        return self.client.post("/api/auth/login/", {"email": email, "password": password}, format="json")

    def autenticar(self, email, password=CLAVE):
        respuesta = self.login(email, password)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {respuesta.json()['access']}")
        return respuesta.json()


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


class AdminUsuariosTests(BaseAPITest):
    def setUp(self):
        super().setUp()
        self.admin = Usuario.objects.create_superuser("admin@nebulab.com", "Nebulab Admin", CLAVE)
        self.cliente = Usuario.objects.create_user("natalia@example.com", "Natalia Ortiz", CLAVE)
        self.autenticar("admin@nebulab.com")

    def test_cliente_no_entra_a_admin(self):
        self.client.credentials()
        self.autenticar("natalia@example.com")
        for url in ["/api/admin/customers/", "/api/admin/admins/", "/api/admin/products/", "/api/admin/orders/", "/api/admin/dashboard/"]:
            self.assertEqual(self.client.get(url).status_code, 403, url)

    def test_listado_de_clientes_con_estadisticas(self):
        datos = self.client.get("/api/admin/customers/").json()
        self.assertEqual(datos["count"], 1)
        cliente = datos["results"][0]
        self.assertEqual(
            set(cliente),
            {"id", "name", "email", "status", "notes", "createdAt", "ordersCount", "totalSpent", "lastOrderAt"},
        )
        self.assertEqual((cliente["ordersCount"], cliente["totalSpent"], cliente["lastOrderAt"]), (0, 0, None))

    def test_crear_editar_bloquear_y_borrar_cliente(self):
        respuesta = self.client.post("/api/admin/customers/", {"name": "Camila", "email": "Camila@Example.com", "notes": "VIP"}, format="json")
        self.assertEqual(respuesta.status_code, 201)
        creado = Usuario.objects.get(email="camila@example.com")
        self.assertFalse(creado.has_usable_password())
        respuesta = self.client.patch(f"/api/admin/customers/{creado.pk}/", {"status": "blocked"}, format="json")
        self.assertEqual(respuesta.json()["status"], "blocked")
        self.assertEqual(self.client.delete(f"/api/admin/customers/{creado.pk}/").status_code, 204)

    def test_errores_de_cliente(self):
        respuesta = self.client.post("/api/admin/customers/", {"name": "", "email": "natalia@example.com"}, format="json")
        self.assertEqual(
            respuesta.json(),
            {"name": ["The customer needs a name."], "email": ["Another customer already uses this email."]},
        )
        respuesta = self.client.post("/api/admin/customers/", {"name": "X", "email": "no-es-email"}, format="json")
        self.assertEqual(respuesta.json(), {"email": ["Enter a valid email address."]})

    def test_buscar_y_filtrar_clientes(self):
        Usuario.objects.create_user("ivan@example.com", "Iván Mateo", CLAVE, status="blocked")
        self.assertEqual(self.client.get("/api/admin/customers/", {"search": "ivan"}).json()["count"], 1)
        self.assertEqual(self.client.get("/api/admin/customers/", {"status": "blocked"}).json()["count"], 1)

    def test_admins_crear_listar_y_reglas_de_borrado(self):
        respuesta = self.client.post("/api/admin/admins/", {"name": "Second Admin", "email": "second@nebulab.com", "password": "secondpass1"}, format="json")
        self.assertEqual(respuesta.status_code, 201)
        segundo = respuesta.json()
        self.assertEqual((segundo["createdBy"], segundo["createdByName"]), (self.admin.pk, "Nebulab Admin"))
        self.assertNotIn("password", segundo)
        lista = self.client.get("/api/admin/admins/").json()
        self.assertEqual(lista["count"], 2)
        primero = [a for a in lista["results"] if a["id"] == self.admin.pk][0]
        self.assertEqual((primero["createdBy"], primero["createdByName"]), (None, None))

        respuesta = self.client.delete(f"/api/admin/admins/{self.admin.pk}/")
        self.assertEqual((respuesta.status_code, respuesta.json()), (400, {"detail": "You cannot delete your own account."}))
        self.assertEqual(self.client.delete(f"/api/admin/admins/{segundo['id']}/").status_code, 204)

    def test_errores_al_crear_admin(self):
        respuesta = self.client.post("/api/admin/admins/", {"name": "", "email": "admin@nebulab.com", "password": "corta"}, format="json")
        self.assertEqual(
            respuesta.json(),
            {
                "name": ["The admin needs a name."],
                "email": ["Another admin already uses this email."],
                "password": ["Use at least 8 characters."],
            },
        )

    def test_borrar_admin_solo_admins(self):
        self.assertEqual(self.client.delete(f"/api/admin/admins/{self.cliente.pk}/").status_code, 404)
        self.assertTrue(Usuario.objects.filter(pk=self.cliente.pk).exists())


class RecuperacionTests(BaseAPITest):
    def setUp(self):
        super().setUp()
        self.usuario = Usuario.objects.create_user("ana@example.com", "Ana", CLAVE)

    def solicitar(self, email="ana@example.com"):
        return self.client.post("/api/auth/password-reset/", {"email": email}, format="json")

    def confirmar(self, token, password="OtraClaveSegura456!"):
        return self.client.post("/api/auth/password-reset/confirm/", {"token": token, "password": password}, format="json")

    def token_del_correo(self):
        return re.search(r"reset-password\?token=([\w-]+)", mail.outbox[-1].body).group(1)

    def test_envia_enlace_y_guarda_solo_el_hash(self):
        self.assertEqual(self.solicitar().status_code, 204)
        self.assertEqual(len(mail.outbox), 1)
        correo = mail.outbox[0]
        self.assertEqual((correo.subject, correo.to), ("Reset your Nebulab password", ["ana@example.com"]))
        token = self.token_del_correo()
        self.assertIn("http://localhost:3000/reset-password?token=", correo.body)
        self.assertIn(token, correo.alternatives[0][0])
        registro = self.usuario.tokens_recuperacion.get()
        self.assertNotEqual(registro.token_hash, token)
        self.assertEqual(len(registro.token_hash), 64)

    def test_email_inexistente_responde_igual(self):
        self.assertEqual(self.solicitar("nadie@example.com").status_code, 204)
        self.assertEqual(len(mail.outbox), 0)

    def test_confirmar_cambia_la_clave_y_el_token_es_de_un_solo_uso(self):
        self.solicitar()
        token = self.token_del_correo()
        self.assertEqual(self.confirmar(token).status_code, 204)
        self.assertEqual(self.login("ana@example.com").status_code, 401)
        self.assertEqual(self.login("ana@example.com", "OtraClaveSegura456!").status_code, 200)
        respuesta = self.confirmar(token)
        self.assertEqual((respuesta.status_code, respuesta.json()), (400, {"detail": "This link is invalid or has expired."}))

    def test_token_invalido_o_vencido(self):
        self.assertEqual(self.confirmar("inventado").json(), {"detail": "This link is invalid or has expired."})
        self.solicitar()
        token = self.token_del_correo()
        self.usuario.tokens_recuperacion.update(expires_at=timezone.now() - timedelta(seconds=1))
        self.assertEqual(self.confirmar(token).json(), {"detail": "This link is invalid or has expired."})

    def test_nueva_solicitud_anula_la_anterior(self):
        self.solicitar()
        primero = self.token_del_correo()
        self.solicitar()
        segundo = self.token_del_correo()
        self.assertEqual(self.confirmar(primero).status_code, 400)
        self.assertEqual(self.confirmar(segundo).status_code, 204)

    def test_clave_debil_no_gasta_el_token(self):
        self.solicitar()
        token = self.token_del_correo()
        respuesta = self.confirmar(token, "123")
        self.assertEqual(respuesta.status_code, 400)
        self.assertIn("password", respuesta.json())
        self.assertGreaterEqual(len(respuesta.json()["password"]), 1)
        self.assertEqual(self.confirmar(token).status_code, 204)

    def test_cierra_las_sesiones_abiertas(self):
        refresh = self.login("ana@example.com").json()["refresh"]
        self.solicitar()
        self.confirmar(self.token_del_correo())
        self.assertEqual(self.client.post("/api/auth/refresh/", {"refresh": refresh}, format="json").status_code, 401)

    def test_limite_de_3_por_email_cada_15_minutos(self):
        codigos = [self.solicitar().status_code for _ in range(4)]
        self.assertEqual(codigos, [204, 204, 204, 429])

    def test_usa_resend_cuando_hay_api_key(self):
        with self.settings(RESEND_API_KEY="re_prueba", FRONTEND_URL="https://nebulab.digital", RESET_PASSWORD_FROM="onboarding@resend.dev"):
            with mock.patch("resend.Emails.send") as enviar:
                self.assertEqual(self.solicitar().status_code, 204)
        datos = enviar.call_args.args[0]
        self.assertEqual((datos["from"], datos["to"], datos["subject"]), ("onboarding@resend.dev", ["ana@example.com"], "Reset your Nebulab password"))
        self.assertIn("https://nebulab.digital/reset-password?token=", datos["html"])
        self.assertEqual(len(mail.outbox), 0)

    def test_si_resend_falla_igual_responde_204(self):
        with self.settings(RESEND_API_KEY="re_prueba"):
            with mock.patch("resend.Emails.send", side_effect=RuntimeError("caído")), self.assertLogs("devconfsite.usuarios.recuperacion", "ERROR"):
                self.assertEqual(self.solicitar().status_code, 204)
