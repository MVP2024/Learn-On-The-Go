from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase

from Users.permissions import HasRole, IsModeratorOrOwner, IsOwnerOrReadOnly

User = get_user_model()


class PermissionsExtraTests(TestCase):
    def setUp(self):
        for g in ("teacher", "student", "admin", "moderator"):
            Group.objects.get_or_create(name=g)
        self.user = User.objects.create_user(email="p_u@a.aa", password="pw")
        self.user.groups.add(Group.objects.get(name="teacher"))
        self.admin = User.objects.create_user(
            email="p_adm@a.aa", password="pw", is_superuser=True
        )
        self.mod = User.objects.create_user(email="p_mod@a.aa", password="pw")
        self.mod.groups.add(Group.objects.get(name="moderator"))

    def test_hasrole_allows_admin_and_group(self):

        req = type("R", (), {"user": type("Anon", (), {"is_authenticated": False})()})()
        role_perm = HasRole()
        role_perm.role = "teacher"
        self.assertFalse(role_perm.has_permission(req, None))

        req2 = type("R", (), {"user": self.user})()
        self.assertTrue(role_perm.has_permission(req2, None))

        req3 = type("R", (), {"user": self.admin})()
        self.assertTrue(role_perm.has_permission(req3, None))

    def test_is_moderator_or_owner_post_permission(self):
        perm = IsModeratorOrOwner()
        req = type("R", (), {"user": self.mod, "method": "POST"})()
        self.assertTrue(perm.has_permission(req, None))
        req2 = type("R", (), {"user": self.user, "method": "POST"})()
        self.assertFalse(perm.has_permission(req2, None))

    def test_owner_or_read_only_object_permission(self):
        perm = IsOwnerOrReadOnly()
        req = type("R", (), {"user": self.user})()
        req.method = "DELETE"
        obj = self.user
        self.assertTrue(perm.has_object_permission(req, None, obj))
        other = User.objects.create_user(email="otherp@a.aa", password="pw")
        self.assertFalse(perm.has_object_permission(req, None, other))
