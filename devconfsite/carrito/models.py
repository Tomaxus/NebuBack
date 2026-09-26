from decimal import ROUND_HALF_UP, Decimal

from django.conf import settings
from django.core.validators import MinValueValidator, RegexValidator
from django.db import models

from devconfsite.catalogo.models import Producto

CENTAVOS = Decimal("0.01")


def redondear(valor):
    return Decimal(valor).quantize(CENTAVOS, rounding=ROUND_HALF_UP)


def calcular_impuesto(subtotal, tasa=None):
    return redondear(Decimal(subtotal) * (settings.IMPUESTO_TASA if tasa is None else tasa))


class Carrito(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        CONVERTED = "converted", "Converted"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="carritos")
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ACTIVE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "carrito"
        verbose_name_plural = "carritos"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user"],
                condition=models.Q(status="active"),
                name="un_carrito_activo_por_usuario",
            ),
        ]

    def __str__(self):
        return f"Carrito {self.pk} de {self.user}"

    @property
    def tax_rate(self):
        return settings.IMPUESTO_TASA

    @property
    def subtotal(self):
        return redondear(sum((item.subtotal for item in self.items.all()), start=Decimal("0")))

    @property
    def tax(self):
        return calcular_impuesto(self.subtotal)

    @property
    def total(self):
        return redondear(self.subtotal + self.tax)


class ItemCarrito(models.Model):
    cart = models.ForeignKey(Carrito, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name="items_carrito")
    slug = models.CharField(max_length=200)
    name = models.CharField(max_length=160)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    image = models.CharField(max_length=500)
    options = models.JSONField(default=list, blank=True)
    quantity = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])

    class Meta:
        verbose_name = "ítem de carrito"
        verbose_name_plural = "ítems de carrito"
        ordering = ["id"]
        constraints = [
            models.UniqueConstraint(fields=["cart", "product", "options"], name="linea_unica_por_opciones"),
            models.CheckConstraint(condition=models.Q(quantity__gte=1), name="cantidad_minima_1"),
        ]

    def __str__(self):
        return f"{self.quantity} x {self.name}"

    @property
    def subtotal(self):
        return self.price * self.quantity


class Pedido(models.Model):
    class Status(models.TextChoices):
        PAID = "paid", "Paid"
        SHIPPED = "shipped", "Shipped"
        DELIVERED = "delivered", "Delivered"
        CANCELLED = "cancelled", "Cancelled"
        REFUNDED = "refunded", "Refunded"

    REVENUE_STATUSES = (Status.PAID, Status.SHIPPED, Status.DELIVERED)
    RESTOCK_STATUSES = (Status.CANCELLED, Status.REFUNDED)

    cart = models.OneToOneField(
        Carrito, null=True, blank=True, on_delete=models.SET_NULL, related_name="order"
    )
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="pedidos"
    )
    number = models.CharField(max_length=20, unique=True, null=True, blank=True, editable=False)
    customer_name = models.CharField(max_length=120)
    customer_email = models.EmailField()
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=4, default=Decimal("0.08"))
    tax = models.DecimalField(max_digits=12, decimal_places=2)
    total = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PAID)
    shipping_address = models.JSONField(default=dict)
    card_last4 = models.CharField(
        max_length=4, validators=[RegexValidator(r"^\d{4}$", "Send the last 4 digits of the card.")]
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "pedido"
        verbose_name_plural = "pedidos"
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["status", "created_at"])]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(total=models.F("subtotal") + models.F("tax")),
                name="total_igual_subtotal_mas_impuesto",
            ),
        ]

    def __str__(self):
        return self.number or f"Pedido {self.pk}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if not self.number:
            self.number = f"NB-{1000 + self.pk}"
            super().save(update_fields=["number"])

    @property
    def units(self):
        return sum(line.quantity for line in self.lines.all())

    @property
    def counts_as_revenue(self):
        return self.status in self.REVENUE_STATUSES


class LineaPedido(models.Model):
    order = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name="lines")
    product = models.ForeignKey(
        Producto, null=True, blank=True, on_delete=models.SET_NULL, related_name="lineas_pedido"
    )
    slug = models.CharField(max_length=200)
    name = models.CharField(max_length=160)
    category = models.CharField(max_length=60, blank=True, default="")
    image = models.CharField(max_length=500)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    options = models.JSONField(default=list, blank=True)

    class Meta:
        verbose_name = "línea de pedido"
        verbose_name_plural = "líneas de pedido"
        ordering = ["id"]

    def __str__(self):
        return f"{self.quantity} x {self.name}"

    @property
    def subtotal(self):
        return self.price * self.quantity
