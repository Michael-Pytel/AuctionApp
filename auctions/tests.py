# tests.py
from django.test import Client
from django.urls import reverse
from django.contrib.messages import get_messages
from django.utils import timezone
from django.core import mail
from .models import User, Comment, Notification
from django.contrib.auth import get_user_model
from django.test import TestCase
from .forms import ListingForm, BidForm
from .models import AuctionListing, Bid, Category


class ViewsTest(TestCase):
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        self.User = get_user_model()

        # Create test users
        self.test_user = User.objects.create_user(
            username='testuser',
            email='test@test.com',
            password='testpass123'
        )
        self.test_user.email_confirmed = True
        self.test_user.save()

        self.other_user = User.objects.create_user(
            username='otheruser',
            email='other@test.com',
            password='testpass123'
        )

        # Create test category
        self.category = Category.objects.create(name='Electronics')

        # Create active listing
        self.listing = AuctionListing.objects.create(
            owner=self.test_user,
            title='Test Listing',
            description='Test Description',
            starting_price=100.00,
            category=self.category
        )

        # Create inactive listing
        self.inactive_listing = AuctionListing.objects.create(
            owner=self.test_user,
            title='Inactive Listing',
            description='Test Description',
            starting_price=50.00,
            category=self.category,
            is_active=False
        )

    def test_notifications_view(self):
        """Test notifications view and marking as read"""
        self.client.login(username='testuser', password='testpass123')

        # Create a notification
        notification = Notification.objects.create(
            user=self.test_user,
            listing=self.listing,
            is_read=False
        )

        response = self.client.get(reverse('notifications'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'auctions/notifications.html')

        # Check if notification was marked as read
        notification.refresh_from_db()
        self.assertTrue(notification.is_read)

    def test_email_confirmation(self):
        """Test email confirmation process"""
        # Create unconfirmed user
        unconfirmed_user = User.objects.create_user(
            username='unconfirmed',
            email='unconfirmed@test.com',
            password='testpass123'
        )
        unconfirmed_user.email_confirmed = False
        unconfirmed_user.confirmation_token = 'test-token'
        unconfirmed_user.token_created_at = timezone.now()
        unconfirmed_user.save()

        # Test invalid token
        response = self.client.get(reverse('confirm_email', args=['invalid-token']))
        messages = list(get_messages(response.wsgi_request))
        self.assertIn('Invalid confirmation link', str(messages[0]))

        # Test valid token
        response = self.client.get(reverse('confirm_email', args=['test-token']))
        unconfirmed_user.refresh_from_db()
        self.assertTrue(unconfirmed_user.email_confirmed)

    def test_password_reset(self):
        """Test password reset functionality"""
        # Request password reset
        response = self.client.post(reverse('password_reset'), {
            'email': self.test_user.email
        })
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Password Reset Request', mail.outbox[0].subject)

        # Get token from user
        user = User.objects.get(email=self.test_user.email)
        token = user.confirmation_token

        # Test reset confirmation
        response = self.client.post(
            reverse('password_reset_confirm', args=[token]),
            {
                'password': 'newpassword123',
                'confirmation': 'newpassword123'
            }
        )
        self.assertRedirects(response, reverse('login'))

        # Verify new password works
        login_success = self.client.login(
            username=self.test_user.username,
            password='newpassword123'
        )
        self.assertTrue(login_success)

    def test_category_filtering(self):
        """Test category-based listing filtering"""
        # Create listings in different categories
        category2 = Category.objects.create(name='Fashion')
        listing2 = AuctionListing.objects.create(
            owner=self.test_user,
            title='Fashion Item',
            description='Fashion Description',
            starting_price=75.00,
            category=category2
        )

        # Test all categories
        response = self.client.get(reverse('index'))
        self.assertEqual(len(response.context['listings']), 2)

        # Test specific category
        response = self.client.get(f"{reverse('index')}?q={self.category.name}")
        self.assertEqual(len(response.context['listings']), 1)
        self.assertEqual(response.context['listings'][0].title, 'Test Listing')

    def test_bid_validation(self):
        """Test bid validation rules"""
        self.client.login(username='otheruser', password='testpass123')

        # Test bid lower than starting price
        response = self.client.post(
            reverse('listing_page', args=[self.listing.id]),
            {'amount': '50.00'}
        )
        messages = list(get_messages(response.wsgi_request))
        self.assertIn('must be higher than', str(messages[0]).lower())

        # Test valid bid
        response = self.client.post(
            reverse('listing_page', args=[self.listing.id]),
            {'amount': '150.00'}
        )
        self.assertTrue(Bid.objects.filter(listing=self.listing, amount=150.00).exists())

        # Test bid not high enough after previous bid
        response = self.client.post(
            reverse('listing_page', args=[self.listing.id]),
            {'amount': '149.00'}
        )
        messages = list(get_messages(response.wsgi_request))
        self.assertIn('must be higher than', str(messages[0]).lower())

    def test_auction_controls(self):
        """Test auction control functionality"""
        self.client.login(username='testuser', password='testpass123')

        # Test activating inactive auction
        response = self.client.post(reverse('auction_control', args=[self.inactive_listing.id]))
        self.inactive_listing.refresh_from_db()
        self.assertTrue(self.inactive_listing.is_active)

        # Test closing auction with no bids
        response = self.client.post(reverse('auction_control', args=[self.listing.id]))
        self.listing.refresh_from_db()
        self.assertFalse(self.listing.is_active)

        # Test closing auction with bids
        self.listing.is_active = True
        self.listing.save()
        Bid.objects.create(
            bidder=self.other_user,
            listing=self.listing,
            amount=150.00
        )

        response = self.client.post(reverse('auction_control', args=[self.listing.id]))
        self.listing.refresh_from_db()
        self.assertFalse(self.listing.is_active)
        self.assertEqual(self.listing.owner, self.other_user)
        self.assertTrue(Notification.objects.filter(user=self.other_user, listing=self.listing).exists())

    def test_rate_limiting(self):
        """Test bid rate limiting functionality"""
        from django.core.cache import cache
        cache.clear()

        # Create multiple listings to avoid self-bid issues
        listings = []
        for i in range(12):
            listing = AuctionListing.objects.create(
                owner=self.test_user,
                title=f'Rate Limit Test Listing {i}',
                description='Test Description',
                starting_price=50.00,
                category=self.category
            )
            listings.append(listing)

        # Login as other user
        self.client.login(username='otheruser', password='testpass123')

        # Make rapid bids on different listings
        all_messages = []
        for i, listing in enumerate(listings):
            response = self.client.post(
                reverse('listing_page', args=[listing.id]),
                {'amount': '100.00'}  # Higher than starting price
            )
            messages = [str(msg).lower() for msg in get_messages(response.wsgi_request)]
            all_messages.extend(messages)

        # Debug output
        print("Debug information:")
        print(f"Total messages: {len(all_messages)}")
        print("All messages received:", all_messages)
        print(f"Number of successful bids: {Bid.objects.filter(bidder=self.other_user).count()}")

        # Check if rate limit message appears
        rate_limit_found = any('too many bid attempts' in msg for msg in all_messages)
        self.assertTrue(
            rate_limit_found,
            f"Rate limit message not found in messages: {all_messages}"
        )

        # Verify the number of bids in the database
        total_bids = Bid.objects.filter(bidder=self.other_user).count()
        self.assertLessEqual(
            total_bids,
            10,
            f"Too many bids were placed: {total_bids} (should be ≤ 10)"
        )

    def test_index_view(self):
        """Test index view"""
        response = self.client.get(reverse('index'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'auctions/index.html')
        self.assertTrue('listings' in response.context)

    def test_register_view(self):
        """Test user registration"""
        # Test GET request
        response = self.client.get(reverse('register'))
        self.assertEqual(response.status_code, 200)

        # Test POST request with valid data
        response = self.client.post(reverse('register'), {
            'username': 'newuser',
            'email': 'new@test.com',
            'password': 'newpass123',
            'confirmation': 'newpass123'
        })
        self.assertEqual(response.status_code, 302)  # Redirect after successful registration
        self.assertTrue(self.User.objects.filter(username='newuser').exists())

    def test_login_view(self):
        """Test login functionality"""
        # Test GET request
        response = self.client.get(reverse('login'))
        self.assertEqual(response.status_code, 200)

        # Test successful login
        response = self.client.post(reverse('login'), {
            'username': 'testuser',
            'password': 'testpass123'
        })
        self.assertEqual(response.status_code, 302)  # Redirect after successful login

    def test_comment_functionality(self):
        """Test commenting on listings"""
        self.client.login(username='testuser', password='testpass123')

        response = self.client.post(
            reverse('listing_comment', args=[self.listing.id]),
            {'body': 'Test comment'}
        )
        self.assertTrue(Comment.objects.filter(
            listing=self.listing,
            body='Test comment'
        ).exists())


class ListingFormTest(TestCase):
    def setUp(self):
        """Set up data for form tests"""
        self.category = Category.objects.create(name='Electronics')
        # Create Other category
        Category.objects.create(name='Other')

    def test_listing_form_valid_data(self):
        """Test form with valid data"""
        form_data = {
            'title': 'Test Listing',
            'description': 'Test Description',
            'starting_price': 100.00,
            'image_url': 'https://example.com/image.jpg',
            'category': self.category.id,
            'is_active': True
        }
        form = ListingForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_listing_form_empty_data(self):
        """Test form with no data"""
        form = ListingForm(data={})
        self.assertFalse(form.is_valid())
        self.assertIn('title', form.errors)
        self.assertIn('starting_price', form.errors)

    def test_listing_form_invalid_price(self):
        """Test form with invalid price"""
        form_data = {
            'title': 'Test Listing',
            'description': 'Test Description',
            'starting_price': -100,  # Negative price
            'category': self.category.id,
            'is_active': True
        }
        form = ListingForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('starting_price', form.errors)

    def test_listing_form_optional_fields(self):
        """Test form with only required fields"""
        form_data = {
            'title': 'Test Listing',
            'starting_price': 100.00,
            'is_active': True
        }
        form = ListingForm(data=form_data)
        self.assertTrue(form.is_valid())


class BidFormTest(TestCase):
    def test_bid_form_valid_data(self):
        """Test form with valid bid amount"""
        form_data = {
            'amount': 100.00
        }
        form = BidForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_bid_form_empty_data(self):
        """Test form with no data"""
        form = BidForm(data={})
        self.assertFalse(form.is_valid())
        self.assertIn('amount', form.errors)

    def test_bid_form_invalid_amount(self):
        """Test form with invalid bid amount"""
        form_data = {
            'amount': -50  # Negative amount
        }
        form = BidForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('amount', form.errors)

    def test_bid_form_non_numeric_amount(self):
        """Test form with non-numeric bid amount"""
        form_data = {
            'amount': 'not a number'
        }
        form = BidForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('amount', form.errors)

    def test_bid_form_zero_amount(self):
        """Test form with zero bid amount"""
        form_data = {
            'amount': 0
        }
        form = BidForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('amount', form.errors)
