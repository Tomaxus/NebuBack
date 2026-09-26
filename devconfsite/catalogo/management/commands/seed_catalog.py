import json
from decimal import Decimal
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.dateparse import parse_datetime

from devconfsite.catalogo.models import Categoria, Producto

SEED_DIR = Path(__file__).resolve().parents[2] / "seed"


class Command(BaseCommand):
    help = "Carga o actualiza las categorías y los productos iniciales de la tienda."

    @transaction.atomic
    def handle(self, *args, **options):
        categorias = json.loads((SEED_DIR / "categories.json").read_text(encoding="utf-8"))
        productos = json.loads((SEED_DIR / "products.json").read_text(encoding="utf-8"))

        por_nombre = {}
        for data in categorias:
            categoria, _ = Categoria.objects.update_or_create(
                slug=data["slug"], defaults={"name": data["name"]}
            )
            por_nombre[categoria.name] = categoria

        creados = 0
        for data in productos:
            producto = Producto(
                slug=data["slug"],
                name=data["name"],
                category=por_nombre[data["category"]],
                price=Decimal(str(data["price"])),
                image=data["image"],
                is_new=data["isNew"],
                recommended=data["recommended"],
                options=data["options"],
                status=data["status"],
                stock=data["stock"],
                description=data["description"],
                created_at=parse_datetime(data["createdAt"]),
            )
            producto.full_clean(exclude=["slug"])
            _, creado = Producto.objects.update_or_create(
                slug=producto.slug,
                defaults={
                    field: getattr(producto, field)
                    for field in (
                        "name", "category", "price", "image", "is_new", "recommended",
                        "options", "status", "stock", "description", "created_at",
                    )
                },
            )
            creados += creado

        self.stdout.write(
            self.style.SUCCESS(
                f"{len(por_nombre)} categorías y {len(productos)} productos listos ({creados} nuevos)."
            )
        )
