from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import UserViewSet, OrganizationViewSet, WorkTypeViewSet, ObjectViewSet, BlockSectionViewSet, FrontTransferViewSet
from django.conf import settings
from django.conf.urls.static import static

router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')
router.register(r'organizations', OrganizationViewSet, basename='organization')
router.register(r'worktypes', WorkTypeViewSet, basename='worktype')
router.register(r'objects', ObjectViewSet, basename='object')
router.register(r'block_sections', BlockSectionViewSet, basename='block_section')
router.register(r'front_transfers', FrontTransferViewSet, basename='front_transfer')

user_retrieve_by_id = UserViewSet.as_view({
    'get': 'retrieve_by_id'
})

urlpatterns = [
    path('', include(router.urls)),
    path('objects/<int:pk>/block_sections/', ObjectViewSet.as_view({'get': 'block_sections'})),
    path('users/by_id/<int:pk>/', user_retrieve_by_id),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)