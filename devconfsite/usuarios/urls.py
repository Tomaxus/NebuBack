from django.urls import path

from .views import admin, auth

urlpatterns = [
    path("auth/register/", auth.RegistroView.as_view(), name="auth-register"),
    path("auth/login/", auth.LoginView.as_view(), name="auth-login"),
    path("auth/refresh/", auth.RefreshView.as_view(), name="auth-refresh"),
    path("auth/logout/", auth.LogoutView.as_view(), name="auth-logout"),
    path("auth/me/", auth.MeView.as_view(), name="auth-me"),
    path("auth/password-reset/", auth.PasswordResetView.as_view(), name="auth-password-reset"),
    path("auth/password-reset/confirm/", auth.PasswordResetConfirmView.as_view(), name="auth-password-reset-confirm"),
    path("admin/customers/", admin.ClienteAdminListView.as_view(), name="admin-clientes"),
    path("admin/customers/<int:pk>/", admin.ClienteAdminDetailView.as_view(), name="admin-cliente-detalle"),
    path("admin/admins/", admin.AdminListView.as_view(), name="admin-admins"),
    path("admin/admins/<int:pk>/", admin.AdminDetailView.as_view(), name="admin-admin-detalle"),
]
