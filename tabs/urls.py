from django.urls import path
from . import views

urlpatterns = [
    path('tabs', views.CreateTabView.as_view(), name='create_tab'),
    path('tabs/<int:tab_id>', views.GetTabView.as_view(), name='get_tab'),
    path('tabs/<int:tab_id>/items', views.AddMenuItemView.as_view(), name='add_menu_item'),
]
