from django.urls import path

from users.views import MeView, RegisterView, UserListView

app_name = 'users'

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('me/', MeView.as_view(), name='me'),
    path('', UserListView.as_view(), name='list'),
]
