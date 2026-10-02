from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerSplitView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerSplitView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/", include("devconfsite.usuarios.urls")),
    path("api/", include("devconfsite.catalogo.urls")),
    path("api/", include("devconfsite.carrito.urls")),
]
