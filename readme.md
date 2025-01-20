# Auction Application

A Django-based web application for creating and managing online auctions with real-time bidding functionality.

## Features

### User Management
- User registration with email verification
- Secure password management with client-side validation
- Password reset functionality
- Custom user model with email confirmation

### Auction Features
- Create and manage auction listings
- Category-based organization
- Active/Inactive listing status
- Watchlist functionality
- Bidding system with rate limiting
- Comment section for each listing
- Real-time notifications for auction winners

### Security Features
- CSRF protection
- Password validation
- Rate limiting for bids (max 10 bids per minute)
- Prevention of self-bidding
- Email verification required for new accounts

## Technologies Used

- **Backend**: Django 5.1
- **Database**: SQLite3
- **Frontend**: HTML5, CSS3, JavaScript
- **Icons**: Font Awesome
- **Email**: Django's email backend (console for development)

## Setup and Installation

1. Clone the repository:
```bash
git clone https://github.com/Michael-Pytel/AuctionApp.git
cd AuctionApp
```

2. Create and activate a virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install required packages:
```bash
pip install -r requirements.txt
```

4. Set up the database (if you want a new one):
```bash
python manage.py makemigrations
python manage.py migrate
```

5. Create a superuser (admin) (if you don't use the db provided):
```bash
python manage.py createsuperuser
```

6. Run the development server:
```bash
python manage.py runserver
```

The application will be available at `http://localhost:8000`

7. Run tests (for a full coverage report run this):
```bash
coverage run --source='.' manage.py test auctions.tests
coverage report
```
without coverage
```bash
python manage.py test auctions.tests
```

## Project Structure

```
AuctionApp/
├── auctions/
│   ├── static/
│   │   ├── css/
│   │   └── js/
│   ├── templates/auctions/
│   │   ├── layout.html
│   │   ├── index.html
│   │   └── ...
│   ├── models.py
│   ├── views.py
│   ├── forms.py
│   └── urls.py
├── AuctionApp/
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
└── manage.py
```

## Models

### User
- Extended Django's AbstractUser
- Added email confirmation functionality
- Notification tracking

### AuctionListing
- Title, description, starting price
- Image URL support
- Category association
- Active/Inactive status
- Owner tracking

### Category
- Name
- Created/Updated timestamps

### Bid
- Bidder and listing association
- Amount
- Timestamp tracking

### Comment
- Commenter and listing association
- Comment body
- Timestamp tracking

### Watchlist
- User and listing association
- Timestamp tracking

### Notification
- User association
- Listing reference
- Read status

## Features in Detail

### Email Verification
- New users must verify their email before logging in
- Confirmation tokens expire after 24 hours
- Resend verification email functionality

### Password Requirements
- Minimum 8 characters
- At least one number
- At least one uppercase letter
- At least one lowercase letter
- At least one special character

### Auction Management
- Users can create new listings
- Set starting prices
- Add to categories
- Control listing status (active/inactive)
- Winner notification system

### Bidding System
- Rate limiting to prevent spam
- Automatic price validation
- Previous bid invalidation
- Prevents self-bidding

## Development Guidelines

1. Always run with DEBUG=True in development
2. Use Django's test server for development
3. Test email functionality using console backend
4. Follow PEP 8 style guidelines
5. Document new features

## Production Deployment Considerations

1. Set DEBUG=False
2. Configure proper email backend
3. Set up proper database (PostgreSQL recommended)
4. Configure ALLOWED_HOSTS
5. Set proper SECRET_KEY
6. Configure static files serving
7. Set up proper web server (e.g., Gunicorn)
8. Configure HTTPS

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

This project is licensed under the MIT License.
