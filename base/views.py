from rest_framework import viewsets, permissions, generics, status
from .models import Video, Category, Like
from .serializers import VideoSerializer, CategorySerializer, UserSerializer
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth.models import User
from rest_framework.views import APIView
from django.contrib.auth.hashers import check_password
from datetime import datetime
from rest_framework.decorators import api_view
from googleapiclient.discovery import build
from django.conf import settings
import requests
import isodate
import random
from collections import Counter



YOUTUBE_API_KEY = settings.YOUTUBE_API_KEY
YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"

class VideoViewSet(viewsets.ModelViewSet):
    serializer_class = VideoSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]  # Allow read for all, write for authenticated users

class VideoViewSet(viewsets.ModelViewSet):
    serializer_class = VideoSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        user = self.request.user
        queryset = Video.objects.all()  # Default to showing all videos

        # Category filters
        category_1 = self.request.query_params.get('category_1')
        category_2 = self.request.query_params.get('category_2')

        if category_1:
            queryset = queryset.filter(categories__id=category_1)

        if category_2:
            queryset = queryset.filter(categories__id=category_2)

        if user.is_staff:
            # Admins can filter by approved/denied
            approved_filter = self.request.query_params.get('approved')
            denied_filter = self.request.query_params.get('denied')
            if approved_filter is not None:
                queryset = queryset.filter(approved=approved_filter.lower() == 'true')
            if denied_filter is not None:
                queryset = queryset.filter(denied=denied_filter.lower() == 'true')

        else:
            # Non-admins can only see approved and not denied videos
            queryset = queryset.filter(approved=True, denied=False)

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
        return Video.objects.filter(like__user=user).order_by('-like__created_at')

class UploadedVideosView(generics.ListAPIView):
    serializer_class = VideoSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Video.objects.filter(user=self.request.user).order_by('-createdTime')
    
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

class UserListView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        users = User.objects.all()
        user_data = [{"id": user.id, "username": user.username, "is_staff": user.is_staff, "is_active": user.is_active,} for user in users]
        return Response(user_data)

class ToggleAdminStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, user_id):
        try:
            user = User.objects.get(id=user_id)
            if request.user.is_staff:  # Only staff/admin users can change admin status
                user.is_staff = not user.is_staff  # Toggle admin status
                user.save()
                return Response({"message": "Admin status updated successfully."}, status=status.HTTP_200_OK)
            else:
                return Response({"error": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)
        except User.DoesNotExist:
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)

class ToggleUserActiveStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, user_id):
        try:
            user = User.objects.get(id=user_id)
            if request.user.is_staff:  # Only staff/admin users can toggle account status
                user.is_active = not user.is_active  # Toggle account active status
                user.save()
                return Response({"message": "Account status updated successfully."}, status=status.HTTP_200_OK)
            else:
                return Response({"error": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)
        except User.DoesNotExist:
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)

@api_view(['GET'])
def get_popular_educational_videos(request):
    def clean_text(text):
        import re
        text = re.sub(r'#\w+', '', text)
        text = re.sub(r'http[s]?://[^\s]+', '', text)
        text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '', text)
        return ' '.join(text.split())

    def generate_ai_description(title, description):
        """
        Generate AI-based description for the video using Hugging Face (or another AI service).
        This function can be modified to use another service like OpenAI or any other model.
        """
        hf_api_url = "https://api-inference.huggingface.co/models/facebook/bart-large-cnn"
        headers = {"Authorization": f"Bearer {settings.HUGGINGFACE_API_KEY}"}

        # Create the prompt for summarization
        prompt = f"Title: {title}\nDescription: {description}\n\nSummarized Description:"

        payload = {"inputs": prompt}

        try:
            response = requests.post(hf_api_url, headers=headers, json=payload)
            response.raise_for_status()
            predictions = response.json()
            if predictions:
                return predictions[0]['summary_text']  # Assuming the model returns 'summary_text'
        except Exception as e:
            print(f"Error using Hugging Face API for description: {e}")
            return description  # Fall back to the original description if AI fails

    def assign_category_huggingface(title, description):
        hf_api_url = "https://api-inference.huggingface.co/models/facebook/bart-large-mnli"
        headers = {"Authorization": f"Bearer {settings.HUGGINGFACE_API_KEY}"}

        candidate_labels = list(Category.objects.values_list('name', flat=True))
        payload = {
            "inputs": f"Title: {title}\nDescription: {description}",
            "parameters": {"candidate_labels": candidate_labels},
        }

        try:
            response = requests.post(hf_api_url, headers=headers, json=payload)
            response.raise_for_status()
            predictions = response.json()
            if predictions and "labels" in predictions:
                return predictions["labels"][0]
        except Exception as e:
            print(f"Error using Hugging Face API for category assignment: {e}")

        return "Uncategorized"

    try:
        youtube = build("youtube", "v3", developerKey=settings.YOUTUBE_API_KEY)

        categories = ["28", "2", "26"]  # Multiple category IDs to fetch videos for
        all_videos = []

        # Fetch videos for each category individually
        for category in categories:
            trending_response = youtube.videos().list(
                part="snippet,contentDetails",
                chart="mostPopular",
                regionCode="US",
                maxResults=55,
                videoCategoryId=category,  # Single category ID at a time
            ).execute()

            for video in trending_response.get("items", []):
                if len(all_videos) >= 10:
                    break
                try:
                    duration_iso = video["contentDetails"]["duration"]
                    duration_seconds = isodate.parse_duration(duration_iso).total_seconds()
                    if duration_seconds > 100:
                        if not video["contentDetails"].get("madeForKids", False):
                            if video["snippet"].get("defaultAudioLanguage") == "en":
                                original_title = video["snippet"]["title"]
                                cleaned_title = clean_text(original_title)
                                original_description = video["snippet"]["description"]
                                cleaned_description = clean_text(original_description)

                                # Get AI-generated description
                                ai_generated_description = generate_ai_description(cleaned_title, cleaned_description)

                                # Assign category after the video data is fetched
                                assigned_category_name = assign_category_huggingface(cleaned_title, cleaned_description)
                                try:
                                    assigned_category_id = Category.objects.get(name=assigned_category_name).id
                                except Category.DoesNotExist:
                                    pass

                                all_videos.append({
                                    "id": video["id"],
                                    "title": cleaned_title,
                                    "description": ai_generated_description,  # Use AI-generated description
                                    "thumbnail": video["snippet"]["thumbnails"]["high"]["url"],
                                    "channelTitle": video["snippet"]["channelTitle"],
                                    "publishedAt": video["snippet"]["publishedAt"],
                                    "category": assigned_category_name,
                                    "categoryId": assigned_category_id,
                                })
                except KeyError as e:
                    print(f"Missing key in video response: {e}")
                    continue

        return Response({"videos": all_videos}, status=200)

    except Exception as e:
        print(f"Error occurred: {str(e)}")
        return Response({"error": str(e)}, status=500)

@api_view(['GET'])
def recommend_videos(request):
    user = request.user

    # Get the last 7 liked videos
    liked_videos = Like.objects.filter(user=user).order_by('-created_at')[:7]
    liked_video_ids = liked_videos.values_list('video_id', flat=True)

    # Get the categories of these 7 videos
    categories = []
    for video in Video.objects.filter(id__in=liked_video_ids):
        categories.extend([category.name for category in video.categories.all()])

    # Count the most common category
    category_counts = Counter(categories)
    favorite_category = category_counts.most_common(1)[0][0] if category_counts else None

    if not favorite_category:
        return Response({"message": "No favorite category found to recommend videos."}, status=400)

    # Retrieve the Category object for the favorite category
    favorite_category_obj = Category.objects.filter(name=favorite_category).first()
    if not favorite_category_obj:
        return Response({"error": "Favorite category does not exist"}, status=400)

    # Get all the videos and their categories
    all_videos = Video.objects.all().prefetch_related('categories')
    
    # Get the liked videos of the user
    liked_video_ids = Like.objects.filter(user=user).values_list('video_id', flat=True)

    # Filter videos by the favorite category, exclude the liked ones, and order by likes (desc)
    videos_in_category = (
        all_videos.filter(categories=favorite_category_obj)
        .exclude(id__in=liked_video_ids)
        .order_by('-likes')  # Order by likes in descending order
    )

    # Select the top 5 most liked videos
    recommended_videos = videos_in_category[:5]

    # Serialize the recommended videos
    videos_data = []
    for video in recommended_videos:
        video_data = {
            "id": video.id,
            "description": video.description,
            "link": video.link,
            "categories": [category.id for category in video.categories.all()],  # Return category IDs
            "likes": video.likes,  
            "user": video.user.username,
            "approved": video.approved,
            "denied": video.denied,
            "createdTime": video.createdTime.strftime("%Y-%m-%d %H:%M:%S"),  # Format date/time
        }
        videos_data.append(video_data)

    # Include the favorite category in the response
    response_data = {
        "favorite_category": favorite_category,  # Include the favorite category name
        "recommended_videos": videos_data,
    }

    return Response(response_data, status=200)
