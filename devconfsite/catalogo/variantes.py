from decimal import Decimal, InvalidOperation

from .models import clave_variante

MENSAJE_PRECIO = "Enter a price of 0 or more."
MENSAJE_STOCK = "Stock must be a whole number, 0 or more."


def normalizar(texto):
    return texto.strip().lower()


def validar_variantes(datos, atributos, existentes_ids):
    """Valida la lista de variantes contra los atributos del producto y la deja normalizada."""
    errores, limpias, claves = [], [], set()
    if datos and not atributos:
        return None, ["This product has no attributes, so it can't have combinations."]
    oficial = {normalizar(a["name"]): (a["name"], a["values"]) for a in atributos}
    for n, variante in enumerate(datos, start=1):
        prefijo = f"Combination {n}: "
        if not isinstance(variante, dict):
            errores.append(prefijo + "invalid data.")
            continue
        opciones = variante.get("options")
        if not isinstance(opciones, list) or not all(
            isinstance(o, dict) and isinstance(o.get("name"), str) and isinstance(o.get("value"), str) for o in opciones
        ):
            errores.append(prefijo + "each option needs a name and a value.")
            continue
        elegido = {}
        for o in opciones:
            elegido.setdefault(normalizar(o["name"]), []).append(o["value"])
        if sorted(elegido) != sorted(oficial) or any(len(v) != 1 for v in elegido.values()):
            errores.append(prefijo + "choose exactly one value for every attribute.")
            continue
        ordenadas, invalido = [], None
        for clave_nombre, (nombre, permitidos) in oficial.items():
            valor = elegido[clave_nombre][0]
            canonico = next((p for p in permitidos if normalizar(p) == normalizar(valor)), None)
            if canonico is None:
                invalido = invalido or (valor.strip(), nombre)
            ordenadas.append({"name": nombre, "value": canonico})
        if invalido:
            errores.append(prefijo + f"\"{invalido[0]}\" is not a value of {invalido[1]}.")
            continue
        clave = clave_variante(ordenadas)
        if clave in claves:
            errores.append(prefijo + "another combination already has these options.")
            continue
        claves.add(clave)
        try:
            precio = Decimal(str(variante.get("price")))
            if not precio.is_finite() or precio < 0 or precio != precio.quantize(Decimal("0.01")):
                raise InvalidOperation
        except (InvalidOperation, ValueError):
            errores.append(prefijo + MENSAJE_PRECIO)
            continue
        stock = variante.get("stock")
        if isinstance(stock, float) and stock.is_integer():
            stock = int(stock)
        if isinstance(stock, bool) or not isinstance(stock, int) or stock < 0:
            errores.append(prefijo + MENSAJE_STOCK)
            continue
        sku = variante.get("sku") or ""
        if not isinstance(sku, str) or len(sku) > 60:
            errores.append(prefijo + "the SKU must be text of 60 characters or less.")
            continue
        id_variante = variante.get("id")
        if id_variante is not None and id_variante not in existentes_ids:
            errores.append(prefijo + "this combination does not belong to the product.")
            continue
        limpias.append({"id": id_variante, "options": ordenadas, "price": precio, "stock": stock, "sku": sku.strip()})
    return (None, errores) if errores else (limpias, [])
