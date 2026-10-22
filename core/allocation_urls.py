from django.urls import path

from . import allocation_views

app_name = "allocation"

urlpatterns = [
    path("manage/", allocation_views.manage_allocations, name="manage"),
    path("my-room/", allocation_views.my_room, name="my_room"),
]
