<p align="center">
  <img src=".github/assets/banner.svg" alt="Nebulab: API REST de la tienda de productos Apple" width="100%">
</p>

<p align="center">
  <a href="https://nebuback.onrender.com/api/docs/"><img alt="Swagger" src="https://img.shields.io/badge/Swagger-docs-85EA2D?style=for-the-badge&logo=swagger&logoColor=black"></a>
  <a href="https://nebuback.onrender.com/api/products/"><img alt="Render" src="https://img.shields.io/badge/Render-en%20vivo-46E3B7?style=for-the-badge&logo=render&logoColor=black"></a>
  <a href="https://nebulab-frontend.vercel.app"><img alt="Frontend" src="https://img.shields.io/badge/Frontend-Vercel-000000?style=for-the-badge&logo=vercel&logoColor=white"></a>
</p>

<p align="center">
  <img alt="Python" src="https://img.shields.io/badge/Python-3.13-3776AB?style=flat-square&logo=python&logoColor=white">
  <img alt="Django" src="https://img.shields.io/badge/Django-5.2%20LTS-092E20?style=flat-square&logo=django&logoColor=white">
  <img alt="DRF" src="https://img.shields.io/badge/DRF-3.18-A30000?style=flat-square&logo=django&logoColor=white">
  <img alt="PostgreSQL" src="https://img.shields.io/badge/PostgreSQL-Neon-4169E1?style=flat-square&logo=postgresql&logoColor=white">
  <img alt="JWT" src="https://img.shields.io/badge/Auth-JWT-000000?style=flat-square&logo=jsonwebtokens&logoColor=white">
  <img alt="OpenAPI" src="https://img.shields.io/badge/OpenAPI-3-6BA539?style=flat-square&logo=openapiinitiative&logoColor=white">
  <img alt="Tests" src="https://img.shields.io/badge/tests-54%20passing-2EA44F?style=flat-square">
</p>

<p align="center">
  <b>NebuBack</b> es el backend de <b>Nebulab</b>, una tienda en línea de productos Apple.<br>
  Expone el catálogo, las cuentas, el carrito, los pedidos y el panel de administración<br>
  como una API REST documentada que consume el frontend en Next.js.
</p>

<p align="center">
  <a href="#-inicio-rápido">Inicio rápido</a> ·
  <a href="#-arquitectura">Arquitectura</a> ·
  <a href="#-endpoints">Endpoints</a> ·
  <a href="#-modelo-de-datos">Modelo de datos</a> ·
  <a href="#-despliegue">Despliegue</a> ·
  <a href="#-equipo">Equipo</a>
</p>

---

## ✨ Qué hace

| | |
|---|---|
| 🛍️ **Catálogo** | 7 categorías y 31 productos con opciones (capacidad, color, talla…). Búsqueda sin tildes, filtros, orden y paginación |
| 👤 **Cuentas** | Registro e inicio de sesión de clientes y administradores con **JWT**: tokens que se renuevan y se anulan al cerrar sesión |
| 🛒 **Carrito** | Un carrito por cliente; subtotal, **impuesto del 8 %** y total calculados en el servidor |
| 💳 **Checkout** | Pedido `NB-1001…` en una sola transacción: valida y descuenta stock, guarda la dirección y los 4 últimos dígitos de la tarjeta (el pago es simulado) |
| 🧑‍💼 **Administración** | CRUD de productos, clientes y administradores; pedidos con cinco estados que ajustan el stock |
| 📊 **Dashboard** | Ingresos, pedidos, ticket promedio, series diarias, ventas por estado y categoría, top de productos y stock bajo |
| 📘 **Documentación** | OpenAPI 3 generada del código y Swagger UI para probar cada endpoint desde el navegador |

---

## 🚀 Enlaces

| | URL |
|---|---|
| **API** | https://nebuback.onrender.com/api/ |
| **Swagger UI** | https://nebuback.onrender.com/api/docs/ |
| **Esquema OpenAPI** | https://nebuback.onrender.com/api/schema/ |
| **Frontend** | https://nebulab-frontend.vercel.app |

> [!NOTE]
> El servicio usa el plan gratuito de Render: después de 15 minutos sin uso se duerme y **la primera petición tarda unos 50 segundos**.

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
```

> [!TIP]
> Si dejas `DATABASE_URL` vacía, el proyecto usa SQLite local, útil para probar sin conexión a Neon.

Prepara la base de datos y arranca:

```bash
python manage.py migrate            # crea las tablas
python manage.py seed_catalog       # carga las 7 categorías y los 31 productos
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
| `FRONTEND_URL` | | Base del enlace del correo de recuperación de contraseña |
| `IMPUESTO_TASA` | | Tasa de impuesto (por defecto `0.08`) |
| `AUTH_THROTTLE_RATE` | | Límite de intentos de login y registro (por defecto `10/min`) |

</details>

---

## 🏗️ Arquitectura

```mermaid
flowchart LR
    U(["👤 Navegador"]) --> F["Frontend<br/>Next.js · Vercel"]
    F -- "HTTPS · JSON · JWT" --> A["API REST<br/>Django + DRF · Render"]
    A -- "TLS" --> D[("PostgreSQL<br/>Neon")]
    A -. "OpenAPI 3" .-> S["Swagger UI<br/>/api/docs/"]
```

Frontend y backend son proyectos independientes que se comunican solo por la API. El backend no renderiza vistas de la tienda.

| Capa | Tecnología |
|---|---|
| Lenguaje | Python 3.13 |
| Framework | Django 5.2 LTS · Django REST Framework 3.18 |
| Autenticación | JWT con `djangorestframework-simplejwt` y lista negra de tokens |
| Filtros | `django-filter` y búsqueda sin tildes |
| Formato | `djangorestframework-camel-case`: JSON en camelCase, parámetros en snake_case |
| Documentación | `drf-spectacular`: OpenAPI 3 y Swagger UI |
| Base de datos | PostgreSQL en Neon (`dj-database-url`, TLS) |
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
│   ├── comun.py                Paginación, permisos, fechas UTC y utilidades compartidas
│   ├── middleware.py           Mensajes de la API en inglés
│   ├── usuarios/               Usuario, autenticación JWT, clientes y admins
│   ├── catalogo/               Categoria, Producto, filtros y comando seed_catalog
│   └── carrito/                Carrito, pedidos, dashboard
│       └── servicios.py        Reglas del negocio: carrito, checkout, estados y métricas
├── build.sh                    Build de Render: dependencias, estáticos y migraciones
├── render.yaml                 Definición del servicio en Render
└── requirements.txt            Dependencias con versiones fijas
```

</details>

---

## 🔌 Endpoints

Base: `https://nebuback.onrender.com/api` · 🌐 público · 🔑 con sesión · 🛡️ solo administradores.

<details open>
<summary><b>Autenticación</b></summary>

| Método | Ruta | | Descripción |
|---|---|:---:|---|
| `POST` | `/auth/register/` | 🌐 | Registra un cliente y devuelve la sesión |
| `POST` | `/auth/login/` | 🌐 | Inicia sesión (clientes y admins) |
| `POST` | `/auth/refresh/` | 🌐 | Renueva los tokens |
| `POST` | `/auth/logout/` | 🔑 | Anula el token de renovación |
| `GET` | `/auth/me/` | 🔑 | Usuario actual |
| `POST` | `/auth/password-reset/` | 🌐 | Envía el correo de recuperación |

</details>

<details open>
<summary><b>Catálogo</b></summary>

| Método | Ruta | | Descripción |
|---|---|:---:|---|
| `GET` | `/categories/` | 🌐 | Las 7 categorías |
| `GET` | `/products/` | 🌐 | Productos visibles, con filtros y 9 por página |
| `GET` | `/products/{slug}/` | 🌐 | Detalle de un producto |

</details>

<details open>
<summary><b>Carrito y pedidos</b></summary>

| Método | Ruta | | Descripción |
|---|---|:---:|---|
| `GET` | `/cart/` | 🔑 | Carrito con subtotal, impuesto y total |
| `POST` | `/cart/items/` | 🔑 | Agrega 1 unidad con las opciones elegidas |
| `PATCH` | `/cart/items/{id}/` | 🔑 | Cambia la cantidad (0 elimina) |
| `DELETE` | `/cart/items/{id}/` | 🔑 | Quita una línea |
| `POST` | `/orders/` | 🔑 | Checkout: crea el pedido y descuenta el stock |

</details>

<details>
<summary><b>Administración</b> (17 endpoints)</summary>

| Método | Ruta | | Descripción |
|---|---|:---:|---|
| `GET` `POST` | `/admin/products/` | 🛡️ | Lista (con desactivados) y crea productos |
| `GET` `PATCH` `DELETE` | `/admin/products/{id}/` | 🛡️ | Ve, edita y borra un producto |
| `GET` `POST` | `/admin/customers/` | 🛡️ | Lista clientes con sus estadísticas y crea clientes |
| `GET` `PATCH` `DELETE` | `/admin/customers/{id}/` | 🛡️ | Ve, edita, bloquea y borra un cliente |
| `GET` | `/admin/orders/` | 🛡️ | Pedidos con resumen de ingresos y conteo por estado |
| `GET` `PATCH` | `/admin/orders/{id}/` | 🛡️ | Ve un pedido y cambia su estado |
| `GET` `POST` | `/admin/admins/` | 🛡️ | Lista y crea administradores |
| `DELETE` | `/admin/admins/{id}/` | 🛡️ | Borra un administrador |
| `GET` | `/admin/dashboard/` | 🛡️ | Métricas de 7, 30 o 90 días |

</details>

**31 endpoints en total.** Parámetros, cuerpos y respuestas: en [Swagger](https://nebuback.onrender.com/api/docs/).

<details>
<summary><b>Ejemplo: iniciar sesión y ver el carrito</b></summary>

```bash
API=https://nebuback.onrender.com/api

# 1. Iniciar sesión
curl -X POST $API/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email": "cliente@example.com", "password": "********"}'
# → { "access": "eyJ...", "refresh": "eyJ...", "user": { "id": 5, "name": "Camila", "role": "cliente" } }

# 2. Usar el token
curl $API/cart/ -H "Authorization: Bearer eyJ..."
# → { "items": [], "subtotal": 0, "taxRate": 0.08, "tax": 0, "total": 0 }
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
    USUARIO ||--o{ CARRITO : tiene
    USUARIO |o--o{ USUARIO : crea
    CARRITO ||--o{ ITEM_CARRITO : contiene
    PRODUCTO ||--o{ ITEM_CARRITO : "se agrega como"
    CARRITO |o--o| PEDIDO : "se convierte en"
    USUARIO |o--o{ PEDIDO : realiza
    PEDIDO ||--|{ LINEA_PEDIDO : incluye
    PRODUCTO |o--o{ LINEA_PEDIDO : "se vendió como"

    USUARIO {
        bigint id PK
        varchar email UK
        varchar role "cliente | admin"
        varchar status "active | blocked"
    }
    PRODUCTO {
        bigint id PK
        varchar slug UK
        decimal price
        int stock
        jsonb options
        varchar status "live | disabled"
    }
    PEDIDO {
        bigint id PK
        varchar number UK "NB-1001"
        decimal subtotal
        decimal tax
        decimal total
        varchar status "paid → shipped → delivered"
    }
```

La base de datos garantiza las reglas clave:
- un solo carrito activo por usuario;
- la cantidad de cada línea es de al menos 1;
- el total de cada pedido es exactamente subtotal más impuesto;
- borrar un producto o un cliente **no borra el historial de ventas**, porque cada pedido guarda una copia de lo comprado.

---

## ✅ Pruebas

```bash
DATABASE_URL="sqlite://:memory:" python manage.py test
```

| Área | Tests | Cubre |
|---|:---:|---|
| Catálogo | 11 | Formato, filtros, búsqueda sin tildes, orden, paginación estable, errores 404 |
| Autenticación y usuarios | 18 | Registro, login, renovación y anulación de tokens, límite de intentos, clientes y admins |
| Carrito, pedidos y admin | 25 | Opciones y stock, checkout completo, cliente bloqueado, estados de pedido, dashboard |

Las pruebas usan una base de datos en memoria y nunca tocan la de producción.

---

## ☁️ Despliegue

El servicio se define en [`render.yaml`](render.yaml) y **se despliega solo con cada merge a `main`**:

```text
build:  pip install → collectstatic → migrate
start:  gunicorn devconf.wsgi:application
```

En Render se configuran `DATABASE_URL` y `CORS_ALLOWED_ORIGINS`. `SECRET_KEY` la genera Render y `DEBUG` queda en `False`.

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

<table>
  <tr>
    <td align="center"><b>Tomás Uribe Sánchez</b><br><sub>Backend · API REST</sub></td>
    <td align="center"><b>Iván Mateo González Angulo</b><br><sub>Base de datos · Infraestructura</sub></td>
    <td align="center"><b>Nicolás Rodríguez Acevedo</b><br><sub>Frontend · Next.js</sub></td>
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
