from django.conf import settings
from django.contrib import admin
from django.urls import path, include, re_path
from django.views.generic import TemplateView
from django.views.static import serve as static_serve

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('api.urls')),
]

if settings.DEBUG:
    # Vite emits `/assets/*` into frontend/dist; serve them directly so the
    # built SPA works when Django is the only server running.
    urlpatterns.append(
        re_path(
            r'^assets/(?P<path>.*)$',
            static_serve,
            {'document_root': str(settings.BASE_DIR.parent / 'frontend' / 'dist' / 'assets')},
            name='spa_assets',
        )
    )

urlpatterns.append(
    re_path(r'^(?!api/|admin/|assets/).*$', TemplateView.as_view(template_name="index.html"), name="spa")
)
