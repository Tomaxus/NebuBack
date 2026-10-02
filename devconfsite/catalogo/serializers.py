import re
from decimal import Decimal

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from devconfsite.comun.campos import DineroField, SerializerBase
from devconfsite.comun.texto import crear_slug

from .models import Categoria, Producto, Variante, validate_image, validate_options
from .variantes import MENSAJE_PRECIO, MENSAJE_STOCK, validar_variantes

SLUG_VALIDO = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
MENSAJE_CATEGORIA = "Choose a valid category."
MENSAJE_NOMBRE = "The product needs a name."
MENSAJE_NOMBRE_CATEGORIA = "The category needs a name."
MENSAJE_SLUG = "Use only lowercase letters, numbers and hyphens."


class CategoriaSerializer(SerializerBase):
    class Meta:
        model = Categoria
        fields = ["id", "name", "slug"]


class CategoriaAdminSerializer(SerializerBase):
    name = serializers.CharField(
        max_length=60, error_messages={"blank": MENSAJE_NOMBRE_CATEGORIA, "required": MENSAJE_NOMBRE_CATEGORIA}
    )
    slug = serializers.CharField(max_length=50, required=False, allow_blank=True)
    products_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Categoria
        fields = ["id", "name", "slug", "products_count"]
        read_only_fields = ["id"]

    def otras(self):
        categorias = Categoria.objects.all()
        return categorias.exclude(pk=self.instance.pk) if self.instance else categorias

    def validate_name(self, value):
        value = " ".join(value.split())
        if self.otras().filter(name__iexact=value).exists():
            raise serializers.ValidationError("Another category already uses this name.")
        return value

    def validate(self, attrs):
        slug = attrs.get("slug")
        if slug is None and self.instance is not None:
            return attrs
        slug = slug or crear_slug(attrs.get("name") or self.instance.name)
        if not SLUG_VALIDO.match(slug):
            raise serializers.ValidationError({"slug": [MENSAJE_SLUG]})
        if self.otras().filter(slug=slug).exists():
            raise serializers.ValidationError({"slug": ["Another category already uses this slug."]})
        attrs["slug"] = slug
        return attrs

    @transaction.atomic
    def update(self, instance, validated_data):
        nombre_anterior = instance.name
        categoria = super().update(instance, validated_data)
        if categoria.name != nombre_anterior:
            for producto in categoria.productos.select_related("category"):
                producto.save(update_fields=["search_text"])
        return categoria


class OpcionSerializer(serializers.Serializer):
    name = serializers.CharField()
    values = serializers.ListField(child=serializers.CharField())
    layout = serializers.ChoiceField(choices=["wrap", "stack"], required=False)


@extend_schema_field(OpcionSerializer(many=True))
class OpcionesField(serializers.JSONField):
    def to_internal_value(self, data):
        data = super().to_internal_value(data)
        try:
            validate_options(data)
        except DjangoValidationError as error:
            raise serializers.ValidationError(error.messages)
        return data


class OpcionElegidaSerializer(serializers.Serializer):
    name = serializers.CharField()
    value = serializers.CharField()


class VarianteSerializer(SerializerBase):
    id = serializers.IntegerField(required=False)
    options = OpcionElegidaSerializer(many=True)
    price = DineroField()
    stock = serializers.IntegerField()
    sku = serializers.CharField(max_length=60, required=False, allow_blank=True, default="")

    class Meta:
        model = Variante
        fields = ["id", "options", "price", "stock", "sku"]


@extend_schema_field(VarianteSerializer(many=True))
class VariantesField(serializers.Field):
    def to_representation(self, variantes):
        return VarianteSerializer(variantes.all(), many=True).data

    def to_internal_value(self, data):
        if not isinstance(data, list):
            raise serializers.ValidationError("Send the combinations as a list.")
        return data


class ProductoSerializer(SerializerBase):
    name = serializers.CharField(max_length=160, error_messages={"blank": MENSAJE_NOMBRE, "required": MENSAJE_NOMBRE})
    slug = serializers.CharField(max_length=200, required=False, allow_blank=True)
    category = serializers.SlugRelatedField(
        slug_field="name",
        queryset=Categoria.objects.all(),
        error_messages={
            "does_not_exist": MENSAJE_CATEGORIA,
            "invalid": MENSAJE_CATEGORIA,
            "required": MENSAJE_CATEGORIA,
            "null": MENSAJE_CATEGORIA,
        },
    )
    price = DineroField(
        min_value=0,
        required=False,
        error_messages={"min_value": MENSAJE_PRECIO, "invalid": MENSAJE_PRECIO, "required": MENSAJE_PRECIO, "null": MENSAJE_PRECIO},
    )
    stock = serializers.IntegerField(
        min_value=0,
        required=False,
        error_messages={"min_value": MENSAJE_STOCK, "invalid": MENSAJE_STOCK, "required": MENSAJE_STOCK, "null": MENSAJE_STOCK},
    )
    image = serializers.CharField(max_length=500, validators=[validate_image])
    options = OpcionesField(required=False)
    variants = VariantesField(required=False)
    price_min = serializers.SerializerMethodField()
    price_max = serializers.SerializerMethodField()

    class Meta:
        model = Producto
        fields = [
            "id", "slug", "name", "category", "price", "image", "is_new", "recommended",
            "options", "variants", "status", "stock", "price_min", "price_max", "description", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def _precios(self, producto):
        precios = [v.price for v in producto.variants.all()]
        return (min(precios), max(precios)) if precios else (producto.price, producto.price)

    def get_price_min(self, producto) -> float:
        return float(self._precios(producto)[0])

    def get_price_max(self, producto) -> float:
        return float(self._precios(producto)[1])

    def validate(self, attrs):
        attrs = self._validar_slug(attrs)
        atributos = attrs.get("options", self.instance.options if self.instance else [])
        existentes = set(self.instance.variants.values_list("id", flat=True)) if self.instance else set()
        if "variants" in attrs:
            limpias, errores = validar_variantes(attrs["variants"], atributos, existentes)
            if errores:
                raise serializers.ValidationError({"variants": errores})
            attrs["variants"] = limpias
        elif self.instance is not None and "options" in attrs and existentes:
            actuales = [{"id": v.id, "options": v.options, "price": v.price, "stock": v.stock, "sku": v.sku} for v in self.instance.variants.all()]
            _, errores = validar_variantes(actuales, atributos, existentes)
            if errores:
                raise serializers.ValidationError({"variants": ["Update the combinations so they match the new attributes."]})
        tendra_variantes = bool(attrs.get("variants")) if "variants" in attrs else bool(existentes)
        if self.instance is None and not tendra_variantes:
            faltan = {}
            if "price" not in attrs:
                faltan["price"] = [MENSAJE_PRECIO]
            if "stock" not in attrs:
                faltan["stock"] = [MENSAJE_STOCK]
            if faltan:
                raise serializers.ValidationError(faltan)
        if self.instance is None and tendra_variantes:
            attrs.setdefault("price", Decimal("0"))
            attrs.setdefault("stock", 0)
        return attrs

    def _validar_slug(self, attrs):
        slug = attrs.get("slug")
        if slug is None and self.instance is not None:
            return attrs
        if not slug:
            nombre = attrs.get("name") or (self.instance.name if self.instance else "")
            slug = crear_slug(nombre)
        if not SLUG_VALIDO.match(slug):
            raise serializers.ValidationError({"slug": [MENSAJE_SLUG]})
        repetidos = Producto.objects.filter(slug=slug)
        if self.instance is not None:
            repetidos = repetidos.exclude(pk=self.instance.pk)
        if repetidos.exists():
            raise serializers.ValidationError({"slug": ["Another product already uses this slug."]})
        attrs["slug"] = slug
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        variantes = validated_data.pop("variants", None)
        producto = super().create(validated_data)
        if variantes:
            self._reemplazar_variantes(producto, variantes)
        return producto

    @transaction.atomic
    def update(self, instance, validated_data):
        variantes = validated_data.pop("variants", None)
        producto = super().update(instance, validated_data)
        if variantes is not None:
            self._reemplazar_variantes(producto, variantes)
        return producto

    def _reemplazar_variantes(self, producto, variantes):
        enviadas_ids = {v["id"] for v in variantes if v["id"] is not None}
        producto.variants.exclude(id__in=enviadas_ids).delete()
        actuales = {v.id: v for v in producto.variants.all()}
        for variante in actuales.values():
            variante.options_key = f"__tmp_{variante.id}"
        Variante.objects.bulk_update(actuales.values(), ["options_key"])
        for datos in variantes:
            variante = actuales.get(datos["id"]) or Variante(product=producto)
            variante.options, variante.price, variante.stock, variante.sku = datos["options"], datos["price"], datos["stock"], datos["sku"]
            variante.save()
        producto.recalcular_desde_variantes()
        if hasattr(producto, "_prefetched_objects_cache"):
            producto._prefetched_objects_cache.pop("variants", None)
