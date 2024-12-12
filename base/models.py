from django.db import models
from django.contrib.auth.models import User

class Category(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

class Video(models.Model):
    link = models.URLField(unique=True)
    description = models.TextField()
    categories = models.ManyToManyField(Category, related_name='videos')  # Allow multiple categories
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    approved = models.BooleanField(default=False)
    createdTime = models.DateTimeField(auto_now_add=True)
    likes = models.PositiveIntegerField(default=0)
    denied = models.BooleanField(default=False)

    def __str__(self):
        return self.link


class Like(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    video = models.ForeignKey(Video, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'video')  # Ensure that a user can like a video only once
