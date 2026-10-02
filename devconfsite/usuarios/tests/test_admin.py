from devconfsite.comun.pruebas import CLAVE, BaseAPITest

from ..models import Usuario


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
