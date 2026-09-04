"""
URL configuration for djangoProject1 project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
"""
from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path
from myapp.views import index, get_high_freq_data, download_video, get_max_danmaku, download_excel

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', index, name='index'),  # 首页
    path('get_high_freq_data/', get_high_freq_data, name='get_high_freq_data'),  # 高频词数据
    path('download_video/', download_video, name='download_video'),  # 下载视频
    path('get_max_danmaku/', get_max_danmaku, name='get_max_danmaku'),  # 获取精彩时间段
    path('download_excel/', download_excel, name='download_excel'),  # 下载Excel
]

# 开发环境下提供静态文件服务
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])
    urlpatterns += static(settings.DOWNLOAD_URL, document_root=settings.DOWNLOAD_ROOT)