from structlog import get_logger

from django.contrib.auth import logout
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.request import Request
from rest_framework import serializers
from rest_framework import status

from leasify.common.views import BaseAPIView
from leasify.common.permissions import IsManager, check_perms
from leasify.common.pagination import get_paginated_response
from leasify.common.throttling import ScopedThrottle

from leasify.users import selectors as sl, serializer as sc, services as sr
from leasify.authentication.tokens import get_user_from_uidb64

logger = get_logger("users.views")

class UserListCreateView(BaseAPIView):
    """
    Serves as an admin's user-list view via get and new user registration via post
    Permission class is determined via method
    Filtering is allowed via 'search' and 'is_active'

    """

    class FilterSerializer(serializers.Serializer):
        search = serializers.CharField()
        is_active = serializers.BooleanField(allow_null=True)

    serializer_class = sc.UserCreateSerializer
    throttle_classes = [ScopedThrottle]
    filter_class = FilterSerializer
    throttle_scope = "user_create"
    

    def get_permissions(self):
        return [IsAuthenticated() if self.request.method == "GET" else AllowAny()]

    def get_throttles(self):
        return [ScopedThrottle()] if self.request.method == "POST" else []

    def get(self, request: Request):
        check_perms(request.user, "users.view_user")
        filters = self.validate_filter(data=request.query_params)
        qs = sl.user_list_for(user=request.user, filters=filters)
        return get_paginated_response(serializer_class=sc.UserListSerializer, queryset=qs, request=request, view=self)

    def post(self, request):
        incoming = self.validate_serializer(data=request.data)
        user = sr.user_account_create(**incoming)
        outgoing = sc.UserDetailSerializer(user)
        return Response(data=outgoing.data, status=status.HTTP_201_CREATED)


class AdminDetailUpdateDestroyView(BaseAPIView):
    """
    Allows Admins or Authroized groups to modify users details
    All methods require priviledged access
    Selectors with _for should be used
    """

    serializer_class = sc.AdminUserUpdateSerializer
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id):
        check_perms(request.user, "users.view_user")
        user = sl.user_get_for(user=request.user, user_id=user_id)
        serialzer_class = sc.UserDetailSerializer(instance=user)
        return Response(status=status.HTTP_200_OK, data=serialzer_class.data)

    def patch(self, request, user_id):
        check_perms(request.user, "users.change_user")
        incoming = self.validate_serializer(data=request.data, partial=True)
        user = sl.user_get_for(user=request.user, user_id=user_id)
        mod = sr.user_update(user, **incoming)

        outgoing = sc.UserDetailSerializer(instance=mod)
        return Response(data=outgoing.data, status=status.HTTP_200_OK)

    def delete(self, request, user_id):
        check_perms(request.user, "users.delete_user")
        user = sl.user_get_for(user=request.user, user_id=user_id)
        sr.user_update_active_status(user=user, status=False)
        return Response(
            status=status.HTTP_200_OK,
            data={"message": f"{user.full_name}'s account deactivated successfully"},
        )


class MeView(BaseAPIView):
    """
    Provides endpoints for users to manage their own account
    """

    serializer_class = sc.UserUpdateSerializer
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = sl.user_get(request.user.pk)
        outgoing = sc.UserDetailSerializer(instance=user)
        return Response(status=status.HTTP_200_OK, data=outgoing.data)

    def patch(self, request):
        incoming = self.validate_serializer(data=request.data, partial=True)
        user = sr.user_update(user=request.user, **incoming)

        outgoing = sc.UserDetailSerializer(instance=user)
        return Response(data=outgoing.data, status=status.HTTP_200_OK)

    def delete(self, request):
        sr.user_update_active_status(user=request.user, status=False)
        # flush the session
        # Fixed bug: Logout requires the request object not request.user
        logout(request)
        return Response(data={"message": "account deactivated successfully"}, status=status.HTTP_204_NO_CONTENT)


class EmailUpdateView(BaseAPIView):
    """
    View allows users to change emails. Limited to once a weeka
    Moved throttling is based on the last_email_change field on the model.
    This centralizes the logic in one place
    """

    permission_classes = [IsAuthenticated]
    serializer_class = sc.UserEmailUpdateSerializer

    def post(self, request):
        incoming = self.validate_serializer(data=request.data, partial=False)
        user = sr.user_email_update(user=request.user, **incoming)

        # In this case its better to respond with the email instead of the whole payload
        # Helps in front end rendering.
        return Response(data={"email": user.email}, status=status.HTTP_200_OK)



class UserUnsubscribeView(BaseAPIView):
    """
    Route to unregister users from mailing list and misc notifications
    """

    permission_classes = [AllowAny]

    def post(self, request, uidb64):
        user = get_user_from_uidb64(uidb64)
        if user.account.can_receive_emails:
            sr.account_update_mailing_status(user.account, status=False)
        return Response(
            data={"message": "You have been unsubscribed from all non-essential emails"},
            status=status.HTTP_200_OK,
        )


class AdminRoleListView(BaseAPIView):
    """
    Allows Admins or Authorized groups to view all the roles available in the system.
    """

    permission_classes = [IsManager]

    def get(self, request):
        groups = sl.groups_list()
        outgoing = [{"key": group.name, "display": group.name} for group in groups]
        return Response(data=outgoing, status=status.HTTP_200_OK)


class AdminRoleDetailView(BaseAPIView):
    """
    Allows Admins or Authorized groups to manage a users role.
    Only a single role can be assigned to a user at a time.
    Patching a role will replace the existing role.
    Deleting a role will remove the assigned role from the user.
    """

    permission_classes = [IsManager]
    serializer_class = sc.AdminRoleUpdateSerializer

    def get(self, request, user_id):
        user = sl.user_get_for(user=request.user, user_id=user_id)
        serializer = sc.AdminRoleDetailSerializer(instance=user)
        return Response(status=status.HTTP_200_OK, data=serializer.data)

    def patch(self, request, user_id):
        user = sl.user_get_for(user=request.user, user_id=user_id)
        incoming = self.validate_serializer(data=request.data)
        # Explicitly acknowledge that an existing role will be replaced if it exists by setting replace to true. This prevents accidental role replacement.
        u = sr.user_set_role(user=user, role=incoming["role"], replace=True)
        serializer = sc.AdminRoleDetailSerializer(instance=u)
        return Response(status=status.HTTP_200_OK, data=serializer.data)

    def delete(self, request, user_id):
        user = sl.user_get_for(user=request.user, user_id=user_id)
        u = sr.user_remove_role(user=user)
        serializer = sc.AdminRoleDetailSerializer(instance=u)
        return Response(status=status.HTTP_200_OK, data=serializer.data)
