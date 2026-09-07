"""
Segment customers with KMeans, then profile the clusters.

This replaces train_customer_segmentation.py.

Why it changed. The old pipeline built the label with

    df['segment'] = pd.qcut(df['total_payment'], q=3, ...)

and then trained a Random Forest whose feature list still contained
total_payment. The label was a deterministic function of a feature the model
could see, so the model recovered an arithmetic rule rather than learning
anything. Accuracy near 1.00 was the symptom, not the result.

Segmentation has no ground-truth label, so it is a clustering problem. This
command scales the behavioural features, picks k by silhouette score, profiles
each cluster from its own feature means, and names the segments from that
profile. It records silhouette and deliberately records no accuracy, because
there is nothing to be accurate against.

    python manage.py segment_customers
    python manage.py segment_customers --k 4
"""

import json
import os

import joblib
import pandas as pd
from django.conf import settings
from django.core.management.base import BaseCommand
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from customer_analytics.models import CustomerOLAP, ModelInfo

FEATURES = [
    "recency_days",
    "rental_count",
    "total_payment",
    "avg_payment",
    "distinct_films",
    "avg_rental_duration_days",
]

CSV_PATH = "customer_olap_data.csv"
MODEL_FILENAME = "customer_segmentation_kmeans.pkl"


class Command(BaseCommand):
    help = "Cluster customers into behavioural segments and profile them"

    def add_arguments(self, parser):
        parser.add_argument("--k", type=int, default=None,
                            help="Force a specific number of clusters")
        parser.add_argument("--k-min", type=int, default=2)
        parser.add_argument("--k-max", type=int, default=8)

    def handle(self, *args, **opts):
        df = self._load()
        if df is None:
            return

        X = df[FEATURES].astype(float)
        self.stdout.write(f"Customers: {len(X)}")

        k = opts["k"] or self._choose_k(X, opts["k_min"], opts["k_max"])

        pipe = Pipeline([
            ("scale", StandardScaler()),
            ("km", KMeans(n_clusters=k, n_init=10, random_state=42)),
        ])
        df["cluster"] = pipe.fit_predict(X)
        sil = silhouette_score(pipe.named_steps["scale"].transform(X), df["cluster"])

        profile = df.groupby("cluster")[FEATURES].mean().round(2)
        profile["customers"] = df["cluster"].value_counts().sort_index()
        profile["share_pct"] = (profile["customers"] / len(df) * 100).round(1)

        self.stdout.write("\nCluster profile, feature means:")
        self.stdout.write(profile.to_string())

        names = self._name_clusters(profile)
        df["segment"] = df["cluster"].map(names)

        self.stdout.write("\nSegments:")
        for seg, n in df["segment"].value_counts().items():
            self.stdout.write(f"  {seg}: {n}")

        self._persist(df, pipe, names, profile, k, sil)

        self.stdout.write(self.style.SUCCESS(f"\nDone. k={k}, silhouette={sil:.3f}"))
        self.stdout.write(
            "Silhouette runs from -1 to 1 and is relative to the dataset, not an "
            "absolute pass mark. Higher means better separated clusters; near 0 "
            "means they overlap. A modest score can be the honest answer for data "
            "that does not contain strongly distinct groups - see the dataset "
            "caveat in the README."
        )

    # -------------------------------------------------------------- helpers
    def _load(self):
        if not os.path.exists(CSV_PATH):
            self.stderr.write(
                "Feature table not found. Run: python manage.py etl_customer_segmentation")
            return None
        df = pd.read_csv(CSV_PATH)
        missing = [c for c in FEATURES if c not in df.columns]
        if missing:
            self.stderr.write("Missing columns: " + ", ".join(missing) +
                              ". Re-run the ETL, the feature set changed.")
            return None
        return df

    def _choose_k(self, X, k_min, k_max):
        scores = {}
        self.stdout.write("Choosing k by silhouette:")
        for cand in range(k_min, k_max + 1):
            pipe = Pipeline([
                ("scale", StandardScaler()),
                ("km", KMeans(n_clusters=cand, n_init=10, random_state=42)),
            ])
            labels = pipe.fit_predict(X)
            scores[cand] = silhouette_score(
                pipe.named_steps["scale"].transform(X), labels)
            self.stdout.write(f"  k={cand}  silhouette={scores[cand]:.3f}")
        best = max(scores, key=scores.get)
        self.stdout.write(self.style.SUCCESS(f"  chosen k={best}"))
        return best

    @staticmethod
    def _name_clusters(profile):
        """Name clusters from their own profile rather than a fixed list."""
        order = profile.sort_values("total_payment", ascending=False).index.tolist()
        median_recency = profile["recency_days"].median()
        names = {}
        for rank, cid in enumerate(order):
            if rank == 0:
                label = "High Value"
            elif rank == len(order) - 1:
                label = "Low Value"
            else:
                label = "Mid Value"
            if profile.loc[cid, "recency_days"] > median_recency * 1.5:
                label = f"At Risk {label}"
            names[cid] = label
        return names

    def _persist(self, df, pipe, names, profile, k, sil):
        by_id = {int(r.customer_id): (r.segment, int(r.cluster))
                 for r in df[["customer_id", "segment", "cluster"]].itertuples()}
        objs = list(CustomerOLAP.objects.filter(customer_id__in=by_id.keys()))
        for o in objs:
            o.segment, o.cluster = by_id[o.customer_id]
        CustomerOLAP.objects.bulk_update(objs, ["segment", "cluster"], batch_size=500)

        os.makedirs(settings.MODEL_DIR, exist_ok=True)
        model_path = os.path.join(settings.MODEL_DIR, MODEL_FILENAME)
        joblib.dump({"pipeline": pipe, "features": FEATURES, "names": names}, model_path)

        ModelInfo.objects.create(
            model_name="Customer Segmentation - KMeans",
            model_type="KMeans",
            silhouette=round(float(sil), 4),
            features=json.dumps({
                "feature_columns": FEATURES,
                "k": int(k),
                "cluster_profile": json.loads(profile.to_json(orient="index")),
                "segment_names": {str(c): n for c, n in names.items()},
            }),
            file_path=model_path,
            notes=(f"Unsupervised segmentation on {len(df)} customers, k={k}, "
                   f"silhouette {sil:.3f}. No accuracy is recorded because "
                   f"segmentation has no ground-truth label to score against."),
        )
        self.stdout.write(f"\nModel saved to {model_path}")
