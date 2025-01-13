from typing import Any, Dict
from django import forms
from .models import AuctionListing, Bid, Category

# adding forms

class ListingForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Add an empty option to the category field's choices
        self.fields['category'].empty_label = "Select a category"  # Change this text

        self.fields['is_active'].label = "Active List"
        self.fields['is_active'].widget.attrs.update({
            'class': 'checkbox-input'
        })

    def clean(self):
        cleaned_data = super().clean()
        category = cleaned_data.get('category')

        # if the category is None (not chosen), set it to 'Other'
        if category is None:
            cleaned_data['category'] = Category.objects.get(name='Other')

        return cleaned_data

    class Meta:
        model = AuctionListing
        fields = ["title", "description", "primary_price", "imageUrl",  "category", "is_active"]

        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter title'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Enter description'}),
            'primary_price': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Enter starting price'}),
            'imageUrl': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'Enter image URL (optional)'}),
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
            'amount': forms.NumberInput(attrs={'class': 'form-control'})
        }
