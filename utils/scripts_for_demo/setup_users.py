#!/usr/bin/env python
"""
Скрипт для создания пользователей с правильными паролями.
"""
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.contrib.auth.models import Group
from Users.models import User
from Students.models import Student
from Teachers.models import Teacher

def create_test_users():
    """
    Создает тестовых пользователей с правильными паролями.
    """
    print("=== Создание тестовых пользователей ===")
    
    # Создаем группы, если их нет
    admin_group, _ = Group.objects.get_or_create(name='admin')
    teacher_group, _ = Group.objects.get_or_create(name='teacher')
    student_group, _ = Group.objects.get_or_create(name='student')
    moderator_group, _ = Group.objects.get_or_create(name='moderator')
    
    users_data = [
        {
            'email': 'admin@a.aa',
            'password': 'Spirocheta77',
            'role': 'admin',
            'first_name': 'Админ',
            'last_name': 'Админов',
            'is_superuser': True,
            'is_staff': True,
        },
        {
            'email': 'teacher_1@a.aa',
            'password': 'Spirocheta77',
            'role': 'teacher',
            'first_name': 'Иван',
            'last_name': 'Иванов',
            'patronymic': 'Иванович',
            'phone_number': '+79000000000',
        },
        {
            'email': 'student_1@a.aa',
            'password': 'Spirocheta77',
            'role': 'student',
            'first_name': 'Степан',
            'last_name': 'Степанов',
            'patronymic': 'Степанович',
            'phone_number': '+79000000001',
        },
        {
            'email': 'moderator_1@a.aa',
            'password': 'Spirocheta77',
            'role': 'moderator',
            'first_name': 'Алена',
            'last_name': 'Алексина',
            'patronymic': 'Алексеевна',
            'phone_number': '+79000000002',
        },
        {
            'email': 'admin_2@a.aa',
            'password': 'Spirocheta77',
            'role': 'admin',
            'first_name': 'Елена',
            'last_name': 'Еленова',
            'patronymic': 'Елисеевна',
        }
    ]
    
    for user_data in users_data:
        email = user_data['email']
        
        # Удаляем существующего пользователя если есть
        User.objects.filter(email=email).delete()
        
        # Выделяем поля для создания пользователя
        password = user_data.pop('password')
        role = user_data.pop('role')
        
        # Создаем пользователя
        if user_data.get('is_superuser'):
            user = User.objects.create_superuser(**user_data)
        else:
            user = User.objects.create_user(**user_data)
            
        # Устанавливаем пароль
        user.set_password(password)
        user.role = role
        user.save()
        
        # Добавляем в группы
        if role == 'admin':
            user.groups.add(admin_group)
        elif role == 'teacher':
            user.groups.add(teacher_group)
            Teacher.objects.get_or_create(user=user)
        elif role == 'student':
            user.groups.add(student_group)
            Student.objects.get_or_create(user=user, defaults={'course': 1})
        elif role == 'moderator':
            user.groups.add(moderator_group)
            
        print(f"✅ Создан пользователь: {email} (роль: {role})")
    
    print("\n✅ Все пользователи созданы успешно!")
    print("\n📋 Данные для входа:")
    print("Email: admin@a.aa, teacher_1@a.aa, student_1@a.aa, moderator_1@a.aa")
    print("Пароль: Spirocheta77 (для всех)")

if __name__ == "__main__":
    create_test_users()