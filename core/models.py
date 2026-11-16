from django.db import models


class Competition(models.Model):
    comp_id = models.IntegerField(unique=True)
    comp_name = models.CharField(max_length=200)
    match_format = models.CharField(max_length=20)  # T20, T20I
    season = models.CharField(max_length=10)

    def __str__(self):
        return f"{self.comp_name} ({self.season})"


class Team(models.Model):
    team_id = models.IntegerField(unique=True)
    team_name = models.CharField(max_length=100)

    def __str__(self):
        return self.team_name


class Player(models.Model):
    player_id = models.IntegerField(unique=True)
    player_name = models.CharField(max_length=100)
    is_uncapped = models.BooleanField(default=False, db_index=True)
    ipl_team = models.CharField(max_length=100, default='', blank=True)
    is_in_ipl_team = models.BooleanField(default=False, db_index=True)

    def __str__(self):
        status = "Uncapped" if self.is_uncapped else "Capped"
        team_str = f" [{self.ipl_team}]" if self.ipl_team else ""
        return f"{self.player_name}{team_str} ({status})"


class Match(models.Model):
    match_id = models.IntegerField(unique=True)
    competition = models.ForeignKey(Competition, on_delete=models.CASCADE, to_field='comp_id')
    match_number = models.IntegerField(null=True, blank=True)
    match_date = models.DateField(null=True, blank=True)
    stage = models.CharField(max_length=50, default='League')
    venue_country = models.CharField(max_length=100, default='')
    home_team = models.CharField(max_length=100, default='')
    away_team = models.CharField(max_length=100, default='')
    win_team_id = models.IntegerField(null=True, blank=True)
    result = models.TextField(default='')
    knock_out = models.BooleanField(default=False)

    def __str__(self):
        return f"Match {self.match_id}: {self.home_team} vs {self.away_team}"


class BallByBall(models.Model):
    match_id = models.IntegerField(db_index=True)
    innings = models.IntegerField()
    overid = models.IntegerField()
    over_ball_num = models.IntegerField()
    innings_ball_num = models.IntegerField()
    batting_team_id = models.IntegerField()
    bowling_team_id = models.IntegerField()
    striker_id = models.IntegerField(db_index=True)
    striker_name = models.CharField(max_length=100)
    non_striker_id = models.IntegerField(null=True, blank=True)
    non_striker_name = models.CharField(max_length=100, default='')
    bowler_id = models.IntegerField(db_index=True)
    bowler_name = models.CharField(max_length=100)
    batting_type = models.CharField(max_length=10, default='')
    bowling_type = models.CharField(max_length=50, default='')
    batting_order = models.IntegerField(null=True, blank=True)
    runs = models.IntegerField(default=0)
    is_four = models.BooleanField(default=False)
    is_six = models.BooleanField(default=False)
    is_wicket = models.BooleanField(default=False)
    dismissal_type = models.CharField(max_length=50, default='')
    dismissed_player_id = models.IntegerField(null=True, blank=True)
    extras_type = models.CharField(max_length=20, default='None')
    extras1_runs = models.IntegerField(default=0)
    extras_2_runs = models.IntegerField(default=0)
    pace_or_spin = models.CharField(max_length=10, default='')
    # Pressure computed fields (populated after load)
    pressure_score = models.FloatField(default=0.0)
    is_pressure = models.BooleanField(default=False)

    class Meta:
        indexes = [
            models.Index(fields=['match_id', 'innings', 'overid']),
            models.Index(fields=['striker_id', 'is_pressure']),
            models.Index(fields=['bowler_id', 'is_pressure']),
        ]


class PlayerPressureStats(models.Model):
    """Pre-computed pressure stats for each player (cached)."""
    player = models.OneToOneField(Player, on_delete=models.CASCADE, to_field='player_id')
    is_uncapped = models.BooleanField(default=False, db_index=True)
    ipl_team = models.CharField(max_length=100, default='', blank=True)
    is_in_ipl_team = models.BooleanField(default=False, db_index=True)
    
    # Batting
    total_balls_faced = models.IntegerField(default=0)
    pressure_balls_faced = models.IntegerField(default=0)
    total_runs_scored = models.IntegerField(default=0)
    pressure_runs_scored = models.IntegerField(default=0)
    total_fours = models.IntegerField(default=0)
    total_sixes = models.IntegerField(default=0)
    pressure_fours = models.IntegerField(default=0)
    pressure_sixes = models.IntegerField(default=0)
    total_dismissals = models.IntegerField(default=0)
    pressure_dismissals = models.IntegerField(default=0)
    normal_strike_rate = models.FloatField(null=True, blank=True)
    pressure_strike_rate = models.FloatField(null=True, blank=True)
    pressure_sr_ratio = models.FloatField(null=True, blank=True)
    batting_pressure_score = models.FloatField(null=True, blank=True)
    batting_matches = models.IntegerField(default=0)
    
    # Bowling
    total_balls_bowled = models.IntegerField(default=0)
    pressure_balls_bowled = models.IntegerField(default=0)
    total_runs_conceded = models.IntegerField(default=0)
    pressure_runs_conceded = models.IntegerField(default=0)
    total_wickets = models.IntegerField(default=0)
    pressure_wickets = models.IntegerField(default=0)
    normal_economy = models.FloatField(null=True, blank=True)
    pressure_economy = models.FloatField(null=True, blank=True)
    pressure_economy_ratio = models.FloatField(null=True, blank=True)
    bowling_pressure_score = models.FloatField(null=True, blank=True)
    bowling_matches = models.IntegerField(default=0)
    
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Stats for {self.player.player_name}"
