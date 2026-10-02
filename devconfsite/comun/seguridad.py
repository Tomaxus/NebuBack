import re

from djangorestframework_camel_case.parser import CamelCaseJSONParser
from rest_framework.exceptions import ValidationError

ETIQUETA_HTML = re.compile(r"<\s*[/!?]?\s*[a-zA-Z][^>]*>|<!--")
MENSAJE_HTML = "HTML tags are not allowed."
CAMPOS_SIN_REVISAR = {"password", "token", "refresh", "access"}

CSP_API = "default-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'"
CSP_DOCS = (
    "default-src 'self'; script-src 'self' https://cdn.jsdelivr.net; "
    "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; img-src 'self' data: https://cdn.jsdelivr.net; "
    "connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
)
CSP_SITIO = (
    "default-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; "
    "frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
)


def tiene_html(valor):
    if isinstance(valor, str):
        return bool(ETIQUETA_HTML.search(valor))
    if isinstance(valor, dict):
        return any(tiene_html(v) for v in valor.values())
    if isinstance(valor, list):
        return any(tiene_html(v) for v in valor)
    return False


class ParserSinHTML(CamelCaseJSONParser):
    """Rechaza con 400 cualquier texto que traiga etiquetas HTML, para que nunca se guarde un script (XSS almacenado)."""

    def parse(self, stream, media_type=None, parser_context=None):
        datos = super().parse(stream, media_type, parser_context)
        if isinstance(datos, dict):
            errores = {campo: [MENSAJE_HTML] for campo, valor in datos.items() if campo not in CAMPOS_SIN_REVISAR and tiene_html(valor)}
            if errores:
                raise ValidationError(errores)
        elif tiene_html(datos):
            raise ValidationError({"non_field_errors": [MENSAJE_HTML]})
        return datos


class PoliticaContenidoMiddleware:
    """Agrega Content-Security-Policy: la API no carga nada, Swagger solo su CDN y el resto solo recursos propios."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        respuesta = self.get_response(request)
        if request.path.startswith("/api/docs/"):
            politica = CSP_DOCS
        elif request.path.startswith("/api/"):
            politica = CSP_API
        else:
            politica = CSP_SITIO
        respuesta.headers.setdefault("Content-Security-Policy", politica)
        return respuesta
