from django.urls import path
from . import views
from django.views.generic import TemplateView

urlpatterns = [ 
    path('', views.LoginView.as_view(), name='login'),
    
    path('leagues', views.LeagueView.as_view(), name='leagues'),

    # Authorisation and Profile
    path('signup', views.SignUpView.as_view(), name='signup'),
    path('login', views.LoginView.as_view(), name='login'),
    path('accounts/login', views.LoginView.as_view(), name='mixinlogin'),
    path('logout', views.LogOutUser, name='logout'),
    path('profile', views.ProfileView.as_view(), name='profile'),

    # New games and invitations
    path('new_game', views.CreateGameView.as_view(), name='new_game'),
    path('invite/<int:pk>', views.InviteView.as_view(), name='invite'), # Invites are always related to a specific game

    # Games and accept and decline invitations
    path('games', views.GamesView.as_view(), name='games'),
    path('games/<int:pk>/accept', views.GameAccept.as_view(), name='game_accept'),
    path('games/<int:pk>/decline', views.GameDecline.as_view(), name='game_decline'),
    path('gamedetail/<int:pk>', views.GameDetail.as_view(), name='gamedetail'),

    # Ranking information
    path('ranking/<int:pk>', views.RankingView.as_view(), name='ranking'),
    path('ranking/<int:game_id>/<int:player_id>/detail', views.RankingDetailView.as_view(), name='ranking_detail'),

    # Today, refresh and fixture info
    path('today', views.TodayView.as_view(), name='today'), 
    path('today/refresh', views.TodayRefreshView.as_view(), name='refresh_today'),
    path('info/fixture/<int:game_id>/<int:fixture_id>', views.InfoFixtureView.as_view(), name='info_fixture'),

    # Tipp
    path('tipp/<int:game_id>/<int:fixture_id>', views.TippCreateView.as_view(), name='tipp_create'),
    path('tipp/<int:tipp_id>/update', views.TippUpdateView.as_view(), name='tipp_update'),
    path('tipp/<int:tipp_id>/delete', views.TippDeleteView.as_view(), name='tipp_delete'),

    # Tests
    path('test_api', TemplateView.as_view(template_name='game/test_api.html'), name='test_api'),
    path('test_days', views.TestDay, name='test_days'),
#    path('profile', views.ProfileView.as_view(), name='profile'),
]