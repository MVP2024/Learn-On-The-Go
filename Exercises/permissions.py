from rest_framework import permissions


class IsTestOwnerOrAdminOrModerator(permissions.BasePermission):
    """
    Разрешение, которое позволяет:
    - Администратору иметь полные права.
    - Модератору иметь полные права (позволим им редактировать любой тест).
    - Владельцу теста иметь полные права на свой тест.
    Применимо к вопросам и ответам, где проверяется владелец теста, к которому они относятся.
    """

    def has_permission(self, request, view):
        # Разрешаем аутентифицированным пользователям создавать объекты, если у них есть соответствующие роли
        if request.method == "POST":
            return request.user.is_authenticated and (
                request.user.is_superuser
                or request.user.groups.filter(name="admin").exists()
                or request.user.groups.filter(name="moderator").exists()
                or request.user.groups.filter(name="teacher").exists()
            )
        return True

    def has_object_permission(self, request, view, obj):
        # Просмотр разрешен всем (если AllowAny в ViewSet)
        if request.method in permissions.SAFE_METHODS:
            return True

        # Администраторы имеют полные права
        if (
            request.user.is_superuser
            or request.user.groups.filter(name="admin").exists()
        ):
            return True

        # Модераторы имеют полные права
        if request.user.groups.filter(name="moderator").exists():
            return True

        # Для Test, Question, Answer: проверяем владельца теста
        # Если obj - Test:
        if hasattr(obj, "owner"):
            return obj.owner == request.user
        # Если obj - Question:
        if hasattr(obj, "test") and hasattr(obj.test, "owner"):
            return obj.test.owner == request.user
        # Если obj - Answer:
        if (
            hasattr(obj, "question")
            and hasattr(obj.question, "test")
            and hasattr(obj.question.test, "owner")
        ):
            return obj.question.test.owner == request.user

        return False  # По умолчанию запрещаем
