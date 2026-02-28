from django.urls import path
from . import views, ui_views

urlpatterns = [
    path("login/", views.login_view, name="login"),
    path("register/", views.register_view, name="register"),
    path("dashboard/", views.dashboard_view, name="dashboard"),
    path("manage-homes/", views.manage_homes_view, name="manage_homes"),
    path("logout/", views.logout_view, name="logout"),
    
    # UI Prototypes
    path("ui/dashboard/", ui_views.ui_dashboard, name="ui_dashboard"),
    path("ui/home-setup/", ui_views.ui_home_setup, name="ui_home_setup"),
    path("ui/appliances/", ui_views.ui_appliances, name="ui_appliances"),
    path("ui/appliance/<uuid:id>/", ui_views.ui_appliance_detail, name="ui_appliance_detail"),
]
