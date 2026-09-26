from django.contrib import admin

from .models import Carrito, ItemCarrito, LineaPedido, Pedido


class ItemCarritoInline(admin.TabularInline):
    model = ItemCarrito
    extra = 0
    autocomplete_fields = ("product",)


class LineaPedidoInline(admin.TabularInline):
    model = LineaPedido
    extra = 0
    can_delete = False
    readonly_fields = ("product", "slug", "name", "category", "image", "price", "quantity", "options")

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Carrito)
class CarritoAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("user__email",)
    inlines = (ItemCarritoInline,)


@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = ("number", "customer_name", "customer_email", "subtotal", "tax", "total", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("number", "customer_name", "customer_email")
    readonly_fields = ("number", "cart", "customer", "subtotal", "tax_rate", "tax", "total", "created_at", "updated_at")
    inlines = (LineaPedidoInline,)
