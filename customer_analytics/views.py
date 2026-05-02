import json
import os
import numpy as np
import pandas as pd
import joblib

from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.db.models import Sum, Count, Avg, Max, Min
from django.core.management import call_command

from .models import Customer, Payment, Rental, CustomerOLAP, ModelInfo
from .forms import CustomerPredictionForm


# =====================================================
# Home Page
# =====================================================
def home(request):
    """Landing page with overview stats"""
    total_customers = CustomerOLAP.objects.count()
    total_revenue = CustomerOLAP.objects.aggregate(total=Sum('total_payment'))['total'] or 0
    total_rentals = CustomerOLAP.objects.aggregate(total=Sum('rental_count'))['total'] or 0
    avg_payment = CustomerOLAP.objects.aggregate(avg=Avg('avg_payment'))['avg'] or 0
    latest_model = ModelInfo.objects.first()

    # Segment counts
    segments = CustomerOLAP.objects.values('segment').annotate(
        count=Count('customer_id')
    ).order_by('segment')

    context = {
        'total_customers': total_customers,
        'total_revenue': round(float(total_revenue), 2),
        'total_rentals': total_rentals,
        'avg_payment': round(float(avg_payment), 2),
        'latest_model': latest_model,
        'segments': list(segments),
    }
    return render(request, 'customer_analytics/home.html', context)


# =====================================================
# Customer List
# =====================================================
def customer_list(request):
    """View semua customer dengan data OLAP"""
    segment_filter = request.GET.get('segment', '')
    search = request.GET.get('search', '')

    customers = CustomerOLAP.objects.all()

    if segment_filter:
        customers = customers.filter(segment=segment_filter)
    if search:
        customers = customers.filter(
            first_name__icontains=search
        ) | customers.filter(
            last_name__icontains=search
        ) | customers.filter(
            email__icontains=search
        )

    customers = customers.order_by('-total_payment')[:100]

    context = {
        'customers': customers,
        'segment_filter': segment_filter,
        'search': search,
    }
    return render(request, 'customer_analytics/customer_list.html', context)


# =====================================================
# Dashboard - Visualization
# =====================================================
def dashboard(request):
    """Dashboard dengan charts dan visualisasi"""
    # Segment distribution
    segments = CustomerOLAP.objects.values('segment').annotate(
        count=Count('customer_id'),
        total_rev=Sum('total_payment'),
        avg_rev=Avg('total_payment'),
        avg_rentals=Avg('rental_count'),
    ).order_by('segment')

    # Latest model info
    latest_model = ModelInfo.objects.first()
    feature_importance = {}
    if latest_model and latest_model.features:
        try:
            feat_data = json.loads(latest_model.features)
            feature_importance = feat_data.get('feature_importance', {})
        except json.JSONDecodeError:
            pass

    # Top customers per segment
    top_high = CustomerOLAP.objects.filter(segment='High Value').order_by('-total_payment')[:5]
    top_medium = CustomerOLAP.objects.filter(segment='Medium Value').order_by('-total_payment')[:5]
    top_low = CustomerOLAP.objects.filter(segment='Low Value').order_by('-total_payment')[:5]

    # Store distribution
    store_data = CustomerOLAP.objects.values('store_id', 'segment').annotate(
        count=Count('customer_id')
    ).order_by('store_id', 'segment')

    context = {
        'segments': list(segments),
        'segments_json': json.dumps(list(segments), default=str),
        'feature_importance': json.dumps(feature_importance),
        'latest_model': latest_model,
        'top_high': top_high,
        'top_medium': top_medium,
        'top_low': top_low,
        'store_data': json.dumps(list(store_data), default=str),
    }
    return render(request, 'customer_analytics/dashboard.html', context)


# =====================================================
# Predict Customer Segment
# =====================================================
def predict(request):
    """Form untuk prediksi segmen customer baru"""
    form = CustomerPredictionForm()
    context = {'form': form}
    return render(request, 'customer_analytics/predict.html', context)
ÜÜÙ^[\YYXÝØÝ\ÝÛY\\]Y\Ý
NTH[Ú[[ZÈYZÜÚH
RV
HY\]Y\ÝY]ÙOH	ÔÔÕ	ÎN]HHÛÛØYÊ\]Y\ÝÙJBÈØY[Ù[[[ÛÙ\[Ù[Ü]HÜË]Ú[Ù][ÜËSÑSÑT	ØÝ\ÝÛY\ÜÙYÛY[][ÛÜÛ	ÊB[ÛÙ\Ü]HÜË]Ú[Ù][ÜËSÑSÑT	ØÝ\ÝÛY\ÜÙYÛY[][ÛÛKÛ	ÊBYÝÜË]^\ÝÊ[Ù[Ü]
N]\ÛÛ\ÜÛÙJÉÙ\ÜÎ	Ó[Ù[ÝÝ[X\ÙHZ[H[Ù[\ÝßKÝ]\ÏM
B[Ù[HØXØY
[Ù[Ü]
BHHØXØY
[ÛÙ\Ü]
BÈ\\H[]X]\\ÂX]\\ÈH\^JÖÂØ]
]KÙ]
	ÝÝ[Ü^[Y[	Ë
JK[
]KÙ]
	Ü[[ØÛÝ[	Ë
JKØ]
]KÙ]
	Ø]×Ü^[Y[	Ë
JKØ]
]KÙ]
	ÛX^Ü^[Y[	Ë
JKØ]
]KÙ]
	ÛZ[Ü^[Y[	Ë
JK[
]KÙ]
	Ù\Ý[ÝÙ[\ÉË
JKØ]
]KÙ]
	Ø]×Ü[[Ù\][ÛÙ^\ÉË
JKWJBÈYXÝYXÝ[ÛÙ[ÛÙYH[Ù[YXÝ
X]\\ÊVÌBYXÝ[ÛÜØHH[Ù[YXÝÜØJX]\\ÊVÌBYXÝ[ÛÛX[HK[\ÙWÝ[ÙÜJÜYXÝ[ÛÙ[ÛÙYJVÌBÈÛ\ÜÈØX[]Y\ÂØWÙXÝHÂK[\ÙWÝ[ÙÜJÚWJVÌNÝ[
Ø]

H
LBÜK[[[Y\]JYXÝ[ÛÜØJBB]\ÛÛ\ÜÛÙJÂ	ÜYXÝ[ÛÎYXÝ[ÛÛX[	ÜØX[]Y\ÉÎØWÙXÝ	Ú[]Ù]IÎ]KJB^Ù\^Ù\[Û\ÈN]\ÛÛ\ÜÛÙJÉÙ\ÜÎÝJ_KÝ]\ÏML
B]\ÛÛ\ÜÛÙJÉÙ\ÜÎ	ÔÔÕY]Ù\]Z\Y	ßKÝ]\ÏM
JBÈOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOBÈUÝ]\ÂÈOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOBY]ÜÝ]\Ê\]Y\Ý
NY]ÈUÝ]\È[YÙÙ\UÛ\ØÛÝ[HÝ\ÝÛY\ÓTØXÝËÛÝ[

BÙYÛY[ÈHÝ\ÝÛY\ÓTØXÝË[Y\Ê	ÜÙYÛY[	ÊK[Ý]JÛÝ[PÛÝ[
	ØÝ\ÝÛY\ÚY	ÊB
KÜ\ØJ	ÜÙYÛY[	ÊBÛÛ^HÂ	ÛÛ\ØÛÝ[	ÎÛ\ØÛÝ[	ÜÙYÛY[ÉÎ\Ý
ÙYÛY[ÊKB]\[\\]Y\Ý	ØÝ\ÝÛY\Ø[[]XÜËÙ]ÜÝ]\Ë[	ËÛÛ^
BÜÜÙ^[\Y[Ù]
\]Y\Ý
NTH[Ú[ÈYÙÙ\UY\]Y\ÝY]ÙOH	ÔÔÕ	ÎNØ[ØÛÛ[X[
	Ù]ØÝ\ÝÛY\ÜÙYÛY[][ÛÊBÛÝ[HÝ\ÝÛY\ÓTØXÝËÛÝ[

B]\ÛÛ\ÜÛÙJÂ	ÜÝ]\ÉÎ	ÜÝXØÙ\ÜÉË	ÛY\ÜØYÙIÎÑUÛÛ\]YØÛÝ[HÝ\ÝÛY\XÛÜÈØÙ\ÜÙYË	ØÛÝ[	ÎÛÝ[JB^Ù\^Ù\[Û\ÈN]\ÛÛ\ÜÛÙJÉÜÝ]\ÉÎ	Ù\ÜË	ÛY\ÜØYÙIÎÝJ_KÝ]\ÏML
B]\ÛÛ\ÜÛÙJÉÙ\ÜÎ	ÔÔÕY]Ù\]Z\Y	ßKÝ]\ÏM
JBÜÜÙ^[\Y[ÝZ[[Ê\]Y\Ý
NTH[Ú[ÈYÙÙ\[Ù[Z[[ÈY\]Y\ÝY]ÙOH	ÔÔÕ	ÎNØ[ØÛÛ[X[
	ÝZ[ØÝ\ÝÛY\ÜÙYÛY[][ÛÊB]\ÝH[Ù[[ËØXÝË\Ý

B]\ÛÛ\ÜÛÙJÂ	ÜÝ]\ÉÎ	ÜÝXØÙ\ÜÉË	ÛY\ÜØYÙIÎ	Ó[Ù[Z[[ÈÛÛ\]YË	ØXØÝ\XÞIÎØ]
]\ÝXØÝ\XÞJHY]\Ý[ÙHJB^Ù\^Ù\[Û\ÈN]\ÛÛ\ÜÛÙJÉÜÝ]\ÉÎ	Ù\ÜË	ÛY\ÜØYÙIÎÝJ_KÝ]\ÏML
B]\ÛÛ\ÜÛÙJÉÙ\ÜÎ	ÔÔÕY]Ù\]Z\Y	ßKÝ]\ÏM
JBÈOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOBÈ[Ù[[ÂÈOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOBY[Ù[Ú[Ê\]Y\Ý
NY]È[Z[Y[Ù[[È[Ù[ÈH[Ù[[ËØXÝË[

BÛÛ^HÉÛ[Ù[ÉÎ[Ù[ßB]\[\\]Y\Ý	ØÝ\ÝÛY\Ø[[]XÜËÛ[Ù[Ú[Ë[	ËÛÛ^
BÈOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOBÈ\ÚØ\]HTH
ÜRVÚ\\]\ÊBÈOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOBY\ÚØ\Ù]J\]Y\Ý
NTH[Ú[]\[È\ÚØ\]H\ÈÓÓÙYÛY[ÈHÝ\ÝÛY\ÓTØXÝË[Y\Ê	ÜÙYÛY[	ÊK[Ý]JÛÝ[PÛÝ[
	ØÝ\ÝÛY\ÚY	ÊKÝ[Ü]TÝ[J	ÝÝ[Ü^[Y[	ÊK]×Ü]P]Ê	ÝÝ[Ü^[Y[	ÊK]×Ü[[ÏP]Ê	Ü[[ØÛÝ[	ÊK
KÜ\ØJ	ÜÙYÛY[	ÊB]\ÝÛ[Ù[H[Ù[[ËØXÝË\Ý

BX]\WÚ[\Ü[ÙHHßBY]\ÝÛ[Ù[[]\ÝÛ[Ù[X]\\ÎNX]Ù]HHÛÛØYÊ]\ÝÛ[Ù[X]\\ÊBX]\WÚ[\Ü[ÙHHX]Ù]KÙ]
	ÙX]\WÚ[\Ü[ÙIËßJB^Ù\ÛÛÓÓXÛÙQ\Ü\ÜÂ]\ÛÛ\ÜÛÙJÂ	ÜÙYÛY[ÉÎ\Ý
ÙYÛY[ÊK	ÙX]\WÚ[\Ü[ÙIÎX]\WÚ[\Ü[ÙK	Û[Ù[ØXØÝ\XÞIÎØ]
]\ÝÛ[Ù[XØÝ\XÞJHY]\ÝÛ[Ù[[ÙHKY][\ÝB
