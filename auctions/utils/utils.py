from django.shortcuts import get_object_or_404
from ..models import Bid, Watchlist, Notification


def annotate_listing_with_max_bid(listing):
    """Add max_bid attribute to a listing object."""
    highest_bid = Bid.objects.filter(listing=listing).first()
    listing.max_bid = highest_bid.amount if highest_bid else None
    return listing


def get_listing_comments(listing):
    """Get all comments for a listing."""
    return listing.comment_set.all()


def get_last_bid(listing):
    """Get the latest bid for a listing."""
    return Bid.objects.filter(listing=listing).first()


def get_listing_bidders(listing):
    """Get all bidders for a listing."""
    return Bid.objects.filter(listing=listing)


def check_watchlist_status(user, listing):
    """Check if a listing is in user's watchlist."""
    if not user.is_authenticated:
        return False
    return Watchlist.objects.filter(user=user, listing=listing).exists()


def handle_auction_close(listing_page, last_bid):
    """Handle the closure of an auction."""
    if not last_bid:
        listing_page.is_active = False
        listing_page.save()
        return "Auction closed successfully."

    listing_page.is_active = False
    listing_page.owner = last_bid.bidder
    listing_page.starting_price = last_bid.amount
    listing_page.save()

    Bid.objects.filter(listing=listing_page).delete()
    Notification.objects.create(user=last_bid.bidder, listing=listing_page)
    return f"Auction closed. New owner: {last_bid.bidder}"
