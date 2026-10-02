from django.urls import path

from .views import admin, tienda

urlpatterns = [
    path("cart/", tienda.CarritoView.as_view(), name="carrito"),
    path("cart/items/", tienda.ItemCarritoCreateView.as_view(), name="carrito-items"),
    path("cart/items/<int:pk>/", tienda.ItemCarritoDetailView.as_view(), name="carrito-item-detalle"),
    path("orders/", tienda.CheckoutView.as_view(), name="checkout"),
    path("admin/orders/", admin.PedidoAdminListView.as_view(), name="admin-pedidos"),
    path("admin/orders/<int:pk>/", admin.PedidoAdminDetailView.as_view(), name="admin-pedido-detalle"),
    path("admin/dashboard/", admin.DashboardView.as_view(), name="admin-dashboard"),
]
