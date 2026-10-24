"""Sesiones con el refresh token en una cookie HttpOnly, una por tipo de sesión (cliente o admin).

El access token viaja en el JSON y el frontend lo guarda solo en memoria. El refresh nunca sale en el JSON:
vive en la cookie, rota en cada renovación y se revoca en el servidor (lista negra de simplejwt).
"""

from datetime import timedelta
from urllib.parse import urlsplit

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.utils.cache import add_never_cache_headers
from rest_framework.exceptions import AuthenticationFailed, PermissionDenied
from rest_framework_simplejwt.exceptions import TokenBackendError
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.state import token_backend
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Usuario

CLIENTE = "customer"
ADMIN = "admin"
TIPOS = (CLIENTE, ADMIN)
CLAIM_TIPO = "kind"

SESION_INVALIDA = "Your session has expired. Please sign in again."
ORIGEN_NO_PERMITIDO = "Origin not allowed."
TIPO_EQUIVOCADO = "This account cannot sign in here."


def nombre_cookie(tipo):
    return f"{settings.AUTH_COOKIE_PREFIJO}nebulab-refresh-{tipo}"


def rol_valido(usuario, tipo):
    return usuario.is_staff if tipo == ADMIN else usuario.role == Usuario.Role.CLIENTE


def exigir_rol(usuario, tipo):
    if not rol_valido(usuario, tipo):
        raise PermissionDenied(TIPO_EQUIVOCADO)


def refresh_para(usuario, tipo):
    refresh = RefreshToken.for_user(usuario)
    refresh[CLAIM_TIPO] = tipo
    # for_user registra el token antes de agregar kind; se guarda la versión final para poder revocar por tipo.
    OutstandingToken.objects.filter(jti=refresh["jti"]).update(token=str(refresh))
    return refresh


def poner_cookie(respuesta, tipo, refresh):
    respuesta.set_cookie(
        nombre_cookie(tipo),
        str(refresh),
        max_age=int(api_settings.REFRESH_TOKEN_LIFETIME.total_seconds()),
        path="/",
        domain=None,
        secure=settings.AUTH_COOKIE_SECURE,
        httponly=True,
        samesite=settings.AUTH_COOKIE_SAMESITE,
    )


def borrar_cookie(respuesta, tipo):
    respuesta.delete_cookie(nombre_cookie(tipo), path="/", domain=None, samesite=settings.AUTH_COOKIE_SAMESITE)
    # delete_cookie no marca Secure por sí sola salvo con el prefijo __Host-/__Secure-; se fuerza igual que al crearla.
    respuesta.cookies[nombre_cookie(tipo)]["secure"] = settings.AUTH_COOKIE_SECURE
    respuesta.cookies[nombre_cookie(tipo)]["httponly"] = True


def sin_cache(respuesta):
    add_never_cache_headers(respuesta)
    return respuesta


def origen_de(request):
    origen = request.headers.get("Origin")
    if origen:
        return origen
    referer = request.headers.get("Referer")
    if referer:
        partes = urlsplit(referer)
        return f"{partes.scheme}://{partes.netloc}"
    return None


def exigir_origen_permitido(request):
    """Defensa CSRF de los endpoints que leen la cookie: el origen debe estar en la lista exacta."""
    if origen_de(request) not in settings.AUTH_ORIGENES_PERMITIDOS:
        raise PermissionDenied(ORIGEN_NO_PERMITIDO)


def decodificar(crudo):
    try:
        return token_backend.decode(crudo, verify=True)
    except TokenBackendError:
        return None


def tipo_de(token_registrado):
    datos = decodificar(token_registrado.token) or {}
    return datos.get(CLAIM_TIPO)


def revocar(usuario, tipo=None):
    """Revoca las sesiones del usuario; con tipo, solo las de ese tipo."""
    for registro in OutstandingToken.objects.filter(user=usuario, blacklistedtoken__isnull=True):
        if tipo is None or tipo_de(registro) == tipo:
            BlacklistedToken.objects.get_or_create(token=registro)


def rotar(crudo, tipo):
    """Cambia el refresh de la cookie por uno nuevo y devuelve (usuario, refresh nuevo).

    La fila del token se bloquea, así que de dos renovaciones simultáneas con el mismo token solo una gana;
    la otra recibe 401 y el frontend reintenta con la cookie nueva. Si llega un token ya rotado fuera del margen
    de gracia, se asume robo y se cierran todas las sesiones de ese tipo.
    """
    # Las revocaciones se confirman antes de responder 401: un error dentro de atomic las desharía.
    with transaction.atomic():
        resultado = _rotar(crudo, tipo)
    if resultado is None:
        raise AuthenticationFailed(SESION_INVALIDA)
    return resultado


def _rotar(crudo, tipo):
    datos = decodificar(crudo or "")
    if not datos or datos.get("token_type") != "refresh" or datos.get(CLAIM_TIPO) != tipo:
        return None
    registro = OutstandingToken.objects.select_for_update().select_related("user").filter(jti=datos["jti"]).first()
    if registro is None or registro.user is None:
        return None
    usuario = registro.user
    revocado = BlacklistedToken.objects.filter(token=registro).first()
    if revocado is not None:
        margen = timedelta(seconds=settings.AUTH_REFRESH_GRACIA_SEGUNDOS)
        if revocado.blacklisted_at < timezone.now() - margen:
            revocar(usuario, tipo)
        return None
    BlacklistedToken.objects.create(token=registro)
    if not usuario.is_active or not rol_valido(usuario, tipo):
        return None
    return usuario, refresh_para(usuario, tipo)


def cerrar(crudo, tipo):
    """Revoca el refresh de la cookie si es válido; no falla si ya venció o no existe (logout idempotente)."""
    datos = decodificar(crudo or "")
    if not datos or datos.get(CLAIM_TIPO) != tipo:
        return
    registro = OutstandingToken.objects.filter(jti=datos.get("jti")).first()
    if registro is not None:
        BlacklistedToken.objects.get_or_create(token=registro)
