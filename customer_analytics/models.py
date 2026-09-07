from django.db import models


# =====================================================
# OLTP models. These mirror tables that already exist in the dvdrental
# sample database, so Django does not manage their schema.
# =====================================================

class Customer(models.Model):
    customer_id = models.AutoField(primary_key=True)
    store_id = models.SmallIntegerField()
    first_name = models.CharField(max_length=45)
    last_name = models.CharField(max_length=45)
    email = models.CharField(max_length=50, blank=True, null=True)
    address_id = models.SmallIntegerField()
    activebool = models.BooleanField(default=True)
    create_date = models.DateField()
    last_update = models.DateTimeField(auto_now=True)
    active = models.IntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'customer'

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


class Payment(models.Model):
    payment_id = models.AutoField(primary_key=True)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, db_column='customer_id')
    staff_id = models.SmallIntegerField()
    rental_id = models.IntegerField()
    amount = models.DecimalField(max_digits=5, decimal_places=2)
    payment_date = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'payment'

    def __str__(self):
        return f"Payment #{self.payment_id} - ${self.amount}"


class Rental(models.Model):
    rental_id = models.AutoField(primary_key=True)
    rental_date = models.DateTimeField()
    inventory_id = models.IntegerField()
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, db_column='customer_id')
    return_date = models.DateTimeField(blank=True, null=True)
    staff_id = models.SmallIntegerField()
    last_update = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = 'rental'

    def __str__(self):
        return f"Rental #{self.rental_id}"


# =====================================================
# OLAP model. One row per customer, written by the ETL command.
# =====================================================

class CustomerOLAP(models.Model):
    customer_id = models.IntegerField(primary_key=True)
    first_name = models.CharField(max_length=45)
    last_name = models.CharField(max_length=45)
    email = models.CharField(max_length=50, blank=True, null=True)
    store_id = models.SmallIntegerField(default=1)

    # Monetary
    total_payment = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    avg_payment = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    max_payment = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    min_payment = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # Frequency
    rental_count = models.IntegerField(default=0)
    distinct_films = models.IntegerField(default=0)
    avg_rental_duration_days = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # Recency. Days between a customer's last rental and the most recent
    # rental anywhere in the dataset. The snapshot is the data's own latest
    # date, not today, because the dvdrental sample data ends in 2006.
    last_rental_date = models.DateTimeField(blank=True, null=True)
    recency_days = models.IntegerField(default=0)

    is_active = models.BooleanField(default=True)
    segment = models.CharField(max_length=32, blank=True, null=True)
    cluster = models.IntegerField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'customer_olap'
        verbose_name = 'Customer OLAP'
        verbose_name_plural = 'Customer OLAP Records'
        indexes = [models.Index(fields=['segment'])]

    def __str__(self):
        return f"{self.first_name} {self.last_name} - {self.segment or 'unsegmented'}"


# =====================================================
# Model metadata.
#
# The metric fields are nullable on purpose. Clustering has no ground-truth
# label, so accuracy, precision, recall and F1 do not exist for it, and
# writing a zero there would read as a real score of zero. A clustering run
# fills in silhouette instead and leaves the rest null.
# =====================================================

class ModelInfo(models.Model):
    model_name = models.CharField(max_length=100)
    model_type = models.CharField(max_length=100)

    accuracy = models.DecimalField(max_digits=6, decimal_places=4, blank=True, null=True)
    precision_score = models.DecimalField(max_digits=6, decimal_places=4, blank=True, null=True)
    recall_score = models.DecimalField(max_digits=6, decimal_places=4, blank=True, null=True)
    f1 = models.DecimalField(max_digits=6, decimal_places=4, blank=True, null=True)
    silhouette = models.DecimalField(max_digits=6, decimal_places=4, blank=True, null=True)

    features = models.TextField(blank=True, null=True)
    file_path = models.CharField(max_length=255)
    trained_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'model_info'
        verbose_name = 'ML Model Info'
        verbose_name_plural = 'ML Model Info'
        ordering = ['-trained_at']

    @property
    def headline_metric(self):
        """What to show in a table when the model type decides the metric."""
        if self.silhouette is not None:
            return f"silhouette {self.silhouette}"
        if self.accuracy is not None:
            return f"accuracy {self.accuracy}"
        return "no metric recorded"

    def __str__(self):
        return f"{self.model_name} ({self.headline_metric})"
