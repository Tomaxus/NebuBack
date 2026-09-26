import unicodedata

from django.db import migrations, models


def normalizar(texto):
    sin_tildes = unicodedata.normalize("NFKD", texto or "")
    return "".join(c for c in sin_tildes if not unicodedata.combining(c)).lower()


def llenar_search_text(apps, schema_editor):
    Producto = apps.get_model("catalogo", "Producto")
    for producto in Producto.objects.select_related("category"):
        producto.search_text = normalizar(f"{producto.name} {producto.category.name}")
        producto.save(update_fields=["search_text"])


class Migration(migrations.Migration):

    dependencies = [
        ('catalogo', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='producto',
            name='search_text',
            field=models.TextField(blank=True, default='', editable=False),
        ),
        migrations.RunPython(llenar_search_text, migrations.RunPython.noop),
    ]
