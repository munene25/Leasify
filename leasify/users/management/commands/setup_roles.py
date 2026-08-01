from django.core.management import BaseCommand, call_command, CommandError
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.conf import settings

ROLE_PERMISSIONS = {
    "manager": {
        "apartment": ["add_apartment", "view_apartment", "change_apartment", "delete_apartment"],
        "tenancy": ["view_tenancy", "change_tenancy", "delete_tenancy"],
        "user": ["add_user", "view_user", "change_user", "delete_user"],
        "billingperiod": ["view_billingperiod", "change_billingperiod", "complete_billingperiod"],
        "payment": ["view_payment", "initiate_payment", "add_payment_manually"],
    },
    "caretaker": {
        "apartment": ["view_apartment", "change_apartment"],
        "tenancy": ["view_tenancy", "change_tenancy"],
        "user": ["add_user", "view_user"],
        "billingperiod": ["view_billingperiod", "change_billingperiod"],
        "payment": ["view_payment"],
    },
    "tenant": {
        "billingperiod": ["view_billingperiod", "change_billingperiod"],
        "tenancy": ["add_tenancy", "view_tenancy", "change_tenancy"],
        "payment": ["view_payment", "initiate_payment"],
    },
}

class Command(BaseCommand):
    help = "Seed groups and permissions"

    def handle(self, *args, **options):
        self.stdout.write("Seeding roles and permissions...")

        for role_name, model_permissions in ROLE_PERMISSIONS.items():
            group, created = Group.objects.get_or_create(name=role_name)
            action = "Created" if created else "Updated"

            for model_name, codenames in model_permissions.items():
                content_type = ContentType.objects.get(model=model_name)
                role_perms = Permission.objects.filter(
                    content_type=content_type,
                    codename__in=codenames,
                )

                if role_perms.count() != len(codenames):
                    raise CommandError(
                        f"Permission mismatch for role '{role_name}' on '{model_name}. {role_perms=}'"
                    )

                group.permissions.add(*role_perms)

            self.stdout.write(
                self.style.SUCCESS(f"  ✓ {action} role: {role_name}")
            )

        self.stdout.write("Dumping fixtures...")
        fixture_dir = settings.APP_DIRS("fixtures/roles.json")
        with open(fixture_dir, "w") as f:
            call_command("dumpdata", "auth.Permission", "auth.Group", indent=4, stdout=f)

        self.stdout.write(self.style.SUCCESS(f"✓ Done. Fixtures at '{fixture_dir}'"))