from django.urls import path

from . import views

app_name = 'customer_analytics'

urlpatterns = [
    path('customers/', views.customer_list, name='customer_list'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('predict/', views.predict, name='predict'),
    path('etl/', views.etl_status, name='etl_status'),
    path('models/', views.model_info, name='model_info'),

    path('api/predict/', views.predict_customer, name='predict_customer'),
    path('api/dashboard-data/', views.dashboard_data, name='dashboard_data'),
    path('api/run-etl/', views.run_etl, name='run_etl'),
    path('api/run-segmentation/', views.run_segmentation, name='run_segmentation'),
]
