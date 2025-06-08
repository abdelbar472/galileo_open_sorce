from django.urls import path
from . import views

urlpatterns = [
    path('', views.CreateSpaceView.as_view(), name='space_list_create'),
    path('<uuid:space_id>/', views.SpaceDetailView.as_view(), name='space_detail'),  # Changed space_pk to space_id
    path('<uuid:space_id>/invite/', views.InviteView.as_view(), name='invite'),  # Changed space_pk to space_id
    path('join/', views.JoinView.as_view(), name='join'),
    path('<uuid:space_id>/space-jwt/', views.SpaceJWTView.as_view(), name='space_jwt'),  # Changed space_pk to space_id
    path('<uuid:space_id>/tokens/', views.SpaceAccessTokenView.as_view(), name='space_access'),
    # Use the correct view name    # New endpoints for removing a member and changing a member's role
    path('<uuid:space_id>/remove-member/', views.RemoveSpaceMemberView.as_view(), name='remove_space_member'),
    path('<uuid:space_id>/change-role/', views.ChangeSpaceMemberRoleView.as_view(), name='change_space_member_role'),
    path('<uuid:space_id>/leave/', views.LeaveSpaceView.as_view(), name='leave_space'),
]
