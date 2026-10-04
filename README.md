<p align="center">
  <img src=".github/assets/banner.svg" alt="Nebulab: API REST de la tienda de productos Apple" width="100%">
</p>

<p align="center">
  <a href="https://www.nebulab.digital"><img alt="Tienda en vivo" src="https://img.shields.io/badge/Tienda-nebulab.digital-000000?style=for-the-badge&logo=vercel&logoColor=white"></a>
  <a href="https://nebuback.onrender.com/api/docs/"><img alt="Swagger" src="https://img.shields.io/badge/Swagger-docs-85EA2D?style=for-the-badge&logo=swagger&logoColor=black"></a>
  <a href="https://nebuback.onrender.com/api/products/"><img alt="API en Render" src="https://img.shields.io/badge/API-en%20vivo-46E3B7?style=for-the-badge&logo=render&logoColor=black"></a>
</p>

<p align="center">
  <img alt="Python" src="https://img.shields.io/badge/Python-3.13-3776AB?style=flat-square&logo=python&logoColor=white">
  <img alt="Django" src="https://img.shields.io/badge/Django-5.2%20LTS-092E20?style=flat-square&logo=django&logoColor=white">
  <img alt="DRF" src="https://img.shields.io/badge/DRF-3.18-A30000?style=flat-square&logo=django&logoColor=white">
  <img alt="PostgreSQL" src="https://img.shields.io/badge/PostgreSQL-Neon-4169E1?style=flat-square&logo=postgresql&logoColor=white">
  <img alt="JWT" src="https://img.shields.io/badge/Auth-JWT-000000?style=flat-square&logo=jsonwebtokens&logoColor=white">
  <img alt="OpenAPI" src="https://img.shields.io/badge/OpenAPI-3-6BA539?style=flat-square&logo=openapiinitiative&logoColor=white">
  <img alt="Resend" src="https://img.shields.io/badge/Correo-Resend-000000?style=flat-square&logo=resend&logoColor=white">
  <img alt="Tests" src="https://img.shields.io/badge/tests-94%20passing-2EA44F?style=flat-square">
</p>

<p align="center">
  <b>NebuBack</b> es el backend de <b>Nebulab</b>, una tienda en línea de productos Apple.<br>
  Expone el catálogo con variantes, las cuentas, el carrito, los pedidos y el panel de administración<br>
  como una API REST documentada que consume el frontend en Next.js.
</p>

<table align="center">
  <tr>
    <td align="center"><h3>37</h3><sub>operaciones REST</sub></td>
    <td align="center"><h3>94</h3><sub>pruebas automáticas</sub></td>
    <td align="center"><h3>9</h3><sub>tablas del dominio</sub></td>
    <td align="center"><h3>3/3</h3><sub>medidas de seguridad<br>(HTTPS · XSS · CSRF)</sub></td>
    <td align="center"><h3>100 %</h3><sub>desplegado y<br>conectado al frontend</sub></td>
  </tr>
</table>

<p align="center">
  <a href="#-pruébala-en-30-segundos">Pruébala</a> ·
  <a href="#-inicio-rápido">Inicio rápido</a> ·
  <a href="#️-arquitectura">Arquitectura</a> ·
  <a href="#-flujos-clave">Flujos</a> ·
  <a href="#-endpoints">Endpoints</a> ·
  <a href="#️-modelo-de-datos">Modelo de datos</a> ·
  <a href="#-seguridad">Seguridad</a> ·
  <a href="#️-estado-del-proyecto">Estado</a> ·
  <a href="#-equipo">Equipo</a>
</p>

---

## ✨ Qué hace

| | |
|---|---|
| 🛍️ **Catálogo** | Categorías administrables y productos con atributos (almacenamiento, color, talla…). Búsqueda sin tildes, filtros, orden y paginación |
| 🎛️ **Variantes** | Cada combinación (por ejemplo, *256GB · Black*) tiene **su propio precio y stock**; el producto muestra el precio "desde" y el stock total |
| 👤 **Cuentas** | Registro e inicio de sesión de clientes y administradores con **JWT**: tokens que rotan en cada renovación y se anulan al cerrar sesión |
| 📧 **Recuperación de contraseña** | Enlace de un solo uso enviado con **Resend** desde `noreply@nebulab.digital`; el token se guarda solo como hash y vence en 1 hora |
| 🛒 **Carrito** | Un carrito por cliente; subtotal, **impuesto del 8 %** y total calculados en el servidor |
| 💳 **Checkout** | Pedido `NB-1001…` en una sola transacción con bloqueo de filas: valida y descuenta el stock de cada variante (el pago es simulado) |
| 🧑‍💼 **Administración** | CRUD de categorías, productos con variantes, clientes y administradores; pedidos con cinco estados que devuelven o descuentan el stock |
| 📊 **Dashboard** | Ingresos, pedidos, ticket promedio, series diarias, ventas por estado y categoría, top de productos y stock bajo |
| 📘 **Documentación** | OpenAPI 3 generada del código y Swagger UI para probar cada endpoint desde el navegador |

---

## 🚀 Enlaces

| | URL |
|---|---|
| 🛍️ **Tienda** | https://www.nebulab.digital |
| 🧑‍💼 **Panel de administración** | https://www.nebulab.digital/login-admin |
| 🔌 **API** | https://nebuback.onrender.com/api/ |
| 📘 **Swagger UI** | https://nebuback.onrender.com/api/docs/ |
| 📄 **Esquema OpenAPI** | https://nebuback.onrender.com/api/schema/ |

> [!NOTE]
> La API usa el plan gratuito de Render: después de 15 minutos sin uso se duerme y **la primera petición tarda cerca de un minuto**. Las siguientes responden al instante.

---

## 🧪 Pruébala en 30 segundos

No necesitas cuenta para el catálogo:

```bash
API=https://nebuback.onrender.com/api

curl "$API/categories/"                                   # las categorías
curl "$API/products/?category=Iphone&ordering=price"      # iPhones del más barato al más caro
curl "$API/products/?search=pro&is_new=true"              # búsqueda + filtro de novedades
curl "$API/products/iphone-17/"                           # detalle con sus variantes
```

<details>
<summary><b>Respuesta de <code>GET /products/iphone-17/</code> (resumida)</b></summary>

```json
{
  "slug": "iphone-17",
  "name": "iPhone 17",
  "category": "Iphone",
  "price": 799.0,
  "priceMin": 799.0,
  "priceMax": 999.0,
  "stock": 144,
  "options": [
    { "name": "Storage", "layout": "stack", "values": ["256GB", "512GB"] },
    { "name": "Color", "layout": "wrap", "values": ["Black", "White", "Mist Blue", "Sage", "Lavender"] }
  ],
  "variants": [
    { "id": 186, "options": [{ "name": "Storage", "value": "256GB" }, { "name": "Color", "value": "Black" }], "price": 799.0, "stock": 23, "sku": "" },
    { "id": 187, "options": [{ "name": "Storage", "value": "256GB" }, { "name": "Color", "value": "White" }], "price": 799.0, "stock": 19, "sku": "" }
  ],
  "isNew": false,
  "recommended": true,
  "status": "live"
}
```

`price` es el precio más bajo de las variantes y `stock` es la suma de todas. El carrito y el checkout usan el precio y el stock de la variante elegida.

</details>

---

## ⚡ Inicio rápido

**Requisitos:** Python 3.13 y Git.

```bash
git clone https://github.com/Tomaxus/NebuBack.git
cd NebuBack

python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Crea un archivo `.env` en la raíz del proyecto:

```env
SECRET_KEY=una-clave-larga-y-aleatoria
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
DATABASE_URL=postgresql://usuario:clave@host/neondb?sslmode=require
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:3001
FRONTEND_URL=http://localhost:3000
```

> [!TIP]
> Si dejas `DATABASE_URL` vacía, el proyecto usa SQLite local. Sin `RESEND_API_KEY`, los correos de recuperación se imprimen en la consola en lugar de enviarse: ideal para desarrollar.

Prepara la base de datos y arranca:

```bash
python manage.py migrate            # crea las tablas
python manage.py seed_catalog       # carga 7 categorías y 31 productos de ejemplo
python manage.py createsuperuser    # crea tu usuario administrador
python manage.py runserver
```

Abre **http://127.0.0.1:8000/api/docs/** y prueba la API.

<details>
<summary><b>Variables de entorno</b></summary>

| Variable | Obligatoria | Descripción |
|---|:---:|---|
| `SECRET_KEY` | ✅ | Clave secreta de Django |
| `DEBUG` | | `True` en desarrollo, `False` en producción |
| `ALLOWED_HOSTS` | | Dominios separados por coma. En Render se agrega el dominio del servicio automáticamente |
| `DATABASE_URL` | | Cadena de conexión de PostgreSQL. Sin ella se usa SQLite |
| `CORS_ALLOWED_ORIGINS` | | Orígenes del frontend autorizados, separados por coma |
| `FRONTEND_URL` | | Base del enlace del correo de recuperación (por defecto `http://localhost:3000`) |
| `RESEND_API_KEY` | | Clave de Resend. Sin ella el correo se envía con el backend de Django (consola) |
| `RESET_PASSWORD_FROM` | | Remitente del correo (por defecto `Nebulab <noreply@nebulab.digital>`) |
| `RESET_TOKEN_MINUTOS` | | Vigencia del enlace de recuperación (por defecto `60`) |
| `IMPUESTO_TASA` | | Tasa de impuesto (por defecto `0.08`) |
| `AUTH_THROTTLE_RATE` | | Límite de intentos de login y registro (por defecto `10/min`) |

</details>

---

## 🏗️ Arquitectura

```mermaid
flowchart LR
    U(["👤 Navegador"]) -- "HTTPS" --> F["Frontend<br/>Next.js · Vercel<br/>www.nebulab.digital"]
    F -- "HTTPS · JSON · Bearer JWT" --> A["API REST<br/>Django + DRF · Gunicorn<br/>Render"]
    A -- "TLS" --> D[("PostgreSQL 18<br/>Neon")]
    A -- "API" --> R["📧 Resend<br/>correo transaccional"]
    A -. "OpenAPI 3" .-> S["Swagger UI<br/>/api/docs/"]
    G["GitHub · main"] -. "deploy automático" .-> A
```

Frontend y backend son proyectos independientes que se comunican solo por la API. El backend no renderiza vistas de la tienda.

| Capa | Tecnología |
|---|---|
| Lenguaje | Python 3.13 |
| Framework | Django 5.2 LTS · Django REST Framework 3.18 |
| Autenticación | JWT con `djangorestframework-simplejwt`, rotación y lista negra de tokens |
| Filtros | `django-filter` y búsqueda sin tildes |
| Formato | `djangorestframework-camel-case`: JSON en camelCase, parámetros en snake_case |
| Documentación | `drf-spectacular`: OpenAPI 3 y Swagger UI |
| Base de datos | PostgreSQL 18 en Neon (`dj-database-url`, TLS) |
| Correo | Resend, con el dominio verificado `nebulab.digital` |
| Servidor | Gunicorn + WhiteNoise para los estáticos |
| Despliegue | Render (Blueprint en `render.yaml`) |

<details>
<summary><b>Estructura del proyecto</b></summary>

```text
NebuBack/
├── devconf/                    Configuración de Django
│   ├── settings.py             Todo se configura por variables de entorno
│   └── urls.py                 /admin/, /api/, /api/docs/, /api/schema/
├── devconfsite/
│   ├── comun/                  Código compartido por las tres apps
│   │   ├── seguridad.py        Rechazo de HTML (XSS) y Content-Security-Policy
│   │   ├── paginacion.py       Paginación y orden estable
│   │   ├── permisos.py         Permiso EsAdmin
│   │   ├── campos.py           Dinero y fechas UTC en los serializers
│   │   ├── limites.py          Límite de intentos de recuperación de contraseña
│   │   ├── texto.py            Slugs y búsqueda sin tildes
│   │   ├── middleware.py       Mensajes de la API en inglés
│   │   ├── pruebas.py          Clases base de los tests
│   │   └── tests/              Tests de HTTPS, XSS y CSRF
│   ├── usuarios/               Usuario, autenticación JWT, clientes y admins
│   │   ├── recuperacion.py     Recuperación de contraseña con Resend
│   │   └── views/              auth.py (público y sesión) · admin.py (panel)
│   ├── catalogo/               Categoria, Producto, Variante, filtros y comando seed_catalog
│   │   ├── variantes.py        Validación de combinaciones
│   │   └── views/              publico.py (tienda) · admin.py (categorías y productos)
│   └── carrito/                Carrito, pedidos y dashboard
│       ├── servicios/          Reglas del negocio: carrito.py · pedidos.py · dashboard.py
│       ├── serializers/        tienda.py · admin.py
│       └── views/              tienda.py (carrito y checkout) · admin.py (pedidos y dashboard)
├── build.sh                    Build de Render: dependencias, estáticos y migraciones
├── render.yaml                 Definición del servicio en Render
└── requirements.txt            Dependencias con versiones fijas
```

Las vistas solo validan y responden; las reglas que tocan varias tablas viven en `servicios/` para poder probarlas por separado.

</details>

---

## 🔄 Flujos clave

### Checkout

Todo ocurre en **una sola transacción**: si algo falla, no se crea el pedido ni se toca el stock.

```mermaid
sequenceDiagram
    autonumber
    actor C as Cliente
    participant F as Frontend
    participant A as API
    participant DB as PostgreSQL
    C->>F: Confirma dirección y tarjeta
    F->>A: POST /api/orders/ {shippingAddress, cardLast4}
    A->>DB: BEGIN · SELECT … FOR UPDATE (carrito, productos, variantes)
    alt Cliente bloqueado, carrito vacío o sin stock
        A-->>F: 400 / 403 con el motivo
    else Todo disponible
        A->>DB: INSERT pedido NB-10xx + líneas (copia de los datos)
        A->>DB: UPDATE stock de cada variante · carrito → converted
        A->>DB: COMMIT
        A-->>F: 201 {number, subtotal, tax, total, lines}
        F-->>C: Confirmación del pedido
    end
```

<details>
<summary><b>Recuperación de contraseña</b></summary>

```mermaid
sequenceDiagram
    autonumber
    actor C as Cliente
    participant F as Frontend
    participant A as API
    participant R as Resend
    C->>F: Escribe su correo
    F->>A: POST /api/auth/password-reset/
    opt La cuenta existe
        A->>A: Token aleatorio · guarda solo su hash SHA-256 (1 h)
        A->>R: Envía el enlace /reset-password?token=…
        R-->>C: Correo desde noreply@nebulab.digital
    end
    A-->>F: 204 siempre (no revela si el correo existe)
    C->>F: Abre el enlace y escribe la contraseña nueva
    F->>A: POST /api/auth/password-reset/confirm/
    A-->>F: 204 · token usado y todas las sesiones cerradas
```

Máximo 3 solicitudes cada 15 minutos por correo y por IP.

</details>

<details>
<summary><b>Ciclo de vida de un pedido</b></summary>

```mermaid
stateDiagram-v2
    state "Vigente · cuenta como ingreso" as Vigente {
        paid --> shipped : enviar
        shipped --> delivered : entregar
    }
    state "Anulado · stock repuesto" as Anulado {
        cancelled
        refunded
    }
    [*] --> paid : checkout · descuenta stock
    Vigente --> Anulado : cancelar o reembolsar · repone stock
    Anulado --> Vigente : reactivar · vuelve a descontar
```

El administrador puede asignar cualquiera de los cinco estados; el stock se ajusta solo al cruzar entre los dos grupos.

</details>

---

## 🔌 Endpoints

Base: `https://nebuback.onrender.com/api` · 🌐 público · 🔑 con sesión · 🛡️ solo administradores.

<details open>
<summary><b>Autenticación</b> (7)</summary>

| Método | Ruta | | Descripción |
|---|---|:---:|---|
| `POST` | `/auth/register/` | 🌐 | Registra un cliente y devuelve la sesión |
| `POST` | `/auth/login/` | 🌐 | Inicia sesión (clientes y admins) |
| `POST` | `/auth/refresh/` | 🌐 | Renueva los tokens |
| `POST` | `/auth/logout/` | 🔑 | Anula el token de renovación |
| `GET` | `/auth/me/` | 🔑 | Usuario actual |
| `POST` | `/auth/password-reset/` | 🌐 | Envía el correo de recuperación |
| `POST` | `/auth/password-reset/confirm/` | 🌐 | Guarda la contraseña nueva con el token del correo |

</details>

<details open>
<summary><b>Catálogo</b> (3)</summary>

| Método | Ruta | | Descripción |
|---|---|:---:|---|
| `GET` | `/categories/` | 🌐 | Todas las categorías |
| `GET` | `/products/` | 🌐 | Productos visibles, con filtros y 9 por página |
| `GET` | `/products/{slug}/` | 🌐 | Detalle de un producto con sus variantes |

</details>

<details open>
<summary><b>Carrito y pedidos</b> (5)</summary>

| Método | Ruta | | Descripción |
|---|---|:---:|---|
| `GET` | `/cart/` | 🔑 | Carrito con subtotal, impuesto y total |
| `POST` | `/cart/items/` | 🔑 | Agrega 1 unidad de la combinación elegida |
| `PATCH` | `/cart/items/{id}/` | 🔑 | Cambia la cantidad (0 elimina) |
| `DELETE` | `/cart/items/{id}/` | 🔑 | Quita una línea |
| `POST` | `/orders/` | 🔑 | Checkout: crea el pedido y descuenta el stock |

</details>

<details>
<summary><b>Administración</b> (22)</summary>

| Método | Ruta | | Descripción |
|---|---|:---:|---|
| `GET` `POST` | `/admin/categories/` | 🛡️ | Lista categorías con su número de productos y crea categorías |
| `GET` `PATCH` `DELETE` | `/admin/categories/{id}/` | 🛡️ | Ve, edita y borra una categoría (solo si no tiene productos) |
| `GET` `POST` | `/admin/products/` | 🛡️ | Lista (con desactivados) y crea productos con sus variantes |
| `GET` `PATCH` `DELETE` | `/admin/products/{id}/` | 🛡️ | Ve, edita y borra un producto |
| `GET` `POST` | `/admin/customers/` | 🛡️ | Lista clientes con sus estadísticas y crea clientes |
| `GET` `PATCH` `DELETE` | `/admin/customers/{id}/` | 🛡️ | Ve, edita, bloquea y borra un cliente |
| `GET` | `/admin/orders/` | 🛡️ | Pedidos con resumen de ingresos y conteo por estado |
| `GET` `PATCH` | `/admin/orders/{id}/` | 🛡️ | Ve un pedido y cambia su estado |
| `GET` `POST` | `/admin/admins/` | 🛡️ | Lista y crea administradores |
| `DELETE` | `/admin/admins/{id}/` | 🛡️ | Borra un administrador |
| `GET` | `/admin/dashboard/` | 🛡️ | Métricas de 7, 30 o 90 días |

</details>

**37 operaciones en total** (8 públicas, 7 con sesión y 22 de administración). Parámetros, cuerpos y respuestas: en [Swagger](https://nebuback.onrender.com/api/docs/).

<details>
<summary><b>Ejemplo: iniciar sesión y agregar al carrito</b></summary>

```bash
API=https://nebuback.onrender.com/api

# 1. Iniciar sesión
curl -X POST $API/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email": "cliente@example.com", "password": "********"}'
# → { "access": "eyJ...", "refresh": "eyJ...", "user": { "id": 5, "name": "Camila", "role": "cliente" } }

# 2. Agregar un iPhone 17 de 256GB en color Sage
curl -X POST $API/cart/items/ \
  -H "Authorization: Bearer eyJ..." -H "Content-Type: application/json" \
  -d '{"slug": "iphone-17", "options": [{"name": "Storage", "value": "256GB"}, {"name": "Color", "value": "Sage"}]}'
# → el carrito completo, con subtotal, impuesto (8 %) y total
```

</details>

### Convenciones de la API

| | |
|---|---|
| **JSON** | Claves en camelCase: `isNew`, `createdAt`, `cardLast4` |
| **Parámetros de URL** | snake_case: `page_size`, `is_new`, `ordering=-created_at` |
| **Rutas** | Siempre con `/` final |
| **Listas** | `{ count, next, previous, results }` con `page` y `page_size` (máximo 100) |
| **Dinero** | Número en USD con 2 decimales |
| **Fechas** | ISO 8601 en UTC |
| **Errores** | `{ "campo": ["mensaje"] }` o `{ "detail": "mensaje" }`, en inglés |
| **Sesión** | Token de acceso de 30 minutos y de renovación de 7 días, que se rota en cada uso |

---

## 🗄️ Modelo de datos

```mermaid
erDiagram
    CATEGORIA ||--o{ PRODUCTO : agrupa
    PRODUCTO ||--o{ VARIANTE : "se ofrece en"
    USUARIO ||--o{ TOKEN_RECUPERACION : solicita
    USUARIO ||--o{ CARRITO : tiene
    USUARIO |o--o{ USUARIO : crea
    CARRITO ||--o{ ITEM_CARRITO : contiene
    PRODUCTO ||--o{ ITEM_CARRITO : "se agrega como"
    VARIANTE |o--o{ ITEM_CARRITO : "se elige en"
    CARRITO |o--o| PEDIDO : "se convierte en"
    USUARIO |o--o{ PEDIDO : realiza
    PEDIDO ||--|{ LINEA_PEDIDO : incluye
    PRODUCTO |o--o{ LINEA_PEDIDO : "se vendió como"
    VARIANTE |o--o{ LINEA_PEDIDO : "se vendió en"

    USUARIO {
        bigint id PK
        varchar email UK
        varchar role "cliente | admin"
        varchar status "active | blocked"
    }
    TOKEN_RECUPERACION {
        bigint id PK
        varchar token_hash UK "SHA-256"
        timestamptz expires_at "1 hora"
        timestamptz used_at
    }
    PRODUCTO {
        bigint id PK
        varchar slug UK
        numeric price "mínimo de variantes"
        int stock "suma de variantes"
        jsonb options "atributos"
        varchar status "live | disabled"
    }
    VARIANTE {
        bigint id PK
        jsonb options "combinación"
        numeric price
        int stock
        varchar sku
    }
    PEDIDO {
        bigint id PK
        varchar number UK "NB-1001"
        numeric subtotal
        numeric tax
        numeric total "subtotal + tax"
        varchar status "5 estados"
    }
```

La base de datos garantiza las reglas clave con restricciones propias:

| Restricción | Regla |
|---|---|
| `precio_no_negativo` · `precio_variante_no_negativo` | Ningún precio puede ser negativo |
| `variante_unica_por_producto` | Una combinación no se repite dentro de un producto |
| `un_carrito_activo_por_usuario` | Un solo carrito activo por cliente |
| `linea_unica_por_opciones` · `cantidad_minima_1` | Sin líneas duplicadas y cantidad de al menos 1 |
| `total_igual_subtotal_mas_impuesto` | El total de un pedido es exactamente subtotal más impuesto |

Borrar un producto, una variante o un cliente **no borra el historial de ventas**: cada pedido guarda una copia de lo comprado.

---

## 🔒 Seguridad

| Medida | Cómo se cumple | Cómo demostrarlo |
|---|---|---|
| **HTTPS** | Render termina TLS; Django redirige todo HTTP a HTTPS (`SECURE_SSL_REDIRECT`), envía HSTS de 1 año con `preload` y marca las cookies como `Secure` | `curl -I http://nebuback.onrender.com/api/categories/` → `301` a `https://`; la respuesta HTTPS trae `Strict-Transport-Security` |
| **XSS** | Todo texto con etiquetas HTML se rechaza antes de guardarse; la API solo responde JSON con `nosniff` y una `Content-Security-Policy: default-src 'none'` | Registrarse con `"name": "<img src=x onerror=alert(1)>"` → `400 {"name": ["HTML tags are not allowed."]}` |
| **CSRF** | La sesión viaja en el encabezado `Authorization: Bearer`, nunca en cookies, así que otro sitio no puede enviar peticiones a nombre del usuario; CORS solo admite los dominios del frontend y no permite credenciales; el admin de Django usa `CsrfViewMiddleware` | Un `POST` sin token responde `401`; un preflight desde un origen ajeno no recibe `Access-Control-Allow-Origin` |

Además: contraseñas con hash PBKDF2 y validadores de Django, tokens JWT con rotación y lista negra, límites de intentos (10/min en login y registro, 3 cada 15 min en recuperación), tokens de recuperación guardados solo como hash y `X-Frame-Options: DENY`. Todos estos casos están automatizados en `devconfsite/comun/tests/` y se verificaron contra producción.

---

## ✅ Pruebas

```bash
DATABASE_URL="sqlite://:memory:" python manage.py test
```

| Área | Tests | Cubre |
|---|:---:|---|
| Autenticación y usuarios | 28 | Registro, login, renovación y anulación de tokens, recuperación de contraseña, límite de intentos, clientes y admins |
| Catálogo | 35 | Formato, filtros, búsqueda sin tildes, paginación, CRUD de categorías y productos, variantes |
| Carrito y pedidos | 21 | Variantes y stock, checkout completo, cliente bloqueado, estados de pedido, dashboard |
| Seguridad | 10 | Redirección a HTTPS y HSTS, rechazo de HTML, cabeceras, sesión que no viaja en cookies, CSRF del admin, CORS |
| **Total** | **94** | **Todas pasan** |

Cada app tiene su carpeta `tests/`, con un archivo por tema. Las pruebas usan una base de datos en memoria y nunca tocan la de producción.

---

## ☁️ Despliegue

| Pieza | Dónde | Cómo se actualiza |
|---|---|---|
| API | Render · `nebuback.onrender.com` | Sola, con cada merge a `main` |
| Base de datos | Neon · PostgreSQL 18 | Migraciones en cada build de Render |
| Correo | Resend · dominio `nebulab.digital` verificado (SPF y DKIM) | — |
| Frontend | Vercel · `www.nebulab.digital` | Repositorio del frontend |

El servicio se define en [`render.yaml`](render.yaml):

```text
build:  pip install → collectstatic → migrate
start:  gunicorn devconf.wsgi:application
```

En Render se configuran `DATABASE_URL`, `CORS_ALLOWED_ORIGINS` y `RESEND_API_KEY`. `SECRET_KEY` la genera Render, `DEBUG` queda en `False` y `FRONTEND_URL` apunta a `https://nebulab.digital`.

---

## 🗺️ Estado del proyecto

| Checkpoint | Semana | Entregable | Estado |
|:---:|:---:|---|:---:|
| 1 | 10 | Definición, planeación y documentación | ✅ |
| 2 | 11 | Modelos, PostgreSQL, API con Swagger y frontend inicial | ✅ |
| 3 | 12 | Integración con el frontend, despliegue, seguridad y catálogo real | ✅ |
| 4 | 13 | Colección de Postman, pruebas de extremo a extremo y estados de carga | 🔄 |
| 5 | 14 | Pruebas del flujo completo desde la interfaz y documentación técnica final | ⏳ |
| 6 | 15 | Cambio de credenciales y revisión final | ⏳ |
| 7 | 16 | Entrega final y sustentación | ⏳ |

---

## 🌿 Flujo de trabajo

```mermaid
gitGraph
    commit id: "inicio"
    branch develop
    checkout develop
    branch feature
    checkout feature
    commit id: "feat: ..."
    checkout develop
    merge feature id: "PR"
    checkout main
    merge develop id: "release → Render"
```

| Rama | Uso |
|---|---|
| `main` | Producción. Render despliega desde aquí |
| `develop` | Integración de las funcionalidades |
| `feature/<tema>` | Una tarea del tablero Kanban; sale de `develop` y vuelve por pull request |

`main` y `develop` están protegidas: solo reciben cambios por pull request. Los commits siguen [Conventional Commits](https://www.conventionalcommits.org/es/) (`feat:`, `fix:`, `docs:`, `chore:`, `refactor:`, `test:`).

---

## 👥 Equipo

<table align="center">
  <tr>
    <td align="center" width="33%"><b>Tomás Uribe Sánchez</b><br><sub>Backend · API REST · Seguridad</sub></td>
    <td align="center" width="33%"><b>Iván Mateo González Angulo</b><br><sub>Base de datos · Infraestructura · Despliegue</sub></td>
    <td align="center" width="33%"><b>Nicolás Rodríguez Acevedo</b><br><sub>Frontend · Next.js · Diseño</sub></td>
  </tr>
</table>

<p align="center">
  Proyecto del curso <b>Desarrollo de Aplicaciones Web</b><br>
  Universidad Pontificia Bolivariana · Seccional Bucaramanga · 2026
</p>

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset=".github/assets/logo-dark.svg">
    <img src=".github/assets/logo-light.svg" alt="Nebulab" width="180">
  </picture>
</p>
