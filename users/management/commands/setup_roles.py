from django.core.management import BaseCommand, call_command
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType

ROLE_PERMISSIONS = {
    "manager": [
        {"apartment" : ["add_apartment", "view_apartment", "change_apartment", "delete_apartment", "view_overview"]},
        {"tenancy": ["view_tenancy", "change_tenancy", "delete_tenancy",]},
        {"user": ["add_user", "view_user", "change_user", "delete_user"]},
        {"billingperiod": ["view_billingperiod", "change_billingperiod", "complete_billingperiod"]},
        {"payment": ["view_payment", "initiate_payment", "add_payment_manually"]}
    ],
    "caretaker": [
        {"apartment": ["view_apartment", "change_apartment"]},
        {"tenancy": ["view_tenancy", "change_tenancy"]},
        {"user": ["add_user", "view_user"]},
        {"billingperiod": ["view_billingperiod", "change_billingperiod"]},
        {"payment": ["view_payment"]},
    ],
    "tenant": [
        {"billingperiod": ["view_billingperiod", "change_billingperiod"]},
        {"tenancy": ["add_tenancy", "view_tenancy", "change_tenancy"]},
        {"payment": ["view_payment", "initiate_payment"]},
    ]

}

class Command(BaseCommand):
    help = "Seed groups and permissions"

    def handle(self, *args, **options):
        print("🗄️  Seeding database...")

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

        print("📂 Loading fixtures...")
        fixture_dir = "fixtures/roles.json"

        with open(fixture_dir, "w") as f:
            call_command("dumpdata", "auth.Permission", "auth.Group", indent=4, stdout=f)

        print(f"✅ Roles setup successfully. Fixtures at '{fixture_dir}'")