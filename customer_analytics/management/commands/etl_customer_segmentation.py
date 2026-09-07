"""
ETL: extract customer behaviour from the dvdrental OLTP tables, transform it
into customer-level features, and load it into the CustomerOLAP table.

This command does not assign segments. It used to, with

    df['segment'] = pd.qcut(df['total_payment'], q=3, ...)

which made the segment a deterministic function of a column that was then fed
to the model as a feature. Segmenting is now a separate step:

    python manage.py etl_customer_segmentation
    python manage.py segment_customers
"""

import pandas as pd
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import connection, transaction
from django.utils import timezone as dj_timezone

from customer_analytics.models import CustomerOLAP

EXTRACT_SQL = """
    SELECT
        c.customer_id,
        c.first_name,
        c.last_name,
        c.email,
        c.store_id,
        c.activebool,
        COALESCE(SUM(p.amount), 0)                       AS total_payment,
        COALESCE(AVG(p.amount), 0)                       AS avg_payment,
        COALESCE(MAX(p.amount), 0)                       AS max_payment,
        COALESCE(MIN(p.amount), 0)                       AS min_payment,
        COUNT(DISTINCT r.rental_id)                      AS rental_count,
        COUNT(DISTINCT i.film_id)                        AS distinct_films,
        MAX(r.rental_date)                               AS last_rental_date,
        COALESCE(
            AVG(EXTRACT(EPOCH FROM (r.return_date - r.rental_date)) / 86400), 0
        )                                                AS avg_rental_duration_days
    FROM customer c
    LEFT JOIN payment   p ON c.customer_id = p.customer_id
    LEFT JOIN rental    r ON c.customer_id = r.customer_id
    LEFT JOIN inventory i ON r.inventory_id = i.inventory_id
    GROUP BY c.customer_id, c.first_name, c.last_name, c.email,
             c.store_id, c.activebool
    ORDER BY c.customer_id;
"""

NUMERIC_COLS = ["total_payment", "avg_payment", "max_payment",
                "min_payment", "avg_rental_duration_days"]

CSV_PATH = "customer_olap_data.csv"


class Command(BaseCommand):
    help = "Extract customer behaviour from the OLTP tables into CustomerOLAP"

    def handle(self, *args, **options):
        # ---- extract ---------------------------------------------------------
        self.stdout.write("Extracting from OLTP tables")
        with connection.cursor() as cur:
            cur.execute(EXTRACT_SQL)
            columns = [c[0] for c in cur.description]
            df = pd.DataFrame(cur.fetchall(), columns=columns)
        self.stdout.write(self.style.SUCCESS(f"  {len(df)} customers"))

        if df.empty:
            self.stderr.write("No rows returned. Is the dvdrental database loaded?")
            return

        # ---- transform -------------------------------------------------------
        self.stdout.write("Transforming")
        for col in NUMERIC_COLS:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).round(2)
        df["rental_count"] = df["rental_count"].fillna(0).astype(int)
        df["distinct_films"] = df["distinct_films"].fillna(0).astype(int)

        # Recency against the data's own latest rental, not today. The sample
        # data ends in 2006, so using today would make every customer equally
        # stale and recency would carry no signal.
        df["last_rental_date"] = pd.to_datetime(df["last_rental_date"])
        if settings.USE_TZ:
            # dvdrental stores rental_date as `timestamp without time zone`, so
            # the values come back naive. Attach the project timezone here
            # rather than let the ORM warn once per customer on insert.
            df["last_rental_date"] = df["last_rental_date"].dt.tz_localize(
                dj_timezone.get_current_timezone(),
                ambiguous=True,
                nonexistent="shift_forward",
            )
        snapshot = df["last_rental_date"].max()
        df["recency_days"] = (snapshot - df["last_rental_date"]).dt.days

        never_rented = df["recency_days"].isna()
        if never_rented.any():
            # A customer who never rented is maximally lapsed, not average.
            df.loc[never_rented, "recency_days"] = int(df["recency_days"].max() or 0) + 1
        df["recency_days"] = df["recency_days"].astype(int)

        self.stdout.write(f"  snapshot date: {snapshot.date()}")
        self.stdout.write(f"  recency: min {df['recency_days'].min()}, "
                          f"median {int(df['recency_days'].median())}, "
                          f"max {df['recency_days'].max()} days")

        # ---- load ------------------------------------------------------------
        self.stdout.write("Loading into CustomerOLAP")
        records = [
            CustomerOLAP(
                customer_id=row.customer_id,
                first_name=row.first_name,
                last_name=row.last_name,
                email=row.email,
                store_id=row.store_id,
                total_payment=row.total_payment,
                avg_payment=row.avg_payment,
                max_payment=row.max_payment,
                min_payment=row.min_payment,
                rental_count=row.rental_count,
                distinct_films=row.distinct_films,
                avg_rental_duration_days=row.avg_rental_duration_days,
                last_rental_date=row.last_rental_date if pd.notna(row.last_rental_date) else None,
                recency_days=row.recency_days,
                is_active=row.activebool,
            )
            for row in df.itertuples(index=False)
        ]

        with transaction.atomic():
            CustomerOLAP.objects.all().delete()
            CustomerOLAP.objects.bulk_create(records, batch_size=500)

        df.to_csv(CSV_PATH, index=False)
        self.stdout.write(self.style.SUCCESS(f"  {len(records)} rows written"))
        self.stdout.write(self.style.SUCCESS(f"  feature table cached at {CSV_PATH}"))
        self.stdout.write("\nNext: python manage.py segment_customers")
