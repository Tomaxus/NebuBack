from django.contrib import admin

from .models import Categoria, Producto, Variante


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "slug")
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}


class VarianteInline(admin.TabularInline):
    model = Variante
    extra = 0
    fields = ("options", "price", "stock", "sku")


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    inlines = (VarianteInline,)
    list_display = ("name", "category", "price", "stock", "status", "is_new", "recommended", "updated_at")
    list_filter = ("category", "status", "is_new", "recommended")
    list_editable = ("price", "stock", "status", "is_new", "recommended")
    search_fields = ("name", "slug", "description")
    list_select_related = ("category",)
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ("updated_at",)

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        form.instance.recalcular_desde_variantes()
