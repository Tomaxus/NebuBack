from django.urls import path

from .views import admin, publico

urlpatterns = [
    path("categories/", publico.CategoriaListView.as_view(), name="categorias"),
    path("products/", publico.ProductoListView.as_view(), name="productos"),
    path("products/<slug:slug>/", publico.ProductoDetailView.as_view(), name="producto-detalle"),
    path("admin/categories/", admin.CategoriaAdminListView.as_view(), name="admin-categorias"),
    path("admin/categories/<int:pk>/", admin.CategoriaAdminDetailView.as_view(), name="admin-categoria-detalle"),
    path("admin/products/", admin.ProductoAdminListView.as_view(), name="admin-productos"),
    path("admin/products/<int:pk>/", admin.ProductoAdminDetailView.as_view(), name="admin-producto-detalle"),
]
