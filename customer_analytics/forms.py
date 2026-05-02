from django import forms


class CustomerPredictionForm(forms.Form):
    """Form untuk input data customer baru dan prediksi segmennya"""

    total_payment = forms.DecimalField(
        label='Total Payment ($)',
        min_value=0,
        max_digits=10,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'form-input',
            'placeholder': 'e.g. 120.50',
            'step': '0.01',
        })
    )
    rental_count = forms.IntegerField(
        label='Total Rentals',
        min_value=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-input',
            'placeholder': 'e.g. 32',
        })
    )
    avg_payment = forms.DecimalField(
        label='Average Payment ($)',
        min_value=0,
        max_digits=10,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'form-input',
            'placeholder': 'e.g. 3.75',
            'step': '0.01',
        })
    )
    max_payment = forms.DecimalField(
        label='Max Payment ($)',
        min_value=0,
        max_digits=10,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'form-input',
            'placeholder': 'e.g. 11.99',
            'step': '0.01',
        })
    )
    min_payment = forms.DecimalField(
        label='Min Payment ($)',
        min_value=0,
        max_digits=10,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'form-input',
            'placeholder': 'e.g. 0.99',
            'step': '0.01',
        })
    )
    distinct_films = forms.IntegerField(
        label='Distinct Films Rented',
        min_value=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-input',
            'placeholder': 'e.g. 25',
        })
    )
    avg_rental_duration_days = forms.DecimalField(
        label='Avg Rental Duration (days)',
        min_value=0,
        max_digits=10,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'form-input',
            'placeholder': 'e.g. 4.5',
            'step': '0.01',
        })
    )
