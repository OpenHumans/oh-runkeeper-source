from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('complete/', views.complete, name='complete'),
    path('runkeeper_complete/',
         views.runkeeper_complete,
         name='runkeeper_complete'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('update_data/', views.update_data, name='update_data'),
    path('remove_runkeeper/',
         views.remove_runkeeper,
         name='remove_runkeeper')
]
