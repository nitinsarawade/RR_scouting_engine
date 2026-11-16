from django.contrib import admin
from .models import Competition, Team, Player, Match, BallByBall, PlayerPressureStats

@admin.register(Competition)
class CompetitionAdmin(admin.ModelAdmin):
    list_display = ('comp_id', 'comp_name', 'match_format', 'season')
    search_fields = ('comp_name', 'season')

@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ('team_id', 'team_name')
    search_fields = ('team_name',)

@admin.register(Player)
class PlayerAdmin(admin.ModelAdmin):
    list_display = ('player_id', 'player_name')
    search_fields = ('player_name',)

@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    list_display = ('match_id', 'competition', 'stage', 'home_team', 'away_team', 'match_date', 'knock_out')
    list_filter = ('knock_out', 'stage')
    search_fields = ('home_team', 'away_team', 'result')

@admin.register(PlayerPressureStats)
class PlayerPressureStatsAdmin(admin.ModelAdmin):
    list_display = ('player', 'batting_pressure_score', 'pressure_strike_rate', 'bowling_pressure_score', 'pressure_economy')
    search_fields = ('player__player_name',)
