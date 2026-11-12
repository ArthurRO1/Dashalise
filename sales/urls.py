from django.urls import path

from . import views

urlpatterns = [
    path("health/", views.health, name="api-health"),
    path("dashboard/", views.dashboard, name="api-dashboard"),
    path("sales/", views.sales_list, name="api-sales"),
    path("sales/<int:sale_id>/reflections/", views.sale_reflection_create, name="api-sale-reflection"),
    path("sales/import-csv/", views.import_sales_csv, name="api-sales-import"),
    path("teams/", views.teams_list, name="api-teams"),
    path("people/", views.people_list, name="api-people"),
    path("products/", views.products_list, name="api-products"),
    path("alerts/", views.alerts_list, name="api-alerts"),
    path("alerts/<int:alert_id>/read/", views.mark_alert_read, name="api-alert-read"),
    path("assistant/", views.assistant, name="api-assistant"),
    path("assistant/status/", views.assistant_status, name="api-assistant-status"),
    path("assistant/messages/<int:message_id>/feedback/", views.assistant_feedback, name="api-assistant-feedback"),
    path("conversations/", views.conversations_list, name="api-conversations"),
    path("conversations/<int:conversation_id>/", views.conversation_detail, name="api-conversation-detail"),
    path("specializations/", views.specializations_list, name="api-specializations"),
    path("specializations/<int:specialization_id>/", views.specialization_detail, name="api-specialization-detail"),
]
