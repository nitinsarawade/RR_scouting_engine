"""
Metrics calculation module for SupeRR Selector (Rajasthan Royals Scouting Engine).
Computes batting and bowling pressure performance metrics and uncapped eligibility.
"""

from django.db.models import Sum

# Known senior international players who only played franchise / domestic in our 2022-2026 dataset
# These players represented their country at senior international level (Tests/ODIs/T20Is)
KNOWN_CAPPED_NAMES = {
    'Mahendra Singh Dhoni', 'Faf du Plessis', 'Sunil Narine', 'Ajinkya Rahane',
    'Shikhar Dhawan', 'Ambati Rayudu', 'Robin Uthappa', 'Dwayne Bravo',
    'Ishant Sharma', 'Amit Mishra', 'Piyush Chawla', 'Mohit Sharma',
    'Sandeep Sharma', 'Jaydev Unadkat', 'T Natarajan', 'Krunal Pandya',
    'Nitish Rana', 'Vijay Shankar', 'Manish Pandey', 'Wriddhiman Saha',
    'David Wiese', 'Joe Root', 'Andrew Tye', 'Navdeep Saini',
    'Chetan Sakariya', 'Rahul Chahar', 'Mayank Markande', 'Devdutt Padikkal',
    'Sarfaraz Khan', 'Rajat Patidar', 'Akash Deep', 'Varun Aaron',
    'Siddarth Kaul', 'Rishi Dhawan', 'Karn Sharma', 'Jayant Yadav',
    'KS Bharat', 'Mandeep Singh', 'Karun Nair', 'Kuldeep Sen',
    'Shahbaz Ahmed', 'Umran Malik', 'Shivam Mavi', 'Avesh Khan',
    'Prasidh Krishna', 'Washington Sundar', 'Deepak Hooda', 'Sanju Samson',
    'Suryakumar Yadav', 'Hardik Pandya', 'Rishabh Pant', 'Shubman Gill',
    'Yashasvi Jaiswal', 'Ruturaj Gaikwad', 'Ishan Kishan', 'Shreyas Iyer',
    'Venkatesh Iyer', 'Tilak Varma', 'Rinku Singh', 'Jitesh Sharma',
    'Mukesh Kumar', 'Arshdeep Singh', 'Ravi Bishnoi', 'Harshit Rana',
    'Nitish Kumar Reddy', 'Mayank Yadav', 'Abhishek Sharma', 'Dhruv Jurel'
}

_CAPPED_PLAYER_IDS = None


def get_capped_player_ids():
    """
    Returns set of player_ids that have played for international teams or T20I competitions.
    Cached in memory.
    """
    global _CAPPED_PLAYER_IDS
    if _CAPPED_PLAYER_IDS is not None:
        return _CAPPED_PLAYER_IDS

    from .models import Competition, Match, BallByBall
    
    # 1. Match format T20I competitions
    t20i_comp_ids = set(Competition.objects.filter(match_format='T20I').values_list('comp_id', flat=True))
    
    # 2. Match IDs of T20I competitions
    t20i_match_ids = set(Match.objects.filter(competition_id__in=t20i_comp_ids).values_list('match_id', flat=True))
    
    # 3. Striker IDs and Bowler IDs in those matches
    strikers = set(BallByBall.objects.filter(match_id__in=t20i_match_ids).values_list('striker_id', flat=True).distinct())
    bowlers = set(BallByBall.objects.filter(match_id__in=t20i_match_ids).values_list('bowler_id', flat=True).distinct())
    
    _CAPPED_PLAYER_IDS = strikers.union(bowlers)
    return _CAPPED_PLAYER_IDS


def determine_uncapped_status(player_id, player_name):
    """
    Determines whether a player is uncapped (never played senior international cricket for country).
    """
    if player_name in KNOWN_CAPPED_NAMES:
        return False
    capped_ids = get_capped_player_ids()
    if player_id in capped_ids:
        return False
    return True


def compute_player_pressure_stats(player_id):
    """
    Compute and save PlayerPressureStats for one player.
    """
    from .models import BallByBall, PlayerPressureStats, Player

    try:
        player = Player.objects.get(player_id=player_id)
    except Player.DoesNotExist:
        return None

    is_uncapped = determine_uncapped_status(player.player_id, player.player_name)
    if player.is_uncapped != is_uncapped:
        player.is_uncapped = is_uncapped
        player.save(update_fields=['is_uncapped'])

    # ---------------- BATTING STATS ----------------
    # Batting deliveries faced (excluding wides)
    batting_balls = BallByBall.objects.filter(
        striker_id=player_id
    ).exclude(extras_type='wide')

    batting_matches = batting_balls.values('match_id').distinct().count()
    total_balls_faced = batting_balls.count()
    total_runs_scored = batting_balls.aggregate(s=Sum('runs'))['s'] or 0
    total_fours = batting_balls.filter(is_four=True).count()
    total_sixes = batting_balls.filter(is_six=True).count()
    total_dismissals = batting_balls.filter(is_wicket=True).count()

    pressure_batting = batting_balls.filter(is_pressure=True)
    pressure_balls_faced = pressure_batting.count()
    pressure_runs_scored = pressure_batting.aggregate(s=Sum('runs'))['s'] or 0
    pressure_fours = pressure_batting.filter(is_four=True).count()
    pressure_sixes = pressure_batting.filter(is_six=True).count()
    pressure_dismissals = pressure_batting.filter(is_wicket=True).count()

    normal_strike_rate = round((total_runs_scored / total_balls_faced) * 100.0, 2) if total_balls_faced > 0 else None
    pressure_strike_rate = round((pressure_runs_scored / pressure_balls_faced) * 100.0, 2) if pressure_balls_faced > 0 else None
    
    if normal_strike_rate and pressure_strike_rate and normal_strike_rate > 0:
        pressure_sr_ratio = round(pressure_strike_rate / normal_strike_rate, 3)
    else:
        pressure_sr_ratio = None

    # Batting qualification: >= 40 pressure balls faced and >= 5 matches
    batting_pressure_score = None
    if pressure_balls_faced >= 40 and batting_matches >= 5 and normal_strike_rate and pressure_sr_ratio:
        normal_boundary_rate = (total_fours + total_sixes) / total_balls_faced if total_balls_faced > 0 else 0.0
        pressure_boundary_rate = (pressure_fours + pressure_sixes) / pressure_balls_faced if pressure_balls_faced > 0 else 0.0
        boundary_rate_ratio = pressure_boundary_rate / max(0.01, normal_boundary_rate)
        sample_weight = min(1.0, pressure_balls_faced / 150.0)
        
        raw_bat_score = (pressure_sr_ratio * 0.40) + (boundary_rate_ratio * 0.30) + (sample_weight * 0.30)
        batting_pressure_score = round(raw_bat_score * 70.0, 1)

    # ---------------- BOWLING STATS ----------------
    bowling_balls = BallByBall.objects.filter(bowler_id=player_id)
    bowling_matches = bowling_balls.values('match_id').distinct().count()

    # Legal balls (not wide and not Overstep)
    legal_balls = bowling_balls.exclude(extras_type__in=['wide', 'Overstep'])
    total_balls_bowled = legal_balls.count()

    # Runs conceded by bowler (exclude byes/legbyes; include extras penalty for wide/no ball)
    bowler_scored_runs = bowling_balls.exclude(extras_type__in=['byes', 'legbyes']).aggregate(s=Sum('runs'))['s'] or 0
    bowler_penalty_runs = bowling_balls.filter(extras_type__in=['wide', 'Overstep']).count()
    total_runs_conceded = bowler_scored_runs + bowler_penalty_runs

    # Bowler wickets (exclude runouts and retired out)
    total_wickets = bowling_balls.filter(is_wicket=True).exclude(dismissal_type__in=['RunOut', 'Retire Out']).count()

    # Pressure bowling
    pressure_bowling = bowling_balls.filter(is_pressure=True)
    pressure_balls_bowled = pressure_bowling.exclude(extras_type__in=['wide', 'Overstep']).count()
    pressure_scored_runs = pressure_bowling.exclude(extras_type__in=['byes', 'legbyes']).aggregate(s=Sum('runs'))['s'] or 0
    pressure_penalty_runs = pressure_bowling.filter(extras_type__in=['wide', 'Overstep']).count()
    pressure_runs_conceded = pressure_scored_runs + pressure_penalty_runs
    pressure_wickets = pressure_bowling.filter(is_wicket=True).exclude(dismissal_type__in=['RunOut', 'Retire Out']).count()

    normal_economy = round(total_runs_conceded / (total_balls_bowled / 6.0), 2) if total_balls_bowled > 0 else None
    pressure_economy = round(pressure_runs_conceded / (pressure_balls_bowled / 6.0), 2) if pressure_balls_bowled > 0 else None

    if normal_economy and pressure_economy and pressure_economy > 0:
        pressure_economy_ratio = round(normal_economy / pressure_economy, 3)
    else:
        pressure_economy_ratio = None

    # Bowling qualification: >= 60 pressure balls (10 overs) and >= 5 matches
    bowling_pressure_score = None
    if pressure_balls_bowled >= 60 and bowling_matches >= 5 and normal_economy and pressure_economy_ratio and total_wickets > 0:
        p_w_rate = pressure_wickets / pressure_balls_bowled if pressure_balls_bowled > 0 else 0.0
        n_w_rate = total_wickets / total_balls_bowled if total_balls_bowled > 0 else 0.001
        wicket_impact = p_w_rate / max(0.001, n_w_rate)
        consistency = min(1.0, pressure_balls_bowled / 200.0)

        raw_bowl_score = (pressure_economy_ratio * 0.45) + (wicket_impact * 0.35) + (consistency * 0.20)
        bowling_pressure_score = round(raw_bowl_score * 70.0, 1)

    # Save to PlayerPressureStats
    stats, _ = PlayerPressureStats.objects.update_or_create(
        player=player,
        defaults={
            'is_uncapped': is_uncapped,
            'total_balls_faced': total_balls_faced,
            'pressure_balls_faced': pressure_balls_faced,
            'total_runs_scored': total_runs_scored,
            'pressure_runs_scored': pressure_runs_scored,
            'total_fours': total_fours,
            'total_sixes': total_sixes,
            'pressure_fours': pressure_fours,
            'pressure_sixes': pressure_sixes,
            'total_dismissals': total_dismissals,
            'pressure_dismissals': pressure_dismissals,
            'normal_strike_rate': normal_strike_rate,
            'pressure_strike_rate': pressure_strike_rate,
            'pressure_sr_ratio': pressure_sr_ratio,
            'batting_pressure_score': batting_pressure_score,
            'batting_matches': batting_matches,
            'total_balls_bowled': total_balls_bowled,
            'pressure_balls_bowled': pressure_balls_bowled,
            'total_runs_conceded': total_runs_conceded,
            'pressure_runs_conceded': pressure_runs_conceded,
            'total_wickets': total_wickets,
            'pressure_wickets': pressure_wickets,
            'normal_economy': normal_economy,
            'pressure_economy': pressure_economy,
            'pressure_economy_ratio': pressure_economy_ratio,
            'bowling_pressure_score': bowling_pressure_score,
            'bowling_matches': bowling_matches,
        }
    )
    return stats
