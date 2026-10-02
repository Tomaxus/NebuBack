from datetime import timezone as dt_timezone

from django.db import models
from rest_framework import serializers


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
