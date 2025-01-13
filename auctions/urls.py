from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("login", views.login_view, name="login"),
    path("logout", views.logout_view, name="logout"),
    path("register", views.register, name="register"),
    path("Notifications", views.Notifications, name="Notifications"),
    path("Profile", views.Profile , name="Profile"),

    path("create-listing", views.CreateListing, name="CreateListing"),
    path("watchlistPage", views.watchlistPage, name="watchlistPage"),

    path("listing-page/<str:pk>/", views.listingPage, name="listingPage"),
    path("listing-comment/<str:pk>/", views.listingComment, name="listingComment"),
    path("add-to-Watchlist/<str:pk>", views.addWatchlist, name="addWatchlist"),
    path("remove-from-Watchlist/<str:pk>", views.removeWatchlist, name="removeWatchlist"),
    path("auction-control/<str:pk>", views.AuctionControl, name="AuctionControl"),
    path('confirm-email/<str:token>', views.confirm_email, name='confirm_email'),
    path('password-reset/', views.password_reset_request, name='password_reset'),
    path('password-reset/<str:token>', views.password_reset_confirm, name='password_reset_confirm'),
]


