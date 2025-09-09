from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase

from Users.permissions import (
    IsModerator,
    IsModeratorOrOwner,
    IsOwnerOrReadOnly,
    IsStudent,
    IsTeacher,
)

User = get_user_model()


class UsersPermissionsUnitTests(TestCase):
    """Небольшие unit-тесты для Users.permissions с русскими докстрингами."""

    def setUp(self):
        # создаём стандартные группы
        for name in ("teacher", "student", "admin", "moderator"):
            Group.objects.get_or_create(name=name)
        self.user = User.objects.create_user(email="u1@a.aa", password="pw")
        self.user.groups.add(Group.objects.get(name="teacher"))
        self.other = User.objects.create_user(email="u2@a.aa", password="pw")
        self.mod = User.objects.create_user(email="mod@a.aa", password="pw")
        self.mod.groups.add(Group.objects.get(name="moderator"))
        self.admin = User.objects.create_user(
            email="adm@a.aa", password="pw", is_superuser=True
        )

    def test_is_owner_or_read_only_behaviour(self):
        """Проверяем IsOwnerOrReadOnly: чтение для всех, запись только для владельца."""
        perm = IsOwnerOrReadOnly()
        # has_permission: требует аутентификацию
        req = type("R", (), {"user": self.user})()
        self.assertTrue(perm.has_permission(req, None))

        # объект — это пользователь
        # безопасный метод -> True
        req.method = "GET"
        self.assertTrue(perm.has_object_permission(req, None, self.user))
        # небезопасный метод и не-владелец -> False
        req.method = "PUT"
        self.assertFalse(perm.has_object_permission(req, None, self.other))
        # владелец -> True
        self.assertTrue(perm.has_object_permission(req, None, self.user))

    def test_hasrole_and_concrete_roles(self):
        """Проверяем HasRole и конкретные реализации (IsTeacher/IsStudent/IsModerator)."""
        # пользователь в группе teacher
        req = type("R", (), {"user": self.user})()
        # IsTeacher должен вернуть True
        it = IsTeacher()
        self.assertTrue(it.has_permission(req, None))
        # IsStudent должен вернуть False
        is_ = IsStudent()
        self.assertFalse(is_.has_permission(req, None))
        # moderator пользователь
        req_mod = type("R", (), {"user": self.mod})()
        im = IsModerator()
        self.assertTrue(im.has_permission(req_mod, None))

    def test_is_moderator_or_owner(self):
        """Проверяем IsModeratorOrOwner: модератор имеет права на создание, владелец имеет права на изменение/удаление, другие — нет."""
        perm = IsModeratorOrOwner()
        # POST модератором -> разрешено
        req_post = type("R", (), {"user": self.mod, "method": "POST"})()
        self.assertTrue(perm.has_permission(req_post, None))
        # POST обычным пользователем -> согласно реализации, POST возвращает True только для moderators/admins; teacher
        req_plain = type("R", (), {"user": self.user, "method": "POST"})()
        self.assertFalse(perm.has_permission(req_plain, None))

        # object разрешение: владелец подтверждённый
        obj = type("O", (), {"owner": self.user})()
        req_owner_put = type("R", (), {"user": self.user, "method": "PUT"})()
        self.assertTrue(perm.has_object_permission(req_owner_put, None, obj))
        # модератору НЕ допускается изменение объектов, принадлежащих другим лицам (в зависимости от реализации)
        req_mod_delete = type("R", (), {"user": self.mod, "method": "DELETE"})()
        self.assertFalse(perm.has_object_permission(req_mod_delete, None, obj))
        # другой пользователь без прав
        req_other = type("R", (), {"user": self.other, "method": "PUT"})()
        self.assertFalse(perm.has_object_permission(req_other, None, obj))
