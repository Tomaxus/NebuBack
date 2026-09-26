import re

from django.core.exceptions import ValidationError as DjangoValidationError
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from devconfsite.comun import DineroField, SerializerBase, crear_slug

from .models import Categoria, Producto, validate_image, validate_options

SLUG_VALIDO = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
MENSAJE_PRECIO = "Enter a price of 0 or more."
MENSAJE_STOCK = "Stock must be a whole number, 0 or more."
MENSAJE_CATEGORIA = "Choose a valid category."
MENSAJE_NOMBRE = "The product needs a name."


class CategoriaSerializer(SerializerBase):
    class Meta:
        model = Categoria
        fields = ["id", "name", "slug"]


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
        error_messages={"min_value": MENSAJE_PRECIO, "invalid": MENSAJE_PRECIO, "required": MENSAJE_PRECIO, "null": MENSAJE_PRECIO},
    )
    stock = serializers.IntegerField(
        min_value=0,
        error_messages={"min_value": MENSAJE_STOCK, "invalid": MENSAJE_STOCK, "required": MENSAJE_STOCK, "null": MENSAJE_STOCK},
    )
    image = serializers.CharField(max_length=500, validators=[validate_image])
    options = OpcionesField(required=False)

    class Meta:
        model = Producto
        fields = [
            "id", "slug", "name", "category", "price", "image", "is_new", "recommended",
            "options", "status", "stock", "description", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate(self, attrs):
        slug = attrs.get("slug")
        if slug is None and self.instance is not None:
            return attrs
        if not slug:
            nombre = attrs.get("name") or (self.instance.name if self.instance else "")
            slug = crear_slug(nombre)
        if not SLUG_VALIDO.match(slug):
            raise serializers.ValidationError({"slug": ["Use only lowercase letters, numbers and hyphens."]})
        repetidos = Producto.objects.filter(slug=slug)
        if self.instance is not None:
            repetidos = repetidos.exclude(pk=self.instance.pk)
        if repetidos.exists():
            raise serializers.ValidationError({"slug": ["Another product already uses this slug."]})
        attrs["slug"] = slug
        return attrs
