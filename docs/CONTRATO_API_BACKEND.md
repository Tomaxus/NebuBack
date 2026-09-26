# Contrato de API para el backend (Nebulab)

Documento para quien construye el backend (Django + DRF + PostgreSQL). Explica **qué hace hoy el front, con qué datos y en qué formato**, para que la API se adapte a él.

## Cómo leer este documento

- **Del código**: todo lo que no lleva marca. Cada dato cita el archivo de donde sale.
- **SUPUESTO**: lo que yo propongo y el front **no** hace todavía. Es una recomendación, no una restricción del código.
- **DEDUCIDO**: un endpoint que el front aún no llama (usa localStorage), pero que hará falta para reemplazarlo. El nombre de la ruta es propuesto; el comportamiento y los datos sí salen del código.
- Todo el texto visible del front está en **inglés**. Este documento está en español.
- Los ejemplos JSON usan los nombres de campo **del front** (inglés, camelCase). Ver la sección 14 sobre nombres.

> **Idea central**: hoy el front **no hace ninguna petición HTTP**. Todo vive en `localStorage` detrás de un puñado de archivos (`app/lib/cart.ts` y `app/lib/cms/*.ts`). Cada función de esos archivos es un punto que se reemplaza por una llamada a la API. Los componentes no se tocan. Por eso este contrato se puede leer como "lo que cada función del front necesita".

---

## Resumen ejecutivo (léelo primero)

**Estado**: el front está terminado pero **no llama a ninguna API todavía**: todo vive en `localStorage`. Este documento dice qué datos, rutas y formatos necesita el front para conectarse. Los endpoints son **propuestos** (marcados DEDUCIDO); los datos y las reglas salen del código.

**Decisiones ya tomadas** (detalle en la sección 15):
- **El pago es simulado.** El backend solo recibe los 4 últimos dígitos de la tarjeta.
- **El checkout pide dirección de envío** y el envío es gratis.
- **Estados de pedido: los 5 del front** (`paid`, `shipped`, `delivered`, `cancelled`, `refunded`).
- **JWT** con `simplejwt` (access 30 min, refresh 7 días con rotación), guardado en `localStorage` con sesión de cliente y de admin por separado.
- Todas las rutas con **`/` final**, bajo `/api/`; JSON con **las claves del front** (inglés, camelCase); precios como **número**; errores en el formato estándar de DRF.

**Las 6 diferencias grandes con tu diseño** (tabla completa en la sección 14):
1. `Producto` necesita **`slug`** único (la URL, el carrito y los pedidos lo usan).
2. En vez de `storage` y `color` fijos, el front usa una lista **genérica `options`** (Storage, Color, Size, Length, Pack…; y productos sin opciones).
3. Faltan en producto: **`isNew`** (novedad) y **`updatedAt`**.
4. `status` del producto es `"live" | "disabled"` (no un booleano).
5. Los pedidos llevan además: `number` (`NB-1001…`), **`shippingAddress`**, `lines[]` (snapshot), `customerName/Email`, `taxRate`, `cardLast4`, `updatedAt`.
6. Los usuarios necesitan `role` (`cliente|admin`), y los clientes además `status` (`active|blocked`) y `notes`.

**Qué construir** (todas con `/` final; la especificación **exacta** de cada ruta, parámetro, cuerpo y respuesta está en el **Anexo A**):

| Área | Rutas |
|---|---|
| Auth | `POST /api/auth/register/`, `/login/`, `/refresh/`, `/logout/`, `GET /api/auth/me/` |
| Catálogo | `GET /api/products/` (filtros y paginación), `GET /api/products/{slug}/`, `GET /api/categories/` |
| Carrito | `GET /api/cart/`, `POST /api/cart/items/`, `PATCH/DELETE /api/cart/items/{id}/` |
| Pedido | `POST /api/orders/` |
| Admin | `/api/admin/{products,customers,orders,admins}/`, `GET /api/admin/dashboard/` |

**Datos iniciales listos**: la carpeta `backend_fixtures/` del repo del front trae las 7 categorías y los 31 productos en el formato exacto de la API (Anexo C).

**Cómo usar este documento**: empieza por este resumen, sigue con el **Anexo A** (es lo que manda: rutas, parámetros, cuerpos, respuestas y errores), consulta el **Anexo B** (modelos Django sugeridos) y el **Anexo C** (datos iniciales). Las secciones 1–14 explican el porqué y de dónde sale cada dato en el front.

**Más abajo**: la sección 16 lista extras que no pidió tu compañero pero conviene tener en cuenta (seguridad, integridad, rendimiento, herramientas, cambios que hará el front y orden de trabajo sugerido).

---

## 1. Resumen

### Stack del front
Fuente: `package.json`, `next.config.ts`, `app/layout.tsx`.

| Tema | Valor |
|---|---|
| Framework | Next.js **16.3.6** (App Router, Turbopack), React **19.2.8**, TypeScript 5 |
| Estilos | Tailwind CSS 4 (no importa para el backend) |
| Animación | GSAP, Lenis (no importa para el backend) |
| Gestor de paquetes | pnpm |
| Cliente HTTP | **No existe.** No hay `fetch`, `axios`, server actions, route handlers (`route.ts`) ni `middleware`/`proxy`. |
| Variables de entorno | **No existe ninguna** de la app. Solo se lee `process.env.NODE_ENV` (herramienta de desarrollo) en `app/layout.tsx`. |
| URL base de la API | **No existe.** **SUPUESTO**: se creará `NEXT_PUBLIC_API_URL` (ej. `http://localhost:8000/api`). |
| Barra final en rutas | **No aplica todavía.** DRF la exige por defecto (`APPEND_SLASH`). **Decidido**: todas las rutas terminan en `/` (sección 15, #6). |

### Dónde vive hoy el "backend falso"
Cada archivo es un almacén en `localStorage` (creado por `app/lib/cms/store.ts`). Reemplazar por API = reescribir estos archivos.

| Archivo | Clave en localStorage | Qué guarda |
|---|---|---|
| `app/lib/cart.ts` | `nebulab-cart` | Carrito del comprador |
| `app/lib/cms/products.ts` | `nebulab-cms-products-v2` | Catálogo (semilla en `app/data/catalog.ts`) |
| `app/lib/cms/customers.ts` | `nebulab-cms-customers` | Clientes |
| `app/lib/cms/orders.ts` | `nebulab-cms-orders-v2` | Pedidos |
| `app/lib/cms/admin-auth.ts` | `nebulab-cms-admins`, `nebulab-admin-session` | Admins y sesión del admin |
| `app/lib/cms/demo-data.ts` | — | Genera clientes y pedidos falsos (solo demo) |
| `app/lib/cms/metrics.ts` | — | Calcula el dashboard en el navegador |
| `app/lib/cms/types.ts` | — | **Interfaces TypeScript = contrato de datos** |
| `app/data/catalog.ts` | — | Tipo `CatalogProduct`, categorías, semilla de 31 productos, filtro |

### Convenciones de datos que usa el front (`app/lib/cms/types.ts`)
- Fechas: **ISO 8601** (`"2026-09-25T21:44:40.201Z"`).
- Dinero: **número JS** en USD con 2 decimales (no texto).
- IDs: en el **mock** el producto es número y cliente/pedido/admin son texto (`"cus_001"`, `"ord_0001"`, `"adm_001"`). **En la API todos los IDs son enteros** (Anexo A.1); los ejemplos con texto de las secciones 4–12 son del mock.
- Booleanos y `null` reales (no `"true"`, no `""` para vacío).

---

## 2. Páginas

Fuente: carpeta `app/`. Hay dos zonas: la **tienda** y el **CMS/admin**.

### Tienda (pública y de cliente)

La sesión del cliente **no existe todavía**: hoy el "estar logueado" lo decide la **URL** (`app/lib/session-routes.ts`): todo lo que empieza por `/home` es la variante "con sesión" de una página pública, y `/bag` y `/account` cuentan como "con sesión" siempre. **SUPUESTO**: cuando haya JWT, ambas variantes se unifican y la sesión decide.

| Ruta | Archivo | Datos que muestra / envía |
|---|---|---|
| `/` | `app/page.tsx` → `LandingPage` | Carrusel del home con productos `recommended` y `live` (`components/Featured.tsx`). Links a categorías. |
| `/home` | `app/home/page.tsx` | Igual que `/` pero variante con sesión. |
| `/products` | `app/products/page.tsx` → `ProductsCatalog` | Catálogo: lista de productos `live`, filtro por categoría/"new", búsqueda, paginación de 9. Lee `?category=`. |
| `/home/products` | `app/home/products/page.tsx` | Igual, variante con sesión. |
| `/products/[slug]` | `app/products/[slug]/page.tsx` → `ProductDetailLoader` | Producto por **slug**: nombre, precio, descripción, imagen, opciones a elegir, stock. Solo si `status = "live"`; si no existe o está desactivado → 404. |
| `/home/products/[slug]` | `app/home/products/[slug]/page.tsx` | Igual, con sesión (permite añadir al carrito). |
| `/login` | `app/login/page.tsx` → `LoginScreen` | Login / registro / "olvidé mi contraseña". `?mode=signup` abre el registro. **No está conectado a nada.** |
| `/bag` | `app/bag/page.tsx` → `BagCheckout`, `BagPayment` | Carrito + formulario de pago **con dirección de envío**. Crea el pedido al pagar. |
| `/account` | `app/account/page.tsx` → `AccountGreeting` | Solo saludo con el nombre (hoy fijo: `"Iván Mateo"`) y botón "Sign Out" (hoy solo lleva a `/`). |
| `/about`, `/contact` | (no existen) | El Navbar enlaza a ellas (`components/Navbar.tsx`) pero **no hay página** (dan 404). |

### CMS / admin

| Ruta | Archivo | Datos |
|---|---|---|
| `/login-admin` | `app/login-admin/page.tsx` + `LoginScreen` (`variant="admin"`) | Login del admin (email + contraseña). |
| `/admin` | `app/admin/page.tsx` → `components/admin/DashboardView.tsx` | Dashboard con métricas (sección 12). |
| `/admin/products` | `ProductsAdmin.tsx`, `ProductEditor.tsx` | Tabla + formulario de producto. |
| `/admin/customers` | `CustomersAdmin.tsx` | Tabla + formulario de cliente + historial de pedidos. |
| `/admin/orders` | `OrdersAdmin.tsx` | "Sales": pedidos y cambio de estado. |
| `/admin/admins` | `AdminsAdmin.tsx` | Crear/eliminar admins. |

Todo `/admin/*` está protegido en el cliente por `components/admin/AdminShell.tsx`: sin sesión redirige a `/login-admin`. No hay middleware de servidor.

---

## 3. Endpoints que el front necesita

> **La referencia exacta (parámetros, cuerpos, respuestas, códigos) está en el Anexo A.** Esta sección solo lista qué función del front reemplaza cada endpoint.

Ningún endpoint se llama hoy. La tabla lista **DEDUCIDO** lo que haría falta para reemplazar cada función local. Prefijo **SUPUESTO**: `/api/`.

Columna "Login": `—` público, `C` cliente autenticado, `A` admin.

### Autenticación

| Método | Ruta (DEDUCIDA) | Login | Reemplaza / archivo hoy |
|---|---|---|---|
| POST | `/api/auth/register/` | — | Registro. Formulario en `components/login/LoginScreen.tsx` (modo `signup`). No conectado. |
| POST | `/api/auth/login/` | — | Login de cliente. `LoginScreen.tsx` (modo `login`). No conectado. |
| POST | `/api/auth/login/` (mismo o uno propio de admin) | — | Login de admin: `signInAdmin()` en `app/lib/cms/admin-auth.ts`. |
| POST | `/api/auth/refresh/` | — | Renovar el access token (sección 8). No existe en el front todavía. |
| POST | `/api/auth/logout/` | C/A | Cierra sesión y anula el refresh. Hoy `signOutAdmin()` solo borra la sesión local. |
| GET | `/api/auth/me/` | C/A | Usuario actual: nombre en `AccountGreeting.tsx` (hoy fijo) y en `AdminShell.tsx` (`useAdminSession`). |
| POST | `/api/auth/password-reset/` | — | Modo "forgot" de `LoginScreen.tsx` (solo campo email, botón "Send email"). No conectado. |

`signOutAdmin()` (`admin-auth.ts`) solo borra la sesión local; **no llama al servidor**.

### Catálogo (tienda)

| Método | Ruta (DEDUCIDA) | Login | Reemplaza / archivo hoy |
|---|---|---|---|
| GET | `/api/products/` | — | Lista paginada solo `live`. `useLiveProducts()` en `app/lib/cms/products.ts` → `components/ProductsCatalog.tsx`. Filtros en sección 6. |
| GET | `/api/products/?recommended=true` | — | Carrusel del home. `components/Featured.tsx`. |
| GET | `/api/products/{slug}/` | — | Detalle. `components/ProductDetailLoader.tsx`. Solo `live`. |
| GET | `/api/categories/` | — | **Opcional.** Hoy las 7 categorías son una constante (`CATEGORIES` en `app/data/catalog.ts`). |

### Carrito

| Método | Ruta (DEDUCIDA) | Login | Reemplaza / archivo hoy |
|---|---|---|---|
| GET | `/api/cart/` | C | `useCart()` en `app/lib/cart.ts` → `BagCheckout.tsx`. |
| POST | `/api/cart/items/` | C | `addToCart()` (`ProductPurchase.tsx`). |
| PATCH | `/api/cart/items/{id}/` | C | `changeQuantity(id, delta)` (`BagItem.tsx`, botones −/+). |
| DELETE | `/api/cart/items/{id}/` | C | Lo mismo: `changeQuantity` con cantidad que llega a 0 borra la línea. |

### Checkout y pedidos

| Método | Ruta (DEDUCIDA) | Login | Reemplaza / archivo hoy |
|---|---|---|---|
| POST | `/api/orders/` (checkout) | C | `placeOrder()` en `app/lib/cms/orders.ts`, llamado por `BagPayment.tsx`. |

El front **no tiene** pantalla de "mis pedidos" ni de confirmación de pedido.

### Admin

| Método | Ruta (DEDUCIDA) | Login | Reemplaza / archivo hoy |
|---|---|---|---|
| GET | `/api/admin/dashboard/?days=7\|30\|90` | A | `buildDashboard()` en `app/lib/cms/metrics.ts`. |
| GET | `/api/admin/products/` | A | Lista completa (live + disabled). `useProducts()`. |
| POST | `/api/admin/products/` | A | `saveProduct()` sin id. |
| PATCH | `/api/admin/products/{id}/` | A | `saveProduct()` con id; también cambio de status desde la tabla (`setProductStatus`). |
| DELETE | `/api/admin/products/{id}/` | A | `deleteProducts()` (la tabla permite borrar varios a la vez). |
| GET | `/api/admin/customers/` | A | `useCustomers()` + `customerStats()`. |
| POST | `/api/admin/customers/` | A | `saveCustomer()` sin id ("New customer"). |
| PATCH | `/api/admin/customers/{id}/` | A | `saveCustomer()` con id y `setCustomerStatus()`. |
| DELETE | `/api/admin/customers/{id}/` | A | `deleteCustomers()`. |
| GET | `/api/admin/orders/` | A | `useOrders()`. También filtrado por cliente para el historial del cliente. |
| PATCH | `/api/admin/orders/{id}/` | A | `setOrderStatus()` (con efecto sobre el stock, sección 10). |
| GET | `/api/admin/admins/` | A | `useAdmins()`. |
| POST | `/api/admin/admins/` | A | `createAdmin()`. |
| DELETE | `/api/admin/admins/{id}/` | A | `deleteAdmin()`. |

Las acciones masivas del admin (activar/desactivar/borrar varios productos; activar/bloquear/borrar varios clientes) hoy son bucles sobre los endpoints individuales; no habrá endpoint masivo: el front repite la llamada por elemento (sección 15, #20).

---

## 4. Formato exacto de cada entidad

Interfaces copiadas de `app/data/catalog.ts` y `app/lib/cms/types.ts`.

### 4.1 Categoría
No es una entidad en el front: es una **cadena** de una lista fija (`app/data/catalog.ts`).

```ts
export const CATEGORIES = ["Iphone","Macbook","Ipad","AirPods","Apple Watch","Apple Vision Pro","Accesories"] as const;
export type Category = (typeof CATEGORIES)[number];
```

- El front compara por **nombre exacto** (mayúsculas incluidas). Ojo: `"Accesories"` está escrito así (con una sola "c"); tiene que coincidir o se corrige en el front.
- El producto lleva `category: "Iphone"` (nombre), no un id.
- No hay CRUD de categorías en el admin.

```json
{ "category": "Apple Watch" }
```

### 4.2 Producto
Fuente: `CatalogProduct` y `ProductOption` en `app/data/catalog.ts`.

```ts
export interface ProductOption {
  name: string;
  values: string[];
  layout?: "stack" | "wrap";
}
export type ProductStatus = "live" | "disabled";

export interface CatalogProduct {
  id: number;
  slug: string;              // /products/<slug>
  name: string;
  category: Category;
  price: number;
  image: string;
  isNew: boolean;
  recommended: boolean;      // sale en el carrusel del home
  options: ProductOption[];  // [] si no tiene atributos
  status: ProductStatus;
  stock: number;             // por producto, no por variante
  description: string;
  createdAt: string;
  updatedAt: string;
}
```

| Campo | Tipo | Puede venir vacío | Notas |
|---|---|---|---|
| `id` | number | no | |
| `slug` | string | no | Único. Minúsculas, `[a-z0-9-]`. Se usa en la URL, en el carrito y en pedidos. |
| `name` | string | no | |
| `category` | string | no | Una de las 7 categorías. |
| `price` | number | no | USD. Puede tener decimales (el admin permite `step 0.01`). |
| `image` | string | no | **Una sola imagen.** Ver sección 7. |
| `isNew` | boolean | no | Filtro "New" del catálogo. |
| `recommended` | boolean | no | Carrusel del home. |
| `options` | array | sí (`[]`) | Ver sección 7. |
| `status` | `"live"`\|`"disabled"` | no | Solo `live` se ve en la tienda. |
| `stock` | number (entero ≥ 0) | no | 0 = "Sold out". |
| `description` | string | **sí** (`""`) | El admin no la exige. |
| `createdAt`, `updatedAt` | string ISO | no | |

```json
{
  "id": 1,
  "slug": "iphone-18-pro-max",
  "name": "iPhone 18 Pro Max",
  "category": "Iphone",
  "price": 1199,
  "image": "/images/catalog/airpods-pro-2.png",
  "isNew": true,
  "recommended": true,
  "options": [
    { "name": "Storage", "values": ["256GB", "512GB", "1TB", "2TB"], "layout": "stack" },
    { "name": "Color", "values": ["Silver", "Cosmic Orange", "Deep Blue"] }
  ],
  "status": "live",
  "stock": 8,
  "description": "",
  "createdAt": "2026-01-15T12:00:00.000Z",
  "updatedAt": "2026-01-15T12:00:00.000Z"
}
```

Producto sin atributos (`options: []`), por ejemplo AirPods o MagSafe Charger:

```json
{ "id": 4, "slug": "airpods-pro-2-gen", "name": "AirPods Pro 2 Gen", "category": "AirPods", "price": 249, "image": "/images/catalog/airpods-pro-2.png", "isNew": false, "recommended": true, "options": [], "status": "live", "stock": 29, "description": "", "createdAt": "2026-01-15T12:00:00.000Z", "updatedAt": "2026-01-15T12:00:00.000Z" }
```

**Datos semilla**: los 31 productos iniciales están en `app/data/catalog.ts` (constante `byCategory`). Sirven de fixture inicial. Los 5 recomendados de fábrica son (`SEED_RECOMMENDED`): `ipad-pro-13`, `iphone-18-pro-max`, `apple-watch-ultra-3`, `airpods-pro-2-gen`, `macbook-air-13-m4`.

### 4.3 Usuario / Cliente
Fuente: `Customer` en `app/lib/cms/types.ts`.

```ts
export type CustomerStatus = "active" | "blocked";
export interface Customer {
  id: string;
  name: string;
  email: string;        // único, comparado en minúsculas
  status: CustomerStatus;
  notes: string;        // nota interna, solo visible en el CMS
  createdAt: string;
}
```

```json
{ "id": "cus_001", "name": "Natalia Ortiz", "email": "natalia.ortiz16@example.com", "status": "active", "notes": "", "createdAt": "2026-09-14T15:20:00.000Z" }
```

El front **ya no usa** teléfono, país ni ciudad. El registro público solo pide nombre, email y contraseña.

### 4.4 Admin (usuario del CMS)
Fuente: `AdminUser` y `AdminSession` en `types.ts`.

```ts
export interface AdminUser {
  id: string;
  name: string;
  email: string;            // único, minúsculas
  passwordHash: string;     // el backend guarda solo un hash
  createdAt: string;
  createdBy: string | null; // id del admin que lo creó; null = el primero
}
export interface AdminSession {
  id: string; email: string; name: string; signedInAt: string;
}
```

La API **nunca** debe devolver `passwordHash`. Respuesta esperada:

```json
{ "id": "adm_002", "name": "Second Admin", "email": "second@nebulab.com", "createdAt": "2026-09-25T22:10:00.000Z", "createdBy": "adm_001" }
```

No hay roles dentro del admin: todos los admins pueden todo.

### 4.5 Carrito e ítem
Fuente: `CartItem`, `ChosenOption` en `app/lib/cart.ts`.

```ts
export interface ChosenOption { name: string; value: string; }
export interface CartItem {
  id: string;            // slug + valores elegidos: iphone-18-pro-max|256GB|Silver
  slug: string;
  name: string;
  price: number;         // precio unitario
  image: string;
  options: ChosenOption[];
  quantity: number;
}
```

```json
{
  "id": "iphone-18-pro-max|256GB|Silver",
  "slug": "iphone-18-pro-max",
  "name": "iPhone 18 Pro Max",
  "price": 1199,
  "image": "/images/catalog/airpods-pro-2.png",
  "options": [ { "name": "Storage", "value": "256GB" }, { "name": "Color", "value": "Silver" } ],
  "quantity": 1
}
```

- Un mismo producto con **opciones distintas** es **otra línea**. Con las mismas opciones, se suma a la línea existente (`addToCart`, `cart.ts`).
- `id` hoy es una cadena compuesta. Con API, el front solo lo usa como identificador opaco de la línea (`changeQuantity(id, delta)`), así que puede ser el id que ponga el backend.
- Los ítems del carrito son un **snapshot**: nombre, precio e imagen del momento de añadir.

### 4.6 Pedido y línea de pedido
Fuente: `Order`, `OrderLine`, `OrderStatus` en `types.ts`.

```ts
export type OrderStatus = "paid" | "shipped" | "delivered" | "cancelled" | "refunded";

export interface OrderLine {
  productId: number | null;   // null si el producto se borró después
  slug: string;
  name: string;
  category: Category | null;
  image: string;
  price: number;              // precio unitario al comprar
  quantity: number;
  options: ChosenOption[];
}

export interface ShippingAddress {
  address: string;      // calle y número
  city: string;
  postalCode: string;
  country: string;      // los 4 obligatorios, texto libre
}

export interface Order {
  id: string;
  number: string;             // "NB-1042": lo que ve y busca la gente
  customerId: string;
  customerName: string;       // snapshot
  customerEmail: string;      // snapshot
  lines: OrderLine[];
  subtotal: number;
  taxRate: number;            // 0.08
  tax: number;
  total: number;
  status: OrderStatus;
  shippingAddress: ShippingAddress;
  cardLast4: string;          // pago simulado: solo los 4 últimos dígitos, para mostrarlos en el CMS
  createdAt: string;
  updatedAt: string;
}
```

```json
{
  "id": "ord_0137",
  "number": "NB-1137",
  "customerId": "cus_027",
  "customerName": "Buyer Test",
  "customerEmail": "buyer.test@example.com",
  "lines": [
    {
      "productId": 1,
      "slug": "iphone-18-pro-max",
      "name": "iPhone 18 Pro Max",
      "category": "Iphone",
      "image": "/images/catalog/airpods-pro-2.png",
      "price": 1199,
      "quantity": 1,
      "options": [ { "name": "Storage", "value": "256GB" }, { "name": "Color", "value": "Silver" } ]
    }
  ],
  "subtotal": 1199,
  "taxRate": 0.08,
  "tax": 95.92,
  "total": 1294.92,
  "status": "paid",
  "shippingAddress": { "address": "Calle 10 #20-30", "city": "Bogota", "postalCode": "110111", "country": "Colombia" },
  "cardLast4": "4242",
  "createdAt": "2026-09-25T22:41:00.000Z",
  "updatedAt": "2026-09-25T22:41:00.000Z"
}
```

Reglas de numeración: `number` = `"NB-"` + un contador que empieza en **1001** y sube de 1 en 1 (`placeOrder` en `app/lib/cms/orders.ts`).

---

## 5. Cuerpo de cada petición que el front enviaría

Hoy ninguna se envía; estos son los **datos que cada formulario o acción produce**. Los nombres de campo son los del front.

### Registro (`LoginScreen.tsx`, modo signup)
Campos del formulario: **Name**, **Email**, **Password** (sin "repetir contraseña").

```json
{ "name": "Camila Rojas", "email": "camila@example.com", "password": "********" }
```

### Login de cliente (`LoginScreen.tsx`)
```json
{ "email": "camila@example.com", "password": "********" }
```

### Login de admin (`LoginScreen.tsx` variante admin → `signInAdmin`)
El front muestra un único mensaje genérico: `"Wrong email or password."` (no revela cuál falló).
```json
{ "email": "admin@nebulab.com", "password": "********" }
```

### Olvidé mi contraseña (`LoginScreen.tsx`, modo forgot)
```json
{ "email": "camila@example.com" }
```

### Añadir al carrito (`ProductPurchase.tsx` → `addToCart`)
El front hoy pasa `slug, name, price, image` + `options`. **SUPUESTO / recomendación de seguridad**: el backend debe **ignorar** `name`, `price` e `image` que envíe el cliente y tomarlos de la base de datos; solo se necesita:
```json
{ "slug": "iphone-18-pro-max", "options": [ { "name": "Storage", "value": "256GB" }, { "name": "Color", "value": "Silver" } ] }
```
El front **obliga** a elegir todos los atributos del producto antes de poder añadir (botones deshabilitados con el texto "Choose storage and color to add this product to your bag."). Un producto sin atributos envía `"options": []`. Cada llamada suma **1 unidad**.

### Cambiar cantidad (`BagItem.tsx` → `changeQuantity`)
Hoy el front cambia la cantidad en pasos de ±1 (si llega a 0 la línea desaparece). **Decisión**: la API recibe la **cantidad absoluta** (el front calcula `quantity ± 1` y la envía). `0` elimina la línea (o se usa `DELETE`).
```json
{ "quantity": 2 }
```
Si `quantity` supera el stock disponible: `400` con `{ "quantity": ["Only 3 left in stock."] }`.

### Checkout (`BagPayment.tsx` → `placeOrder`)
Campos del formulario, con sus validaciones en el cliente:

| Campo (UI) | Validación en el front |
|---|---|
| Email Address | Formato `algo@algo.algo` |
| Shipping Address (calle y número) | No vacío |
| City | No vacío |
| Postal code | No vacío (texto libre, no se valida el formato por país) |
| Country | No vacío (texto libre) |
| Card Number | 16 dígitos (se muestra con espacios: `4242 4242 4242 4242`; placeholder `XXXX XXXX XXXX XXXX`) |
| Expiry date | `MM/YY`: mes 01–12 y fecha **no vencida** (este mes o posterior) |
| Security code (CVC) | 3 dígitos |
| Card Holder | Texto no vacío |

El botón **Pay** está **deshabilitado** hasta que todos los campos son válidos (no se puede enviar un formulario incompleto). Debajo del botón se muestra el primer problema pendiente (todos en inglés): `"Enter a valid email address."`, `"Enter your shipping address."`, `"Enter your city."`, `"Enter your postal code."`, `"Enter your country."`, `"Enter the 16 digits of your card."`, `"Enter the expiry date as MM/YY."`, `"That expiry date is not valid or the card has expired."`, `"Enter the 3-digit security code."`, `"Enter the name on the card."`. Si el email es de un cliente bloqueado sale además `"This account can't place orders. Contact support."`. El número de tarjeta **no** se valida con Luhn (es ficticio: cualquier número de 16 dígitos sirve).

**Decisión — el pago es simulado.** No hay pasarela, cobro ni validación real. El número completo, la caducidad y el CVC **nunca salen del navegador ni llegan al backend**. Lo único que el backend recibe de la tarjeta son los **4 últimos dígitos**, y solo para mostrarlos en el CMS ("Paid with Card •••• 4242"). Todo pedido nace como `paid`.

Cuerpo del checkout (los ítems los toma el backend del **carrito del usuario autenticado**; el cliente y su email salen del token, no del formulario):
```json
{
  "shippingAddress": {
    "address": "Calle 10 #20-30",
    "city": "Bogota",
    "postalCode": "110111",
    "country": "Colombia"
  },
  "cardLast4": "4242"
}
```

### Formulario de producto (admin, `ProductEditor.tsx`)
Campos: Name, Slug, Category, Status, Price, Stock, New arrival, **Recommended**, Description, Image URL, Attributes.
```json
{
  "name": "iPhone 18 Pro Max",
  "slug": "iphone-18-pro-max",
  "category": "Iphone",
  "status": "live",
  "price": 1199,
  "stock": 8,
  "isNew": true,
  "recommended": false,
  "description": "",
  "image": "https://cdn.ejemplo.com/iphone-18.png",
  "options": [
    { "name": "Storage", "values": ["256GB", "512GB"], "layout": "stack" },
    { "name": "Color", "values": ["Silver", "Deep Blue"], "layout": "wrap" }
  ]
}
```
Validaciones que hace el front (mensajes en inglés):
- Nombre obligatorio: `"The product needs a name."`
- Slug: no vacío y **único**: `"Another product already uses this slug."` El slug se genera solo desde el nombre (minúsculas, sin tildes, guiones) mientras el admin no lo edite a mano.
- Precio ≥ 0: `"Enter a price of 0 or more."`
- Stock entero ≥ 0: `"Stock must be a whole number, 0 or more."`
- Cada atributo necesita nombre y al menos un valor: `"Every attribute needs a name and at least one value."`
- Imagen: `"Enter an image URL starting with https:// (or a path of this site, like /images/catalog/photo.png)."`

Cambio de estado desde la tabla: `{ "status": "disabled" }`.

### Formulario de cliente (admin, `CustomersAdmin.tsx`)
Campos: Name, Email, Internal notes (y el estado Active/Blocked al editar).
```json
{ "name": "Camila Rojas", "email": "camila@example.com", "notes": "" }
```
Cambio de estado: `{ "status": "blocked" }`. Errores del front: `"The customer needs a name."`, `"Enter a valid email address."`, `"Another customer already uses this email."`.

### Cambio de estado de un pedido (admin, `OrdersAdmin.tsx`)
```json
{ "status": "shipped" }
```
Botón principal del detalle: `paid → shipped` ("Mark as shipped") y `shipped → delivered` ("Mark as delivered"). También se puede elegir cualquier estado en el selector.

### Crear admin (`AdminsAdmin.tsx` → `createAdmin`)
Campos: Name, Email, Password, Repeat password (el "repetir" solo se valida en el front, no se envía).
```json
{ "name": "Second Admin", "email": "second@nebulab.com", "password": "secondpass1" }
```
Errores del front: `"The admin needs a name."`, `"Enter a valid email address."`, `"Another admin already uses this email."`, `"Use at least 8 characters."`, `"The passwords do not match."`. La contraseña mínima es de **8 caracteres** (`MIN_PASSWORD` en `admin-auth.ts`).

### Eliminar admin
Sin cuerpo. Reglas que aplica el front (`deleteAdmin`): no se puede eliminar **a uno mismo** (`"You cannot delete your own account."`) ni dejar el sistema sin admins (`"There must be at least one admin."`). Si se elimina a un admin con sesión abierta, esa sesión deja de valer.

---

## 6. Catálogo: filtros, búsqueda, orden y paginación

Fuente: `app/data/catalog.ts` (`filterProducts`, `parseFilter`, `PAGE_SIZE`), `components/ProductsCatalog.tsx`, `CatalogSidebar.tsx`, `CatalogSearch.tsx`, `CatalogPagination.tsx`.

Hoy **todo se filtra y pagina en el navegador** sobre la lista completa de productos `live`. Con la API hay que trasladarlo al servidor.

| Función | Comportamiento actual | Parámetro propuesto (**SUPUESTO**) |
|---|---|---|
| Solo activos | Solo `status = "live"` | (implícito en el endpoint público) |
| Categoría | Una categoría por nombre exacto | `?category=Iphone` |
| Nuevos | Filtro "New": `isNew = true` | `?is_new=true` |
| Solo recomendados | Carrusel del home: `recommended = true` | `?recommended=true` |
| Búsqueda | Texto libre. Se parte en palabras; **todas** deben aparecer en `name` + `category`. Ignora mayúsculas y tildes (`Hermès` = `hermes`). Se filtra en cada tecla. | `?search=macbook air` |
| Tamaño de página | **9** productos (`PAGE_SIZE`) | `?page_size=9` |
| Página | Número de página, empieza en 1; vuelve a 1 al cambiar filtro o búsqueda | `?page=2` |
| Orden | **No hay selector de orden.** La lista sin filtrar sale **intercalada por categoría** (uno de cada categoría por ronda; ver `buildProducts` en `catalog.ts`). | Ninguno usado. Decisión: `-createdAt` por defecto y parámetro `ordering` (sección 15, #13). |

- Valor `all` = sin filtro. `new` es el filtro especial de novedades (no es una categoría).
- El enlace de categorías del home usa `/products?category=Iphone#catalog`; `parseFilter()` acepta el nombre en cualquier capitalización y el alias `watch` = `Apple Watch`.
- Paginación: el front necesita `count` (para calcular `ceil(count / 9)` páginas) y el número de página. **No usa** las URLs `next`/`previous`, pero no molestan.

Respuesta paginada esperada (coincide con lo planeado):

```json
{
  "count": 31,
  "next": "http://localhost:8000/api/products/?page=2&page_size=9",
  "previous": null,
  "results": [ { "id": 1, "slug": "iphone-18-pro-max", "name": "iPhone 18 Pro Max", "category": "Iphone", "price": 1199, "image": "...", "isNew": true, "recommended": true, "options": [], "status": "live", "stock": 8, "description": "", "createdAt": "2026-01-15T12:00:00.000Z", "updatedAt": "2026-01-15T12:00:00.000Z" } ]
}
```

Para el carrusel del home el front necesita **todos** los recomendados (no pagina): usar `?recommended=true` con un `page_size` suficientemente grande, decisión #14 de la sección 15.

Las tablas del admin ordenan y paginan (10 por página) también en el cliente. Columnas ordenables:
- Productos: nombre, estado, slug, categoría, precio, stock, actualizado.
- Clientes: nombre, estado, pedidos, total gastado, último pedido, alta.
- Pedidos: número, fecha, cliente, unidades, total, estado.
- Admins: nombre, creado.

**SUPUESTO**: si el backend pagina esas listas, aceptar `?ordering=-updatedAt`, `?page=`, `?page_size=`, `?search=`. El front tendría que adaptarse (hoy recibe la lista completa).

---

## 7. Variantes de producto (opciones) e imágenes

Fuente: `ProductOption` en `catalog.ts`, `ProductPurchase.tsx`, `ProductEditor.tsx`.

- **Un producto es UNA fila.** Las opciones (color, capacidad, talla…) **no son productos separados**: son una lista `options` dentro del mismo producto.
- Las opciones son **genéricas**, no solo `storage` y `color`. En los datos semilla aparecen: `Storage`, `Color`, `Size`, `Length`, `Pack`. Hay productos con varias, con una sola (`iPhone 17e` solo `Color`) y con ninguna (`AirPods`, `MagSafe Charger`).
- Cada opción: `name` (texto libre), `values` (lista de textos) y `layout` opcional (`"stack"` = un botón por fila, usado en Storage; `"wrap"` por defecto). `layout` es **solo de presentación**.
- Los valores pueden **repetirse** (la semilla de MacBook Neo tiene `"Citrus"` dos veces, tal como está en el diseño). El front elige el botón por **posición**, no por texto.
- **No hay precio ni stock por variante.** El precio y el stock son del producto entero. Cambiar de capacidad no cambia el precio. Se mantiene así (sección 15, #15).
- El comprador **debe elegir todas** las opciones del producto antes de añadir al carrito; lo elegido viaja en `options: [{name, value}]` del ítem del carrito y se guarda en las líneas del pedido.
- Imagen: **una sola** por producto (`image: string`). No hay galería. La foto de la ficha, el catálogo y el carrito usa esa misma imagen.

### Cómo maneja el admin las imágenes
Solo por **URL** (campo "Image URL" de `ProductEditor.tsx`). **Ya no hay subida de archivos.** Acepta:
- Una URL **`https://…`** (cualquier host; `next.config.ts` tiene `remotePatterns: [{ protocol: "https", hostname: "**" }]`).
- O una **ruta del propio sitio** que empiece por `/` (ej. `/images/catalog/airpods-pro-2.png`), que es lo que usa la semilla.
- **No** acepta `http://` (sin s) ni otros esquemas.
- Valor por defecto de un producto nuevo: `/images/catalog/airpods-pro-2.png`.
- Recomendación de formato: imagen apaisada 16:9 con el producto centrado (las tarjetas del catálogo la recortan alrededor del centro).

Consecuencia para Django: el campo de imagen no puede ser un `URLField` estricto si va a aceptar rutas relativas como `/images/...`. Decisión: `CharField` con regex (sección 15, #17).

---

## 8. Autenticación

**Estado real**: el front **no tiene autenticación de cliente**; el admin tiene una autenticación **simulada** en el navegador. Nada llama a un servidor.

### Campos (`LoginScreen.tsx`)
| Modo | Campos |
|---|---|
| Login | `email`, `password` |
| Registro | `name`, `email`, `password` |
| Olvidé contraseña | `email` |
| Login admin | `email`, `password` (sin registro ni "olvidé", solo un enlace "Back to the store") |

### Sesión hoy
- **Cliente**: no hay sesión. "Con sesión" = URL bajo `/home` (`app/lib/session-routes.ts`). El nombre en `/account` es fijo (`"Iván Mateo"`, `AccountGreeting.tsx`).
- **Admin**: `localStorage["nebulab-admin-session"]` = `{ id, email, name, signedInAt }` (`app/lib/cms/admin-auth.ts`). Sin token, sin expiración, sin refresco.
- Contraseñas del admin: hash SHA-256 salado con el email en `nebulab-cms-admins`. Solo es un mock.

### Protección de rutas hoy
- Solo en el **cliente**: `AdminShell.tsx` redirige a `/login-admin` si no hay sesión; `/login-admin` redirige a `/admin` si ya la hay. Sin middleware de Next.
- Los botones "Add to cart" / "Buy now" de un visitante sin sesión llevan a `/login` (`ProductPurchase.tsx`); el carrito y la cuenta también mandan a `/login` desde el Navbar.
- El front separa **admin** y **cliente**: dos logins (`/login`, `/login-admin`) y dos conceptos de datos (`Customer` con `status`/`notes`, `AdminUser` con `createdBy`).

### Cómo manejaría el JWT (**decisión recomendada**)

**Librería**: `djangorestframework-simplejwt`. Login por **email** (modelo de usuario con `USERNAME_FIELD = "email"`).

**Endpoints**

| Método | Ruta | Cuerpo | Respuesta |
|---|---|---|---|
| POST | `/api/auth/register/` | `{ name, email, password }` | Igual que login (queda con la sesión iniciada; el front va directo a `/home`). |
| POST | `/api/auth/login/` | `{ email, password }` | `{ access, refresh, user }` |
| POST | `/api/auth/refresh/` | `{ refresh }` | `{ access, refresh }` (el refresh rota) |
| POST | `/api/auth/logout/` | `{ refresh }` | `204` (mete el refresh en la lista negra) |
| GET | `/api/auth/me/` | — | `user` (necesita `Authorization`) |
| POST | `/api/auth/password-reset/` | `{ email }` | `204` siempre (no revela si el email existe). Prioridad baja: el front no tiene la pantalla de "nueva contraseña". Puede ser un stub que imprime el correo en consola. |

```json
{
  "access": "<jwt de corta duración>",
  "refresh": "<jwt de larga duración>",
  "user": { "id": "adm_001", "name": "Nebulab Admin", "email": "admin@nebulab.com", "role": "admin" }
}
```

**Duración y rotación**: `access` = **30 minutos**; `refresh` = **7 días**, con `ROTATE_REFRESH_TOKENS = True` y `BLACKLIST_AFTER_ROTATION = True` (app `rest_framework_simplejwt.token_blacklist`). Así un refresh robado deja de servir en cuanto se usa el siguiente.

**Dónde guarda el token el front** (decisión): en `localStorage`, con **dos sesiones independientes**, como ya hace hoy el admin:
- `nebulab-session` → `{ access, refresh, user }` del cliente.
- `nebulab-admin-session` → lo mismo para el admin.

Así un admin puede probar la tienda como cliente al mismo tiempo. El cliente HTTP del front elige qué token enviar según la ruta: `/api/admin/*` usa la sesión de admin; el resto, la del cliente. Header: `Authorization: Bearer <access>`.

*Por qué `localStorage` y no cookies `httpOnly`*: front (`:3000`) y API (`:8000`) son **orígenes distintos**; las cookies obligarían a `SameSite`, `CORS_ALLOW_CREDENTIALS` y protección CSRF, más piezas móviles. `localStorage` es más simple y es lo que el front ya usa, **pero es vulnerable a XSS**. Para un proyecto universitario es aceptable. Si algún día va a producción, se pasa el `refresh` a una cookie `httpOnly` (`SameSite=Lax`) puesta por Django y el `access` a memoria; el cambio queda dentro de `app/lib/cms/*.ts`, sin tocar componentes.

**Qué hace el front al expirar la sesión**
1. Una petición devuelve `401` (token vencido).
2. El cliente intenta **un solo** `POST /api/auth/refresh/` (si varias peticiones fallan a la vez, comparten ese intento).
3. Si sale bien, guarda los tokens nuevos y **repite la petición una vez**.
4. Si el refresh falla (vencido, en lista negra, usuario borrado), borra **esa** sesión y redirige: cliente → `/login`, admin → `/login-admin`.
5. Un `403` **no** cierra sesión: significa "no tienes permiso".

**Roles**
- Una sola tabla de usuarios con `role`: `"cliente"` | `"admin"`. El login es el mismo endpoint; el `role` viene en `user`.
- `/login-admin` (front): si el `role` no es `admin`, **no guarda la sesión** y muestra el mismo mensaje genérico `"Wrong email or password."` (no revela que la cuenta existe).
- Backend: **todo** `/api/admin/*` exige `role = "admin"` con una clase de permiso propia (`IsAdminRole`). La verdad de la seguridad está en el backend; el front solo esconde pantallas.
- Un admin puede iniciar sesión también en `/login` y comprar como cliente; el listado de clientes del CMS filtra `role = "cliente"`.

**Reglas de cuenta**
- Contraseña: mínimo **8 caracteres** (validadores de Django); se guarda con el hasher por defecto de Django (PBKDF2). Nunca se devuelve.
- Error de login: `401 { "detail": "Wrong email or password." }`, idéntico si falla el email o la contraseña.
- Email único, comparado en **minúsculas** (normalizar al guardar).
- **Cliente creado por un admin** (el formulario no pide contraseña): se crea con contraseña inutilizable (`set_unusable_password()`). Cuando esa persona se **registra** con ese mismo email, el registro **reclama** la cuenta (define su contraseña) en vez de dar error. Si la cuenta ya tiene contraseña: `400 { "email": ["An account with this email already exists."] }`.
- **Cliente bloqueado** (`status = "blocked"`): puede iniciar sesión y navegar, pero **no puede hacer checkout** (`403 { "detail": "This account can't place orders. Contact support." }`).
- **Admin eliminado**: su refresh deja de funcionar y el front lo saca a `/login-admin`. Su `access` actual sigue válido hasta vencer (máx. 30 min); es aceptable.
- **Rate limit** en login y registro (DRF `ScopedRateThrottle`, p. ej. `10/min` por IP). El front no lo maneja: solo mostraría el `detail` del `429`.

**CORS**: `django-cors-headers` con `CORS_ALLOWED_ORIGINS = ["http://localhost:3000", "http://localhost:3001"]` en desarrollo (y el dominio del front en producción). Permitir el header `Authorization`.

## 9. Carrito

Fuente: `app/lib/cart.ts`, `BagCheckout.tsx`, `BagItem.tsx`, `ProductPurchase.tsx`.

**Hoy**: el carrito vive en el front (`localStorage["nebulab-cart"]`), se guarda en cada acción y se comparte entre pestañas. **Con la API** pasa al backend: **un carrito activo por usuario autenticado**, creado la primera vez que se usa.

Lo que hace el front (y por tanto lo que la API debe soportar):
- **Añadir 1 unidad** de un producto con las opciones elegidas. Mismo producto + mismas opciones → suma a la línea existente; opciones distintas → línea nueva.
- **Cambiar cantidad** (el front envía la cantidad final; `0` elimina la línea).
- **Vaciar**: ocurre solo al pagar (lo hace el checkout).
- **Sin login no se puede usar**: los botones llevan a `/login` (coincide con tu plan de "el carrito requiere login").
- Muestra: por línea foto, nombre, precio unitario, opciones y cantidad; y abajo Subtotal, `Tax (8%)` y Total.
- No hay cupones ni costo de envío (el envío es gratis: ver sección 10).

**Decisiones**
- **Snapshot al añadir** (como en tu plan): nombre, precio e imagen se copian del producto **en el servidor** al añadir. El cliente no puede mandarlos. Si el admin cambia el precio después, el carrito conserva el precio de cuando se añadió (se acepta).
- **Stock**: al añadir o cambiar cantidad se valida `quantity ≤ stock`; si no: `400 { "quantity": ["Only 3 left in stock."] }`. El checkout **vuelve a validar** dentro de la transacción.
- **Producto desactivado o borrado después de añadirlo**: si se borra, la línea desaparece del carrito (FK con cascade). Si solo se desactiva (`disabled`), la línea sigue en el carrito pero **el checkout falla** con `400 { "detail": "Some items are no longer available.", "items": ["<id de línea>"] }`.
- **Los totales los calcula el backend** en cada respuesta.

Respuesta de `GET /api/cart/` (los campos del ítem son los del front; `subtotal`, `taxRate`, `tax`, `total` son números con 2 decimales):

```json
{
  "items": [
    {
      "id": 15,
      "slug": "iphone-18-pro-max",
      "name": "iPhone 18 Pro Max",
      "price": 1199,
      "image": "/images/catalog/airpods-pro-2.png",
      "options": [ { "name": "Storage", "value": "256GB" }, { "name": "Color", "value": "Silver" } ],
      "quantity": 1
    }
  ],
  "subtotal": 1199,
  "taxRate": 0.08,
  "tax": 95.92,
  "total": 1294.92
}
```

Carrito vacío: `"items": []` y totales en `0` (el front muestra "Your bag is empty"). El `id` de línea es el **entero** de la fila del ítem del carrito (el front solo lo devuelve en `PATCH`/`DELETE`). En el mock era un texto compuesto (`iphone-18-pro-max|256GB|Silver`).

Validación de opciones al añadir (el front ya lo impone, pero el backend **debe** repetirlo): el producto debe estar `live`; deben venir **todas** las opciones del producto, cada una con un `value` que exista en `values`; y no puede venir ninguna opción que el producto no tenga.

## 10. Checkout y pedidos

Fuente: `BagPayment.tsx`, `app/lib/cms/orders.ts`, `customers.ts`, `products.ts`.

### Campos del checkout
Email, **dirección de envío** (calle y número, ciudad, código postal, país), número de tarjeta, caducidad, CVC y titular. Detalle y validaciones en la sección 5. **El pago es simulado** (decisión de la sección 5): el backend solo recibe la dirección y los 4 últimos dígitos.

### Envío
- La dirección es **texto libre**: `address`, `city`, `postalCode`, `country` (4 cadenas, todas obligatorias). No se valida por país ni se geolocaliza.
- **No hay costo de envío**: el envío es siempre **gratis** y no aparece en los totales. (El texto de la ficha de producto dice "complimentary shipping on orders over $200", pero es solo texto: no hay umbral ni cálculo.) `total = subtotal + tax`.
- La dirección viaja **dentro del pedido** (`shippingAddress`) como snapshot. El front no guarda direcciones en el perfil del cliente ni ofrece "usar mi dirección anterior".
- El admin la ve en el detalle del pedido, en el bloque "Ship to".

### Qué debe hacer el backend al crear el pedido (**una sola transacción**)
Es lo que hoy hace `placeOrder` en el navegador. En Django: `transaction.atomic()` y `select_for_update()` sobre los productos del carrito.

1. Requiere usuario autenticado con carrito **no vacío** (si está vacío: `400 { "detail": "Your bag is empty." }`; esto también evita pedidos duplicados por doble clic).
2. Rechaza al cliente **bloqueado**: `403 { "detail": "This account can't place orders. Contact support." }`.
3. Verifica que cada producto siga `live` y con stock suficiente; si no, `400` (ver sección 9).
4. Crea el `Order` con `status = "paid"`, los `lines` copiados del carrito (snapshot: `productId`, `slug`, `name`, `category`, `image`, `price`, `quantity`, `options`), `shippingAddress` y `cardLast4`. `customerName` y `customerEmail` son snapshots del usuario autenticado.
5. Calcula `subtotal`, `tax = round2(subtotal × 0.08)` y `total = round2(subtotal + tax)` (mismo redondeo que la sección 11).
6. Asigna `number = "NB-" + (1000 + id)` (el primer pedido es `NB-1001`); se puede generar tras insertar, a partir de la clave primaria, sin condiciones de carrera.
7. **Descuenta el stock** de cada producto por la cantidad comprada.
8. **Vacía el carrito**.
9. Responde `201` con el pedido completo.

### Reglas de stock y estados (`setOrderStatus` en `orders.ts`)
**Decisión: se adoptan los 5 estados del front** (`paid`, `shipped`, `delivered`, `cancelled`, `refunded`); el backend **no** usa `pendiente/completado/cancelado`. Guardarlos como texto con `choices` de esos cinco valores en inglés.

- `paid` → `shipped` → `delivered` es el camino normal. `cancelled` y `refunded` **devuelven el stock** y **dejan de contar como ingreso**.
- Al pasar **a** `cancelled`/`refunded` desde otro estado: `stock += cantidad` de cada línea.
- Al pasar **de** `cancelled`/`refunded` a otro estado: `stock −= cantidad` (mínimo 0).
- Entre estados "normales" no toca el stock.
- Cualquier estado puede pasar a cualquier otro (el admin elige libremente en un selector); no hay máquina de estados estricta. Si prefieres una, avisa al front (hoy permite todos los cambios).
- Ingresos = pedidos en `paid`, `shipped` o `delivered` (`REVENUE_STATUSES` en `types.ts`).
- El cambio de estado y el ajuste de stock van en **la misma transacción**.

### Reglas extra
- Un producto vendido queda **copiado** en la línea del pedido: editar o borrar el producto no cambia pedidos ya hechos. Si el producto se borra, `productId` pasa a `null` (`SET_NULL`) y la línea conserva `slug`, `name`, `price`, etc.
- Borrar un cliente **no borra** sus pedidos: conservan `customerName`/`customerEmail` (`customerId` pasa a `null`).
- No existe "pedido pendiente de pago": el pago es simulado y siempre se da por hecho.

### Qué se muestra al terminar
Solo un **aviso** (toast) `"Order NB-1137 placed"`; los campos del formulario se limpian y el carrito queda vacío ("Your bag is empty"). **No hay pantalla de confirmación** ni redirección. Al front le basta con que la respuesta traiga `number`; conviene devolver el pedido completo.

Respuesta de `POST /api/orders/` (`201`), con la forma de `Order` (sección 4.6):

```json
{
  "id": 137,
  "number": "NB-1137",
  "customerId": 27,
  "customerName": "Buyer Test",
  "customerEmail": "buyer.test@example.com",
  "lines": [
    { "productId": 1, "slug": "iphone-18-pro-max", "name": "iPhone 18 Pro Max", "category": "Iphone", "image": "/images/catalog/airpods-pro-2.png", "price": 1199, "quantity": 1, "options": [ { "name": "Storage", "value": "256GB" } ] }
  ],
  "subtotal": 1199,
  "taxRate": 0.08,
  "tax": 95.92,
  "total": 1294.92,
  "status": "paid",
  "shippingAddress": { "address": "Calle 10 #20-30", "city": "Bogota", "postalCode": "110111", "country": "Colombia" },
  "cardLast4": "4242",
  "createdAt": "2026-09-25T22:41:00.000Z",
  "updatedAt": "2026-09-25T22:41:00.000Z"
}
```

## 11. Precios e impuesto

- **Tipo**: el precio es un **número** en el JSON (`1199`, `39`, `1199.5`), nunca texto. Django REST Framework serializa `DecimalField` como **string** por defecto: hay que configurar `COERCE_DECIMAL_TO_STRING = False` (o un `FloatField`/serializer que devuelva número), o el front tendría que convertir.
- **Moneda**: USD, un único valor, sin campo de moneda.
- **Cálculo del 8 %**: hoy lo calcula **el front** (`TAX_RATE = 0.08`, exportado desde `app/lib/cms/demo-data.ts` y usado en `BagCheckout.tsx`, `BagPayment.tsx`, `orders.ts`). Con la API, **el backend debe calcularlo** y devolver `subtotal`, `taxRate`, `tax` y `total`; el front mostrará lo que reciba.
- **Redondeo**: `tax = Math.round(subtotal * 0.08 * 100) / 100` y `total = Math.round((subtotal + tax) * 100) / 100` (a 2 decimales, "half up"). El backend debe redondear igual (Decimal con `ROUND_HALF_UP`) para no dar centavos distintos.
- **Formato al mostrar** (hay tres, según pantalla):

| Dónde | Formato | Ejemplo | Archivo |
|---|---|---|---|
| Tienda (catálogo, ficha, carrito por línea) | `$` + número tal cual | `$1199` | `CatalogProductCard.tsx`, `ProductOverview.tsx`, `BagItem.tsx` |
| Resumen y botón de pago | `$ ` + `toFixed(2)` | `$ 1620.00` | `BagPayment.tsx` |
| Admin | `Intl.NumberFormat("en-US", currency USD)` | `$1,199.00` | `components/admin/format.ts` |

Como la tienda muestra el precio **sin formato**, un precio con centavos (`1199.5`) se vería `$1199.5`. **Decisión**: por convención los precios del catálogo son **enteros** (`1199`). Si el negocio necesitara centavos, el front pasaría a mostrarlos con 2 decimales; avísale antes de crearlos.

---

## 12. Panel de admin

Existe completo en el front (sección 2). Autenticación y forma de sesión: sección 8.

### Pantallas y sus formularios

| Pantalla | Qué permite | Campos (formulario) |
|---|---|---|
| **Dashboard** `/admin` | Ver métricas por período 7 / 30 / 90 días | Selector de período |
| **Products** `/admin/products` | Buscar, filtrar (estado, categoría, "Low stock"), ordenar, paginar (10), crear, editar, activar/desactivar, borrar (uno o varios) | Name, Slug, Category, Status, Price, Stock, New arrival, Recommended, Description, Image URL, Attributes (nombre + valores + layout) |
| **Customers** `/admin/customers` | Buscar (nombre, email), filtrar por estado, ordenar, crear, editar, bloquear/activar, borrar (uno o varios), ver historial de pedidos | Name, Email, Internal notes, Status |
| **Sales** `/admin/orders` | Buscar (número, cliente, email, producto), filtrar por estado y rango (7 / 30 / 90 días / todo), cambiar estado | Estado |
| **Admins** `/admin/admins` | Listar, crear, eliminar | Name, Email, Password, Repeat password |

### Datos derivados que el admin muestra (hoy los calcula el front)
- En **Customers**: por cliente, `orders` (nº de pedidos), `spent` (suma de `total` de pedidos que cuentan como ingreso) y `lastOrderAt` (`customerStats` en `customers.ts`). **Pídele al backend** esos tres campos ya calculados en el listado de clientes (ej. `ordersCount`, `totalSpent`, `lastOrderAt`).
- En **Sales**: tarjetas de Revenue, Orders y Avg. order del conjunto filtrado, y contadores por estado dentro del rango.

### Dashboard: estructura de datos
El dashboard entero se calcula en `buildDashboard()` (`app/lib/cms/metrics.ts`) sobre TODOS los pedidos, clientes y productos. Con la API conviene un endpoint que devuelva esta forma (interfaz `Dashboard`):

```ts
export interface Dashboard {
  days: 7 | 30 | 90;
  revenue: number;          // suma de total de pedidos paid/shipped/delivered del período
  orders: number;           // pedidos del período (todos los estados)
  avgOrder: number;         // revenue / nº de pedidos que cuentan como ingreso
  newCustomers: number;     // clientes creados en el período
  revenueDelta: { pct: number | null };   // cambio vs período anterior (0.12 = +12 %), null si el anterior fue 0
  ordersDelta: { pct: number | null };
  avgOrderDelta: { pct: number | null };
  customersDelta: { pct: number | null };
  series: { date: string; revenue: number; orders: number }[]; // un punto POR DÍA, "YYYY-MM-DD", incluye días en 0
  byStatus: { status: OrderStatus; count: number }[];          // los 5 estados, aunque el conteo sea 0
  byCategory: { category: string; revenue: number; units: number }[]; // de pedidos que cuentan como ingreso, mayor primero
  topProducts: { slug: string; name: string; image: string; units: number; revenue: number }[]; // top 5 por ingreso
  lowStock: CatalogProduct[];   // productos live con stock <= 5 (LOW_STOCK), menor stock primero
  catalog: { live: number; disabled: number; soldOut: number };
  totals: { customers: number; blocked: number; orders: number }; // "todo el tiempo"
  recent: Order[];              // los 6 pedidos más recientes
}
```

```json
{
  "days": 30,
  "revenue": 86130,
  "orders": 86,
  "avgOrder": 1118.57,
  "newCustomers": 3,
  "revenueDelta": { "pct": 0.19 },
  "ordersDelta": { "pct": 0.41 },
  "avgOrderDelta": { "pct": -0.15 },
  "customersDelta": { "pct": null },
  "series": [ { "date": "2026-08-27", "revenue": 3120.5, "orders": 3 }, { "date": "2026-08-28", "revenue": 0, "orders": 0 } ],
  "byStatus": [ { "status": "paid", "count": 5 }, { "status": "shipped", "count": 17 }, { "status": "delivered", "count": 55 }, { "status": "cancelled", "count": 6 }, { "status": "refunded", "count": 3 } ],
  "byCategory": [ { "category": "Iphone", "revenue": 24500, "units": 22 } ],
  "topProducts": [ { "slug": "iphone-18", "name": "iPhone 18", "image": "/images/catalog/airpods-pro-2.png", "units": 8, "revenue": 7192 } ],
  "lowStock": [],
  "catalog": { "live": 31, "disabled": 0, "soldOut": 0 },
  "totals": { "customers": 26, "blocked": 1, "orders": 161 },
  "recent": []
}
```

Reglas de período: el período es `days` días **terminando hoy inclusive** (día calendario **local del navegador**), y el "anterior" es el mismo número de días justo antes. Los días se agrupan por la fecha del pedido. **Zona horaria**: hoy usa la del navegador; el backend debe fijar una (sección 15, #18).

### Imágenes en el admin
Solo URL. Ver sección 7.

---

## 13. Errores

**El front no tiene ningún formato de error de API** (no hay llamadas). Lo que sí hace hoy:

- **Validación de formularios**: mensajes en inglés, **debajo del campo** (`role="alert"`, en rojo) o, en el checkout y el login admin, en una línea bajo los campos. Un error por campo (el primero que falla). Lista completa de mensajes en la sección 5.
- **Éxito**: notificación (toast) de 3 segundos (`app/lib/toast.ts`, `components/Toaster.tsx`), ej. `"Product added to your bag"`, `"Order NB-1137 placed"`.
- **Operaciones destructivas**: diálogo de confirmación propio antes de borrar.
- **Credenciales incorrectas** (admin): un solo mensaje genérico, `"Wrong email or password."`.

**SUPUESTO** — formato recomendado (el estándar de DRF, para que el front pueda mostrar cada mensaje bajo su campo):

Error de validación (`400`):
```json
{ "slug": ["Another product already uses this slug."], "price": ["Enter a price of 0 or more."] }
```
Error general (`400`/`401`/`403`/`404`/`409`):
```json
{ "detail": "This account can't place orders. Contact support." }
```

Es importante que las **claves de error coincidan con los nombres de campo del front** (`name`, `slug`, `price`, `stock`, `options`, `image`, `email`, `password`…) y que el `detail` traiga texto legible en inglés. Códigos que el front va a necesitar distinguir: `401` (sesión inválida → login), `403` (no es admin), `404` (producto no existe → 404 de la página), `400` (validación), `409` (slug o email duplicado, opcional).

---

## 14. Diferencias con el backend planeado

Convención de nombres: el backend "se adapta al front", así que **el JSON debe usar las claves del front** (inglés, camelCase). En Django se puede conservar el modelo en español y mapear en el serializer (`source="titulo"`, etc.).

| Tema | Backend planeado | Lo que usa el front | Propuesta |
|---|---|---|---|
| Nombre de campos | `titulo`, `descripcion`, `precio`, `imagen`, `recomendado`, `date`, `nombre` | `name`, `description`, `price`, `image`, `recommended`, `createdAt`/`updatedAt`, `name` | Serializar con los nombres del front. |
| Categoría | Entidad `{id, nombre, slug}`; producto con FK | Cadena por **nombre exacto** (`"Iphone"`…), sin id ni slug | Devolver/aceptar `category` como **nombre** en el producto. Mantener la tabla `Categoria`, pero exponer el nombre. Respetar `"Accesories"` o corregirlo en el front. |
| Slug de producto | No existe en `Producto` (solo en `Categoria`) | **Obligatorio y único**: la URL, el carrito y los pedidos lo usan | **Añadir `slug`** único a `Producto`. |
| Variantes | `storage` y `color` como campos fijos | Lista genérica `options: [{name, values[], layout?}]`; hay `Size`, `Length`, `Pack`… y productos sin opciones | Reemplazar `storage`/`color` por un `JSONField` `options` (o tablas `Option`/`OptionValue`). Ver sección 7. |
| "Novedad" | No existe | `isNew` (filtro "New" del catálogo) | **Añadir** `isNew` (booleano). |
| Visibilidad | `status (visible)` | `status: "live"\|"disabled"` | Exponer `status` con esos dos valores (`live` = visible). |
| Stock | `stock` | `stock` entero por producto (no por variante); baja al pagar y se repone al cancelar/reembolsar | Igual, más la lógica de la sección 10. |
| Fecha del producto | `date` | `createdAt` y **`updatedAt`** | Añadir `updatedAt`; renombrar. |
| Imagen | Una URL | Una cadena: URL `https://…` **o ruta relativa `/…`** | Usar `CharField` (no `URLField` estricto). |
| Usuario / rol | Una tabla `Usuario` con `rol: "cliente"\|"admin"` | Dos conceptos: `Customer` (`status: active\|blocked`, `notes`) y `AdminUser` (`createdBy`) | Puedes usar una tabla con `role`, pero **añade** `status` (bloqueado) y `notes` para clientes, y `createdBy` para admins. Exponer `role`. |
| Registro | `fecha_registro` | `createdAt` | Renombrar. |
| Login de admin | (un solo login por JWT) | Pantalla propia `/login-admin`; solo admins | El backend debe rechazar a no-admins en ese flujo. |
| Datos del cliente | No detallado | Solo `name`, `email`, `notes`, `status`, `createdAt` (sin teléfono/país/ciudad) | No crear esos campos. |
| ID de cliente/pedido/admin | Numérico de Django | Cadenas opacas (`"cus_001"`); producto sí numérico | Aceptable devolver números (o cadenas): el front los trata como opacos salvo el de producto, que es número. Confirmarlo. |
| Carrito | Requiere login; un carrito activo por usuario; snapshot | Coincide. Cada ítem: `slug`, `name`, `price`, `image`, `options[]`, `quantity`; línea distinta por opciones distintas | Igual. El backend debe derivar nombre/precio/imagen de la BD, no del cliente. |
| Cantidad | — | El front cambia ±1 | **Decidido**: cantidad absoluta `{ "quantity": n }` (sección 15, #11). |
| Cálculo de totales | Backend (8 %) | Hoy el **front** calcula; con API mostrará lo recibido | Backend devuelve `subtotal`, `taxRate`, `tax`, `total` (números, 2 decimales, half-up). |
| Estados de pedido | `pendiente`, `completado`, `cancelado` | `paid`, `shipped`, `delivered`, `cancelled`, `refunded` | **Decidido: se adoptan los 5 del front.** El backend deja de usar los 3 suyos. |
| Estado inicial del pedido | `pendiente` | `paid` (el pago es simulado y siempre se da por hecho) | **Decidido:** crear el pedido como `paid`. |
| Pago | (no detallado) | Simulado: solo `cardLast4` | **Decidido:** no hay pasarela; el backend nunca recibe número, caducidad ni CVC. |
| Dirección de envío | No existe | `shippingAddress` `{address, city, postalCode, country}`, obligatoria en el checkout | **Añadir** al pedido (snapshot). Envío gratis, sin costo en los totales. |
| Pedido: campos | subtotal, impuesto, total, estado, fecha | Además: `number` (`NB-1001…`), `customerId/Name/Email`, `lines[]` (snapshot), `taxRate`, `shippingAddress`, `cardLast4`, `updatedAt` | Añadirlos. |
| Paginación | `{count, next, previous, results}` | Necesita `count` y número de página; tamaño **9** en el catálogo; el admin hoy pagina en cliente (10) | Compatible. Añadir `page` y `page_size`. |
| Parámetros de filtro | — | `category`, novedades, `recommended`, búsqueda por texto | Ver sección 6. |
| Dashboard | — | Necesita agregados (sección 12) | Añadir el endpoint. |
| Errores | — | Sin formato definido | Estándar DRF (sección 13). |
| CORS | — | El front corre en otro origen (Next en `localhost:3000/3001`, API en `localhost:8000`) | **SUPUESTO**: habilitar CORS para el origen del front. |
| Barra final | DRF la exige | Sin definir | Usar `/` final en todas las rutas y que el front lo respete. |

---

## 15. Pendientes resueltos (decisiones tomadas)

Las dudas que quedaban abiertas al escribir la primera versión ya tienen decisión. Si algo no te sirve, se cambia; pero **con esto puedes empezar sin esperar respuestas**.

| # | Tema | Decisión |
|---|---|---|
| 1 | Pago | **Simulado.** Sin pasarela. El backend solo guarda `cardLast4` (para mostrarlo en el CMS). Nunca recibe número completo, caducidad ni CVC. Todo pedido nace `paid`. Ver secciones 5 y 10. |
| 2 | Dirección de envío | **Añadida al checkout** (`address`, `city`, `postalCode`, `country`, todo obligatorio y texto libre). Va dentro del pedido como `shippingAddress`. **Envío gratis siempre**, sin costo en los totales. Ver sección 10. |
| 3 | Cliente del pedido | Sale del **usuario autenticado** (token). El campo Email del formulario se precargará con el email de la cuenta y quedará de solo lectura. El backend no lo recibe. |
| 4 | Estados de pedido | Se adoptan los **5 del front**: `paid`, `shipped`, `delivered`, `cancelled`, `refunded`. Ver sección 10. |
| 5 | JWT | `simplejwt`, access 30 min, refresh 7 días con rotación y lista negra; `localStorage` con dos sesiones (cliente y admin). Ver sección 8. |
| 6 | URL base y barra final | `NEXT_PUBLIC_API_URL=http://localhost:8000/api`. **Todas las rutas terminan en `/`** (por defecto de DRF). El front añade la barra. |
| 7 | CORS | `django-cors-headers` con `http://localhost:3000` y `http://localhost:3001` en desarrollo. |
| 8 | "Olvidé mi contraseña" | Endpoint `204` siempre; puede ser un stub (correo en consola). Prioridad baja: el front no tiene pantalla de nueva contraseña. |
| 9 | Cliente creado por un admin (sin contraseña) | Se crea con contraseña inutilizable. Al **registrarse** con ese email, el registro reclama la cuenta. Ver sección 8. |
| 10 | Cliente bloqueado | Puede entrar y navegar; **no puede hacer checkout** (`403`). |
| 11 | Cantidad del carrito | **Absoluta** (`{ "quantity": n }`); `0` elimina. Con validación de stock (`400`). Ver secciones 5 y 9. |
| 12 | Stock y concurrencia | Validar en carrito **y** en checkout. En checkout: `transaction.atomic()` + `select_for_update()` sobre los productos. |
| 13 | Orden del catálogo | Por defecto **más nuevo primero** (`-createdAt`). Parámetro `ordering` con `createdAt`, `-createdAt`, `price`, `-price`, `name`. El front hoy no muestra selector de orden. (El mock intercala categorías; no hace falta replicarlo.) |
| 14 | Recomendados del home | `GET /api/products/?recommended=true&page_size=50`. Sin tope de recomendados. |
| 15 | Variantes | Precio y stock **por producto**, no por variante. Se mantiene así. |
| 16 | Imágenes | **Una** por producto. Sin subida de archivos ni carpeta `MEDIA`: solo se guarda la URL. |
| 17 | Rutas relativas de imagen | `image` es un `CharField`, no `URLField`. Válido: `https://…` **o** ruta que empieza por `/`. Validar con regex en el serializer. Al cargar la semilla, mantener las rutas `/images/catalog/...` (existen en el front). |
| 18 | Zona horaria | `TIME_ZONE = "America/Bogota"` (**SUPUESTO**: cámbiala si tu universidad usa otra). Las fechas viajan en ISO 8601 UTC; los **días** del dashboard se agrupan en esa zona. |
| 19 | Borrado | **Duro**. Los pedidos no se pierden porque guardan snapshot (`SET_NULL` en `productId`/`customerId`). |
| 20 | Acciones masivas | **Sin endpoint masivo**: el front repite la llamada individual por elemento. |
| 21 | Número de pedido | `NB-` + (1000 + id). Único y sin carreras. |
| 22 | Categorías | Las **7 fijas**, cargadas en la BD desde un fixture. Solo lectura (`GET /api/categories/`, opcional). El producto expone `category` como **nombre**. Respetar `"Accesories"` tal cual. |
| 23 | `/about` y `/contact` | Sin API. No existen aún. |
| 24 | Límite de intentos | Throttling en login y registro (ver sección 8). |
| 25 | Idioma de los mensajes | **Inglés** para todo texto que el front muestre (`detail` y errores de campo). |
| 26 | Datos demo | **No migrar** `demo-data.ts` (clientes y pedidos falsos). Los 31 productos de `app/data/catalog.ts` **sí** son la semilla del catálogo. |
| 27 | Primer admin | Un fixture o `createsuperuser` con `role = "admin"`. Ya no hay credenciales fijas en el código. |
| 29 | IDs | **Enteros** en toda la API (producto, cliente, pedido, admin, línea de carrito, categoría). Los `"cus_001"` de los ejemplos son del mock. Ver Anexo A.1. |
| 30 | Nombres | JSON en **camelCase**; parámetros de la URL y valores de `ordering` en **snake_case**. Ver Anexo A.1. |
| 28 | Historial de pedidos del cliente | El front **no** tiene pantalla "mis pedidos". Solo hace falta el listado de pedidos por cliente en el admin (`?customer=<id>`). |

### Dudas que siguen abiertas (pocas)
- **Dominio de producción del front** (para CORS) y si habrá despliegue: solo importa si se publica.
- **Zona horaria** real del proyecto (ver #18).
- **Idioma del CMS/tienda**: todo está en inglés en el front; si se traduce, cambian los mensajes de la API.

---

## 16. Extras que no pidió tu compañero pero conviene tener en cuenta

### Seguridad
- **Nunca confiar en el cliente** para precios, nombres, imágenes ni totales: se toman de la BD (secciones 9 y 10).
- **Permisos**: `IsAdminRole` en todo `/api/admin/*`; el carrito y los pedidos del cliente filtrados siempre por `request.user` (evitar que un usuario lea el carrito o el pedido de otro cambiando un id).
- **Nunca devolver** `password`/`passwordHash` en ninguna respuesta.
- **Secretos por variable de entorno**: `SECRET_KEY`, credenciales de la BD, `DEBUG=False` fuera de desarrollo. Un `.env.example` en el repo ayuda.
- **No revelar** si un email existe (login y recuperación devuelven el mismo mensaje).
- Validar y **limitar** `page_size` (máximo 100) para que nadie pida toda la tabla de golpe.

### Integridad de datos
- Dinero con **`DecimalField(max_digits=12, decimal_places=2)`** y redondeo `ROUND_HALF_UP`; serializar como **número** (`COERCE_DECIMAL_TO_STRING = False`).
- Restricciones únicas: `Product.slug`, email de usuario (normalizado a minúsculas al guardar) y `Order.number`.
- `stock` con `PositiveIntegerField`; `price ≥ 0`.
- Guardar `slug` solo con `[a-z0-9-]`. Ojo: **cambiar el slug de un producto cambia su URL** y no hay redirección; el admin puede hacerlo libremente.
- Índices útiles: `Product(slug)`, `Product(status, recommended)`, `Product(category, status)`, `Order(status, createdAt)`, `Order(customer)`.
- `updatedAt` automático (`auto_now`).

### Rendimiento
- **Dashboard**: calcularlo con agregados de la BD (`Sum`, `Count`, `TruncDate`, `Coalesce`), no cargando todos los pedidos en memoria. Los días sin ventas **deben venir igualmente** en `series` con `0` (el gráfico espera un punto por día).
- Listado de productos: `select_related("category")`. Pedidos: `prefetch_related("lines")`.

### Herramientas que ahorran tiempo
- **Documentación automática** con `drf-spectacular` (Swagger en `/api/docs/`): el front puede probar sin preguntar.
- **Datos iniciales**: ya están generados en `backend_fixtures/` (Anexo C): 7 categorías y 31 productos. Cárgalos con un comando propio antes de probar el catálogo.
- Un comando `manage.py seed_demo` **opcional** que genere clientes y pedidos falsos, para que el dashboard no se vea vacío en la demo del proyecto.
- Una colección de **Postman/Thunder** o tests con `APIClient` de los flujos: registro → login → añadir al carrito → checkout → cambiar estado en admin.

### Cosas del front que cambiarán al conectar (para que no te sorprendan)
1. Se crea un **cliente HTTP** único (`fetch` + `NEXT_PUBLIC_API_URL`) que añade el token, refresca y redirige al expirar.
2. `app/lib/cart.ts` y `app/lib/cms/*.ts` dejan de usar `localStorage` y llaman a la API; los componentes casi no cambian.
3. El carrito pasa a **enviar la cantidad final** (no delta) y a mostrar el error de stock (`400`).
4. El checkout **no enviará** email, titular, número, caducidad ni CVC; solo `shippingAddress` y `cardLast4`. Precargará el email de la cuenta.
5. Las listas del admin (productos, clientes, pedidos) hoy **filtran, ordenan y paginan en el navegador** con la lista completa. Con la API pasan a usar `?search=`, `?ordering=`, `?page=`, `?page_size=` y filtros por estado/categoría/rango. Hasta que eso se haga, la API puede devolver listas completas (con `page_size` alto) y funciona igual, pero **no escala**.
6. El **carrusel del home** y el **catálogo** pedirán a la API en vez de leer el store local; `Featured.tsx` seguirá usando 5 imágenes recortadas a mano para 5 slugs y `image` para el resto.
7. Habrá que mostrar **estados de carga y error** (hoy no existen porque todo es local).
8. El botón **Restore demo data** del menú CMS desaparece.

### Orden de trabajo sugerido
1. Proyecto Django, modelos (`Category`, `Product`, `User` con `role`/`status`/`notes`, `Cart`/`CartItem`, `Order`/`OrderLine`), migraciones, **fixtures** de categorías y productos.
2. **Auth** (registro, login, refresh, logout, `me`) + CORS. Con esto el front ya puede probar sesiones.
3. **Catálogo público** (lista con filtros, detalle por slug, recomendados).
4. **Carrito**.
5. **Checkout y pedidos** (la transacción de la sección 10).
6. **CRUD admin**: productos, clientes, pedidos (con la lógica de stock), admins.
7. **Dashboard**.
8. Swagger, tests de los flujos y seed de demo.

## Anexo A. Referencia exacta de la API (esta es la versión que manda)

Si algo de las secciones 1–16 contradice este anexo, **gana el anexo**. Aquí están cerradas todas las decisiones de forma para que puedas construir y el front pueda conectarse sin adivinar.

### A.1 Reglas generales

| Tema | Regla |
|---|---|
| Base | `{NEXT_PUBLIC_API_URL}` = `http://localhost:8000/api`. **Toda ruta termina en `/`.** |
| Formato | JSON (`Content-Type: application/json`). |
| **Claves del JSON** | **camelCase** en cuerpos y respuestas (`isNew`, `createdAt`, `shippingAddress`). En Django: `djangorestframework-camel-case` (parser y renderer) o nombrar los campos a mano. |
| **Parámetros de la URL (query)** | **snake_case** (`page_size`, `is_new`, `low_stock`, `ordering=-created_at`). Los valores de `ordering` también van en snake_case. |
| IDs | **Enteros** para todo (producto, cliente, pedido, admin, línea de carrito, categoría). Los ejemplos con `"cus_001"`, `"ord_0001"` de las secciones anteriores vienen del mock del front; el front pasará a tratar los IDs como números. |
| Fechas | ISO 8601 en **UTC** con `Z`: `"2026-09-25T22:41:00Z"` (con o sin milisegundos). |
| Dinero | **Número** con hasta 2 decimales, USD. |
| Vacíos | Los campos **siempre vienen** (no se omiten). Texto vacío = `""` (no `null`), lista vacía = `[]`. Solo puede ser `null`: `Order.lines[].productId`, `Order.customerId`, `Admin.createdBy`, `Customer.lastOrderAt`, `Dashboard.*Delta.pct`. |
| Autenticación | `Authorization: Bearer <access>`. Sin token → `401`. Con token pero sin permiso (no admin) → `403`. |
| Actualizar | **`PATCH` parcial** (solo los campos enviados). No se usa `PUT`. |
| Borrar | `204` sin cuerpo. Borrar algo que no existe → `404`. |
| Crear | `201` con el objeto creado completo. |

### A.2 Paginación

Todas las listas usan el mismo sobre (paginación por número de página de DRF):

```json
{ "count": 31, "next": "http://localhost:8000/api/products/?page=2", "previous": null, "results": [] }
```

| Parámetro | Significado |
|---|---|
| `page` | Número de página, desde 1. |
| `page_size` | Elementos por página. Máximo **100**. |

Valor por defecto de `page_size`: **9** en el catálogo público, **10** en las listas del admin. Una página fuera de rango devuelve `404 { "detail": "Invalid page." }` (el front lo controla y vuelve a la 1). El front solo usa `count` y `results`.

Excepciones **sin** paginar (devuelven un arreglo): `GET /api/categories/`.

### A.3 Errores

| Caso | Código | Cuerpo |
|---|---|---|
| Validación de campos | `400` | `{ "slug": ["Another product already uses this slug."] }` (clave = nombre del campo camelCase; valor = **lista** de mensajes) |
| Regla de negocio | `400` / `403` / `409` | `{ "detail": "This account can't place orders. Contact support." }` |
| Sin token o vencido | `401` | `{ "detail": "...", "code": "token_not_valid" }` (formato de simplejwt) |
| Sin permiso | `403` | `{ "detail": "You do not have permission to perform this action." }` |
| No existe | `404` | `{ "detail": "Not found." }` |
| Demasiados intentos | `429` | `{ "detail": "Request was throttled." }` |

Los errores de una lista anidada se devuelven bajo la clave del campo, por ejemplo `{ "options": ["Every attribute needs a name and at least one value."] }`. Todos los mensajes en **inglés**.

### A.4 Objetos

**Product** (público y admin; el admin también recibe los `disabled`):

```json
{
  "id": 1, "slug": "iphone-18-pro-max", "name": "iPhone 18 Pro Max", "category": "Iphone",
  "price": 1199, "image": "/images/catalog/airpods-pro-2.png", "isNew": true, "recommended": true,
  "options": [ { "name": "Storage", "values": ["256GB", "512GB"], "layout": "stack" } ],
  "status": "live", "stock": 8, "description": "",
  "createdAt": "2026-01-15T12:00:00Z", "updatedAt": "2026-01-15T12:00:00Z"
}
```

**Category**: `{ "id": 1, "name": "Iphone", "slug": "iphone" }`.

**User** (respuesta de login, registro y `me`): `{ "id": 5, "name": "Camila Rojas", "email": "camila@example.com", "role": "cliente" }` (`role` = `"cliente"` | `"admin"`).

**Customer** (admin): los campos de la sección 4.3 **más** estadísticas calculadas por el servidor:

```json
{
  "id": 12, "name": "Natalia Ortiz", "email": "natalia.ortiz16@example.com", "status": "active", "notes": "", "createdAt": "2026-09-14T15:20:00Z",
  "ordersCount": 2, "totalSpent": 4314.6, "lastOrderAt": "2026-09-24T19:53:46Z"
}
```

`totalSpent` suma solo los pedidos que cuentan como ingreso (`paid`, `shipped`, `delivered`). `lastOrderAt` es `null` si no tiene pedidos.

**Admin** (admin): `{ "id": 2, "name": "Second Admin", "email": "second@nebulab.com", "createdAt": "2026-09-25T22:10:00Z", "createdBy": 1, "createdByName": "Nebulab Admin" }`. (`createdBy` y `createdByName` son `null` para el primero.)

**Order** (cliente y admin): el de la sección 4.6, con `id`, `customerId` y `lines[].productId` como enteros. En las respuestas **del admin** se añade `units` (suma de `quantity` de las líneas):

```json
{
  "id": 137, "number": "NB-1137", "customerId": 27, "customerName": "Buyer Test", "customerEmail": "buyer.test@example.com",
  "lines": [ { "productId": 1, "slug": "iphone-18-pro-max", "name": "iPhone 18 Pro Max", "category": "Iphone", "image": "/images/catalog/airpods-pro-2.png", "price": 1199, "quantity": 1, "options": [ { "name": "Storage", "value": "256GB" } ] } ],
  "subtotal": 1199, "taxRate": 0.08, "tax": 95.92, "total": 1294.92, "status": "paid",
  "shippingAddress": { "address": "Calle 10 #20-30", "city": "Bogota", "postalCode": "110111", "country": "Colombia" },
  "cardLast4": "4242", "units": 1,
  "createdAt": "2026-09-25T22:41:00Z", "updatedAt": "2026-09-25T22:41:00Z"
}
```

**Cart**: el de la sección 9, con el `id` de línea **entero**.

### A.5 Endpoints públicos y de cliente

| # | Método y ruta | Auth | Parámetros / cuerpo | Respuesta |
|---|---|---|---|---|
| 1 | `POST /api/auth/register/` | — | `{ name, email, password }` | `201` `{ access, refresh, user }` |
| 2 | `POST /api/auth/login/` | — | `{ email, password }` | `200` `{ access, refresh, user }` · error `401` |
| 3 | `POST /api/auth/refresh/` | — | `{ refresh }` | `200` `{ access, refresh }` |
| 4 | `POST /api/auth/logout/` | sí | `{ refresh }` | `204` |
| 5 | `GET /api/auth/me/` | sí | — | `200` User |
| 6 | `POST /api/auth/password-reset/` | — | `{ email }` | `204` siempre |
| 7 | `GET /api/categories/` | — | — | `200` arreglo de Category |
| 8 | `GET /api/products/` | — | ver A.5.1 | `200` paginado de Product (solo `live`) |
| 9 | `GET /api/products/{slug}/` | — | — | `200` Product · `404` si no existe o está `disabled` |
| 10 | `GET /api/cart/` | cliente | — | `200` Cart (lo crea vacío si no existe) |
| 11 | `POST /api/cart/items/` | cliente | `{ slug, options: [{name, value}] }` | `200` Cart completo |
| 12 | `PATCH /api/cart/items/{id}/` | cliente | `{ quantity }` (`0` elimina) | `200` Cart completo |
| 13 | `DELETE /api/cart/items/{id}/` | cliente | — | `200` Cart completo |
| 14 | `POST /api/orders/` | cliente | `{ shippingAddress, cardLast4 }` | `201` Order |

Las tres operaciones de carrito devuelven **el carrito entero ya recalculado** (así el front reemplaza su estado sin un `GET` extra). Errores del carrito y del pedido: ver secciones 9 y 10 (`400` de stock, opciones incompletas, producto no disponible, carrito vacío; `403` cliente bloqueado).

**A.5.1 Filtros de `GET /api/products/`** (públicos)

| Parámetro | Valores | Efecto |
|---|---|---|
| `category` | nombre exacto: `Iphone`, `Macbook`, `Ipad`, `AirPods`, `Apple Watch`, `Apple Vision Pro`, `Accesories` | Solo esa categoría. Sin parámetro = todas. |
| `is_new` | `true` | Solo novedades. |
| `recommended` | `true` | Solo recomendados (carrusel del home; pedir con `page_size=50`). |
| `search` | texto | Se parte en palabras; **todas** deben aparecer en `name` + nombre de categoría; sin distinguir mayúsculas ni tildes. |
| `ordering` | `created_at`, `-created_at`, `price`, `-price`, `name`, `-name` | Por defecto `-created_at`. |
| `page`, `page_size` | ver A.2 | Por defecto 9. |

### A.6 Endpoints de admin

Todos exigen `role = "admin"` (`403` si no).

| # | Método y ruta | Parámetros / cuerpo | Respuesta |
|---|---|---|---|
| 15 | `GET /api/admin/dashboard/` | `days=7\|30\|90` (por defecto 30) | `200` Dashboard (sección 12) |
| 16 | `GET /api/admin/products/` | ver A.6.1 | `200` paginado de Product (todos los estados) |
| 17 | `POST /api/admin/products/` | cuerpo de A.6.1 | `201` Product |
| 18 | `GET /api/admin/products/{id}/` | — | `200` Product |
| 19 | `PATCH /api/admin/products/{id}/` | cualquier subconjunto del cuerpo | `200` Product |
| 20 | `DELETE /api/admin/products/{id}/` | — | `204` |
| 21 | `GET /api/admin/customers/` | ver A.6.2 | `200` paginado de Customer |
| 22 | `POST /api/admin/customers/` | `{ name, email, notes }` | `201` Customer |
| 23 | `GET /api/admin/customers/{id}/` | — | `200` Customer |
| 24 | `PATCH /api/admin/customers/{id}/` | subconjunto de `{ name, email, notes, status }` | `200` Customer |
| 25 | `DELETE /api/admin/customers/{id}/` | — | `204` |
| 26 | `GET /api/admin/orders/` | ver A.6.3 | `200` paginado de Order **con `summary` y `statusCounts`** |
| 27 | `GET /api/admin/orders/{id}/` | — | `200` Order |
| 28 | `PATCH /api/admin/orders/{id}/` | `{ status }` | `200` Order (con el ajuste de stock de la sección 10) |
| 29 | `GET /api/admin/admins/` | `page`, `page_size`, `ordering=created_at\|-created_at\|name\|-name` | `200` paginado de Admin |
| 30 | `POST /api/admin/admins/` | `{ name, email, password }` | `201` Admin |
| 31 | `DELETE /api/admin/admins/{id}/` | — | `204` · `400 { "detail": "You cannot delete your own account." }` · `400 { "detail": "There must be at least one admin." }` |

Los pedidos **no** se crean ni se borran desde el admin.

**A.6.1 Productos (admin)**

| Parámetro | Valores | Efecto |
|---|---|---|
| `search` | texto | Palabras (todas) contra `name` + `slug` + categoría, sin tildes ni mayúsculas. |
| `status` | `live` \| `disabled` | Por estado. |
| `category` | nombre exacto | Por categoría. |
| `low_stock` | `true` | Productos con `stock ≤ 5`, **de cualquier estado**. |
| `ordering` | `name`, `status`, `slug`, `category`, `price`, `stock`, `updated_at` (y con `-`) | Por defecto `-updated_at`. |
| `page`, `page_size` | — | Por defecto 10. |

Cuerpo de `POST`/`PATCH` (`id`, `createdAt`, `updatedAt` son de solo lectura):

```json
{
  "name": "iPhone 18 Pro Max", "slug": "iphone-18-pro-max", "category": "Iphone", "status": "live",
  "price": 1199, "stock": 8, "isNew": true, "recommended": false, "description": "",
  "image": "https://cdn.ejemplo.com/iphone-18.png",
  "options": [ { "name": "Storage", "values": ["256GB", "512GB"], "layout": "stack" } ]
}
```

Validaciones (mensajes exactos que el front espera mostrar):

| Campo | Regla | Mensaje |
|---|---|---|
| `name` | Obligatorio | `The product needs a name.` |
| `slug` | Obligatorio, único, `[a-z0-9-]`. Si viene vacío en `POST`, se genera desde `name` (minúsculas, sin tildes, guiones). | `Another product already uses this slug.` |
| `category` | Uno de los 7 nombres | `Choose a valid category.` |
| `price` | Número ≥ 0 | `Enter a price of 0 or more.` |
| `stock` | Entero ≥ 0 | `Stock must be a whole number, 0 or more.` |
| `options` | Cada elemento con `name` no vacío y `values` con al menos 1 texto; `layout` ∈ {`wrap`,`stack`} (opcional) | `Every attribute needs a name and at least one value.` |
| `image` | `https://…` o ruta que empieza por `/` (no `//`) | `Enter an image URL starting with https:// (or a path of this site, like /images/catalog/photo.png).` |

**A.6.2 Clientes (admin)**

| Parámetro | Valores | Efecto |
|---|---|---|
| `search` | texto | Palabras contra `name` + `email`. |
| `status` | `active` \| `blocked` | Por estado. |
| `ordering` | `name`, `status`, `orders_count`, `total_spent`, `last_order_at`, `created_at` (y con `-`) | Por defecto `-created_at`. |
| `page`, `page_size` | — | Por defecto 10. |

Lista solo usuarios con `role = "cliente"`. Errores: `{ "name": ["The customer needs a name."] }`, `{ "email": ["Enter a valid email address."] }`, `{ "email": ["Another customer already uses this email."] }`.

**A.6.3 Pedidos (admin)**

| Parámetro | Valores | Efecto |
|---|---|---|
| `search` | texto | Palabras contra `number` + `customerName` + `customerEmail` + nombres de los productos de las líneas. |
| `status` | `paid`, `shipped`, `delivered`, `cancelled`, `refunded` | Por estado. |
| `days` | `7`, `30`, `90` | Solo pedidos creados en los últimos N días (ventana móvil que termina ahora). Sin parámetro = todos. |
| `customer` | id de cliente | Pedidos de ese cliente (historial). |
| `ordering` | `number`, `created_at`, `customer_name`, `units`, `total`, `status` (y con `-`) | Por defecto `-created_at`. |
| `page`, `page_size` | — | Por defecto 10. |

El sobre paginado de esta lista lleva **dos objetos extra**, que el front usa para las tarjetas y las pestañas de estado:

```json
{
  "count": 72, "next": null, "previous": null,
  "summary": { "revenue": 85838.4, "orders": 72, "avgOrder": 1320.59 },
  "statusCounts": { "all": 72, "paid": 10, "shipped": 8, "delivered": 47, "cancelled": 4, "refunded": 3 },
  "results": []
}
```

- `summary` se calcula sobre **todo el conjunto filtrado** (con `search`, `status`, `days` y `customer` aplicados, no solo la página): `revenue` = suma de `total` de los que cuentan como ingreso; `orders` = cantidad de pedidos (todos los estados); `avgOrder` = `revenue` / cantidad de pedidos que cuentan como ingreso (0 si no hay).
- `statusCounts` se calcula con **solo `days` y `customer`** aplicados (ignora `status` y `search`), para que las pestañas muestren cuántos hay de cada estado dentro del rango. `all` = suma de todos.

### A.7 Ejemplo de flujo completo (para probar con Postman)

1. `POST /api/auth/register/` → guarda `access`.
2. `GET /api/products/?category=Iphone&page_size=9`.
3. `POST /api/cart/items/` con `{ "slug": "iphone-18-pro-max", "options": [{ "name": "Storage", "value": "256GB" }, { "name": "Color", "value": "Silver" }] }`.
4. `PATCH /api/cart/items/{id}/` con `{ "quantity": 2 }`.
5. `POST /api/orders/` con `{ "shippingAddress": { "address": "Calle 10 #20-30", "city": "Bogota", "postalCode": "110111", "country": "Colombia" }, "cardLast4": "4242" }` → comprobar que el stock baja en 2 y el carrito queda vacío.
6. Como admin: `PATCH /api/admin/orders/{id}/` con `{ "status": "cancelled" }` → el stock **vuelve a subir**.

---

## Anexo B. Modelos sugeridos (Django)

Punto de partida; nombres de columna libres mientras el JSON siga el Anexo A.

```python
class Category(models.Model):
    name = models.CharField(max_length=60, unique=True)      # "Iphone", "Accesories"...
    slug = models.SlugField(unique=True)

class Product(models.Model):
    slug = models.SlugField(unique=True)                      # [a-z0-9-]
    name = models.CharField(max_length=160)
    category = models.ForeignKey(Category, on_delete=models.PROTECT)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    image = models.CharField(max_length=500)                 # https://... o /ruta (NO URLField)
    is_new = models.BooleanField(default=False)
    recommended = models.BooleanField(default=False)
    options = models.JSONField(default=list)                 # [{name, values[], layout?}]
    status = models.CharField(max_length=10, choices=[("live", "live"), ("disabled", "disabled")], default="live")
    stock = models.PositiveIntegerField(default=0)
    description = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class User(AbstractBaseUser, PermissionsMixin):              # USERNAME_FIELD = "email"
    email = models.EmailField(unique=True)                   # guardar en minúsculas
    name = models.CharField(max_length=120)
    role = models.CharField(max_length=10, choices=[("cliente", "cliente"), ("admin", "admin")], default="cliente")
    status = models.CharField(max_length=10, choices=[("active", "active"), ("blocked", "blocked")], default="active")  # solo clientes
    notes = models.TextField(blank=True, default="")         # solo clientes
    created_by = models.ForeignKey("self", null=True, blank=True, on_delete=models.SET_NULL)  # solo admins
    created_at = models.DateTimeField(auto_now_add=True)

class Cart(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)

class CartItem(models.Model):
    cart = models.ForeignKey(Cart, related_name="items", on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    # snapshot al añadir:
    slug = models.CharField(max_length=200); name = models.CharField(max_length=160)
    price = models.DecimalField(max_digits=12, decimal_places=2); image = models.CharField(max_length=500)
    options = models.JSONField(default=list)                 # [{name, value}]
    quantity = models.PositiveIntegerField()

class Order(models.Model):
    customer = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    customer_name = models.CharField(max_length=120); customer_email = models.EmailField()   # snapshot
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=4, default=Decimal("0.08"))
    tax = models.DecimalField(max_digits=12, decimal_places=2)
    total = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=10, choices=[(s, s) for s in ["paid", "shipped", "delivered", "cancelled", "refunded"]], default="paid")
    shipping_address = models.JSONField()                    # {address, city, postalCode, country}
    card_last4 = models.CharField(max_length=4)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    # number = "NB-" + str(1000 + id)  (propiedad calculada, o campo unique rellenado tras insertar)

class OrderLine(models.Model):
    order = models.ForeignKey(Order, related_name="lines", on_delete=models.CASCADE)
    product = models.ForeignKey(Product, null=True, on_delete=models.SET_NULL)
    slug = models.CharField(max_length=200); name = models.CharField(max_length=160)
    category = models.CharField(max_length=60, blank=True)   # nombre, snapshot
    image = models.CharField(max_length=500)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    quantity = models.PositiveIntegerField()
    options = models.JSONField(default=list)
```

`options` como `JSONField` evita 3 tablas extra y el front lo entrega/lee tal cual; si prefieres normalizar, el JSON de la API no cambia.

---

## Anexo C. Datos iniciales (fixtures)

En la carpeta **`backend_fixtures/`** del repo del front hay dos archivos listos:

| Archivo | Contenido |
|---|---|
| `categories.json` | Las 7 categorías con `id`, `name`, `slug`. |
| `products.json` | Los **31 productos** de la tienda, **con el formato exacto del API** (los mismos campos y valores que devuelve `GET /api/products/`). |

Generados a partir de `app/data/catalog.ts`. Para cargarlos: escribe un comando (`manage.py seed_catalog`) o un script que lea los JSON y cree las filas; **no son un fixture de `loaddata`** (no traen el nombre del modelo). Notas:
- El campo `category` de cada producto es el **nombre** de la categoría: resuelve el FK por nombre.
- `id` puede reasignarse (que quede autoincremental) siempre que los `slug` se conserven; el front no depende de los ids del catálogo.
- `image` es `/images/catalog/airpods-pro-2.png` en todos (imagen de relleno que existe en el front). Cuando haya fotos reales se cambian desde el admin.
- Los 5 recomendados de fábrica ya vienen con `"recommended": true`.
- **No** hay pedidos ni clientes iniciales: no migres nada de `demo-data.ts`. El primer admin se crea con `createsuperuser` o un comando propio (`role = "admin"`).
- Un usuario `admin` inicial sugerido para pruebas: el que quieras; el front ya no tiene credenciales fijas.

---

## Anexo D. Qué archivo cambiar en el front cuando exista la API

Cuando el backend esté listo, el front solo reescribe estos archivos (los componentes ya llaman a estas funciones):

| Archivo | Funciones que pasan a ser llamadas HTTP |
|---|---|
| `app/lib/cart.ts` | `useCart`, `addToCart`, `changeQuantity`, `clearCart` |
| `app/lib/cms/products.ts` | `useProducts`, `useLiveProducts`, `saveProduct`, `setProductStatus`, `deleteProducts`, `adjustStock` (esta última desaparece: la hace el servidor) |
| `app/lib/cms/customers.ts` | `useCustomers`, `saveCustomer`, `findOrCreateCustomer`, `setCustomerStatus`, `deleteCustomers`, `customerStats` (pasa a venir del servidor) |
| `app/lib/cms/orders.ts` | `useOrders`, `placeOrder`, `setOrderStatus` |
| `app/lib/cms/admin-auth.ts` | `signInAdmin`, `signOutAdmin`, `useAdminSession`, `useAdmins`, `createAdmin`, `deleteAdmin` |
| `app/lib/cms/metrics.ts` | `buildDashboard` (pasa a `GET /api/admin/dashboard/`) |
| `app/components/login/LoginScreen.tsx` | Formularios de login/registro/olvidé (hoy sin conectar) de la tienda |
| `app/account/…` (`AccountGreeting.tsx`) | Nombre real del usuario |
