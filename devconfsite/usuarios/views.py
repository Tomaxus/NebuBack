from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.db.models import Count, DecimalField, Max, Q, Sum, Value
from django.db.models.functions import Coalesce
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import generics, status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView

from devconfsite.comun import EsAdmin, OrdenamientoEstable, ReglaDeNegocio, filtrar_por_palabras

from .models import Usuario
from .serializers import (
    AdminSerializer,
    ClienteAdminSerializer,
    LoginSerializer,
    LogoutSerializer,
    PasswordResetSerializer,
    RefreshSerializer,
    RegistroSerializer,
    SesionSerializer,
    UsuarioSerializer,
    tokens_para,
)


def respuesta_sesion(usuario, codigo):
    return Response({**tokens_para(usuario), "user": UsuarioSerializer(usuario).data}, status=codigo)


class VistaAuth(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_scope = "auth"

    def get_authenticate_header(self, request):
        return 'Bearer realm="api"'


@extend_schema(tags=["Autenticación"], summary="Registrar cliente", request=RegistroSerializer, responses={201: SesionSerializer})
class RegistroView(VistaAuth):
    def post(self, request):
        serializer = RegistroSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return respuesta_sesion(serializer.save(), status.HTTP_201_CREATED)


@extend_schema(
    tags=["Autenticación"],
    summary="Iniciar sesión",
    description="Sirve para clientes y admins. El rol viene en user.role. Credenciales incorrectas: 401 \"Wrong email or password.\"",
    request=LoginSerializer,
    responses={200: SesionSerializer},
)
class LoginView(VistaAuth):
    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        return respuesta_sesion(serializer.validated_data["user"], status.HTTP_200_OK)


@extend_schema(tags=["Autenticación"], summary="Renovar el access token", description="Devuelve un access y un refresh nuevos. El refresh anterior deja de servir.")
class RefreshView(TokenRefreshView):
    serializer_class = RefreshSerializer
    throttle_scope = "auth"


@extend_schema(tags=["Autenticación"], summary="Cerrar sesión", request=LogoutSerializer, responses={204: None})
class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            token = RefreshToken(serializer.validated_data["refresh"])
            if str(token.get("user_id")) != str(request.user.pk):
                raise TokenError()
            token.blacklist()
        except TokenError:
            raise ValidationError({"refresh": ["Token is invalid or expired."]})
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(tags=["Autenticación"], summary="Usuario actual", responses=UsuarioSerializer)
class MeView(generics.RetrieveAPIView):
    serializer_class = UsuarioSerializer

    def get_object(self):
        return self.request.user


@extend_schema(
    tags=["Autenticación"],
    summary="Olvidé mi contraseña",
    description="Siempre responde 204, exista o no el email. Si existe, el enlace se envía por correo (en desarrollo se imprime en la consola).",
    request=PasswordResetSerializer,
    responses={204: None},
)
class PasswordResetView(VistaAuth):
    def post(self, request):
        serializer = PasswordResetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        usuario = Usuario.objects.filter(email=serializer.validated_data["email"].strip().lower(), is_active=True).first()
        if usuario:
            uid = urlsafe_base64_encode(force_bytes(usuario.pk))
            token = default_token_generator.make_token(usuario)
            enlace = f"{settings.FRONTEND_URL}/reset-password?uid={uid}&token={token}"
            send_mail(
                "Nebulab: reset your password",
                f"Hi {usuario.name},\n\nUse this link to choose a new password:\n{enlace}\n",
                None,
                [usuario.email],
            )
        return Response(status=status.HTTP_204_NO_CONTENT)


def clientes_con_estadisticas():
    from devconfsite.carrito.models import Pedido

    ingresos = Q(pedidos__status__in=Pedido.REVENUE_STATUSES)
    return Usuario.objects.filter(role=Usuario.Role.CLIENTE).annotate(
        orders_count=Count("pedidos", distinct=True),
        total_spent=Coalesce(
            Sum("pedidos__total", filter=ingresos), Value(0), output_field=DecimalField(max_digits=12, decimal_places=2)
        ),
        last_order_at=Max("pedidos__created_at"),
    )


class VistaAdmin:
    permission_classes = [EsAdmin]
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]


@extend_schema_view(
    get=extend_schema(
        summary="Listar clientes",
        description="Solo usuarios con rol cliente, con ordersCount, totalSpent y lastOrderAt calculados. 10 por página.",
        parameters=[
            OpenApiParameter("search", OpenApiTypes.STR, description="Palabras contra nombre y email."),
            OpenApiParameter(
                "ordering",
                OpenApiTypes.STR,
                enum=[v for c in ["name", "status", "orders_count", "total_spent", "last_order_at", "created_at"] for v in (c, f"-{c}")],
                description="Por defecto -created_at.",
            ),
        ],
    ),
    post=extend_schema(summary="Crear cliente", description="Se crea sin contraseña. Cuando esa persona se registre con el mismo email, reclama la cuenta."),
)
@extend_schema(tags=["Admin · Clientes"])
class ClienteAdminListView(VistaAdmin, generics.ListCreateAPIView):
    serializer_class = ClienteAdminSerializer
    filterset_fields = ["status"]
    ordering_fields = ["name", "status", "orders_count", "total_spent", "last_order_at", "created_at"]
    ordering = ["-created_at"]

    def get_queryset(self):
        clientes = clientes_con_estadisticas()
        buscar = self.request.query_params.get("search")
        if buscar:
            clientes = filtrar_por_palabras(clientes, buscar, ["name", "email"])
        return clientes

    def perform_create(self, serializer):
        serializer.instance = clientes_con_estadisticas().get(pk=serializer.save().pk)


@extend_schema_view(
    get=extend_schema(summary="Ver cliente"),
    patch=extend_schema(summary="Editar o bloquear cliente", description="Actualización parcial de name, email, notes o status."),
    delete=extend_schema(summary="Borrar cliente", description="Sus pedidos se conservan con el nombre y email copiados."),
)
@extend_schema(tags=["Admin · Clientes"])
class ClienteAdminDetailView(VistaAdmin, generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ClienteAdminSerializer

    def get_queryset(self):
        return clientes_con_estadisticas()

    def perform_update(self, serializer):
        serializer.instance = clientes_con_estadisticas().get(pk=serializer.save().pk)


@extend_schema_view(
    get=extend_schema(
        summary="Listar admins",
        parameters=[OpenApiParameter("ordering", OpenApiTypes.STR, enum=["created_at", "-created_at", "name", "-name"], description="Por defecto -created_at.")],
    ),
    post=extend_schema(summary="Crear admin", description="El admin que hace la petición queda registrado en createdBy."),
)
@extend_schema(tags=["Admin · Admins"])
class AdminListView(VistaAdmin, generics.ListCreateAPIView):
    serializer_class = AdminSerializer
    queryset = Usuario.objects.filter(role=Usuario.Role.ADMIN).select_related("created_by")
    filter_backends = [OrdenamientoEstable]
    ordering_fields = ["created_at", "name"]
    ordering = ["-created_at"]


@extend_schema(
    tags=["Admin · Admins"],
    summary="Borrar admin",
    description="No se puede borrar la propia cuenta ni dejar el sistema sin admins.",
)
class AdminDetailView(VistaAdmin, generics.DestroyAPIView):
    queryset = Usuario.objects.filter(role=Usuario.Role.ADMIN)
    serializer_class = AdminSerializer

    def perform_destroy(self, instance):
        if instance.pk == self.request.user.pk:
            raise ReglaDeNegocio("You cannot delete your own account.")
        if not Usuario.objects.filter(role=Usuario.Role.ADMIN).exclude(pk=instance.pk).exists():
            raise ReglaDeNegocio("There must be at least one admin.")
        instance.delete()
