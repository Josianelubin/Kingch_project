from django.urls import path
from . import views

urlpatterns = [
    path('',                               views.home_view,         name='home'),
    path('login/',                         views.login_view,        name='login'),
    path('register/',                      views.register_view,     name='register'),
    path('logout/',                        views.logout_view,       name='logout'),
    path('dashboard/',                     views.dashboard_view,    name='dashboard'),
    path('quiz/<int:question_id>/',        views.quiz_view,         name='quiz'),
    path('quiz/<int:question_id>/result/', views.quiz_result_view,  name='quiz_result'),
    # IMPORTANT: profile/edit/ MUST come before profile/<str:username>/
    # otherwise Django matches 'edit' as a username string
    path('profile/',                       views.profile_view,      name='profile'),
    path('edit_profile/',                  views.edit_profile_view, name='edit_profile'),
    path('profile/<str:username>/',        views.profile_view,      name='profile_detail'),
    path('parrainage/',                    views.parrainage_view,   name='parrainage'),
    path('certificats/',                   views.certificats_view,  name='certificats'),
    path('settings/',                      views.settings_view,     name='settings'),
    path('notifications/',                 views.notifications_view,name='notifications'),
    path('leaderboard/',                   views.leaderboard_view,  name='leaderboard'),
    path('createur/',                      views.createur_view,     name='createur'),
]
