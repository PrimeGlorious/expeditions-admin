from rest_framework.routers import SimpleRouter

from expeditions.views import ExpeditionViewSet

app_name = 'expeditions'

router = SimpleRouter()
router.register('', ExpeditionViewSet, basename='expedition')

urlpatterns = router.urls
