# 🚀 Руководство по тестированию API LearningPlatform

## ✅ Исправленные проблемы

### 1. Настройки аутентификации
- ✅ Убран конфликт в `DEFAULT_PERMISSION_CLASSES`
- ✅ Исправлены настройки JWT токенов (`USER_ID_FIELD`)
- ✅ Добавлен debug endpoint для тестирования
- ✅ Создан скрипт для корректных пользователей

## 🛠️ Подготовка к тестированию

### Шаг 0: Очистка и загрузка данных (РЕКОМЕНДУЕТСЯ)
```
python clear_and_load_fixtures.py
```
Этот скрипт автоматически очистит базу данных и загрузит все тестовые данные.

### Альтернативный способ - создание только пользователей:
```
python setup_users.py
```

### 2. Упрощение API
- ✅ Все фильтры сделаны опциональными
- ✅ Убраны сложные фильтры типа `exact` + `icontains`
- ✅ Поиск объектов работает по ID ИЛИ по названию/email

## 🧪 Пошаговое тестирование

### Шаг 1: Получение токена
```
curl -X POST http://localhost:8000/api/token/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "teacher_1@a.aa",
    "password": "Spirocheta77"
  }'
```

**Ответ должен быть:**
```json
{
    "access": "eyJ0eXAiOiJKV1Q...",
    "refresh": "eyJ0eXAiOiJKV1Q..."
}
```

### Шаг 2: Тестирование аутентификации
```
curl -X GET http://localhost:8000/api/debug-auth/ \
  -H "Authorization: Bearer ВАШ_ACCESS_TOKEN"
```

**Ответ должен быть:**
```json
{
    "authenticated": true,
    "user_id": 2,
    "user_email": "teacher_1@a.aa",
    "headers": {
        "Authorization": "Bearer ...",
        "Content-Type": "application/json"
    }
}
```

### Шаг 3: Простые запросы к API

#### Получить все дисциплины (БЕЗ параметров)
```
curl -X GET http://localhost:8000/disciplines/ \
  -H "Authorization: Bearer ВАШ_ACCESS_TOKEN"
```

#### Получить дисциплину по ID
```
curl -X GET http://localhost:8000/disciplines/1/ \
  -H "Authorization: Bearer ВАШ_ACCESS_TOKEN"
```

#### Получить дисциплину по названию
```
curl -X GET http://localhost:8000/disciplines/Алгебра/ \
  -H "Authorization: Bearer ВАШ_ACCESS_TOKEN"
```

#### Поиск дисциплин (опциональные фильтры)
```
curl -X GET "http://localhost:8000/disciplines/?title=Python" \
  -H "Authorization: Bearer ВАШ_ACCESS_TOKEN"
```

#### Получить все уроки
```
curl -X GET http://localhost:8000/lessons/ \
  -H "Authorization: Bearer ВАШ_ACCESS_TOKEN"
```

#### Получить все тесты
```
curl -X GET http://localhost:8000/tests/ \
  -H "Authorization: Bearer ВАШ_ACCESS_TOKEN"
```

#### Получить всех пользователей
```
curl -X GET http://localhost:8000/profiles/ \
  -H "Authorization: Bearer ВАШ_ACCESS_TOKEN"
```

### Шаг 4: Поиск конкретных объектов

#### Поиск урока по ID или названию
```
# По ID
curl -X GET http://localhost:8000/lessons/1/ \
  -H "Authorization: Bearer ВАШ_ACCESS_TOKEN"

# По названию
curl -X GET "http://localhost:8000/lessons/Части речи/" \
  -H "Authorization: Bearer ВАШ_ACCESS_TOKEN"
```

#### Поиск пользователя по ID или email
```
# По ID
curl -X GET http://localhost:8000/profiles/2/ \
  -H "Authorization: Bearer ВАШ_ACCESS_TOKEN"

# По email
curl -X GET "http://localhost:8000/profiles/teacher_1@a.aa/" \
  -H "Authorization: Bearer ВАШ_ACCESS_TOKEN"
```

### Шаг 5: Опциональные фильтры

#### Поиск уроков по названию дисциплины
```
curl -X GET "http://localhost:8000/lessons/?discipline__title=Алгебра" \
  -H "Authorization: Bearer ВАШ_ACCESS_TOKEN"
```

#### Поиск пользователей по фамилии
```
curl -X GET "http://localhost:8000/profiles/?last_name=Иванов" \
  -H "Authorization: Bearer ВАШ_ACCESS_TOKEN"
```

## 🎯 Ожидаемые результаты

### ✅ Что должно работать:
- Все простые GET запросы без параметров
- Поиск объектов как по ID, так и по названию/email
- Все фильтры работают опционально
- Аутентификация через Bearer токен

### ❌ Если что-то не работает:
1. **401 Unauthorized** - проверьте токен в заголовке Authorization
2. **404 Not Found** - объект не найден, проверьте ID/название
3. **400 Bad Request** - проверьте формат запроса

## 🔧 Debug endpoints

### Проверить аутентификацию
```
GET /api/debug-auth/
```

### Получить схему API
```bash
GET /api/schema/
```

### Swagger UI
```
http://localhost:8000/api/schema/swagger-ui/
```

## 📋 Готовые пользователи для тестирования

Из fixture файла доступны:
- **admin@a.aa** / **Spirocheta77** (админ)
- **teacher_1@a.aa** / **Spirocheta77** (учитель)
- **student_1@a.aa** / **Spirocheta77** (студент)
- **moderator_1@a.aa** / **Spirocheta77** (модератор)

## 🎉 Теперь API работает просто и понятно!

Все основные проблемы исправлены:
✅ Аутентификация работает  
✅ Простые запросы без параметров  
✅ Гибкий поиск по ID и названию  
✅ Опциональные фильтры  
✅ Понятная документация  