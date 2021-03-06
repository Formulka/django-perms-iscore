from django.contrib.auth.models import User
from django.test import override_settings

from germanium import config
from germanium.annotations import login
from germanium.test_cases.client import ClientTestCase
from germanium.tools import assert_true, assert_false, assert_equal, assert_not_equal
from germanium.tools.http import assert_http_redirect, assert_http_ok, assert_http_forbidden

from fperms_iscore.models import IsCorePerm

from .test_case import HelperTestCase, AsSuperuserTestCase


class UIPermissionsTestCase(AsSuperuserTestCase, HelperTestCase, ClientTestCase):
    USER_UI_URL = '/user/'

    def set_up(self):
        IsCorePerm.objects.create_from_str(
            perms=[
                'core.issue_tracker.IssueIsCore.read',
                'core.issue_tracker.IssueIsCore.create',
                'core.issue_tracker.UserIsCore.read',
                'core.issue_tracker.UserIsCore.create',
                'core.issue_tracker.UserIsCore.update',
            ]
        )

    def authorize(self, username, password):
        resp = self.post(config.LOGIN_URL, {config.USERNAME: username, config.PASSWORD: password})
        assert_http_redirect(resp)

    def test_non_logged_user_should_receive_302(self):
        resp = self.get(self.USER_UI_URL)
        assert_http_redirect(resp)

    @login(is_superuser=False)
    def test_home_view_should_return_ok(self):
        resp = self.get('/')
        assert_http_ok(resp)

    @login(is_superuser=True)
    def test_superuser_may_read_users_grid(self):
        resp = self.get(self.USER_UI_URL)
        assert_http_ok(resp)

    @login(is_superuser=False)
    def test_ouser_can_read_users_grid(self):
        self.logged_user.user.perms.add_perm('core.issue_tracker.UserIsCore.read')
        resp = self.get(self.USER_UI_URL)
        assert_http_ok(resp)

    @login(is_superuser=True)
    def test_superuser_may_edit_user(self):
        user = self.get_user_obj()
        resp = self.get('%s%s/' % (self.USER_UI_URL, user.pk))
        assert_http_ok(resp)

        CHANGED_USERNAME = 'changed_nick'
        self.post('%s%s/' % (self.USER_UI_URL, user.pk), data={'edit-is-user-username': CHANGED_USERNAME})
        assert_http_ok(resp)
        assert_equal(User.objects.get(pk=user.pk).username, CHANGED_USERNAME)

    @login(is_superuser=False)
    def test_only_superuser_may_edit_user(self):
        user = self.get_user_obj()
        resp = self.get('%s%s/' % (self.USER_UI_URL, user.pk))
        assert_http_forbidden(resp)

        CHANGED_USERNAME = 'changed_nick'
        self.post('%s%s/' % (self.USER_UI_URL, user.pk), data={'edit-is-user-username': CHANGED_USERNAME})
        assert_http_forbidden(resp)
        assert_not_equal(User.objects.get(pk=user.pk).username, CHANGED_USERNAME)

    @login(is_superuser=False)
    def test_user_may_edit_itself(self):
        user = self.logged_user.user
        resp = self.get('%s%s/' % (self.USER_UI_URL, user.pk))
        assert_http_ok(resp)

        CHANGED_USERNAME = 'changed_nick'
        self.post('%s%s/' % (self.USER_UI_URL, user.pk), data={'edit-is-user-username': CHANGED_USERNAME})
        assert_http_ok(resp)
        assert_equal(User.objects.get(pk=user.pk).username, CHANGED_USERNAME)

    @login(is_superuser=True)
    def test_superuser_may_add_user(self):
        USERNAME = 'new_nick'

        resp = self.post('%sadd/' % self.USER_UI_URL, data={'add-is-user-username': USERNAME,
                                                            'add-is-user-password': 'password'})
        assert_http_redirect(resp)
        assert_true(User.objects.filter(username=USERNAME).exists())

    @login(is_superuser=False)
    def test_only_superuser_may_add_user(self):
        USERNAME = 'new_nick'

        resp = self.post('%sadd/' % self.USER_UI_URL, data={'add-is-user-username': USERNAME,
                                                            'add-is-user-password': 'password'})
        assert_http_forbidden(resp)
        assert_false(User.objects.filter(username=USERNAME).exists())

    @login(is_superuser=False)
    def test_user_with_permission_may_add_user(self):
        self.logged_user.user.perms.add_perm('core.issue_tracker.UserIsCore.create')

        USERNAME = 'new_nick'

        resp = self.post('%sadd/' % self.USER_UI_URL, data={'add-is-user-username': USERNAME,
                                                            'add-is-user-password': 'password'})
        assert_http_redirect(resp)
        assert_true(User.objects.filter(username=USERNAME).exists())

    @override_settings(PERM_AUTO_CREATE=True)
    @login(is_superuser=False)
    def test_user_with_permission_may_add_user_auto_create_perm(self):
        IsCorePerm.objects.all().delete()

        self.logged_user.user.perms.add_perm('core.issue_tracker.UserIsCore.create')

        USERNAME = 'new_nick'

        resp = self.post('%sadd/' % self.USER_UI_URL, data={'add-is-user-username': USERNAME,
                                                            'add-is-user-password': 'password'})
        assert_http_redirect(resp)
        assert_true(User.objects.filter(username=USERNAME).exists())
