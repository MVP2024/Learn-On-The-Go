from django.db import migrations, models
from django.db.models import Q


class Migration(migrations.Migration):

    dependencies = [
        ("Admin", "0002_initial"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="adminkey",
            index=models.Index(
                fields=["expires_at"],
                name="adminkey_expires_idx",
                condition=Q(is_active=True),
            ),
        ),
    ]
