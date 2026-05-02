from django.db import models


# =====================================================
# OLTP Models (mirror dari DVD Rental DB yang sudah ada)
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
# OLAP Model (tabel baru untuk analytics)
# =====================================================

class CustomerOLAP(models.Model):
    customer_id = models.IntegerField(primary_key=True)
    first_name = models.CharField(max_length=45)
    last_name = models.CharField(max_length=45)
    email = models.CharField(max_length=50, blank=True, null=True)
    store_id = models.SmallIntegerField(default=1)
    total_payment = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    rental_count = models.IntegerField(default=0)
    avg_payment = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    max_payment = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    min_payment = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    distinct_films = models.IntegerField(default=0)
    avg_rental_duration_days = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)
    segment = models.CharField(max_length=20, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'customer_olap'
        verbose_name = 'Customer OLAP'
        verbose_name_plural = 'Customer OLAP Records'

    def __str__(self):
        return f"{self.first_name} {self.last_name} - {self.segment}"


# =====================================================
# Model Info (menyimpan info ML model)
# =====================================================

class ModelInfo(models.Model):
    model_name = models.CharField(max_length=100)
    model_type = models.CharField(max_length=100)
    accuracy = models.DecimalField(max_digits=5, decimal_places=4)
    precision_score = models.DecimalField(max_digits=5, decimal_places=4, default=0)
    recall_score = models.DecimalField(max_digits=5, decimal_places=4, default=0)
    f1 = models.DecimalField(max_digits=5, decimal_places=4, default=0)
    features = models.TextField(blank=True, null=True)
    file_path = models.CharField(max_length=255)
    trained_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'model_info'
        verbose_name = 'ML Model Info'
        verbose_name_plural = 'ML Model Info'
        ordering = ['-trained_at']

    def __str__(self):
        return f"{self.model_name} (acc: {self.accuracy})"
