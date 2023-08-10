from django.urls import path

from employers import views

urlpatterns = [
    path('', views.DepartmentsView.as_view(), name='staff'),
    path('table', views.WorkersView.as_view(), name='workers_table'),
]
