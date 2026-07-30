from django.contrib import admin
from django.urls import path, re_path, include
from django.conf import settings
from django.views.static import serve as serve_static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('application.urls')),
    # django.conf.urls.static.static() only registers this route when
    # DEBUG=True — on Render (DEBUG=False in production) uploaded photos
    # and videos would otherwise 404. This is Django's own dev file server,
    # not meant for heavy traffic, but appropriate for this deployment's
    # scale (and media isn't persisted across deploys on the free plan
    # regardless, so a CDN would be solving the wrong problem here).
    re_path(r'^media/(?P<path>.*)$', serve_static, {'document_root': settings.MEDIA_ROOT}),
]
