# NebuBack

API REST de **Nebulab**, tienda en línea de productos Apple. Django + Django REST Framework + PostgreSQL (Neon), documentada con Swagger/OpenAPI y desplegada en Render.

## Arquitectura

| Capa | Tecnología | Despliegue |
|---|---|---|
| Backend (este repo) | Django + DRF | Render |
| Base de datos | PostgreSQL | Neon |
| Frontend | Next.js | Vercel |

## Flujo de ramas (Git Flow)

| Rama | Uso |
|---|---|
| `main` | Producción. Render despliega automáticamente desde aquí. |
| `develop` | Integración. Todo PR de trabajo apunta aquí. |
| `feature/<tema>` | Una tarea del tablero Kanban. Sale de `develop`. |
| `release/semana-XX` | Cierre de cada checkpoint: `develop` → `main` con tag. |
| `hotfix/<tema>` | Arreglo urgente en producción. Sale de `main`. |

Los commits siguen [Conventional Commits](https://www.conventionalcommits.org/es/): `feat:`, `fix:`, `docs:`, `chore:`, `refactor:`, `test:`.

## Equipo

Proyecto de aula de Desarrollo de Aplicaciones Web — Universidad Pontificia Bolivariana, Bucaramanga.

- Tomás Uribe Sánchez — Backend
