from django.urls import path
from .views import *
urlpatterns = [
    path('<uuid:space_id>/', CreatePostView.as_view(), name='create-post'),#post
    path('update/<uuid:pk>/', UpdatePostView.as_view(), name='update-post'),#put
    path('delete/<uuid:pk>/', DeletePostView.as_view(), name='delete-post'),#delete
    path('<uuid:space_id>/list/', ListPostView.as_view(), name='scheduled-posts'),#get
    path('<uuid:id>/', RetrievePostView.as_view(), name='upcoming-posts'),#get

]