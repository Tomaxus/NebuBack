from drf_spectacular.utils import extend_schema
from rest_framework import generics, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from devconfsite.comun.limites import ThrottleRecuperacionEmail, ThrottleRecuperacionIP

from .. import recuperacion, sesiones
from ..serializers import (
    LoginSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetSerializer,
    RegistroSerializer,
    SesionSerializer,
    TipoSesionSerializer,
    UsuarioSerializer,
)

COOKIE = (
    "El refresh token no viaja en el JSON: llega en la cookie HttpOnly __Host-nebulab-refresh-{kind} "
    "(Secure, SameSite=Lax, Path=/). El frontend debe usar credentials: \"include\"."
)


def respuesta_sesion(usuario, tipo, codigo, refresh=None):
    refresh = refresh or sesiones.refresh_para(usuario, tipo)
    respuesta = Response({"access": str(refresh.access_token), "user": UsuarioSerializer(usuario).data}, status=codigo)
    sesiones.poner_cookie(respuesta, tipo, refresh)
    return respuesta


class VistaAuth(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_scope = "auth"

    def get_authenticate_header(self, request):
        return 'Bearer realm="api"'

    def finalize_response(self, request, response, *args, **kwargs):
        return sesiones.sin_cache(super().finalize_response(request, response, *args, **kwargs))


class VistaCookie(VistaAuth):
    """Endpoints que leen la cookie de sesión: solo aceptan peticiones de los orígenes del frontend (CSRF)."""

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        sesiones.exigir_origen_permitido(request)

    def tipo(self, request):
        serializer = TipoSesionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return serializer.validated_data["kind"]


@extend_schema(
    tags=["Autenticación"],
    summary="Registrar cliente",
    description="Crea la cuenta y abre la sesión de cliente. " + COOKIE,
    request=RegistroSerializer,
    responses={201: SesionSerializer},
)
class RegistroView(VistaAuth):
    def post(self, request):
        serializer = RegistroSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return respuesta_sesion(serializer.save(), sesiones.CLIENTE, status.HTTP_201_CREATED)


@extend_schema(
    tags=["Autenticación"],
    summary="Iniciar sesión",
    description=(
        "kind dice qué sesión se abre: customer (tienda) o admin (CMS). Credenciales incorrectas: 401 \"Wrong email or password.\". "
        "Cuenta de otro rol: 403 \"This account cannot sign in here.\". " + COOKIE
    ),
    request=LoginSerializer,
    responses={200: SesionSerializer},
)
class LoginView(VistaAuth):
    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        usuario, tipo = serializer.validated_data["user"], serializer.validated_data["kind"]
        sesiones.exigir_rol(usuario, tipo)
        return respuesta_sesion(usuario, tipo, status.HTTP_200_OK)


@extend_schema(
    tags=["Autenticación"],
    summary="Renovar el access token",
    description=(
        "Sin token en el cuerpo: usa la cookie del kind indicado, la rota y devuelve un access nuevo con el usuario. "
        "Cookie ausente, vencida, revocada o de otro rol: 401. Origen no permitido: 403. " + COOKIE
    ),
    request=TipoSesionSerializer,
    responses={200: SesionSerializer},
)
class RefreshView(VistaCookie):
    throttle_scope = "refresh"

    def post(self, request):
        tipo = self.tipo(request)
        usuario, refresh = sesiones.rotar(request.COOKIES.get(sesiones.nombre_cookie(tipo)), tipo)
        return respuesta_sesion(usuario, tipo, status.HTTP_200_OK, refresh)


@extend_schema(
    tags=["Autenticación"],
    summary="Cerrar sesión",
    description="Revoca la sesión del kind indicado y borra su cookie. Siempre 204, aunque el access haya vencido; no toca la otra sesión.",
    request=TipoSesionSerializer,
    responses={204: None},
)
class LogoutView(VistaCookie):
    throttle_scope = None

    def post(self, request):
        tipo = self.tipo(request)
        sesiones.cerrar(request.COOKIES.get(sesiones.nombre_cookie(tipo)), tipo)
        respuesta = Response(status=status.HTTP_204_NO_CONTENT)
        sesiones.borrar_cookie(respuesta, tipo)
        return respuesta


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
