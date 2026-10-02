import hashlib

from rest_framework.throttling import SimpleRateThrottle


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
