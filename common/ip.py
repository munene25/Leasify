def get_client_ip(request):
    xff = request.META.get('HTTP_X_FORWARDED_FOR')
    remote_address = request.META.get('REMOTE_ADDR')
    ip = xff.split(',')[0] if xff else remote_address
    return ip