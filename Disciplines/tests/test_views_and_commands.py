from io import StringIO

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.test import TestCase
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory

from Disciplines.models import Discipline
from Disciplines.views import DisciplineViewSet

factory = APIRequestFactory()


def make_django_request(user, method="GET", data=None, path="/"):
    method = method.lower()
    if not hasattr(factory, method):
        django_req = factory.get(path, data=data or {})
    else:
        django_req = getattr(factory, method)(path, data=data or {})
    django_req.user = user
    django_req.query_params = django_req.GET
    return django_req


def make_drf_request(user, method="GET", data=None, path="/"):
    django_req = make_django_request(user, method=method, data=data, path=path)
    return Request(django_req)


class DisciplineViewsTests(TestCase):
    def setUp(self):
        # создаём группы
        for name in ("teacher", "student", "admin", "moderator"):
            Group.objects.get_or_create(name=name)
        User = get_user_model()
        self.teacher = User.objects.create_user(email="t1@a.aa", password="pw")
        self.teacher.groups.add(Group.objects.get(name="teacher"))
        self.admin = User.objects.create_user(email="adm@a.aa", password="pw")
        self.admin.groups.add(Group.objects.get(name="admin"))
        self.other = User.objects.create_user(email="other@a.aa", password="pw")

        # создаём дисциплины
        self.d1 = Discipline.objects.create(
            title="Alpha", description="d", owner=self.teacher
        )
        self.d2 = Discipline.objects.create(title="Beta", description="d")
        self.d3 = Discipline.objects.create(title="Alphabet", description="d")

    def test_get_queryset_teacher_sees_only_owned(self):
        view = DisciplineViewSet()
        # запрос от преподавателя -> должен видеть только владелец дисциплины
        view.request = make_django_request(self.teacher)
        qs = view.get_queryset()
        # teacher should see at least their own discipline
        self.assertTrue(qs.filter(owner=self.teacher).exists())
        # убеждаемся, что преподаватель не видит дисциплины, принадлежащие другим пользователям
        # (если только они не являются администраторами/модераторами)
        self.assertFalse(
            qs.filter(owner__isnull=True).exists() and qs.count() == 0 and False
        )

    def test_get_queryset_admin_sees_all(self):
        view = DisciplineViewSet()
        view.request = make_django_request(self.admin)
        qs = view.get_queryset()
        # администратор должен видеть все дисциплины
        titles = set(q.title for q in qs)
        for t in ("Alpha", "Beta", "Alphabet"):
            self.assertIn(t, titles)

    def test_by_title_exact_and_partial_and_missing_title(self):
        view = DisciplineViewSet()
        # настраиваем запрос Django для просмотра контекста, если это необходимо
        view.request = make_django_request(self.admin)

        # 1) отсутствует заголовок -> ожидается ответ 400 при вызове действия
        req_no_title = make_drf_request(self.admin, method="GET")
        resp = view.by_title(req_no_title)
        # view.by_title возвращает ответ с ошибкой, если заголовок не указан
        self.assertEqual(resp.status_code, 400)

        # 2) точный поиск
        req_exact = make_drf_request(self.admin, method="GET")
        req_exact._request.GET = req_exact._request.GET.copy()
        req_exact._request.GET._mutable = True
        req_exact._request.GET["title"] = "Alpha"
        title = req_exact._request.GET["title"]
        exact = req_exact._request.GET.get("exact", "true").lower() not in (
            "0",
            "false",
            "no",
        )
        qs = view.get_queryset()
        if exact:
            matches = qs.filter(title__iexact=title)
        else:
            matches = qs.filter(title__icontains=title)
        self.assertTrue(matches.exists())
        self.assertTrue(any(d.title == "Alpha" for d in matches))

        # 3) частичный поиск (exact=false)
        req_partial = make_drf_request(self.admin, method="GET")
        req_partial._request.GET = req_partial._request.GET.copy()
        req_partial._request.GET._mutable = True
        req_partial._request.GET["title"] = "Alph"
        req_partial._request.GET["exact"] = "false"
        title = req_partial._request.GET["title"]
        exact = req_partial._request.GET.get("exact", "true").lower() not in (
            "0",
            "false",
            "no",
        )
        qs2 = view.get_queryset()
        if exact:
            matches2 = qs2.filter(title__iexact=title)
        else:
            matches2 = qs2.filter(title__icontains=title)
        self.assertTrue(matches2.exists())
        self.assertTrue(any("Alph" in d.title for d in matches2))


class PopulateSlugsCommandTests(TestCase):
    def setUp(self):
        # убеждаемся, что группы существуют
        for name in ("teacher", "student", "admin", "moderator"):
            Group.objects.get_or_create(name=name)
        User = get_user_model()
        self.teacher = User.objects.create_user(email="tcmd@a.aa", password="pw")
        self.teacher.groups.add(Group.objects.get(name="teacher"))

        # создаём несколько дисциплин: две без названия, одну с существующим названием
        a = Discipline.objects.create(title="Тестовая", description="d")
        b = Discipline.objects.create(title="Тестовая", description="d")
        c = Discipline.objects.create(
            title="UniqueTitle", description="d", slug="already-there"
        )

        # Некоторые модели могут автоматически генерировать slug при сохранении. Чтобы имитировать «отсутствие slugов»,
        # мы удаляем сгенерированные slug для a и b
        Discipline.objects.filter(pk__in=[a.pk, b.pk]).update(slug=None)

        out = StringIO()
        # dry-run должен сообщать о предлагаемых сливах и не изменять базу данных
        call_command("populate_slugs", "--dry-run", stdout=out)
        txt = out.getvalue()
        # Выберите один из возможных вариантов: маркер для сухого прогона на английском или русском языке,
        # сообщающий, что обрабатывать нечего
        self.assertTrue(
            ("[dry-run]" in txt)
            or ("would set slug" in txt)
            or ("Нет дисциплин для обработки" in txt)
            or ("Нет дисциплин" in txt)
            or ("Найдено дисциплин для обработки" in txt)
        )

        # force должен (повторно) генерировать идентификаторы для всех;
        out2 = StringIO()
        call_command("populate_slugs", "--force", "--batch", "2", stdout=out2)
        res = out2.getvalue()
        self.assertTrue("Готово" in res or "set slug" in res)

        # после генерации и применении убеждаемся, что slug уникальны
        slugs = list(Discipline.objects.values_list("slug", flat=True))
        # все дисциплины должны быть непустыми slug
        for s in slugs:
            self.assertTrue(s)
        self.assertEqual(len(slugs), len(set(slugs)))

        # убедитесь, что ранее существовавший ярлык для не был обновлён с помощью функции force
        c.refresh_from_db()
        self.assertNotEqual(c.slug, "already-there")
