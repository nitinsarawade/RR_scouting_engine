from django.urls import path
from . import views

urlpatterns = [
    path('overview/', views.overview_view, name='overview'),
    path('players/', views.players_list_view, name='players_list'),
    path('players/<int:player_id>/', views.player_detail_view, name='player_detail'),
    path('players/<int:player_id>/matches/', views.player_matches_view, name='player_matches'),
    path('competitions/', views.competitions_list_view, name='competitions'),
    path('leaderboard/batting/', views.leaderboard_batting_view, name='leaderboard_batting'),
    path('leaderboard/bowling/', views.leaderboard_bowling_view, name='leaderboard_bowling'),
    path('methodology/', views.methodology_view, name='methodology'),
    path('compare/', views.compare_players_view, name='compare'),
]
