from django.utils import translation


class APIEnInglesMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not request.path.startswith("/api/"):
            return self.get_response(request)
        translation.activate("en")
        request.LANGUAGE_CODE = "en"
        try:
            return self.get_response(request)
        finally:
            translation.deactivate()
