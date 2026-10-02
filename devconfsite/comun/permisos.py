from rest_framework.permissions import BasePermission


class EsAdmin(BasePermission):
    message = "You do not have permission to perform this action."

    def has_permission(self, request, view):
        usuario = request.user
        return bool(usuario and usuario.is_authenticated and usuario.is_active and usuario.is_staff)
