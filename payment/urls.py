from django.urls import path
from . import views

urlpatterns = [
    path('tabs/<int:tab_id>/payment_intent', views.CreatePaymentIntentView.as_view(), name='create_payment_intent'),
    path('tabs/<int:tab_id>/take_payment', views.TakePaymentView.as_view(), name='take_payment'),
]
