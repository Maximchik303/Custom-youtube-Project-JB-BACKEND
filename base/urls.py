from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (VideoViewSet, CategoryViewSet, MyTokenObtainPairView,
UserRegisterView, UserProfileView, LikedVideosView, ChangePasswordView, UploadedVideosView)


router = DefaultRouter()
router.register('videos', VideoViewSet, basename='video')
router.register('categories', CategoryViewSet)


urlpatterns = [
    path('api/token/', MyTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),  # Refresh token
    path('', include(router.urls)),
    path('api/register/', UserRegisterView.as_view(), name='user_register'),
    path('api/user/', UserProfileView.as_view(), name='user_profile'),
    path('api/liked-videos/', LikedVideosView.as_view(), name='liked_videos'),
    path('api/change-password/', ChangePasswordView.as_view(), name='change-password'),
    path('api/user-videos/', UploadedVideosView.as_view(), name='user-videos'), 
]
