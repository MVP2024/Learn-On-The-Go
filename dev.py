"""
Кроссплатформенный помощник разработчика для изучения платформы.
Позволяет запускать общие команды из Windows (make не установлен), macOS и Linux.
Использование:
  python dev.py
обновление python dev.py тестирование-настройка-запуск
python dev.py перенос

Это отражает цели из Makefile, но не требует GNU make.
"""

import argparse
import shutil
import subprocess
import sys

CMDS = {
    "build": ["docker", "compose", "build"],
    "up": ["docker", "compose", "up", "-d", "--build"],
    "down": ["docker", "compose", "down", "-v"],
    "logs": ["docker", "compose", "logs", "-f", "web"],
    "shell": ["docker", "compose", "exec", "web", "sh"],
    "migrate": ["docker", "compose", "exec", "web", "python", "manage.py", "migrate"],
    "fixtures": [
        "docker",
        "compose",
        "exec",
        "web",
        "python",
        "utils/clear_and_load_fixtures.py",
        "--yes",
    ],
    # запускайте тесты в одноразовом контейнере, явно указав DJANGO_SETTINGS_MODULE
    "test-docker-run": [
        "docker",
        "compose",
        "run",
        "--rm",
        "-e",
        "DJANGO_SETTINGS_MODULE=config.test_settings",
        "web",
        "python",
        "-m",
        "pytest",
        "-q",
        "-o",
        "addopts=",
    ],
    # Запускаем минимальную инфраструктуру и pytest в веб-контейнере (exec)
    "test-docker": [
        "sequence_start_db_redis_and_exec_pytest",
    ],
}


def check_docker_available():
    if shutil.which("docker") is None:
        print(
            "Ошибка: интерфейс командной строки docker не найден в PATH. "
            "Пожалуйста, установите Docker Desktop или интерфейс командной строки docker."
        )
        return False
    return True


def run(cmd, check=True):
    print("> ", " ".join(cmd))
    try:
        subprocess.run(cmd, check=check)
    except subprocess.CalledProcessError as e:
        print(f"Ошибка выполнения команды с кодом завершения {e.returncode}")
        if check:
            sys.exit(e.returncode)
    except FileNotFoundError:
        print(f"Команда не найдена: {cmd[0]}")
        sys.exit(2)


def run_test_docker():
    # Запускаем db и redis (только их), а затем можем выполнить команду pytest в веб-интерфейсе с тестовыми настройками
    if not check_docker_available():
        sys.exit(1)
    run(["docker", "compose", "up", "-d", "--build", "db", "redis"])
    # запускаем pytest внутри веб-контейнера с помощью DJANGO_SETTINGS_MODULE переопределяя
    run(
        [
            "docker",
            "compose",
            "exec",
            "-e",
            "DJANGO_SETTINGS_MODULE=config.test_settings",
            "web",
            "python",
            "-m",
            "pytest",
            "-q",
            "-o",
            "addopts=",
        ]
    )


def main():
    parser = argparse.ArgumentParser(
        description="Помощник разработчика для изучения платформы"
    )
    parser.add_argument(
        "target", nargs="?", default="help", help="Какую цель запустить"
    )
    args = parser.parse_args()
    t = args.target
    if t == "help":
        print("Доступные цели:")
        for k in sorted(list(CMDS.keys()) + ["help"]):
            print(" - ", k)
        sys.exit(0)

    if t not in CMDS:
        print(
            f"Неизвестная цель: {t}\nRun: python dev.py (без аргументов) для просмотра доступных целей"
        )
        sys.exit(1)

    if t == "test-docker":
        run_test_docker()
        return

    cmd = CMDS[t]
    if isinstance(cmd, list) and cmd:
        if not check_docker_available():
            sys.exit(1)
        run(cmd)


if __name__ == "__main__":
    main()
