from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.db.models import Q
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render, redirect
from django.urls import reverse
from django.core.cache import cache
from django.shortcuts import redirect
from .models import User, Category, AuctionListing, Bid, Comment, Watchlist, Notification
from .forms import ListingForm, BidForm

from django.utils import timezone
# django flash messages
from django.contrib import messages
from datetime import timedelta
from django.conf import settings
import secrets
from django.core.mail import send_mail
from .utils import send_confirmation_email  # This will work now



def index(request):
    # Get the selected category from query parameter
    selected_category = request.GET.get('q', '')

    # Get all active listings filtered by category if selected
    if selected_category:
        listings = AuctionListing.objects.filter(
            is_active=True,
            category__name=selected_category
        )
    else:
        listings = AuctionListing.objects.filter(is_active=True)

    # Get the highest bid for each listing
    for listing in listings:
        highest_bid = Bid.objects.filter(listing=listing).first()
        listing.max_bid = highest_bid.amount if highest_bid else None

    # Get all categories
    Categories = Category.objects.all()

    # Calculate category counts
    category_counts = {}
    for category in Categories:
        category_counts[category.name] = AuctionListing.objects.filter(
            category=category,
            is_active=True
        ).count()

    # Get total active listings count
    total_listings = AuctionListing.objects.filter(is_active=True).count()

    context = {
        'listings': listings,
        'Categories': Categories,
        'category_counts': category_counts,
        'total_listings': total_listings,
        'selected_category': selected_category
    }
    return render(request, "auctions/index.html", context)


@login_required(login_url='login')
def Profile(request):
    listings = AuctionListing.objects.filter(owner=request.user)

    # Update the max_bid attribute for each listing
    for listing in listings:
        highest_bid = Bid.objects.filter(listing=listing).first()
        listing.max_bid = highest_bid.amount if highest_bid else None

    context = {"listings": listings}
    return render(request, "auctions/profile.html", context)


def login_view(request):
    if request.method == "POST":
        username = request.POST["username"]
        password = request.POST["password"]
        user = authenticate(request, username=username, password=password)

        if user is not None:
            if not user.email_confirmed:
                messages.error(request,
                               "Please confirm your email before logging in. Check your inbox.")
                return render(request, "auctions/login.html")

            login(request, user)
            return HttpResponseRedirect(reverse("index"))
        else:
            return render(request, "auctions/login.html", {
                "message": "Invalid username and/or password."
            })
    else:
        return render(request, "auctions/login.html")


def logout_view(request):
    logout(request)
    return HttpResponseRedirect(reverse("index"))


def register(request):
    if request.method == "POST":
        username = request.POST["username"]
        email = request.POST["email"]

        # Ensure password matches confirmation
        password = request.POST["password"]
        confirmation = request.POST["confirmation"]
        if password != confirmation:
            return render(request, "auctions/register.html", {
                "message": "Passwords must match."
            })

        # Attempt to create new user
        try:
            user = User.objects.create_user(username, email, password)
            user.is_active = False  # Deactivate until email is confirmed
            user.save()

            # Send confirmation email
            send_confirmation_email(user)

            messages.success(request,
                             "Registration successful! Please check your email to confirm your account.")
            return HttpResponseRedirect(reverse("login"))
        except IntegrityError:
            return render(request, "auctions/register.html", {
                "message": "Username already taken."
            })
    else:
        return render(request, "auctions/register.html")


# a view for adding listing
@login_required(login_url='login')
def CreateListing(request):
    form = ListingForm()

    if request.method == 'POST':
        form = ListingForm(request.POST)
        if form.is_valid():
            listing = form.save(commit=False)
            listing.owner = request.user
            listing.save()
            return redirect('index')

    context = {'form': form}
    return render(request, 'auctions/Listing_form.html', context)


def confirm_email(request, token):
    try:
        user = User.objects.get(confirmation_token=token)

        # Check if token is expired (24 hours)
        if user.token_created_at < timezone.now() - timedelta(days=1):
            messages.error(request,
                           "Email confirmation link has expired. Please register again.")
            user.delete()
            return HttpResponseRedirect(reverse("register"))

        user.email_confirmed = True
        user.is_active = True
        user.confirmation_token = ''
        user.save()

        messages.success(request,
                         "Email confirmed! You can now log in to your account.")
        return HttpResponseRedirect(reverse("login"))
    except User.DoesNotExist:
        messages.error(request,
                       "Invalid confirmation link.")
        return HttpResponseRedirect(reverse("login"))


# a view for geting the listing page
def place_bid(request, listing_page, bid_amount):
    """
    Helper function to handle bid placement with rate limiting and self-bid prevention

    Args:
        request: The HTTP request object
        listing_page: The AuctionListing instance
        bid_amount: The amount of the bid

    Returns:
        tuple: (bool, str) - (success status, message)
    """
    # Rate limiting check
    cache_key = f'user_{request.user.id}_bid_count'
    bid_count = cache.get(cache_key, 0)

    if bid_count > 10:  # Max 10 bids per minute
        return False, "Too many bid attempts. Please wait a minute."

    # Get the last bid for validation
    last_bid = Bid.objects.filter(listing=listing_page).first()

    # Check if the user is trying to outbid themselves
    if last_bid and last_bid.bidder == request.user:
        return False, "You already have the highest bid on this item"

    # Validate bid amount
    if not last_bid and bid_amount <= listing_page.primary_price:
        return False, "Bid must be higher than the primary price"
    elif last_bid and bid_amount <= last_bid.amount:
        return False, "Bid must be higher than the current highest bid"

    try:
        # Create and save the new bid
        bid = Bid(
            bidder=request.user,
            listing=listing_page,
            amount=bid_amount
        )
        bid.save()

        # Increment the bid count in cache
        cache.set(cache_key, bid_count + 1, 60)  # Expires in 60 seconds

        return True, "Bid placed successfully!"

    except Exception as e:
        return False, f"Error processing bid: {str(e)}"


def listingPage(request, pk):
    listing_page = AuctionListing.objects.get(id=pk)
    comments = Comment.objects.filter(listing=listing_page)
    # get the last bid for this listing, if any
    last_bid = Bid.objects.filter(listing=listing_page).first()
    # get the Bidders in this lisitng
    Bidders = Bid.objects.filter(listing=listing_page)

    # is the listing added to the watchlist
    is_in_watchlist = False
    if request.user.is_authenticated:
        is_in_watchlist = Watchlist.objects.filter(user=request.user, listing=listing_page).exists()

    # if user make a bid 
    if request.method == 'POST':
        form = BidForm(request.POST)
        if form.is_valid():
            bid_amount = form.cleaned_data['amount']

            success, message = place_bid(request, listing_page, bid_amount)

            if success:
                messages.success(request, message)
                return redirect("listingPage", pk=listing_page.id)
            else:
                messages.warning(request, message)
    else:
        form = BidForm()

    context = {'listing_page': listing_page, 'form': form,
               'last_bid': last_bid, 'comments': comments,
               'Bidders': Bidders, 'is_in_watchlist': is_in_watchlist}
    return render(request, 'auctions/listing_page.html', context)


# user add a comment
def listingComment(request, pk):
    listing_page = AuctionListing.objects.get(id=pk)
    if request.method == "POST":
        comment = Comment.objects.create(
            creater=request.user,
            listing=listing_page,
            body=request.POST.get('body')
        )

    return redirect("listingPage", pk=listing_page.id)


# Watchlist view
@login_required(login_url='login')
def watchlistPage(request):
    # get the objects associated with the watchlist of the user
    watched_listings = Watchlist.objects.filter(user=request.user).values('listing')
    # get the primary key of the listings in the watched_listings queryset
    listing_pks = watched_listings.values_list('listing', flat=True)
    # get the listings from there primary keys
    watched_listings_data = AuctionListing.objects.filter(pk__in=listing_pks)

    # Update the max_bid attribute for each listing
    for listing in watched_listings_data:
        highest_bid = Bid.objects.filter(listing=listing).first()
        listing.max_bid = highest_bid.amount if highest_bid else None

    context = {'watched_listings': watched_listings_data}
    return render(request, 'auctions/watchlist.html', context)


# add
@login_required(login_url='login')
def addWatchlist(request, pk):
    listing_page = AuctionListing.objects.get(id=pk)
    if request.method == "POST":
        Watchlist.objects.create(user=request.user, listing=listing_page)
        return redirect("listingPage", pk=listing_page.id)


# remove
@login_required(login_url='login')
def removeWatchlist(request, pk):
    listing_page = AuctionListing.objects.get(id=pk)
    if request.method == "POST":
        Watchlist.objects.filter(user=request.user, listing=listing_page).delete()
        return redirect("listingPage", pk=listing_page.id)


# Auction Control
@login_required(login_url='login')
def AuctionControl(request, pk):
    listing_page = AuctionListing.objects.get(id=pk)
    if request.method == "POST":
        if listing_page.is_active:  # if it's active --> close it
            # check if there are any bidders
            last_bid = Bid.objects.filter(listing=listing_page).first()
            if last_bid:  # there is a bidder --> process winner notification and ownership transfer
                listing_page.is_active = False
                listing_page.owner = last_bid.bidder
                # Set the primary_price to the amount of the last bid
                listing_page.primary_price = last_bid.amount
                listing_page.save()
                # Delete all previous bids related to this listing
                Bid.objects.filter(listing=listing_page).delete()
                # CREATE A NOTIFICATION sented to the winner
                notification = Notification.objects.create(user=last_bid.bidder, listing=listing_page)
                messages.success(request,
                                 f"You have been successfully Closed this auction, the new owner of this auction is @{last_bid.bidder}")
            else:  # no bidders --> just close the auction
                listing_page.is_active = False
                listing_page.save()
                messages.success(request, "You have been successfully Closed this auction.")

            return redirect("listingPage", pk=listing_page.id)
        else:  # if it's not active --> activate it
            listing_page.is_active = True
            listing_page.save()
            messages.success(request, "You have been successfully Activate this auction.")
            return redirect("listingPage", pk=listing_page.id)


# Notifications view
@login_required(login_url='login')
def Notifications(request):
    notifications = Notification.objects.filter(user=request.user)

    notifications.update(is_read=True)
    context = {"notifications": notifications}
    return render(request, 'auctions/Notifications.html', context)


def password_reset_request(request):
    if request.method == "POST":
        email = request.POST.get('email')
        try:
            user = User.objects.get(email=email)
            # Generate token
            token = secrets.token_urlsafe(48)
            user.confirmation_token = token
            user.token_created_at = timezone.now()
            user.save()

            # Send email
            reset_link = f"http://{settings.SITE_URL}/password-reset/{token}"
            send_mail(
                'Password Reset Request',
                f'''Hi {user.username},

You requested a password reset. Click this link to reset your password:
{reset_link}

This link will expire in 24 hours.

If you did not request a password reset, please ignore this email.''',
                'noreply@auctionsite.com',
                [user.email],
                fail_silently=False,
            )

            messages.success(request, "Password reset instructions have been sent to your email.")
            return HttpResponseRedirect(reverse("login"))
        except User.DoesNotExist:
            messages.error(request, "No user found with that email address.")

    return render(request, "auctions/password_reset.html")


def password_reset_confirm(request, token):
    try:
        user = User.objects.get(confirmation_token=token)

        # Check if token is expired (24 hours)
        if user.token_created_at < timezone.now() - timedelta(days=1):
            messages.error(request, "Password reset link has expired. Please try again.")
            return HttpResponseRedirect(reverse("password_reset"))

        if request.method == "POST":
            password = request.POST.get("password")
            confirmation = request.POST.get("confirmation")

            if password != confirmation:
                messages.error(request, "Passwords must match.")
                return render(request, "auctions/password_reset_confirm.html")

            user.set_password(password)
            user.confirmation_token = ''
            user.save()

            messages.success(request, "Password has been reset successfully. You can now log in.")
            return HttpResponseRedirect(reverse("login"))

        return render(request, "auctions/password_reset_confirm.html")
    except User.DoesNotExist:
        messages.error(request, "Invalid password reset link.")
        return HttpResponseRedirect(reverse("login"))


