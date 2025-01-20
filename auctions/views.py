from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseNotAllowed
from django.shortcuts import render
from django.urls import reverse
from django.core.cache import cache
from .models import User, Category, AuctionListing, Bid, Comment, Watchlist, Notification
from .forms import ListingForm, BidForm
from django.utils import timezone
from django.contrib import messages
from datetime import timedelta
from django.conf import settings
import secrets
from django.core.mail import send_mail
from .utils import send_confirmation_email
from django.shortcuts import get_object_or_404, redirect
from .utils import (annotate_listing_with_max_bid, get_listing_comments,
                    get_last_bid, get_listing_bidders, check_watchlist_status,
                    handle_auction_close)


def index(request):
    """Display active listings, optionally filtered by category."""
    selected_category = request.GET.get('q', '')

    listings = AuctionListing.objects.filter(is_active=True)
    if selected_category:
        listings = listings.filter(category__name=selected_category)

    for listing in listings:
        annotate_listing_with_max_bid(listing)

    context = {
        'listings': listings,
        'Categories': Category.objects.all(),
        'category_counts': {
            category.name: AuctionListing.objects.filter(
                category=category, is_active=True).count()
            for category in Category.objects.all()
        },
        'total_listings': AuctionListing.objects.filter(is_active=True).count(),
        'selected_category': selected_category
    }
    return render(request, "auctions/index.html", context)


@login_required(login_url='login')
def profile(request):
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
def create_listing(request):
    form = ListingForm()

    if request.method == 'POST':
        form = ListingForm(request.POST)
        if form.is_valid():
            listing = form.save(commit=False)
            listing.owner = request.user
            listing.save()
            return redirect('index')

    context = {'form': form}
    return render(request, 'auctions/listing_form.html', context)


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
    # Basic validation checks
    if not listing_page.is_active:
        return False, "This auction is closed"

    if listing_page.owner == request.user:
        return False, "You cannot bid on your own listing"

    # Validate bid amount is numeric and positive
    try:
        bid_amount = float(bid_amount)
        if bid_amount <= 0:
            return False, "Bid amount must be positive"
    except (TypeError, ValueError):
        return False, "Invalid bid amount"

    # Rate limiting check
    cache_key = f'user_{request.user.id}_bid_count'
    bid_count = cache.get(cache_key, 0)

    if bid_count >= 10:
        return False, "Too many bid attempts. Please wait a minute"

    # Get the last bid for validation
    last_bid = Bid.objects.filter(listing=listing_page).order_by('-amount').first()

    # Check if the user is trying to outbid themselves
    if last_bid and last_bid.bidder == request.user:
        return False, "You already have the highest bid on this item"

    # Validate bid amount against starting price and current highest bid
    if not last_bid and bid_amount <= listing_page.starting_price:
        return False, f"Bid must be higher than the starting price (${listing_page.starting_price})"
    elif last_bid and bid_amount <= last_bid.amount:
        return False, f"Bid must be higher than the current highest bid (${last_bid.amount})"

    try:
        # Create and save the new bid within a transaction
        from django.db import transaction
        with transaction.atomic():
            bid = Bid.objects.create(
                bidder=request.user,
                listing=listing_page,
                amount=bid_amount
            )

            # Update cache for rate limiting
            cache.set(cache_key, bid_count + 1, 60)  # Expires in 60 seconds

        return True, "Bid placed successfully!"

    except Exception as e:
        return False, f"Error processing bid: {str(e)}"


def listing_page(request, listing_id):  # Renamed from listingPage
    """Display details of a specific listing."""
    listing_page = get_object_or_404(AuctionListing, id=listing_id)
    context = {
        'listing_page': listing_page,
        'comments': get_listing_comments(listing_page),
        'last_bid': get_last_bid(listing_page),
        'Bidders': get_listing_bidders(listing_page),
        'is_in_watchlist': check_watchlist_status(request.user, listing_page),
        'form': BidForm()
    }

    if request.method == 'POST':
        return handle_bid_submission(request, listing_page)

    return render(request, 'auctions/listing_page.html', context)


def handle_bid_submission(request, listing_page):
    """
    Handle the submission of a new bid.

    Args:
        request: The HTTP request object
        listing_page: The AuctionListing instance

    Returns:
        HttpResponse: Redirect to the listing page with appropriate message
    """
    form = BidForm(request.POST)
    if form.is_valid():
        bid_amount = form.cleaned_data['amount']
        success, message = place_bid(request, listing_page, bid_amount)

        if success:
            messages.success(request, message)
        else:
            messages.warning(request, message)

    return redirect("listing_page", listing_id=listing_page.id)


# user add a comment
@login_required(login_url='login')
def listing_comment(request, listing_id):
    listing_page = get_object_or_404(AuctionListing, id=listing_id)
    if request.method == "POST":
        comment_body = request.POST.get('body', '').strip()

        # Validate comment is not empty
        if not comment_body:
            messages.error(request, "Comment cannot be empty")
            return redirect("listing_page", listing_id=listing_id)

        # Validate comment length
        if len(comment_body) > 500:
            messages.error(request, "Comment is too long (maximum 500 characters)")
            return redirect("listing_page", listing_id=listing_id)

        # Validate listing is active
        if not listing_page.is_active:
            messages.error(request, "Cannot comment on closed listings")
            return redirect("listing_page", listing_id=listing_id)

        comment = Comment.objects.create(
            creator=request.user,
            listing=listing_page,
            body=comment_body
        )

    return redirect("listing_page", listing_id=listing_id)


# Watchlist view
@login_required(login_url='login')
def watchlist_page(request):
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
def add_watchlist(request, listing_id):
    if request.method == "POST":
        listing_page = get_object_or_404(AuctionListing, id=listing_id)

        # Check if already in watchlist
        if Watchlist.objects.filter(user=request.user, listing=listing_page).exists():
            messages.warning(request, "Item already in watchlist")
            return redirect("listing_page", listing_id=listing_id)

        # Validate owner isn't adding their own listing
        if listing_page.owner == request.user:
            messages.warning(request, "Cannot add your own listing to watchlist")
            return redirect("listing_page", listing_id=listing_id)

        Watchlist.objects.create(user=request.user, listing=listing_page)
        messages.success(request, "Added to watchlist")
    return redirect("listing_page", listing_id=listing_id)


# remove
@login_required(login_url='login')
def remove_watchlist(request, listing_id):  # Changed from pk
    listing_page = get_object_or_404(AuctionListing, id=listing_id)
    if request.method == "POST":
        Watchlist.objects.filter(user=request.user, listing=listing_page).delete()
        return redirect("listing_page", listing_id=listing_id)


# Auction Control
@login_required(login_url='login')
def auction_control(request, listing_id):
    listing_page = get_object_or_404(AuctionListing, id=listing_id)

    if not listing_page.is_active:
        listing_page.is_active = True
        listing_page.save()
        messages.success(request, "Auction activated successfully.")
        return redirect("listing_page", listing_id=listing_id)

    last_bid = get_last_bid(listing_page)
    message = handle_auction_close(listing_page, last_bid)
    messages.success(request, message)
    return redirect("listing_page", listing_id=listing_id)


# Notifications view
@login_required(login_url='login')
def notifications(request):
    notifications = Notification.objects.filter(user=request.user)

    notifications.update(is_read=True)
    context = {"notifications": notifications}
    return render(request, 'auctions/notifications.html', context)


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
