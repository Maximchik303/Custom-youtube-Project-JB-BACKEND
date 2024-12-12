import re
from rest_framework import serializers
from .models import Video, Category, User

class VideoSerializer(serializers.ModelSerializer):
    user = serializers.CharField(source='user.username', read_only=True)
    categories = serializers.PrimaryKeyRelatedField(queryset=Category.objects.all(), many=True)  # Handle multiple categories

    class Meta:
        model = Video
        fields = ['id', 'link', 'description', 'categories', 'user', 'approved', 'denied', 'createdTime', 'likes']
        read_only_fields = ['id', 'createdTime', 'likes', 'approved', 'user']  # user is set server-side

    def validate_categories(self, value):
        # Ensure that a video has 1 or 2 categories (adjust the logic if you need more specific validation)
        if len(value) > 2:
            raise serializers.ValidationError("A video can only have up to 2 categories.")
        return value

    def validate_link(self, value):
        youtube_regex = r'^(https?\:\/\/)?(www\.youtube\.com|youtu\.?be)\/.+$'
        if not re.match(youtube_regex, value):
            raise serializers.ValidationError("This is not a valid YouTube link.")
        if Video.objects.filter(link=value).exists():
            raise serializers.ValidationError("This video link has already been submitted.")
        return value

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name']

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['username', 'password', 'email']

    def create(self, validated_data):
        user = User(**validated_data)
        user.set_password(validated_data['password'])  # Hash the password
        user.save()
        return user
