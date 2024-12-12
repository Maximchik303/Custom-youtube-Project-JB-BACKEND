from django.contrib import admin
from .models import Video, Category

class VideoAdmin(admin.ModelAdmin):
    list_display = ['link', 'user', 'approved', 'denied', 'createdTime', 'likes']
    list_filter = ['approved', 'categories'] 
    search_fields = ['link', 'user__username', 'description']

admin.site.register(Video, VideoAdmin)
admin.site.register(Category)
