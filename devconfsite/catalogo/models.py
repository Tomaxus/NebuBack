from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, RegexValidator
from django.db import models
from django.utils import timezone

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

    @property
    def is_live(self):
        return self.status == self.Status.LIVE
