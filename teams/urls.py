from django.urls import path
from .views import *

urlpatterns = [
    # Path for creating a team
    #path('create/', CreateTeamView.as_view(), name='create_team'),  # POST

    # Path for joining a team using a token
  #  path('join/', JoinTeamView.as_view(), name='join_team'),  # POST

    # Path for listing all teams a user belongs to
    path('', ListTeamsView.as_view(), name='list_teams'),  # GET

    # Path for generating an OTP for a team
   # path('otp/', GenerateOTPAPIView.as_view(), name='generate_otp'),  # POST

    # Path for removing a member from a team
    path('<int:team_id>/remove-member/', RemoveMemberView.as_view(), name='remove-member'),  # DELETE

    # Path for viewing team members
    path('<int:team_id>/members/', TeamMembersView.as_view(), name='team_members'),  # GET
]