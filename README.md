# DVD Rental Customer Segmentation

Full-stack Django web application for customer segmentation on the PostgreSQL dvdrental sample database. Includes an ETL pipeline that extracts customer behavior features from the OLTP schema, a Random Forest classifier for segment prediction, and an interactive dashboard for exploring results.

## Features

- **ETL Pipeline** -- Extracts rental and payment data from the dvdrental OLTP database, transforms it into customer-level features (RFM metrics, rental duration, film diversity), and loads it into an OLAP table for analysis.
- **ML Model Training** -- Trains a Random Forest classifier on the OLAP data to segment customers into groups (e.g., Premium, Standard, Basic, At-Risk). Model artifacts are versioned and stored for serving.
- **Prediction Interface** -- Web form where you can input customer metrics and get a real-time segment prediction via AJAX.
- **Dashboard** -- Visual overview of customer segments, segment distribution, and key metrics.
- **Django Admin** -- Full admin interface for managing OLAP data and model metadata.

## Architecture

```
dvdrental (PostgreSQL OLTP)
        |
        v
   ETL Command --> CustomerOLAP (OLAP table)
        |
        v
  Training Command --> Random Forest Model (.pkl)
        |
        v
   Django Views --> Dashboard + Prediction API
```

## Tech Stack

- **Backend:** Django, Python
- **Database:** PostgreSQL (dvdrental sample DB)
- **ML:** Scikit-learn (Random Forest, StandardScaler, LabelEncoder)
- **Frontend:** Django templates, HTML/CSS

## Project Structure

```
âââ manage.py
âââ dvdrental_project/
â   âââ settings.py              # Django config, PostgreSQL connection
â   âââ urls.py                  # Root URL routing
â   âââ wsgi.py
âââ customer_analytics/
â   âââ models.py                # ORM models: Customer, Payment, Rental (OLTP), CustomerOLAP, ModelInfo
â   âââ views.py                 # Views: dashboard, predict, ETL status, model info
â   âââ urls.py                  # App URL patterns
â   âââ forms.py                 # CustomerPredictionForm (7 feature inputs)
â   âââ admin.py                 # Admin registration for OLAP + ModelInfo
â   âââ management/commands/
â       âââ etl_customer_segmentation.py    # ETL pipeline command
â       âââ train_customer_segmentation.py  # Model training command
âââ README.md
```

## How It Works

1. **Run ETL** -- `python manage.py etl_customer_segmentation` extracts customer behavior from the dvdrental tables (customer, payment, rental, inventory, film) and computes features like total payment, rental count, average payment, rental duration, and film diversity. Results are stored in the CustomerOLAP table.

2. **Train Model** -- `python manage.py train_customer_segmentation` reads the OLAP data, applies StandardScaler, trains a Random Forest classifier, and saves the model + encoders as pickle files. Model metadata (accuracy, feature importances) is stored in the ModelInfo table.

3. **Use the App** -- Navigate to the web interface to view the dashboard, browse customer segments, or predict the segment for new customer data.

## What I Learned

- Designing an ETL pipeline that bridges OLTP and OLAP schemas within the same database is a practical pattern for analytics on transactional data.
- Django management commands are a clean way to expose data pipelines as CLI tools while keeping everything within the Django ecosystem.
- Random Forest works well for customer segmentation when you have interpretable features -- feature importances map directly to business insights about what drives customer value.
