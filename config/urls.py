from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path
from django.views.generic import TemplateView

from core import views

urlpatterns = [
    path("admin/", admin.site.urls),

    # Public
    path("", views.home, name="home"),
    path("about/", views.about, name="about"),
    path("privacy/", views.privacy, name="privacy"),

    # Auth
    path("signup/", views.signup, name="signup"),
    path("login/", auth_views.LoginView.as_view(template_name="login.html"),
         name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),

    # Access Passport
    path("onboarding/", views.onboarding, name="onboarding"),
    path("passports/", views.passport_list, name="passport_list"),
    path("passports/<int:pk>/activate/", views.passport_activate, name="passport_activate"),
    path("passports/<int:pk>/delete/", views.passport_delete, name="passport_delete"),
    path("passports/<int:pk>/export/", views.passport_export, name="passport_export"),
    path("passports/import/", views.passport_import, name="passport_import"),

    # Tasks
    path("tasks/", views.task_list, name="task_list"),
    path("tasks/new/", views.task_new, name="task_new"),
    path("tasks/<int:pk>/", views.task_player, name="task_player"),
    path("tasks/<int:pk>/analysis/", views.task_analysis, name="task_analysis"),
    path("tasks/<int:pk>/action/", views.task_action, name="task_action"),
    path("tasks/<int:pk>/repeat/", views.task_repeat, name="task_repeat"),
    path("tasks/<int:pk>/delete/", views.task_delete, name="task_delete"),

    # Live "Look around" (on-device object detection)
    path("look/", views.look, name="look"),

    # Sound Watch (visual + vibration sound alerts) and Conversation Mode
    path("soundwatch/", views.soundwatch, name="soundwatch"),
    path("captions/", views.captions, name="captions"),

    # Communication Bridge
    path("communication/", views.communication, name="communication"),
    path("communication/phrase/add/", views.phrase_add, name="phrase_add"),
    path("communication/phrase/<int:pk>/delete/", views.phrase_delete, name="phrase_delete"),

    # Resources + population
    path("resources/", views.resources, name="resources"),
    path("dashboard/", views.dashboard, name="dashboard"),

    # Voice output (ElevenLabs proxy; falls back to browser speech)
    path("api/tts/", views.tts_speak, name="tts_speak"),
    path("api/recent/", views.recent_summary, name="recent_summary"),

    # Privacy actions
    path("privacy/delete-all/", views.delete_all_data, name="delete_all_data"),

    # PWA
    path("manifest.webmanifest",
         TemplateView.as_view(template_name="pwa/manifest.webmanifest",
                              content_type="application/manifest+json"),
         name="manifest"),
    path("service-worker.js",
         TemplateView.as_view(template_name="pwa/service-worker.js",
                              content_type="application/javascript"),
         name="service_worker"),
    path("offline/", TemplateView.as_view(template_name="pwa/offline.html"),
         name="offline"),
]
