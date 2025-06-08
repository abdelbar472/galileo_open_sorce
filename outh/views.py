from django.shortcuts import redirect,render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, generics
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.tokens import AccessToken
from .serializers import *
from rest_framework.permissions import IsAuthenticated
from django.core.mail import send_mail
from django.core.mail import EmailMessage
from rest_framework.authentication import SessionAuthentication  # Added for session auth



def home(request):
    return render(request, 'login.html')

class CompleteProfileAPIView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserSerializer
    authentication_classes = [SessionAuthentication, JWTAuthentication]

    def get(self, request):
        user = request.user
        serializer = UserSerializer(user, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        user = request.user
        serializer = UserSerializer(user, data=request.data, partial=True, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "Profile updated successfully", "data": serializer.data}, status=status.HTTP_200_OK)
        return Response({"errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

class SignupAPIView(APIView):
    authentication_classes = []
    def post(self, request):
        serializer = SignupSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            refresh = RefreshToken.for_user(user)
            token = str(refresh.access_token)
            send_mail(
                subject="Welcome to the App!",
                message=f"Hi {user.username},\nWelcome to the app! Your profile setup is pending.",
                from_email='your_email',
                recipient_list=[user.email],
            )
            redirect_url = f"http://127.0.0.1:8000/profile/"
            return Response({"redirect_url": redirect_url}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class LoginAPIView(APIView):
    authentication_classes = []
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            validated_data = serializer.validated_data
            user = validated_data['user']
            remember_me = validated_data.get('remember_me', False)
            login(request, user)
            tokens = validated_data['tokens']
            if not remember_me:
                request.session.set_expiry(0)
            redirect_url = f"http://127.0.0.1:8000/space/"
            return Response(
                {
                    "message": "Login successful!",
                    "access_token": tokens['access'],
                    "refresh_token": tokens['refresh'],
                    "redirect_url": redirect_url
                },
                status=status.HTTP_200_OK,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class LogoutAPIView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            logout(request)
            request.session.flush()
            return Response({"message": "Logout successful"}, status=status.HTTP_200_OK)
        return Response({"error": "Invalid refresh token"}, status=status.HTTP_400_BAD_REQUEST)