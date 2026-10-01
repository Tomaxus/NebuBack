from django.urls import path

from . import views

urlpatterns = [
    path("auth/register/", views.RegistroView.as_view(), name="auth-register"),
    path("auth/login/", views.LoginView.as_view(), name="auth-login"),
    path("auth/refresh/", views.RefreshView.as_view(), name="auth-refresh"),
    path("auth/logout/", views.LogoutView.as_view(), name="auth-logout"),
    path("auth/me/", views.MeView.as_view(), name="auth-me"),
    path("auth/password-reset/", views.PasswordResetView.as_view(), name="auth-password-reset"),
    path("auth/password-reset/confirm/", views.PasswordResetConfirmView.as_view(), name="auth-password-reset-confirm"),
    path("admin/customers/", views.ClienteAdminListView.as_view(), name="admin-clientes"),
    path("admin/customers/<int:pk>/", views.ClienteAdminDetailView.as_view(), name="admin-cliente-detalle"),
    path("admin/admins/", views.AdminListView.as_view(), name="admin-admins"),
    path("admin/admins/<int:pk>/", views.AdminDetailView.as_view(), name="admin-admin-detalle"),
]
