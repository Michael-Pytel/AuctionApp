from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("login", views.login_view, name="login"),
    path("logout", views.logout_view, name="logout"),
    path("register", views.register, name="register"),
    path("notifications", views.notifications, name="notifications"),
    path("profile", views.profile, name="profile"),

    path("create-listing", views.create_listing, name="create_listing"),
    path("watchlist", views.watchlist_page, name="watchlist"),

    path("listing-page/<str:listing_id>/", views.listing_page, name="listing_page"),
    path("listing-comment/<str:listing_id>/", views.listing_comment, name="listing_comment"),
    path("add-to-watchlist/<str:listing_id>", views.add_watchlist, name="add_watchlist"),
    path("remove-from-watchlist/<str:listing_id>", views.remove_watchlist, name="remove_watchlist"),
    path("auction-control/<str:listing_id>", views.auction_control, name="auction_control"),
    path('confirm-email/<str:token>', views.confirm_email, name='confirm_email'),
    path('password-reset/', views.password_reset_request, name='password_reset'),
    path('password-reset/<str:token>', views.password_reset_confirm, name='password_reset_confirm'),
]


