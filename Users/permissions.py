from rest_framework import permissions

class IsOwnerOrReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj == request.user


class HasRole(permissions.BasePermission):
    """
    Базовый класс для проверки роли пользователя.
    """
    role = None

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        if request.user.is_superuser or request.user.groups.filter(name='admin').exists():
            return True # Администраторы всегда имеют права
        return request.user.groups.filter(name=self.role).exists()


class IsTeacher(HasRole):
    role = 'teacher'


class IsStudent(HasRole):
    role = 'student'


class IsModerator(HasRole):
    role = 'moderator'


class IsModeratorOrOwner(permissions.BasePermission):
    """
    Разрешение для модераторов или владельцев объекта.
    Модераторы могут создавать объекты, но редактировать/удалять только свои.
    Владельцы всегда могут редактировать/удалять свои объекты.
    """
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        # Модераторы и администраторы могут создавать объекты
        if request.method == 'POST':
            return request.user.is_superuser or request.user.groups.filter(name='admin').exists() or \
                   request.user.groups.filter(name='moderator').exists()
        return True # Для остальных методов, проверка будет на уровне объекта

    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False

        # Администраторы всегда имеют полные права
        if request.user.is_superuser or request.user.groups.filter(name='admin').exists():
            return True

        # Разрешить чтение всем
        if request.method in permissions.SAFE_METHODS:
            return True

        # Модераторы могут изменять/удалять свои объекты
        if request.user.groups.filter(name='moderator').exists():
            # Предполагается, что у объекта есть поле 'owner'
            return hasattr(obj, 'owner') and obj.owner == request.user

        # Владелец объекта всегда может его изменить/удалить
        return hasattr(obj, 'owner') and obj.owner == request.user