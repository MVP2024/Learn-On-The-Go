import argparse
import os
import sys
from pathlib import Path
from typing import Type, cast

# Настройка Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django
from django.conf import settings

django.setup()

from django.apps import apps
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.db import transaction
from django.db.models import Model as DjangoModel

FIXTURE_PATH = Path(__file__).resolve().parent.parent / "fixtures" / "initial_data.json"

# Модели в порядке удаления (чтобы не было проблем с FK)
MODELS_TO_CLEAR = [
    ("Payments", "PurchasedContent"),
    ("Payments", "Payment"),
    ("Payments", "PriceConfiguration"),
    ("Lessons", "UserLessonProgress"),
    ("Lessons", "Lesson"),
    ("Disciplines", "Section"),
    ("Disciplines", "Discipline"),
    ("Exercises", "Answer"),
    ("Exercises", "Question"),
    ("Exercises", "Test"),
    ("Admin", "AdminKey"),
    ("Teachers", "Teacher"),
    ("Students", "Student"),
    ("Users", "User"),
]

REQUIRED_GROUPS = ["admin", "teacher", "student", "moderator"]


def confirm(prompt: str) -> bool:
    resp = input(prompt + " [y/N]: ").strip().lower()
    return resp in ("y", "yes")


def check_safety_flags(force: bool) -> None:
    # Не даём запустить в продакшне без явного согласия
    if not settings.DEBUG and not force:
        allow = os.environ.get("ALLOW_FIXTURE_CLEAR")
        if allow != "1":
            print(
                "❌ Скрипт запрещён в production пока DEBUG=False. Установите ALLOW_FIXTURE_CLEAR=1 или запустите в режиме DEBUG."
            )
            sys.exit(1)


def verify_fixture_file(path: Path) -> None:
    if not path.exists():
        print(f"❌ Файл фикстур не найден: {path}")
        sys.exit(2)
    print(f"📦 Найден файл фикстур: {path}")


def run_fixture_checker() -> None:
    """
    Вызываем существующий скрипт utils/check_fixtures_users.py для проверки ссылок на пользователей.
    Вызов выполняется через импорт и перехват SystemExit чтобы корректно обработать код выхода.
    """
    try:
        from utils import check_fixtures_users

        print("🔎 Запускаем проверку фикстур (utils/check_fixtures_users.py)...")
        try:
            check_fixtures_users.main()
        except SystemExit as e:
            code = e.code if isinstance(e.code, int) else 1
            if code != 0:
                print("❌ Проверка фикстур не пройдена. Операция отменена.")
                sys.exit(code)
    except Exception as e:
        print("⚠️ Не удалось выполнить проверку фикстур автоматически:", e)
        print(
            "Попытка продолжить загрузку фикстур, но рекомендуется вручную проверить fixtures/initial_data.json"
        )


def clear_database(dry_run: bool = False):
    print("\n🧹 Начинаем очистку базы данных (основные модели)")
    deleted_summary = []
    with transaction.atomic():
        for app_label, model_name in MODELS_TO_CLEAR:
            try:
                model = apps.get_model(app_label, model_name)
            except LookupError:
                print(f"⚪ Модель не найдена (пропускаем): {app_label}.{model_name}")
                continue
            if not model:
                print(f"⚪ Модель не найдена (пропускаем): {app_label}.{model_name}")
                continue
            # Приведение типа для статических анализаторов (mypy/IDE)
            ModelClass = cast(Type[DjangoModel], model)
            # Получаем manager безопасно через getattr — это снимает предупреждения анализатора
            manager = getattr(ModelClass, "objects", None)
            if manager is None:
                print(
                    f"⚠️ У модели нет manager 'objects': {app_label}.{model_name} — пропускаем"
                )
                continue
            try:
                count = manager.count()
            except Exception:
                print(
                    f"⚠️ Не удалось посчитать записи для: {app_label}.{model_name} — пропускаем"
                )
                continue
            if count == 0:
                print(f"⚪ Нет записей для удаления: {app_label}.{model_name}")
                continue
            if dry_run:
                print(
                    f"🧾 [dry-run] Будет удалено {count} записей: {app_label}.{model_name}"
                )
                deleted_summary.append((f"{app_label}.{model_name}", count))
                continue
            # Реальное удаление через manager
            try:
                manager.all().delete()
                print(f"✅ Удалено {count} записей: {app_label}.{model_name}")
                deleted_summary.append((f"{app_label}.{model_name}", count))
            except Exception as e:
                print(f"❌ Ошибка при удалении записей {app_label}.{model_name}: {e}")
                continue
    return deleted_summary


def ensure_groups():
    created = []
    for name in REQUIRED_GROUPS:
        g, created_flag = Group.objects.get_or_create(name=name)
        if created_flag:
            created.append(name)
    if created:
        print(f"✅ Созданы группы: {', '.join(created)}")
    else:
        print("⚪ Все требуемые группы уже существуют")


def load_fixtures(path: Path, verbosity: int = 1):
    print(f"\n📥 Загружаем фикстуры из: {path}")
    try:
        call_command("loaddata", str(path), verbosity=verbosity)
        print("✅ Фикстуры успешно загружены!")
    except Exception as e:
        # Улучшаем диагностику для известной ошибки десериализации Permission
        import traceback

        msg = str(e)
        print(f"❌ Ошибка загрузки фикстур: {msg}")
        # Печатаем полный traceback чтобы можно было точно увидеть причину
        traceback.print_exc()
        if "Permission has no content_type" in msg or "Permission has no" in msg:
            print(
                "⚠️ Обнаружена ошибка десериализации объектов auth.Permission — попробуем загрузить фикстуры без записей auth.Permission"
            )
            try:
                import json

                # Открываем с utf-8-sig чтобы не падать на BOM
                with open(path, "r", encoding="utf-8-sig") as fh:
                    raw = json.load(fh)

                filtered = [
                    o for o in raw if o.get("model", "").lower() != "auth.permission"
                ]
                if len(filtered) == len(raw):
                    print(
                        "⚠️ Не найдено записей auth.Permission для фильтрации — пробуем завершить с оригинальной ошибкой"
                    )
                    raise
                tmp_path = path.with_suffix(".noperms.json")
                with open(tmp_path, "w", encoding="utf-8") as f:
                    json.dump(filtered, f, ensure_ascii=False, indent=2)
                print(f"🔁 Попытка загрузить фикстуры без auth.Permission: {tmp_path}")
                call_command("loaddata", str(tmp_path), verbosity=verbosity)
                print(
                    "✅ Фикстуры успешно загружены (без auth.Permission). Обратите внимание, что права/permissions нужно установить отдельно."
                )
                try:
                    tmp_path.unlink()
                except Exception:
                    pass
                return
            except Exception as e2:
                print(
                    "❌ Не удалось автоматически обойти проблему с auth.Permission:", e2
                )
        raise


def verify_data():
    print("\n=== Проверка загруженных данных ===")
    checks = [
        ("Users", "User", "пользователи"),
        ("Disciplines", "Discipline", "дисциплины"),
        ("Lessons", "Lesson", "уроки"),
        ("Exercises", "Test", "тесты"),
        ("Exercises", "Question", "вопросы"),
        ("Exercises", "Answer", "ответы"),
        ("Payments", "PriceConfiguration", "конфигурации цен"),
        ("Payments", "Payment", "платежи"),
        ("Payments", "PurchasedContent", "купленный контент"),
    ]
    for app_label, model_name, pretty in checks:
        try:
            model = apps.get_model(app_label, model_name)
            manager = getattr(model, "objects", None)
            if manager is None:
                count = "-"
            else:
                count = manager.count()
        except LookupError:
            count = "-"
        print(f"  {pretty}: {count}")

    try:
        User = apps.get_model("Users", "User")
        user_manager = getattr(User, "objects", None)
        if user_manager is not None:
            for u in user_manager.all():
                print(f"  📧 {u.email} (роль: {getattr(u, 'role', '—')})")
        else:
            print("  ⚪ Менеджер объектов для Users.User не обнаружен")
    except LookupError:
        print("  ⚪ Модель Users.User не найдена")


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Очистить БД и загрузить fixtures/initial_data.json"
    )
    parser.add_argument(
        "--yes", "-y", action="store_true", help="Не запрашивать подтверждение"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Показать что будет удалено, но не удалять",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Принудительный режим (обходит проверку DEBUG)",
    )
    args = parser.parse_args(argv)

    print("🗂️  Скрипт очистки и загрузки фикстур для LearningPlatform")
    print("=" * 60)

    check_safety_flags(args.force)

    verify_fixture_file(FIXTURE_PATH)

    # Проверка содержимого fixture через утилиту
    run_fixture_checker()

    if args.dry_run:
        print("\n⚠️  Dry-run режим: покажем что будет удалено и выйдем")
        clear_database(dry_run=True)
        print("\n✅ Dry-run завершён")
        return

    if not args.yes:
        ok = confirm(
            "Вы действительно хотите очистить базу данных основных сущностей и загрузить фикстуры?"
        )
        if not ok:
            print("❗ Загрузка отменена пользователем.")
            return

    # Очистка
    try:
        clear_database(dry_run=False)
    except Exception as e:
        print(f"❌ Ошибка при очистке базы: {e}")
        sys.exit(1)

    # Убедимся, что группы существуют
    try:
        ensure_groups()
    except Exception as e:
        print(f"⚠️ Не удалось создать/проверить группы: {e}")

    # Загрузка фикстур
    try:
        load_fixtures(FIXTURE_PATH, verbosity=2)
    except Exception:
        print("❌ Ошибка загрузки фикстур — операция прервана.")
        sys.exit(1)

    # Проверяем результат
    try:
        verify_data()
    except Exception as e:
        print(f"⚠️ Ошибка при проверке данных после загрузки: {e}")

    print("\n🎉 Готово!")
    print("\n📋 Данные для тестирования: ")
    print("Email: admin@a.aa, teacher_1@a.aa, student_1@a.aa, moderator_1@a.aa")
    print("Пароль: Spirocheta77 (для всех)")


if __name__ == "__main__":
    main()
