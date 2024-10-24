from rest_framework import viewsets, permissions, generics, status
from .models import Video, Category, Like
from .serializers import VideoSerializer, CategorySerializer, UserSerializer
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework.decorators import api_view
from django.contrib.auth.hashers import check_password




class VideoViewSet(viewsets.ModelViewSet):
    serializer_class = VideoSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]  # Allow read for all, write for authenticated users

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            # Admins can see all videos
            queryset = Video.objects.all()   # Non-admin users see only approved videos
            category_id = self.request.query_params.get('category')  # Get category ID from the query parameters
            if category_id:
                queryset = queryset.filter(category_id=category_id)  # Filter by category if provided
            if user.is_staff:
                approved_filter = self.request.query_params.get('approved')
                denied_filter = self.request.query_params.get('denied')
                if approved_filter is not None:
                    queryset = queryset.filter(approved=approved_filter.lower() == 'true')
                if denied_filter is not None:
                    queryset = queryset.filter(denied=denied_filter.lower() == 'true')
            return queryset
        else:
            # Non-admins can only see approved videos
            queryset = Video.objects.filter(approved=True, denied=False)  # Non-admin users see only approved videos
            category_id = self.request.query_params.get('category')  # Get category ID from the query parameters
            if category_id:
                queryset = queryset.filter(category_id=category_id)  # Filter by category if provided
            return queryset

    def perform_create(self, serializer):
        # Associate the video with the currently authenticated user
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticatedOrReadOnly])
    def like(self, request, pk=None):
        video = self.get_object()
        user = request.user

        # Check if the user has already liked this video
        if Like.objects.filter(user=user, video=video).exists():
            return Response({'detail': 'You have already liked this video.'}, status=status.HTTP_400_BAD_REQUEST)

        # Create a new Like object
        Like.objects.create(user=user, video=video)

        # Increment the like count on the video
        video.likes += 1
        video.save()

        return Response({'detail': 'Video liked successfully.'}, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['delete'], permission_classes=[IsAuthenticatedOrReadOnly])
    def unlike(self, request, pk=None):
        video = self.get_object()
        user = request.user

        # Check if the user has liked this video
        like_instance = Like.objects.filter(user=user, video=video).first()
        if not like_instance:
            return Response({'detail': 'You have not liked this video.'}, status=status.HTTP_400_BAD_REQUEST)

        # Remove the Like object
        like_instance.delete()

        # Decrement the like count on the video
        video.likes -= 1
        video.save()

        return Response({'detail': 'Video unliked successfully.'}, status=status.HTTP_200_OK)

    def perform_update(self, serializer):
        if 'approved' in self.request.data:
            serializer.save(approved=self.request.data['approved'])
        else:
            serializer.save()

class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['username'] = user.username
        token['is_staff'] = user.is_staff 
        return token

class MyTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

class UserRegisterView(generics.CreateAPIView):
    serializer_class = UserSerializer
    permission_classes = (permissions.AllowAny,)


class UserProfileView(generics.RetrieveAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user  # Get the current authenticated user

class LikedVideosView(generics.ListAPIView):
    serializer_class = VideoSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        # Fetch liked videos and order by the timestamp of the Like in descending order
        return Video.objects.filter(like__user=user).order_by('-like__created_at')
    
class ChangePasswordView(generics.UpdateAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user = request.user
        current_password = request.data.get("current_password")
        new_password = request.data.get("new_password")

        # Check if the current password is correct
        if not check_password(current_password, user.password):
            return Response({"detail": "Current password is incorrect."}, status=status.HTTP_400_BAD_REQUEST)

        # Set the new password
        user.set_password(new_password)
        user.save()

        return Response({"detail": "Password updated successfully."}, status=status.HTTP_200_OK)

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes = [IsAdminUser]
        else:
            permission_classes = [permissions.AllowAny]
        return [permission() for permission in permission_classes]
