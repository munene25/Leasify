from users.models import User
from users.services import user_deactivate, account_unsubscribe, user_remove_roles

class TestUserDeactivation:
    def test_deactivation_succeeds(self, user: User, django_assert_num_queries):
        """
        Very simple, just check whether the returned user is deactivated
        Also check the number of querries
        """
        with django_assert_num_queries(3):
            mod_user = user_deactivate(user)
        fetched = User.objects.get(pk=user.pk)
        assert fetched == mod_user == user
        assert mod_user.is_active == False

        with django_assert_num_queries(2):
            user_deactivate(mod_user)
        
class TestAccountUnsubscribe:
    def test_deactivation_succeeds(self, user: User, django_assert_num_queries):
        """
        Account should be marked as cannot receive emails
        Count querries
        """
        with django_assert_num_queries(3):
            mod_acc = account_unsubscribe(user.account)
        fetched = User.objects.get(pk=user.pk).account
        assert fetched == mod_acc == user.account
        assert mod_acc.can_receive_emails == False

        with django_assert_num_queries(2):
            account_unsubscribe(mod_acc)


class TestRoleRemoval:
    def test_role_removal_successfull(self, manager_user: User):
        first_role = manager_user.groups.first()

        assert first_role is not None
        assert manager_user.roles == [first_role.name]
        mod_user = user_remove_roles(user=manager_user, roles=[first_role])

        assert mod_user == manager_user

        assert mod_user.roles == []
        assert mod_user.groups.count() == 0

    def test_multiple_role_removal_successfull(self, user: User, roles_list):
        user.groups.add(*roles_list)
        assert list(user.groups.all()) == roles_list

        user_remove_roles(user=user, roles=roles_list)

        assert user.roles == []
        assert user.groups.count() == 0