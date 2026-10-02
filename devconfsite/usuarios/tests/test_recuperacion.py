import re
from datetime import timedelta
from unittest import mock

from django.core import mail
from django.utils import timezone

from devconfsite.comun.pruebas import CLAVE, BaseAPITest

from ..models import Usuario


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
