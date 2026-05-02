"""
ETL Command: Extract customer data from OLTP tables, transform, and load to OLAP table.

Usage:
    python manage.py etl_customer_segmentation
"""

from django.core.management.base import BaseCommand
from django.db import connection
from customer_analytics.models import CustomerOLAP
import pandas as pd


class Command(BaseCommand):
    help = 'ETL: Extract customer+payment+rental data, transform features, load to CustomerOLAP'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('='*60))
        self.stdout.write(self.style.WARNING('  ETL Customer Segmentation - Starting...'))
        self.stdout.write(self.style.WARNING('='*60))

        # =====================================================
        # STEP 1: EXTRACT - Query data from OLTP tables
        # =====================================================
        self.stdout.write('\n[Step 1] Extracting data from OLTP tables...')

        query = """
            SELECT
                c.customer_id,
                c.first_name,
                c.last_name,
                c.email,
                c.store_id,
                c.activebool,
                COALESCE(SUM(p.amount), 0) AS total_payment,
                COUNT(DISTINCT r.rental_id) AS rental_count,
                COALESCE(AVG(p.amount), 0) AS avg_payment,
                COALESCE(MAX(p.amount), 0) AS max_payment,
                COALESCE(MIN(p.amount), 0) AS min_payment,
                COUNT(DISTINCT i.film_id) AS distinct_films,
                COALESCE(
                    AVG(
                        EXTRACT(EPOCH FROM (r.return_date - r.rental_date)) / 86400
                    ), 0
                ) AS avg_rental_duration_days
            FROM customer c
            LEFT JOIN payment p ON c.customer_id = p.customer_id
            LEFT JOIN rental r ON c.customer_id = r.customer_id
            LEFT JOIN inventory i ON r.inventory_id = i.inventory_id
            GROUP BY c.customer_id, c.first_name, c.last_name, c.email, c.store_id, c.activebool
            ORDER BY c.customer_id;
        """

        with connection.cursor() as cursor:
            cursor.execute(query)
            columns = [col[0] for col in cursor.description]
            rows = cursor.fetchall()

        df = pd.DataFrame(rows, columns=columns)
        self.stdout.write(self.style.SUCCESS(f'  -> Extracted {len(df)} customers'))

        # =====================================================
        # STEP 2: TRANSFORM - Clean and prepare data
        # =====================================================
        self.stdout.write('\n[Step 2] Transforming data...')

        # Convert decimal types
        numeric_cols = ['total_payment', 'avg_payment', 'max_payment', 'min_payment', 'avg_rental_duration_days']
        for col in numeric_cols:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).round(2)

        df['rental_count'] = df['rental_count'].fillna(0).astype(int)
        df['distinct_films'] = df['distinct_films'].fillna(0).astype(int)

        # Create segments based on total_payment quantiles
        df['segment'] = pd.qcut(
            df['total_payment'],
            q=3,
            labels=['Low Value', 'Medium Value', 'High Value']
        )

        self.stdout.write(self.style.SUCCESS(f'  -> Transformation complete'))
        self.stdout.write(f'  -> Segment distribution:')
        for seg, count in df['segment'].value_counts().items():
            self.stdout.write(f'     {seg}: {count} customers')

        # =====================================================
        # STEP 3: LOAD - Save to OLAP table
        # =====================================================
        self.stdout.write('\n[Step 3] Loading data to CustomerOLAP table...')

        # Clear existing OLAP data
        CustomerOLAP.objects.all().delete()

        # Bulk create
        olap_records = []
        for _, row in df.iterrows():
            olap_records.append(CustomerOLAP(
                customer_id=row['customer_id'],
                first_name=row['first_name'],
                last_name=row['last_name'],
                email=row['email'],
                store_id=row['store_id'],
                total_payment=row['total_payment'],
                rental_count=row['rental_count'],
                avg_payment=row['avg_payment'],
                max_payment=row['max_payment'],
                min_payment=row['min_payment'],
                distinct_films=row['distinct_films'],
                avg_rental_duration_days=row['avg_rental_duration_days'],
                is_active=row['activebool'],
                segment=row['segment'],
            ))

        CustomerOLAP.objects.bulk_create(olap_records)

        # Also save CSV for ML training
        csv_path = 'customer_olap_data.csv'
        df.to_csv(csv_path, index=False)

        self.stdout.write(self.style.SUCCESS(f'  -> Loaded {len(olap_records)} records to CustomerOLAP'))
        self.stdout.write(self.style.SUCCESS(f'  -> Saved CSV to {csv_path}'))

        self.stdout.write(self.style.SUCCESS('\n' + '='*60))
        self.stdout.write(self.style.SUCCESS('  ETL Complete!'))
        self.stdout.write(self.style.SUCCESS('='*60))
