import time
from celery import shared_task
from . import selectors

@shared_task(ignore_results=False)
def show_detail(tenancy_id):
    time.sleep(10)
    tenancy = selectors.tenancy_get_by_id(tenancy_id=tenancy_id)
    return f'User {tenancy.user.get_full_name()} just requested this page'