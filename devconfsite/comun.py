import hashlib
import re
import unicodedata
from datetime import timezone as dt_timezone

from django.db import models
from rest_framework import serializers
from rest_framework.exceptions import APIException
from rest_framework.filters import OrderingFilter
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import BasePermission
from rest_framework.throttling import SimpleRateThrottle


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


class ThrottleVentana(SimpleRateThrottle):
    """Límite de N peticiones en una ventana de minutos arbitraria (DRF solo admite s, m, h o d)."""

    peticiones = 3
    minutos = 15

    def get_rate(self):
        return f"{self.peticiones}/{self.minutos}min"

    def parse_rate(self, rate):
        return self.peticiones, self.minutos * 60


class ThrottleRecuperacionIP(ThrottleVentana):
    scope = "recuperacion_ip"

    def get_cache_key(self, request, view):
        return self.cache_format % {"scope": self.scope, "ident": self.get_ident(request)}


class ThrottleRecuperacionEmail(ThrottleVentana):
    scope = "recuperacion_email"

    def get_cache_key(self, request, view):
        email = request.data.get("email") if hasattr(request.data, "get") else None
        if not isinstance(email, str) or not email.strip():
            return None
        return self.cache_format % {"scope": self.scope, "ident": hashlib.sha256(email.strip().lower().encode()).hexdigest()}
