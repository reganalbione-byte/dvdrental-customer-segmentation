from django import forms


class CustomerPredictionForm(forms.Form):
    """Inputs for assigning an unseen customer to a segment.

    The field list matches FEATURES in segment_customers.py exactly. If you
    change the feature set there, change it here too, or the model will be
    handed columns in the wrong order.
    """

    _num = {"class": "form-input", "step": "0.01"}
    _int = {"class": "form-input"}

    recency_days = forms.IntegerField(
        label="Days since last rental", min_value=0,
        help_text="Measured against the latest rental in the dataset, not today.",
        widget=forms.NumberInput(attrs={**_int, "placeholder": "e.g. 34"}))
    rental_count = forms.IntegerField(
        label="Total rentals", min_value=0,
        widget=forms.NumberInput(attrs={**_int, "placeholder": "e.g. 32"}))
    total_payment = forms.DecimalField(
        label="Total payment", min_value=0, max_digits=10, decimal_places=2,
        widget=forms.NumberInput(attrs={**_num, "placeholder": "e.g. 120.50"}))
    avg_payment = forms.DecimalField(
        label="Average payment", min_value=0, max_digits=10, decimal_places=2,
        widget=forms.NumberInput(attrs={**_num, "placeholder": "e.g. 3.75"}))
    distinct_films = forms.IntegerField(
        label="Distinct films rented", min_value=0,
        widget=forms.NumberInput(attrs={**_int, "placeholder": "e.g. 25"}))
    avg_rental_duration_days = forms.DecimalField(
        label="Average rental duration in days", min_value=0,
        max_digits=10, decimal_places=2,
        widget=forms.NumberInput(attrs={**_num, "placeholder": "e.g. 4.5"}))
