from django.urls import include, path

from . import views

urlpatterns = [
    path("get_package_data/", views.get_package_data, name="get_package_data"),
    path("browse/", views.index, name="index"),
    path("registry/packages", views.index, name="index"),
    path("directory/", views.directory, name="directory"),
    path("manifest/<str:manifest_uri>", views.manifest, name="manifest"),
    path("browse/<str:chain_name>/", views.find_registry, name="find_registry"),
    path("browse/<str:chain_name>/<str:registry_addr>", views.browse, name="browse"),
    path("", views.index, name="index"),
]
