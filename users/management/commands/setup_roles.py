from django.core.management import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType


ROLE_PERMISSIONS = {
    "manager": [
        {"apartment" : ["add_apartment", "view_apartment", "change_apartment", "delete_apartment", "view_overview"]},
        {"tenancy": ["add_tenancy", "view_tenancy", "change_tenancy", "delete_tenancy",]},
        {"user": ["add_user", "view_user", "change_user", "delete_user"]},
        {"payment": ["add_payment", "view_payment"]}
    ],
    "caretaker": [
        {"apartment": ["view_apartment", "change_apartment"]},
        {"tenancy": ["add_tenancy", "view_tenancy", "change_tenancy"]},
        {"user": ["add_user", "view_user"]},
        {"payment": ["view_payment"]},
    ],
    "tenant": [
        {"tenancy": ["view_tenancy"]},
    ]

}

class Command(BaseCommand):
    help = "Seed groups and permissions"

    def handle(self, *args, **options):
        for role_name, model_permissions_list in ROLE_PERMISSIONS.items():
            group, _ = Group.objects.get_or_create(name=role_name)

            for model_perm_map in model_permissions_list:
                for model_name, codenames in model_perm_map.items():
                    content_type = ContentType.objects.get(model=model_name)

                    role_perms = Permission.objects.filter(
                        content_type=content_type,
                        codename__in=codenames,
                    )

                    if role_perms.count() != len(codenames):
                        raise RuntimeError(
                            f"Permission mismatch for role '{role_name}' on model '{model_name}'"
                        )

                    group.permissions.add(*role_perms)
        print("✅ Roles and permissions successfully seeded")