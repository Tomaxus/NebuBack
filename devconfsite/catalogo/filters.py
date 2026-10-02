import django_filters
from django.db.models import Q

from devconfsite.comun import normalizar_texto

from .models import Producto

AYUDA_CATEGORIA = "Nombre exacto de la categoría (no distingue mayúsculas), por ejemplo Iphone o Apple Watch. La lista sale de GET /api/categories/."


def buscar_en(queryset, texto, campos):
    for palabra in normalizar_texto(texto).split():
        condicion = Q()
        for campo in campos:
            condicion |= Q(**{f"{campo}__contains": palabra})
        queryset = queryset.filter(condicion)
    return queryset


class ProductoFilter(django_filters.FilterSet):
    category = django_filters.CharFilter(field_name="category__name", lookup_expr="iexact", help_text=AYUDA_CATEGORIA)
    is_new = django_filters.BooleanFilter(help_text="true = solo novedades.")
    recommended = django_filters.BooleanFilter(help_text="true = solo recomendados (carrusel del home).")
    search = django_filters.CharFilter(
        method="filtrar_busqueda",
        help_text="Texto libre. Todas las palabras deben aparecer en el nombre o la categoría. No distingue mayúsculas ni tildes.",
    )

    class Meta:
        model = Producto
        fields = ["category", "is_new", "recommended", "search"]

    def filtrar_busqueda(self, queryset, name, value):
        return buscar_en(queryset, value, ["search_text"])


class ProductoAdminFilter(django_filters.FilterSet):
    search = django_filters.CharFilter(
        method="filtrar_busqueda",
        help_text="Palabras contra nombre, slug y categoría. No distingue mayúsculas ni tildes.",
    )
    status = django_filters.ChoiceFilter(choices=Producto.Status.choices)
    category = django_filters.CharFilter(field_name="category__name", lookup_expr="iexact", help_text=AYUDA_CATEGORIA)
    low_stock = django_filters.BooleanFilter(method="filtrar_poco_stock", help_text="true = productos con stock de 5 o menos, de cualquier estado.")

    class Meta:
        model = Producto
        fields = ["search", "status", "category", "low_stock"]

    def filtrar_busqueda(self, queryset, name, value):
        return buscar_en(queryset, value, ["search_text", "slug"])

    def filtrar_poco_stock(self, queryset, name, value):
        return queryset.filter(stock__lte=5) if value else queryset
