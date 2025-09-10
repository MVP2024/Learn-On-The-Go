import json
import os
import sys
import traceback
from pathlib import Path

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django

django.setup()
from django.core import serializers
from django.db import transaction

BASE = Path(__file__).resolve().parent.parent
FIXTURE = BASE / "fixtures" / "initial_data.json"


def read_fixture(path: Path):
    if not path.exists():
        print(f"Файл фикстур не найден: {path}")
        sys.exit(2)
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            return json.load(f)
    except Exception as e:
        print("Ошибка при чтении JSON фикстуры:", e)
        traceback.print_exc()
        sys.exit(3)


def try_deserialize_one(obj):
    # попробуем десериализовать единичный объект (формируем JSON списка с одним элементом)
    s = json.dumps([obj], ensure_ascii=False)
    try:
        it = serializers.deserialize("json", s)
    except Exception as e:
        print("Ошибка десериализации (json -> objects):", repr(e))
        traceback.print_exc()
        return False, ("deserialization", e)

    sid = transaction.savepoint()
    try:
        for o in it:
            o.save()
        # если дошли сюда — объект смог сохраниться, откатываем чтобы не менять БД
        transaction.savepoint_rollback(sid)
        return True, None
    except Exception as e:
        transaction.savepoint_rollback(sid)
        return False, ("save", e)


def main():
    data = read_fixture(FIXTURE)
    if not isinstance(data, list):
        print("Ожидался список объектов в JSON фикстуре. Тип =", type(data))
        sys.exit(4)

    print(f"Прочитано объектов: {len(data)}")

    from collections import Counter

    models = [str(o.get("model", "")).lower() for o in data]
    cnt = Counter(models)
    print("Топ моделей в фикстуре:")
    for m, c in cnt.most_common(30):
        print(f"  {m}: {c}")

    # Специальная проверка на auth.permission / contenttypes
    perm_count = cnt.get("auth.permission", 0)
    if perm_count:
        print(
            f"⚠️ В фикстуре найдено auth.permission: {perm_count} записей — они часто ломают loaddata (contenttypes mismatch)."
        )

    # Проходим по объектам и тестируем
    for i, obj in enumerate(data):
        model = obj.get("model")
        pk = obj.get("pk")
        if not obj.get("model") or "fields" not in obj:
            print(
                f"Запись #{i} не имеет model/fields -> возможно повреждена. obj={json.dumps(obj, ensure_ascii=False)[:2000]}"
            )
            return
        ok, info = try_deserialize_one(obj)
        if not ok:
            kind, err = info
            print("\n❌ Найдена проблемная запись:")
            print(f"  индекс: {i}")
            print(f"  model: {model}")
            print(f"  pk: {pk}")
            print(f"  ошибка при: {kind}")
            print(f"  exception: {repr(err)}")
            print("\nЗапись (полностью, усечено до 4000 символов):")
            try:
                print(json.dumps(obj, ensure_ascii=False, indent=2)[:4000])
            except Exception:
                print(str(obj)[:4000])

            # сохраняем проблемную запись в файл для удобства
            out = FIXTURE.with_name("problem_record.json")
            try:
                with open(out, "w", encoding="utf-8") as f:
                    json.dump(obj, f, ensure_ascii=False, indent=2)
                print(f"Проблемная запись сохранена в: {out}")
            except Exception as e:
                print("Не удалось записать problem_record.json:", e)

            print("\nПодробный traceback ошибки:")
            traceback.print_exception(type(err), err, err.__traceback__)
            return

    print(
        "\n✅ Все объекты прошли тест сохранения (с откатом). Вероятно проблема — не в отдельных записях."
    )


if __name__ == "__main__":
    main()
