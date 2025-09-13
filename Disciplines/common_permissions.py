from rest_framework import permissions


class IsAdminOrModerator(permissions.BasePermission):
    """
    Разрешение, которое позволяет доступ только администраторам или модераторам.
    """

    def has_permission(self, request, view):
        return request.user.is_authenticated and (
            request.user.is_superuser
            or request.user.groups.filter(name="admin").exists()
            or request.user.groups.filter(name="moderator").exists()
        )


class IsOwnerOrAdminOrModerator(permissions.BasePermission):
    """
    Разрешение, которое позволяет:
    - Администратору иметь полные права.
    - Модератору иметь полные права.
    - Владельцу объекта иметь полные права.
    """

    def has_object_permission(self, request, view, obj):
        # Разрешаем методы  (GET, HEAD, OPTIONS) тем, кто прошёл аутентификацию
        if request.method in permissions.SAFE_METHODS:
            return True

        # Администраторы и модераторы имеют полный доступ
        if (
            request.user.is_superuser
            or request.user.groups.filter(name="admin").exists()
            or request.user.groups.filter(name="moderator").exists()
        ):
            return True

        # Владельцы своих объектов имеют полный доступ к ним
        return obj.owner == request.user


class IsTeacherOrAdminOrModerator(permissions.BasePermission):
    """
    Разрешение, которое позволяет создавать объекты учителям, администраторам и модераторам.
    """

    def has_permission(self, request, view):
        return request.user.is_authenticated and (
            request.user.is_superuser
            or request.user.groups.filter(name="admin").exists()
            or request.user.groups.filter(name="moderator").exists()
            or request.user.groups.filter(name="teacher").exists()
        )


class IsOwner(permissions.BasePermission):
    """
    Пользователь имеет разрешение на уровне объекта только для своих собственных объектов.
    Предполагается, что экземпляр объекта имеет атрибут `owner`.
    """

    def has_object_permission(self, request, view, obj):
        # Разрешения на чтение разрешены любому запросу.
        if request.method in permissions.SAFE_METHODS:
            return True

        # Разрешения на запись разрешены только владельцу объекта.
        return obj.owner == request.user
