from django.urls import path

from . import views

urlpatterns = [
    path("categories/", views.CategoriaListView.as_view(), name="categorias"),
    path("products/", views.ProductoListView.as_view(), name="productos"),
    path("products/<slug:slug>/", views.ProductoDetailView.as_view(), name="producto-detalle"),
    path("admin/products/", views.ProductoAdminListView.as_view(), name="admin-productos"),
    path("admin/products/<int:pk>/", views.ProductoAdminDetailView.as_view(), name="admin-producto-detalle"),
]
