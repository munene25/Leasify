from rest_framework.permissions import BasePermission, SAFE_METHODS

MESSAGE = "Only priviledged members are allowed to perform this action"


class IsPrivilegedAll(BasePermission):
    message = MESSAGE
    privileged_roles = {"manager", "caretaker"}
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and set(request.user.roles) & self.privileged_roles
        )


class AllowPostForUnauthenticatedUsers(BasePermission):
    message = "You do not have permission to perform this action"
    allowed_methods = ["POST", "HEAD", "OPTIONS"]

    def has_permission(self, request, view):
        if request.method in self.allowed_methods:
            return True
        return False


class GuestCanCreateOnly(BasePermission):
    message = MESSAGE
    privileged_methods = ["GET"]
    privileged_roles = {"manager", "caretaker"}

    def has_permission(self, request, view):
        if request.method in self.privileged_methods:
            return bool(
                request.user
                and request.user.is_authenticated
                and set(request.user.roles) & self.privileged_roles
            )
        return True


class ManagersAllCaretakerViewOnly(BasePermission):
    message = MESSAGE
    manager_methods = ["DELETE", "PUT", "PATCH"]
    
    def has_permission(self, request, view):
        if request.method in self.manager_methods:
            return bool(
                request.user
                and request.user.is_authenticated
                and "manager" in request.user.roles
            )
        
        return bool(
            request.user
            and request.user.is_authenticated
            and (
                "manager" in request.user.roles
                or "caretaker" in request.user.roles
            )
            
        )