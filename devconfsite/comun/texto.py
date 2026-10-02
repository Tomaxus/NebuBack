import re
import unicodedata

from django.db import models


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
