from django.db import IntegrityError, transaction
from rest_framework.exceptions import NotFound
from rest_framework.serializers import ValidationError

from devconfsite.catalogo.models import Producto, Variante, clave_variante
from devconfsite.comun.excepciones import ReglaDeNegocio

from ..models import Carrito, ItemCarrito


def mensaje_stock(stock):
    return "This product is sold out." if stock == 0 else f"Only {stock} left in stock."


def carrito_activo(usuario):
    try:
        with transaction.atomic():
            carrito, _ = Carrito.objects.get_or_create(user=usuario, status=Carrito.Status.ACTIVE)
    except IntegrityError:
        carrito = Carrito.objects.get(user=usuario, status=Carrito.Status.ACTIVE)
    return carrito


def normalizar_opciones(producto, elegidas):
    mensaje = "Choose a valid value for every attribute of this product."
    if not isinstance(elegidas, list):
        raise ValidationError({"options": [mensaje]})
    por_nombre = {}
    for opcion in elegidas:
        if not isinstance(opcion, dict) or not isinstance(opcion.get("name"), str) or not isinstance(opcion.get("value"), str):
            raise ValidationError({"options": [mensaje]})
        if opcion["name"] in por_nombre:
            raise ValidationError({"options": [mensaje]})
        por_nombre[opcion["name"]] = opcion["value"]
    nombres_producto = [opcion["name"] for opcion in producto.options]
    if set(por_nombre) != set(nombres_producto):
        raise ValidationError({"options": [mensaje]})
    normalizadas = []
    for opcion in producto.options:
        valor = por_nombre[opcion["name"]]
        if valor not in opcion["values"]:
            raise ValidationError({"options": [mensaje]})
        normalizadas.append({"name": opcion["name"], "value": valor})
    return normalizadas


def variante_de(producto, opciones, bloquear=False):
    variantes = Variante.objects.filter(product=producto, options_key=clave_variante(opciones))
    if bloquear:
        variantes = variantes.select_for_update()
    return variantes.first()


@transaction.atomic
def agregar_al_carrito(usuario, slug, opciones):
    producto = Producto.objects.select_for_update().filter(slug=slug, status=Producto.Status.LIVE).first()
    if producto is None:
        raise ValidationError({"slug": ["This product is not available."]})
    opciones = normalizar_opciones(producto, opciones)
    variante = None
    if producto.variants.exists():
        variante = variante_de(producto, opciones, bloquear=True)
        if variante is None:
            raise ReglaDeNegocio("That combination is not available.")
        if variante.stock <= 0:
            raise ReglaDeNegocio("Sold out.")
    carrito = carrito_activo(usuario)
    item = ItemCarrito.objects.filter(cart=carrito, product=producto, options=opciones).first()
    nueva_cantidad = (item.quantity if item else 0) + 1
    if variante is not None:
        if nueva_cantidad > variante.stock:
            raise ReglaDeNegocio(f"Only {variante.stock} left in stock.")
    elif nueva_cantidad > producto.stock:
        raise ValidationError({"quantity": [mensaje_stock(producto.stock)]})
    if item:
        item.quantity = nueva_cantidad
        item.variant = variante
        item.save(update_fields=["quantity", "variant"])
    else:
        ItemCarrito.objects.create(
            cart=carrito,
            product=producto,
            variant=variante,
            slug=producto.slug,
            name=producto.name,
            price=variante.price if variante else producto.price,
            image=producto.image,
            options=opciones,
            quantity=1,
        )
    return carrito


def stock_de_linea(item):
    if item.variant_id is not None:
        return item.variant.stock
    if item.product.variants.exists():
        variante = variante_de(item.product, item.options)
        return variante.stock if variante else 0
    return item.product.stock


def item_del_usuario(usuario, item_id):
    item = (
        ItemCarrito.objects.select_related("product", "variant", "cart")
        .filter(pk=item_id, cart__user=usuario, cart__status=Carrito.Status.ACTIVE)
        .first()
    )
    if item is None:
        raise NotFound()
    return item


@transaction.atomic
def cambiar_cantidad(usuario, item_id, cantidad):
    item = item_del_usuario(usuario, item_id)
    if cantidad == 0:
        item.delete()
        return item.cart
    disponible = stock_de_linea(item)
    if cantidad > disponible:
        raise ValidationError({"quantity": [mensaje_stock(disponible)]})
    item.quantity = cantidad
    item.save(update_fields=["quantity"])
    return item.cart


@transaction.atomic
def quitar_del_carrito(usuario, item_id):
    item = item_del_usuario(usuario, item_id)
    item.delete()
    return item.cart
