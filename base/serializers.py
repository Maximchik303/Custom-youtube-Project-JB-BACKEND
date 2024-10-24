import re
from rest_framework import serializers
from .models import Video, Category, User

class VideoSerializer(serializers.ModelSerializer):
    user = serializers.CharField(source='user.username', read_only=True)
    category = serializers.PrimaryKeyRelatedField(queryset=Category.objects.all())  # Accept category ID

    class Meta:
        model = Video
        fields = ['id', 'link', 'description', 'category', 'user', 'approved', 'denied', 'createdTime', 'likes']
        read_only_fields = ['id', 'createdTime', '`like`s', 'approved', 'user']  # user is set server-side

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
