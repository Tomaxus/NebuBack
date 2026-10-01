from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, RegexValidator
from django.db import models
from django.utils import timezone

from devconfsite.comun import normalizar_texto

validate_image = RegexValidator(
    regex=r"^(https://\S+|/(?!/)\S*)$",
    message="Enter an image URL starting with https:// (or a path of this site, like /images/catalog/photo.png).",
)


def validate_options(value):
    message = "Every attribute needs a name and at least one value."
    if not isinstance(value, list):
        raise ValidationError(message)
    for option in value:
        if not isinstance(option, dict):
            raise ValidationError(message)
        name = option.get("name")
        values = option.get("values")
        if not isinstance(name, str) or not name.strip():
            raise ValidationError(message)
        if not isinstance(values, list) or not values or not all(isinstance(v, str) and v.strip() for v in values):
            raise ValidationError(message)
        if option.get("layout", "wrap") not in ("wrap", "stack"):
            raise ValidationError(message)


class Categoria(models.Model):
    name = models.CharField(max_length=60, unique=True)
    slug = models.SlugField(unique=True)

    class Meta:
        verbose_name = "categoría"
        verbose_name_plural = "categorías"
        ordering = ["id"]

    def __str__(self):
        return self.name


class Producto(models.Model):
    class Status(models.TextChoices):
        LIVE = "live", "Live"
        DISABLED = "disabled", "Disabled"

    slug = models.SlugField(max_length=200, unique=True)
    name = models.CharField(max_length=160)
    category = models.ForeignKey(Categoria, on_delete=models.PROTECT, related_name="productos")
    price = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    image = models.CharField(max_length=500, validators=[validate_image])
    is_new = models.BooleanField(default=False)
    recommended = models.BooleanField(default=False)
    options = models.JSONField(default=list, blank=True, validators=[validate_options])
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.LIVE)
    stock = models.PositiveIntegerField(default=0)
    description = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    search_text = models.TextField(blank=True, default="", editable=False)

    class Meta:
        verbose_name = "producto"
        verbose_name_plural = "productos"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "recommended"]),
            models.Index(fields=["category", "status"]),
        ]
        constraints = [
            models.CheckConstraint(condition=models.Q(price__gte=0), name="precio_no_negativo"),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        self.search_text = normalizar_texto(f"{self.name} {self.category.name}")
        update_fields = kwargs.get("update_fields")
        if update_fields is not None:
            kwargs["update_fields"] = {*update_fields, "search_text"}
        super().save(*args, **kwargs)

    @property
    def is_live(self):
        return self.status == self.Status.LIVE

    def recalcular_desde_variantes(self):
        datos = self.variants.aggregate(minimo=models.Min("price"), total=models.Sum("stock"), cantidad=models.Count("id"))
        if not datos["cantidad"]:
            return False
        Producto.objects.filter(pk=self.pk).update(price=datos["minimo"], stock=datos["total"])
        self.price, self.stock = datos["minimo"], datos["total"]
        return True


def clave_variante(opciones):
    return "|".join(sorted(f"{o['name'].strip().lower()}={o['value'].strip().lower()}" for o in opciones))


class Variante(models.Model):
    product = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name="variants")
    options = models.JSONField(default=list)
    options_key = models.CharField(max_length=500, editable=False)
    price = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    stock = models.PositiveIntegerField(default=0)
    sku = models.CharField(max_length=60, blank=True, default="")

    class Meta:
        verbose_name = "variante"
        verbose_name_plural = "variantes"
        ordering = ["id"]
        constraints = [
            models.UniqueConstraint(fields=["product", "options_key"], name="variante_unica_por_producto"),
            models.CheckConstraint(condition=models.Q(price__gte=0), name="precio_variante_no_negativo"),
        ]

    def __str__(self):
        return f"{self.product} ({', '.join(o['value'] for o in self.options)})"

    def save(self, *args, **kwargs):
        self.options_key = clave_variante(self.options)
        update_fields = kwargs.get("update_fields")
        if update_fields is not None:
            kwargs["update_fields"] = {*update_fields, "options_key"}
        super().save(*args, **kwargs)
