# Система платежей — краткая сводка

Это сводка по реализации платежей в LearningPlatform. Документы с подробностями: Payments/QUICK_START.md, Payments/YOOKASSA_SETUP.md, Payments/STRIPE_SETUP.md.

Что реализовано (кратко)
- Модели:
  - Payment — запись платёжной операции (тип, сумма, статус, внешние id).
  - PurchasedContent — купленный контент (дисциплина/урок) связанный с Payment.
  - PriceConfiguration — цены, флаги "бесплатно" и сведения о скидках.

- API:
  - /api/payments/ — создание/просмотр платежей (PaymentViewSet)
  - /api/purchased-content/ — просмотр купленного контента
  - /api/price-configurations/ — управление ценами (для админов/модераторов)
  - Webhook: /api/payments/yookassa-webhook/ (ЮKassa)

Основная логика и ключевые моменты
- Покупка дисциплины/урока создаёт Payment. Если цена = 0 — платеж сразу помечается как completed и создаётся PurchasedContent.
- Для платных платежей Payment остаётся pending до завершения: внешняя система (YooKassa/Stripe) меняет статус и/или webhook вызывает завершение.
- После завершения платежа создаётся PurchasedContent (receiver post_save в Payments.signals делает get_or_create — идемпотентно).
- Покупка контента даёт доступ к просмотру материалов (уроков/видео), но доступ к тестам требует дополнительных условий:
  - Тесты, привязанные к уроку, доступны только после завершения этого урока.
  - Итоговые тесты (для дисциплины) доступны только после завершения всех уроков дисциплины.
  (Логика в PaymentService.get_available_tests_for_user и Exercises.services/_accessible_tests_for_student.)

Интеграции
- YooKassa
  - Поддержка создания платежа, подтверждения, получение информации и webhook.
  - Для тестирования используйте ngrok и тестовые карты (см. Payments/YOOKASSA_SETUP.md).
- Stripe
  - Поддержка создания PaymentIntent, проверки статуса, отмен и возвратов.
  - Для тестов используйте тестовые карты Stripe (см. Payments/STRIPE_SETUP.md).

Безопасность и эксплуатация
- Никогда не храните секреты в репозитории — используйте .env (в .gitignore) и CI-секреты.
- Webhook в продакшне должен быть доступен по HTTPS и проверяться на подпись.
- Для локального тестирования webhook используйте туннели (ngrok/Cloudflare Tunnel).

Быстрый старт (см. подробный QUICK_START.md)
1. Применить миграции: python manage.py migrate
2. Настроить цены: python utils/scripts_for_demo/setup_prices.py [setup|free|discount]
3. Создать платёж через API /api/payments/create_payment/

---

← [← В README](README.md) | **Далее:** [Payments/QUICK_START.md](Payments/QUICK_START.md) → | [Все руководства](README.md#6-документы-и-подробные-руководства)
