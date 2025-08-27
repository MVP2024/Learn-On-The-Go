from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include, re_path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from Tests.views import AnswerViewSet, QuestionViewSet, TestViewSet
from Disciplines.views import DisciplineViewSet
from Lessons.views import LessonViewSet
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)

from django.views.generic import RedirectView
from rest_framework.permissions import AllowAny
from Users.serializers import CustomTokenObtainPairSerializer
from Users.views import UserProfileViewSet, RegisterView


from Payments.views import PaymentViewSet, PurchasedContentViewSet, PriceConfigurationViewSet, YooKassaWebhookView

router = DefaultRouter()
router.register(r"tests", TestViewSet, basename="test")
router.register(r"questions", QuestionViewSet, basename="question")
router.register(r"answers", AnswerViewSet, basename="answer")
router.register(r"disciplines", DisciplineViewSet, basename="discipline")
router.register(r"lessons", LessonViewSet, basename="lesson")
router.register(r"profiles", UserProfileViewSet, basename="user-profile")
router.register(r"payments", PaymentViewSet, basename="payment")
router.register(r"purchased-content", PurchasedContentViewSet, basename="purchased-content")
router.register(r"price-configurations", PriceConfigurationViewSet, basename="price-configuration")
urlpatterns = [
    # Редирект с корня на документацию Swagger UI
    re_path(
        r"^$", RedirectView.as_view(url="/api/schema/swagger-ui/", permanent=False)
    ),
    path("admin/", admin.site.urls),
    path("api/register/", RegisterView.as_view(), name="register"),
    path("", include(router.urls)),
    # Эндпоинты для JWT авторизации
    path(
        "api/token/",
        TokenObtainPairView.as_view(serializer_class=CustomTokenObtainPairSerializer),
        name="token_obtain_pair",
    ),
    path("api/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    # Документация API
    path(
        "api/schema/",
        SpectacularAPIView.as_view(permission_classes=[AllowAny]),
        name="schema",
    ),
    path(
        "api/schema/swagger-ui/",
        SpectacularSwaggerView.as_view(
            url_name="schema", permission_classes=[AllowAny]
        ),
        name="swagger-ui",
    ),
    path(
        "api/schema/redoc/",
        SpectacularRedocView.as_view(url_name="schema", permission_classes=[AllowAny]),
        name="redoc",
    ),
    # Webhook для ЮKassa
    path("api/payments/yookassa-webhook/", YooKassaWebhookView.as_view(), name="yookassa-webhook"),
]

# Для отдачи медиа файлов в режиме отладки
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
