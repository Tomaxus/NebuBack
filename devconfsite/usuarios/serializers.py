from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.tokens import RefreshToken

from devconfsite.comun import DineroField, FechaUTCField, SerializerBase

from .models import Usuario

CREDENCIALES_INVALIDAS = "Wrong email or password."


def tokens_para(usuario):
    refresh = RefreshToken.for_user(usuario)
    return {"access": str(refresh.access_token), "refresh": str(refresh)}


def email_en_uso(email, excluir=None):
    usuarios = Usuario.objects.filter(email__iexact=email)
    if excluir is not None:
        usuarios = usuarios.exclude(pk=excluir.pk)
    return usuarios.exists()


class UsuarioSerializer(SerializerBase):
    class Meta:
        model = Usuario
        fields = ["id", "name", "email", "role"]
        read_only_fields = fields


class SesionSerializer(serializers.Serializer):
    access = serializers.CharField()
    refresh = serializers.CharField()
    user = UsuarioSerializer()


class RegistroSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=120, error_messages={"blank": "Enter your name.", "required": "Enter your name."})
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate_email(self, value):
        value = value.strip().lower()
        existente = Usuario.objects.filter(email=value).first()
        if existente and existente.has_usable_password():
            raise serializers.ValidationError("An account with this email already exists.")
        self.context["existente"] = existente
        return value

    def validate(self, attrs):
        candidato = self.context.get("existente") or Usuario(email=attrs["email"], name=attrs["name"])
        try:
            validate_password(attrs["password"], candidato)
        except DjangoValidationError as error:
            raise serializers.ValidationError({"password": list(error.messages)})
        return attrs

    def create(self, validated_data):
        existente = self.context.get("existente")
        if existente:
            existente.name = validated_data["name"]
            existente.set_password(validated_data["password"])
            existente.save()
            return existente
        return Usuario.objects.create_user(
            email=validated_data["email"], name=validated_data["name"], password=validated_data["password"]
        )


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate(self, attrs):
        usuario = authenticate(
            request=self.context.get("request"),
            username=attrs["email"].strip().lower(),
            password=attrs["password"],
        )
        if usuario is None:
            raise AuthenticationFailed(CREDENCIALES_INVALIDAS)
        attrs["user"] = usuario
        return attrs


class RefreshSerializer(TokenRefreshSerializer):
    def validate(self, attrs):
        try:
            return super().validate(attrs)
        except Usuario.DoesNotExist:
            raise AuthenticationFailed("No active account found for the given token.", "no_active_account")


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()


class PasswordResetSerializer(serializers.Serializer):
    email = serializers.EmailField()


class ClienteAdminSerializer(SerializerBase):
    name = serializers.CharField(
        max_length=120,
        error_messages={"blank": "The customer needs a name.", "required": "The customer needs a name."},
    )
    email = serializers.EmailField(error_messages={"invalid": "Enter a valid email address."})
    orders_count = serializers.IntegerField(read_only=True, default=0)
    total_spent = DineroField(read_only=True, default=0)
    last_order_at = FechaUTCField(read_only=True, allow_null=True, default=None)

    class Meta:
        model = Usuario
        fields = ["id", "name", "email", "status", "notes", "created_at", "orders_count", "total_spent", "last_order_at"]
        read_only_fields = ["id", "created_at"]

    def validate_email(self, value):
        value = value.strip().lower()
        if email_en_uso(value, excluir=self.instance):
            raise serializers.ValidationError("Another customer already uses this email.")
        return value

    def create(self, validated_data):
        return Usuario.objects.create_user(
            email=validated_data["email"],
            name=validated_data["name"],
            password=None,
            notes=validated_data.get("notes", ""),
            status=validated_data.get("status", Usuario.Status.ACTIVE),
        )


class AdminSerializer(SerializerBase):
    name = serializers.CharField(
        max_length=120,
        error_messages={"blank": "The admin needs a name.", "required": "The admin needs a name."},
    )
    email = serializers.EmailField(error_messages={"invalid": "Enter a valid email address."})
    password = serializers.CharField(write_only=True, trim_whitespace=False)
    created_by_name = serializers.CharField(source="created_by.name", read_only=True, allow_null=True, default=None)

    class Meta:
        model = Usuario
        fields = ["id", "name", "email", "password", "created_at", "created_by", "created_by_name"]
        read_only_fields = ["id", "created_at", "created_by"]

    def validate_email(self, value):
        value = value.strip().lower()
        if email_en_uso(value):
            raise serializers.ValidationError("Another admin already uses this email.")
        return value

    def validate_password(self, value):
        if len(value) < 8:
            raise serializers.ValidationError("Use at least 8 characters.")
        return value

    def create(self, validated_data):
        return Usuario.objects.create_user(
            email=validated_data["email"],
            name=validated_data["name"],
            password=validated_data["password"],
            role=Usuario.Role.ADMIN,
            created_by=self.context["request"].user,
        )
