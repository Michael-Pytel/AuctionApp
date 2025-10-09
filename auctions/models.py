from django.contrib.auth.models import AbstractUser
from django.utils.functional import cached_property
from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator

# models.py


def validate_image_url(value):
    """Validate that URL ends with an image extension"""
    valid_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg']
    if not any(value.lower().endswith(ext) for ext in valid_extensions):
        raise ValidationError('URL must point to an image file (.jpg, .png, etc.)')


class User(AbstractUser):
    email_confirmed = models.BooleanField(default=False)
    confirmation_token = models.CharField(max_length=64, blank=True, null=True)
    token_created_at = models.DateTimeField(null=True, blank=True)

    # Existing unread_notification_count property
    @cached_property
    def unread_notification_count(self):
        return Notification.objects.filter(user=self, is_read=False).count()


class Category(models.Model):
    name = models.CharField(max_length=40)

    # take a snapshot on every time we save an item/and when we create it
    updated = models.DateTimeField(auto_now=True)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created']

    def __str__(self):
        return self.name


class AuctionListing(models.Model):
    """
    Represents an auction listing in the system.

    Attributes:
        owner (User): User who created the listing
        title (str): Title of the item being auctioned
        description (str): Detailed description of the item
        starting_price (float): Initial asking price
        image_url (str, optional): URL to item's image
        is_active (bool): Whether the auction is ongoing
        category (Category, optional): Item's category
    """
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='listings')
    title = models.CharField(max_length=50, db_index=True)
    description = models.CharField(max_length=500, null=True, blank=True)
    starting_price = models.FloatField()
    image_url = models.URLField(
        max_length=500,
        validators=[validate_image_url],
        blank=True,
        null=True
    )
    is_active = models.BooleanField(default=True, db_index=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE,
                                 related_name='category_listings', null=True, blank=True)
    updated = models.DateTimeField(auto_now=True)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created']

    def __str__(self):
        return self.title



class Watchlist(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    listing = models.ForeignKey(AuctionListing, on_delete=models.CASCADE, related_name='whatchedListings')

    # take a snapshot on every time we save an item/and when we create it
    updated = models.DateTimeField(auto_now=True)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created']

    def __str__(self):
        return f"Watchlist of {self.user}"


class Comment(models.Model):
    creator = models.ForeignKey(User, on_delete=models.CASCADE)
    listing = models.ForeignKey(AuctionListing, on_delete=models.CASCADE)
    body = models.CharField(max_length=500)

    # take a snapshot on every time we save an item/and when we create it
    updated = models.DateTimeField(auto_now=True)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created']

    def __str__(self):
        return self.body[0:50]


class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    listing = models.ForeignKey(AuctionListing, on_delete=models.CASCADE)
    is_read = models.BooleanField(default=False)

    # take a snapshot on every time we create an item
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created']

    def __str__(self):
        return self.user.username


class Bid(models.Model):
    bidder = models.ForeignKey(User, on_delete=models.CASCADE)
    listing = models.ForeignKey(AuctionListing, on_delete=models.CASCADE)
    amount = models.FloatField()

    # take a snapshot on every time we save an item/and when we create it
    updated = models.DateTimeField(auto_now=True)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-amount']

    def __str__(self):
        return str(self.listing.id)
