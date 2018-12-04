from django.urls import include, path

from . import views

urlpatterns = [
    path('get_package_data/', views.get_package_data, name='get_package_data'),
    path('', views.index, name='index'),
]
