from celery import shared_task
from tenancy import selectors as sl

@shared_task(ignore_results=False)
def show_detail(tenancy_id):
    tenancy = sl.tenancy_get(tenancy_id=tenancy_id)
    return f'User {tenancy.user.get_full_name()} just requested this page'