from rest_framework.permissions import BasePermission, SAFE_METHODS

MESSAGE = "Only priviledged users are allowed to perform this action"


class GuestsCanPostOnly(BasePermission):
    message = MESSAGE
    allowed_method = ["POST"]

    def has_permission(self, request, view):
        if request.method in self.allowed_method:
            return True
        
