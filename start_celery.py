#!/usr/bin/env python
"""
Скрипт для запуска Celery worker и beat.
Использовать для разработки и тестирования.
"""
import os
import subprocess
import sys
import time
from pathlib import Path

# Установка переменной Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

BASE_DIR = Path(__file__).resolve().parent

def start_celery():
    """Запускает Celery worker и beat"""
    print("🚀 Запускаем Celery для LearningPlatform")
    print("=" * 50)
    
    worker_cmd = [
        sys.executable,
        '-m', 'celery',
        '-A', 'config',
        'worker',
        '--loglevel=info',
        '--concurrency=2',
    ]
    
    beat_cmd = [
        sys.executable,
        '-m', 'celery',
        '-A', 'config',
        'beat',
        '--loglevel=info'
    ]
    
    print("📋 Доступные задачи:")
    print("• utils.celery_tasks.cleanup_expired_payments")
    print("• utils.celery_tasks.cleanup_expired_discounts") 
    print("• utils.celery_tasks.generate_daily_reports")
    print("• utils.celery_tasks.update_user_progress_stats")
    print("• utils.celery_tasks.send_course_reminders")
    print("• Users.tasks.send_admin_key_email")
    print("• Users.tasks.notify_superusers_about_admin_key_request")
    print()
    
    choice = input("Выберите:\n1 - Worker + Beat\n2 - Только Worker\n3 - Только Beat\nВведите номер (1-3): ")
    
    if choice == "1":
        print("\n🔄 Запускаем Worker + Beat...")
        # В продакшене лучше запускать отдельно
        try:
            # Запускаем worker в фоне
            worker_process = subprocess.Popen(worker_cmd)
            time.sleep(2)
            
            # Запускаем beat
            beat_process = subprocess.Popen(beat_cmd)
            
            print("✅ Celery запущен!")
            print("Worker PID:", worker_process.pid)
            print("Beat PID:", beat_process.pid)
            print("\nДля остановки нажмите Ctrl+C")
            
            # Ждём сигнала для завершения
            try:
                worker_process.wait()
                beat_process.wait()
            except KeyboardInterrupt:
                print("\n🛑 Останавливаем Celery...")
                worker_process.terminate()
                beat_process.terminate()
                print("✅ Celery остановлен")
                
        except Exception as e:
            print(f"❌ Ошибка запуска: {e}")
            
    elif choice == "2":
        print("\n🔄 Запускаем только Worker...")
        try:
            subprocess.run(worker_cmd)
        except KeyboardInterrupt:
            print("\n🛑 Worker остановлен")
            
    elif choice == "3":
        print("\n🔄 Запускаем только Beat...")
        try:
            subprocess.run(beat_cmd)
        except KeyboardInterrupt:
            print("\n🛑 Beat остановлен")
    else:
        print("❌ Неверный выбор")

def show_status():
    """Показывает статус Celery"""
    status_cmd = [
        sys.executable,
        '-m', 'celery',
        '-A', 'config',
        'status'
    ]
    
    try:
        result = subprocess.run(status_cmd, capture_output=True, text=True)
        print("📊 Статус Celery:")
        print(result.stdout)
        if result.stderr:
            print("Ошибки:", result.stderr)
    except Exception as e:
        print(f"❌ Ошибка получения статуса: {e}")

def run_task():
    """Запускает отдельную задачу"""
    print("🎯 Доступные задачи:")
    tasks = [
        "utils.celery_tasks.cleanup_expired_payments",
        "utils.celery_tasks.cleanup_expired_discounts", 
        "utils.celery_tasks.generate_daily_reports",
        "utils.celery_tasks.update_user_progress_stats",
        "utils.celery_tasks.send_course_reminders"
    ]
    
    for i, task in enumerate(tasks, 1):
        print(f"{i}. {task}")
    
    choice = input("\nВыберите номер задачи (1-5): ")
    
    try:
        task_num = int(choice) - 1
        if 0 <= task_num < len(tasks):
            task_name = tasks[task_num]
            
            # Запускаем задачу через shell
            from django.core.management import execute_from_command_line
            execute_from_command_line([
                'manage.py',
                'shell', '-c', 
                f'from {task_name.rsplit(".", 1)[0]} import {task_name.split(".")[-1]}; print({task_name.split(".")[-1]}.delay())'
            ])
        else:
            print("❌ Неверный номер задачи")
    except ValueError:
        print("❌ Введите число")
    except Exception as e:
        print(f"❌ Ошибка: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "status":
            show_status()
        elif sys.argv[1] == "task":
            run_task()
        else:
            print("Использование: python start_celery.py [status|task]")
    else:
        start_celery()