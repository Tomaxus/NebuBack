from drf_spectacular.utils import extend_schema
from rest_framework import generics, status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView

from devconfsite.comun.limites import ThrottleRecuperacionEmail, ThrottleRecuperacionIP

from .. import recuperacion
from ..serializers import (
    LoginSerializer,
    LogoutSerializer,
    PasswordResetConfirmSerializer,
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
    description=(
        "Siempre responde 204, exista o no el email. Si existe, envía con Resend un enlace de un solo uso "
        "a {FRONTEND_URL}/reset-password?token=... que vence en 1 hora. Límite: 3 solicitudes por email y por IP cada 15 minutos."
    ),
    request=PasswordResetSerializer,
    responses={204: None},
)
class PasswordResetView(VistaAuth):
    throttle_classes = [ScopedRateThrottle, ThrottleRecuperacionIP, ThrottleRecuperacionEmail]

    def post(self, request):
        serializer = PasswordResetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        recuperacion.solicitar_recuperacion(serializer.validated_data["email"])
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(
    tags=["Autenticación"],
    summary="Guardar la contraseña nueva",
    description=(
        "Recibe el token del correo y la contraseña nueva. El token sirve una sola vez. "
        "Token inexistente, usado o vencido: 400 \"This link is invalid or has expired.\". "
        "Cierra todas las sesiones abiertas del usuario."
    ),
    request=PasswordResetConfirmSerializer,
    responses={204: None},
)
class PasswordResetConfirmView(VistaAuth):
    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        recuperacion.confirmar_recuperacion(serializer.validated_data["token"], serializer.validated_data["password"])
        return Response(status=status.HTTP_204_NO_CONTENT)
