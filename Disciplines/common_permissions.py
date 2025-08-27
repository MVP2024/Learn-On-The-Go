from rest_framework import permissions

class IsAdminOrModerator(permissions.BasePermission):
    """
    Разрешение, которое позволяет доступ только администраторам или модераторам.
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and (
            request.user.is_superuser or
            request.user.groups.filter(name='admin').exists() or
            request.user.groups.filter(name='moderator').exists()
        )

class IsOwnerOrAdminOrModerator(permissions.BasePermission):
    """
    Разрешение, которое позволяет:
    - Администратору иметь полные права.
    - Модератору иметь полные права.
    - Владельцу объекта иметь полные права.
    """
    def has_object_permission(self, request, view, obj):
        # Allow safe methods (GET, HEAD, OPTIONS) for anyone authenticated
        if request.method in permissions.SAFE_METHODS:
            return True

        # Admins and Moderators have full access
        if request.user.is_superuser or \
           request.user.groups.filter(name='admin').exists() or \
           request.user.groups.filter(name='moderator').exists():
            return True

        # Object owners have full access
        return obj.owner == request.user

class IsTeacherOrAdminOrModerator(permissions.BasePermission):
    """
    Разрешение, которое позволяет создавать объекты учителям, администраторам и модераторам.
    (Для actions like 'create' where object is not yet created).
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and (
            request.user.is_superuser or
            request.user.groups.filter(name='admin').exists() or
            request.user.groups.filter(name='moderator').exists() or
            request.user.groups.filter(name='teacher').exists()
        )