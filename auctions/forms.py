from django import forms
from django.core.validators import MinValueValidator
from .models import AuctionListing, Bid, Category


class ListingForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['category'].empty_label = "Select a category"
        self.fields['is_active'].label = "Active List"
        self.fields['is_active'].widget.attrs.update({
            'class': 'checkbox-input'
        })
        # Add validation for starting_price
        self.fields['starting_price'].validators = [MinValueValidator(0.01)]

    def clean(self):
        cleaned_data = super().clean()
        category = cleaned_data.get('category')

        if category is None:
            try:
                cleaned_data['category'] = Category.objects.get(name='Other')
            except Category.DoesNotExist:
                cleaned_data['category'] = Category.objects.create(name='Other')

        return cleaned_data

    class Meta:
        model = AuctionListing
        fields = ["title", "description", "starting_price", "image_url", "category", "is_active"]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter title'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Enter description'}),
            'starting_price': forms.NumberInput(
                attrs={'class': 'form-control', 'placeholder': 'Enter starting price', 'min': '0.01'}),
            'image_url': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'Enter image URL (optional)'}),
            'category': forms.Select(attrs={'class': 'form-group'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class BidForm(forms.ModelForm):
    class Meta:
        model = Bid
        fields = ["amount"]
        labels = {
            'amount': 'Enter your bid amount',
        }
        widgets = {
            'amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0.01',
                'step': '0.01'
            })
        }

    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount is not None and amount <= 0:
            raise forms.ValidationError("Bid amount must be greater than zero")
        return amount
