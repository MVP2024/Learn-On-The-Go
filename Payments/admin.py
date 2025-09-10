from django.contrib import admin

from .models import Payment, PriceConfiguration, PurchasedContent


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "payment_type",
        "get_content_title",
        "amount",
        "status",
        "created_at",
        "completed_at",
    )
    list_filter = ("payment_type", "status", "created_at", "payment_method")
    search_fields = (
        "user__email",
        "user__first_name",
        "user__last_name",
        "transaction_id",
    )
    readonly_fields = ("transaction_id", "created_at", "completed_at")
    ordering = ("-created_at",)

    fieldsets = (
        (
            "Основная информация",
            {"fields": ("user", "payment_type", "discipline", "lesson")},
        ),
        (
            "Платежная информация",
            {"fields": ("amount", "status", "payment_method", "transaction_id")},
        ),
        (
            "Временные метки",
            {"fields": ("created_at", "completed_at"), "classes": ("collapse",)},
        ),
    )

    def get_content_title(self, obj):
        if obj.discipline:
            return f"Дисциплина: {obj.discipline.title}"
        elif obj.lesson:
            return f"Урок: {obj.lesson.title}"
        return "Неизвестно"

    get_content_title.short_description = "Контент"

    def get_readonly_fields(self, request, obj=None):
        if obj and obj.status == "completed":
            # Если платеж завершен, делаем больше полей только для чтения
            return self.readonly_fields + (
                "user",
                "payment_type",
                "discipline",
                "lesson",
                "amount",
                "status",
            )
        return self.readonly_fields


@admin.register(PurchasedContent)
class PurchasedContentAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "get_content_type",
        "get_content_title",
        "get_payment_amount",
        "purchased_at",
    )
    list_filter = ("purchased_at", "payment__payment_type")
    search_fields = (
        "user__email",
        "user__first_name",
        "user__last_name",
        "discipline__title",
        "lesson__title",
    )
    readonly_fields = ("purchased_at",)
    ordering = ("-purchased_at",)

    def get_content_type(self, obj):
        if obj.discipline:
            return "Дисциплина"
        elif obj.lesson:
            return "Урок"
        return "Неизвестно"

    get_content_type.short_description = "Тип контента"

    def get_content_title(self, obj):
        if obj.discipline:
            return obj.discipline.title
        elif obj.lesson:
            return obj.lesson.title
        return "Неизвестно"

    get_content_title.short_description = "Название"

    def get_payment_amount(self, obj):
        return f"{obj.payment.amount} ₽"

    get_payment_amount.short_description = "Сумма платежа"


@admin.register(PriceConfiguration)
class PriceConfigurationAdmin(admin.ModelAdmin):
    list_display = (
        "get_content_title",
        "get_content_type",
        "price",
        "is_free",
        "discount_price",
        "discount_end_date",
        "get_current_price_display",
    )
    list_filter = ("is_free", "discount_end_date", "created_at")
    search_fields = ("discipline__title", "lesson__title")
    readonly_fields = ("created_at", "updated_at", "get_current_price_display")

    # отсутствие проверки PyUnresolvedReferences
    fieldsets = (
        ("Контент", {"fields": ("discipline", "lesson")}),
        (
            "Цена",
            {
                "fields": (
                    "price",
                    "is_free",
                    "discount_price",
                    "discount_end_date",
                    "get_current_price_display",
                )
            },
        ),
        (
            "Временные метки",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    def get_content_type(self, obj):
        if obj.discipline:
            return "Дисциплина"
        elif obj.lesson:
            return "Урок"
        return "Неизвестно"

    get_content_type.short_description = "Тип"

    def get_content_title(self, obj):
        if obj.discipline:
            return obj.discipline.title
        elif obj.lesson:
            return obj.lesson.title
        return "Неизвестно"

    get_content_title.short_description = "Название"

    def get_current_price_display(self, obj):
        current_price = obj.get_current_price()
        if obj.is_free:
            return "Бесплатно"
        return f"{current_price} ₽"

    get_current_price_display.short_description = "Текущая цена"
