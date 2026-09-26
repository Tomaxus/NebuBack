import re
import unicodedata
from datetime import timezone as dt_timezone

from django.db import models
from rest_framework import serializers
from rest_framework.exceptions import APIException
from rest_framework.filters import OrderingFilter
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import BasePermission


def normalizar_texto(texto):
    sin_tildes = unicodedata.normalize("NFKD", texto or "")
    return "".join(c for c in sin_tildes if not unicodedata.combining(c)).lower()


def crear_slug(texto):
    return re.sub(r"[^a-z0-9]+", "-", normalizar_texto(texto)).strip("-")


def filtrar_por_palabras(queryset, texto, campos):
    for palabra in (texto or "").split():
        variantes = {palabra, normalizar_texto(palabra)}
        condicion = models.Q()
        for campo in campos:
            for variante in variantes:
                condicion |= models.Q(**{f"{campo}__icontains": variante})
        queryset = queryset.filter(condicion)
    return queryset.distinct()


class FechaUTCField(serializers.DateTimeField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("default_timezone", dt_timezone.utc)
        super().__init__(*args, **kwargs)


class DineroField(serializers.DecimalField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("max_digits", 12)
        kwargs.setdefault("decimal_places", 2)
        kwargs.setdefault("coerce_to_string", False)
        super().__init__(*args, **kwargs)


class SerializerBase(serializers.ModelSerializer):
    serializer_field_mapping = {
        **serializers.ModelSerializer.serializer_field_mapping,
        models.DateTimeField: FechaUTCField,
    }


class Paginacion(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100


class OrdenamientoEstable(OrderingFilter):
    def get_ordering(self, request, queryset, view):
        orden = super().get_ordering(request, queryset, view) or []
        alias = getattr(view, "ordering_aliases", {})
        traducido = []
        for campo in orden:
            signo = "-" if campo.startswith("-") else ""
            traducido.append(signo + alias.get(campo.lstrip("-"), campo.lstrip("-")))
        return traducido

    def filter_queryset(self, request, queryset, view):
        queryset = super().filter_queryset(request, queryset, view)
        orden = list(queryset.query.order_by or queryset.model._meta.ordering)
        if "id" not in orden and "-id" not in orden:
            queryset = queryset.order_by(*orden, "id")
        return queryset


class EsAdmin(BasePermission):
    message = "You do not have permission to perform this action."

    def has_permission(self, request, view):
        usuario = request.user
        return bool(usuario and usuario.is_authenticated and usuario.is_active and usuario.is_staff)


class ReglaDeNegocio(APIException):
    status_code = 400
    default_detail = "This action is not allowed."
    default_code = "business_rule"
