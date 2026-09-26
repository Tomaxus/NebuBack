from django.urls import path

from . import views

urlpatterns = [
    path("cart/", views.CarritoView.as_view(), name="carrito"),
    path("cart/items/", views.ItemCarritoCreateView.as_view(), name="carrito-items"),
    path("cart/items/<int:pk>/", views.ItemCarritoDetailView.as_view(), name="carrito-item-detalle"),
    path("orders/", views.CheckoutView.as_view(), name="checkout"),
    path("admin/orders/", views.PedidoAdminListView.as_view(), name="admin-pedidos"),
    path("admin/orders/<int:pk>/", views.PedidoAdminDetailView.as_view(), name="admin-pedido-detalle"),
    path("admin/dashboard/", views.DashboardView.as_view(), name="admin-dashboard"),
]
