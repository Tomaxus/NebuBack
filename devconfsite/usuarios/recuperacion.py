import hashlib
import logging
import secrets
from datetime import timedelta
from html import escape

import resend
from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone
from rest_framework.serializers import ValidationError
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken

from devconfsite.comun import ReglaDeNegocio

from .models import TokenRecuperacion, Usuario

logger = logging.getLogger(__name__)

ENLACE_INVALIDO = "This link is invalid or has expired."
ASUNTO = "Reset your Nebulab password"


def hash_token(token):
    return hashlib.sha256(token.encode()).hexdigest()


def enlace_de(token):
    return f"{settings.FRONTEND_URL.rstrip('/')}/reset-password?token={token}"


def contenido_correo(enlace):
    minutos = settings.RESET_TOKEN_MINUTOS
    vigencia = "1 hour" if minutos == 60 else f"{minutos} minutes"
    texto = (
        "Hi,\n\n"
        "We received a request to reset your Nebulab password. Open the link below to choose a new one.\n"
        f"This link expires in {vigencia} and can only be used once.\n\n"
        f"{enlace}\n\n"
        "If you didn't request this, you can safely ignore this email.\n\n"
        "— Nebulab\n"
    )
    enlace_html = escape(enlace, quote=True)
    html = f"""<div style="font-family:Helvetica,Arial,sans-serif;max-width:480px;margin:0 auto;color:#16181d">
  <p>Hi,</p>
  <p>We received a request to reset your Nebulab password. Click the button below to choose a new one.
     This link expires in {vigencia} and can only be used once.</p>
  <p style="margin:28px 0"><a href="{enlace_html}" style="background:#111;color:#fff;padding:12px 22px;border-radius:999px;text-decoration:none;display:inline-block">Reset your password</a></p>
  <p style="color:#5b6270;font-size:13px">If the button doesn't work, copy this link into your browser:<br><a href="{enlace_html}">{enlace_html}</a></p>
  <p>If you didn't request this, you can safely ignore this email.</p>
  <p>— Nebulab</p>
</div>"""
    return texto, html


def enviar_correo(destinatario, enlace):
    texto, html = contenido_correo(enlace)
    if settings.RESEND_API_KEY:
        resend.api_key = settings.RESEND_API_KEY
        resend.Emails.send({
            "from": settings.RESET_PASSWORD_FROM,
            "to": [destinatario],
            "subject": ASUNTO,
            "html": html,
            "text": texto,
        })
    else:
        send_mail(ASUNTO, texto, settings.RESET_PASSWORD_FROM, [destinatario], html_message=html)


def solicitar_recuperacion(email):
    usuario = Usuario.objects.filter(email=email.strip().lower(), is_active=True).first()
    if usuario is None:
        return
    token = secrets.token_urlsafe(32)
    ahora = timezone.now()
    with transaction.atomic():
        TokenRecuperacion.objects.filter(user=usuario, used_at__isnull=True).update(used_at=ahora)
        TokenRecuperacion.objects.create(
            user=usuario,
            token_hash=hash_token(token),
            expires_at=ahora + timedelta(minutes=settings.RESET_TOKEN_MINUTOS),
        )
    try:
        enviar_correo(usuario.email, enlace_de(token))
    except Exception:
        logger.exception("No se pudo enviar el correo de recuperación a %s", usuario.email)


def cerrar_sesiones(usuario):
    for token in OutstandingToken.objects.filter(user=usuario):
        BlacklistedToken.objects.get_or_create(token=token)


@transaction.atomic
def confirmar_recuperacion(token, password):
    registro = (
        TokenRecuperacion.objects.select_for_update()
        .select_related("user")
        .filter(token_hash=hash_token(token or ""))
        .first()
    )
    if registro is None or registro.used_at is not None or registro.expires_at < timezone.now() or not registro.user.is_active:
        raise ReglaDeNegocio(ENLACE_INVALIDO)
    usuario = registro.user
    try:
        validate_password(password, usuario)
    except DjangoValidationError as error:
        raise ValidationError({"password": list(error.messages)})
    usuario.set_password(password)
    usuario.save(update_fields=["password"])
    registro.used_at = timezone.now()
    registro.save(update_fields=["used_at"])
    cerrar_sesiones(usuario)
