"""
Views for the customer analytics app.

Rewritten. The previous views.py was corrupted in the repository from the
predict view onwards: roughly half the file was unreadable bytes rather than
Python, so the module could not be imported and the project would not start.
"""

import json
import os

import joblib
import pandas as pd
from django.conf import settings
from django.core.management import call_command
from django.db.models import Avg, Count, Q, Sum
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST

from .forms import CustomerPredictionForm
from .models import CustomerOLAP, ModelInfo

MODEL_FILENAME = "customer_segmentation_kmeans.pkl"


# ---------------------------------------------------------------- helpers
def _load_model():
    """Return the saved clustering bundle, or None if nothing is trained yet."""
    path = os.path.join(settings.MODEL_DIR, MODEL_FILENAME)
    if not os.path.exists(path):
        return None
    return joblib.load(path)


def _segment_summary():
    return list(
        CustomerOLAP.objects
        .exclude(segment__isnull=True)
        .values("segment")
        .annotate(
            count=Count("customer_id"),
            total_revenue=Sum("total_payment"),
            avg_revenue=Avg("total_payment"),
            avg_rentals=Avg("rental_count"),
            avg_recency=Avg("recency_days"),
        )
        .order_by("-total_revenue")
    )


# ---------------------------------------------------------------- pages
def home(request):
    agg = CustomerOLAP.objects.aggregate(
        customers=Count("customer_id"),
        revenue=Sum("total_payment"),
        rentals=Sum("rental_count"),
        avg_payment=Avg("avg_payment"),
    )
    return render(request, "customer_analytics/home.html", {
        "total_customers": agg["customers"] or 0,
        "total_revenue": round(float(agg["revenue"] or 0), 2),
        "total_rentals": agg["rentals"] or 0,
        "avg_payment": round(float(agg["avg_payment"] or 0), 2),
        "latest_model": ModelInfo.objects.first(),
        "segments": _segment_summary(),
    })


def customer_list(request):
    segment = request.GET.get("segment", "")
    search = request.GET.get("search", "")

    qs = CustomerOLAP.objects.all()
    if segment:
        qs = qs.filter(segment=segment)
    if search:
        qs = qs.filter(
            Q(first_name__icontains=search)
            | Q(last_name__icontains=search)
            | Q(email__icontains=search)
        )

    return render(request, "customer_analytics/customer_list.html", {
        "customers": qs.order_by("-total_payment")[:100],
        "segment_filter": segment,
        "search": search,
        "all_segments": (CustomerOLAP.objects
                         .exclude(segment__isnull=True)
                         .values_list("segment", flat=True)
                         .distinct()
                         .order_by("segment")),
    })


def dashboard(request):
    segments = _segment_summary()
    latest = ModelInfo.objects.first()

    cluster_profile = {}
    if latest and latest.features:
        try:
            cluster_profile = json.loads(latest.features).get("cluster_profile", {})
        except json.JSONDecodeError:
            pass

    return render(request, "customer_analytics/dashboard.html", {
        "segments": segments,
        "segments_json": json.dumps(segments, default=str),
        "cluster_profile": json.dumps(cluster_profile, default=str),
        "latest_model": latest,
        "top_customers": CustomerOLAP.objects.order_by("-total_payment")[:10],
        "store_data": json.dumps(
            list(CustomerOLAP.objects
                 .exclude(segment__isnull=True)
                 .values("store_id", "segment")
                 .annotate(count=Count("customer_id"))
                 .order_by("store_id", "segment")),
            default=str),
    })


def predict(request):
    return render(request, "customer_analytics/predict.html", {
        "form": CustomerPredictionForm(),
        "model_ready": _load_model() is not None,
    })


def etl_status(request):
    return render(request, "customer_analytics/etl_status.html", {
        "olap_rows": CustomerOLAP.objects.count(),
        "segmented_rows": CustomerOLAP.objects.exclude(segment__isnull=True).count(),
        "latest_model": ModelInfo.objects.first(),
    })


def model_info(request):
    return render(request, "customer_analytics/model_info.html", {
        "models": ModelInfo.objects.all()[:20],
    })


# ---------------------------------------------------------------- API
@require_POST
def predict_customer(request):
    """Assign a segment to an unseen customer using the saved clustering model."""
    form = CustomerPredictionForm(request.POST)
    if not form.is_valid():
        return JsonResponse({"success": False, "errors": form.errors}, status=400)

    bundle = _load_model()
    if bundle is None:
        return JsonResponse(
            {"success": False,
             "error": "No model has been fitted yet. Run: python manage.py segment_customers"},
            status=409)

    features = bundle["features"]
    row = pd.DataFrame([{f: float(form.cleaned_data[f]) for f in features}])[features]

    cluster = int(bundle["pipeline"].predict(row)[0])
    segment = bundle["names"].get(cluster, f"Cluster {cluster}")

    return JsonResponse({
        "success": True,
        "cluster": cluster,
        "segment": segment,
        "note": ("Assigned to the nearest cluster centroid. This is an assignment, "
                 "not a probabilistic prediction, so no confidence score is reported."),
    })


def dashboard_data(request):
    return JsonResponse({"segments": _segment_summary()}, safe=False, encoder=DecimalEncoder)


@require_POST
def run_etl(request):
    try:
        call_command("etl_customer_segmentation")
    except Exception as exc:  # surfaced to the user, not swallowed
        return JsonResponse({"success": False, "error": str(exc)}, status=500)
    return JsonResponse({"success": True, "rows": CustomerOLAP.objects.count()})


@require_POST
def run_segmentation(request):
    try:
        call_command("segment_customers")
    except Exception as exc:
        return JsonResponse({"success": False, "error": str(exc)}, status=500)
    latest = ModelInfo.objects.first()
    return JsonResponse({
        "success": True,
        "model": latest.model_name if latest else None,
        "silhouette": float(latest.silhouette) if latest and latest.silhouette else None,
    })


class DecimalEncoder(json.JSONEncoder):
    """Decimal and date values come back from aggregates; make them JSON-safe."""

    def default(self, o):
        try:
            return float(o)
        except (TypeError, ValueError):
            return str(o)
