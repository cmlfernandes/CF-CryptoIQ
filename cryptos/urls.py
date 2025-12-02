from django.urls import path
from . import views

app_name = 'cryptos'

urlpatterns = [
    # Authentication
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # User management (admin only)
    path('users/', views.user_list, name='user_list'),
    path('users/add/', views.user_add, name='user_add'),
    path('users/<int:user_id>/edit/', views.user_edit, name='user_edit'),
    path('users/<int:user_id>/delete/', views.user_delete, name='user_delete'),
    
    # Root redirect to Analysis Overview
    path('', views.analysis_overview, name='root'),
    
    # Crypto management
    path('cryptos/', views.crypto_list, name='crypto_list'),
    path('add/', views.crypto_add, name='crypto_add'),
    path('<int:crypto_id>/edit/', views.crypto_edit, name='crypto_edit'),
    path('<int:crypto_id>/delete/', views.crypto_delete, name='crypto_delete'),
    path('<int:crypto_id>/analysis/', views.crypto_analysis, name='crypto_analysis'),
    path('analysis/overview/', views.analysis_overview, name='analysis_overview'),
    path('<int:crypto_id>/update-price/', views.update_price, name='update_price'),
    path('settings/', views.settings_view, name='settings'),
    path('settings/load-models/', views.load_models_ajax, name='load_models'),
    path('api/price/<str:symbol>/', views.get_price, name='get_price'),
]

