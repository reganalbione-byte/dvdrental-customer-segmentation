# DVD Rental Customer Segmentation

Django application that segments customers of the PostgreSQL `dvdrental` sample
database. An ETL step aggregates transactional rentals and payments into
customer-level RFM features, a clustering step groups customers on those
features, and a small web interface exposes the result as a dashboard, a
searchable customer list, and a form that places an unseen customer into a
segment.

## Pipeline

```
dvdrental (PostgreSQL, OLTP)
        |
        |  etl_customer_segmentation
        v
customer_olap  (one row per customer: recency, frequency, monetary, variety)
        |
        |  segment_customers
        v
KMeans on scaled features  ->  cluster profile  ->  named segments
        |
        v
Django views: dashboard, customer list, segment assignment
```

The two steps are separate on purpose. The ETL produces features and nothing
else; segmenting is a decision made from those features, not a column derived
alongside them.

## Features used

| Feature | Meaning | RFM axis |
|---|---|---|
| `recency_days` | Days from the customer's last rental to the latest rental in the dataset | Recency |
| `rental_count` | Number of rentals | Frequency |
| `total_payment` | Sum of payments | Monetary |
| `avg_payment` | Mean payment per transaction | Monetary |
| `distinct_films` | Number of different films rented | Variety |
| `avg_rental_duration_days` | Mean days held per rental | Behaviour |

Recency is measured against the most recent rental **in the data**, not against
today. The sample database ends in 2006, so measuring against the current date
would make every customer equally lapsed and recency would carry no signal.

### A caveat in this dataset

124 customers have `recency_days` exactly 0. That is not 124 unusually active
customers, it is an artefact: `dvdrental` contains a single bulk batch of
rentals all timestamped 2006-02-14 15:16:03. Recency in this data is
effectively binary, either 0 or roughly 150 to 180 days, and the third cluster
forms largely along that seam rather than along real customer behaviour.

The silhouette score reflects this. At k=3 it is 0.279, which is weak
separation. The clustering is implemented correctly; the sample database simply
does not contain three strongly distinct behavioural groups. On real
transactional data with rentals spread continuously over time, recency would
carry the signal it is supposed to.

## Why clustering and not classification

An earlier version of this project created the target like this:

```python
df['segment'] = pd.qcut(df['total_payment'], q=3,
                        labels=['Low Value', 'Medium Value', 'High Value'])
```

and then trained a Random Forest whose feature list still contained
`total_payment`. The label was a deterministic function of a feature the model
could see, so the model was recovering an arithmetic rule rather than learning a
pattern. Accuracy sat near 1.00, which looked like a good result and was
actually the evidence of the problem. That is target leakage.

Customer segments have no ground truth to predict, so segmentation is a
clustering problem. `segment_customers` scales the features, chooses `k` by
silhouette score, profiles each cluster from its own feature means, and names
the segments from that profile. It records a silhouette score and deliberately
records no accuracy, because there is nothing to be accurate against.

If a supervised model is wanted here, the target has to be something the
features do not already contain, for example whether a customer rents again in
the next 30 days, trained only on data from before that window.

## Setup

```bash
git clone https://github.com/reganalbione-byte/dvdrental-customer-segmentation.git
cd dvdrental-customer-segmentation

python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env        # then fill in your own values
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Load the `dvdrental` sample database into PostgreSQL first, then:

```bash
python manage.py migrate
python manage.py etl_customer_segmentation
python manage.py segment_customers
python manage.py runserver
```

`segment_customers` searches `k` from 2 to 8 and keeps the best silhouette.
Pass `--k 4` to force a value.

## Configuration

All configuration comes from environment variables, listed in `.env.example`.
`.env` is gitignored. Nothing in this repository contains a credential.

## Project layout

```
manage.py
dvdrental_project/
    settings.py                 # env-driven configuration
    urls.py
customer_analytics/
    models.py                   # OLTP mirrors (unmanaged) + CustomerOLAP + ModelInfo
    views.py                    # pages and JSON endpoints
    forms.py                    # segment assignment inputs
    admin.py
    urls.py
    migrations/
    templates/customer_analytics/
    management/commands/
        etl_customer_segmentation.py
        segment_customers.py
```

## Notes on the data model

`Customer`, `Payment` and `Rental` mirror tables that already exist in the
sample database and are declared `managed = False`, so Django never tries to
create or alter them. `CustomerOLAP` and `ModelInfo` are this project's own
tables and are migrated normally.

The metric fields on `ModelInfo` are nullable. A clustering run fills in
`silhouette` and leaves accuracy, precision, recall and F1 null, because writing
zero there would read as a real score of zero rather than a metric that does not
apply.

## What I learned

- Bridging an OLTP schema and an OLAP table inside the same database is a
  practical pattern for analytics on transactional data, and Django management
  commands are a clean way to expose the pipeline as CLI steps.
- Finding target leakage in my own project taught me more than the model did.
  The tell was the accuracy: a segmentation model scoring near 1.00 on held-out
  data usually means the label was derived from a feature, not that the model is
  good.
- Naming clusters from their own profile, rather than deciding the names first
  and forcing data into them, is what makes the segments mean something. "At
  Risk" only appears when a cluster's recency actually says so.
