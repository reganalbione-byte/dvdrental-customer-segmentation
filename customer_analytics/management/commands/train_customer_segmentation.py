"""
Train Customer Segmentation Model (Random Forest Classifier)

Usage:
    python manage.py train_customer_segmentation
"""

from django.core.management.base import BaseCommand
from django.conf import settings
from customer_analytics.models import ModelInfo
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, classification_report
import joblib
import os
import json


class Command(BaseCommand):
    help = 'Train Random Forest model for customer segmentation'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('='*60))
        self.stdout.write(self.style.WARNING('  Training Customer Segmentation Model'))
        self.stdout.write(self.style.WARNING('='*60))

        # =====================================================
        # Step 1: Load CSV data
        # =====================================================
        self.stdout.write('\n[Step 1] Loading data...')
        csv_path = 'customer_olap_data.csv'

        if not os.path.exists(csv_path):
            self.stdout.write(self.style.ERROR(
                f'  CSV not found at {csv_path}. Run ETL first: python manage.py etl_customer_segmentation'
            ))
            return

        df = pd.read_csv(csv_path)
        self.stdout.write(self.style.SUCCESS(f'  -> Loaded {len(df)} records'))

        # =====================================================
        # Step 2: Define features and target
        # =====================================================
        self.stdout.write('\n[Step 2] Preparing features and target...')

        feature_columns = [
            'total_payment',
            'rental_count',
            'avg_payment',
            'max_payment',
            'min_payment',
            'distinct_films',
            'avg_rental_duration_days',
        ]

        X = df[feature_columns]
        y = df['segment']

        # Encode target labels
        le = LabelEncoder()
        y_encoded = le.fit_transform(y)

        self.stdout.write(f'  -> Features: {feature_columns}')
        self.stdout.write(f'  -> Classes: {list(le.classes_)}')

        # =====================================================
        # Step 3: Split train-test
        # =====================================================
        self.stdout.write('\n[Step 3] Splitting train-test data (80/20)...')
        X_train, X_test, y_train, y_test = train_test_split(
            X, y_encoded, test_size=0.2, random_state=42, stratify=y_encoded
        )
        self.stdout.write(f'  -> Train: {len(X_train)} | Test: {len(X_test)}')

        # =====================================================
        # Step 4: Train the model
        # =====================================================
        self.stdout.write('\n[Step 4] Training Random Forest Classifier...')
        model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            random_state=42,
            n_jobs=-1
        )
        model.fit(X_train, y_train)
        self.stdout.write(self.style.SUCCESS('  -> Model trained successfully'))

        # =====================================================
        # Step 5: Evaluate the model
        # =====================================================
        self.stdout.write('\n[Step 5] Evaluating model...')
        y_pred = model.predict(X_test)

        acc = accuracy_score(y_test, y_pred)
        prec = precision_score(y_test, y_pred, average='weighted')
        rec = recall_score(y_test, y_pred, average='weighted')
        f1 = f1_score(y_test, y_pred, average='weighted')

        self.stdout.write(f'  -> Accuracy:  {acc:.4f}')
        self.stdout.write(f'  -> Precision: {prec:.4f}')
        self.stdout.write(f'  -> Recall:    {rec:.4f}')
        self.stdout.write(f'  -> F1 Score:  {f1:.4f}')

        self.stdout.write('\n  Classification Report:')
        report = classification_report(y_test, y_pred, target_names=le.classes_)
        self.stdout.write(report)

        # Feature importance
        importances = model.feature_importances_
        self.stdout.write('\n  Feature Importance:')
        for feat, imp in sorted(zip(feature_columns, importances), key=lambda x: x[1], reverse=True):
            bar = 'â' * int(imp * 40)
            self.stdout.write(f'  {feat:30s} {imp:.4f} {bar}')

        # =====================================================
        # Step 6: Save model to .pkl file
        # =====================================================
        self.stdout.write('\n[Step 6] Saving model...')
        model_filename = 'customer_segmentation_rf.pkl'
        encoder_filename = 'customer_segmentation_le.pkl'
        model_path = os.path.join(settings.MODEL_DIR, model_filename)
        encoder_path = os.path.join(settings.MODEL_DIR, encoder_filename)

        joblib.dump(model, model_path)
        joblib.dump(le, encoder_path)
        self.stdout.write(self.style.SUCCESS(f'  -> Model saved to {model_path}'))
        self.stdout.write(self.style.SUCCESS(f'  -> Encoder saved to {encoder_path}'))

        # =====================================================
        # Step 7: Save model info to database
        # =====================================================
        self.stdout.write('\n[Step 7] Saving model info to database...')

        feature_importance_dict = {
            feat: round(float(imp), 4)
            for feat, imp in zip(feature_columns, importances)
        }

        ModelInfo.objects.create(
            model_name='Customer Segmentation - Random Forest',
            model_type='RandomForestClassifier',
            accuracy=round(acc, 4),
            precision_score=round(prec, 4),
            recall_score=round(rec, 4),
            f1=round(f1, 4),
            features=json.dumps({
                'feature_columns': feature_columns,
                'feature_importance': feature_importance_dict,
                'classes': list(le.classes_),
                'n_estimators': 100,
                'max_depth': 10,
                'train_size': len(X_train),
                'test_size': len(X_test),
            }),
            file_path=model_path,
            notes=f'Trained on {len(df)} customers. 3-class segmentation: High/Medium/Low Value.'
        )

        self.stdout.write(self.style.SUCCESS('\n' + '='*60))
        self.stdout.write(self.style.SUCCESS('  Training Complete!'))
        self.stdout.write(self.style.SUCCESS('='*60))
