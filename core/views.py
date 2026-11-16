from django.shortcuts import render
from django.db.models import Q, F, Sum, Count
from django.core.paginator import Paginator
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import Competition, Team, Player, Match, BallByBall, PlayerPressureStats
from .pressure import IS_PRESSURE_THRESHOLD
from .metrics import determine_uncapped_status

IPL_TEAMS_LIST = [
    'Chennai Super Kings', 'Mumbai Indians', 'Rajasthan Royals', 'Punjab Kings',
    'Royal Challengers Bengaluru', 'Delhi Capitals', 'Kolkata Knight Riders',
    'Sunrisers Hyderabad', 'Gujarat Titans', 'Lucknow Super Giants'
]


@api_view(['GET'])
def overview_view(request):
    """
    Returns summary metrics, Top 10 uncapped prospects (all & non-IPL), and Top 10 global leaders.
    """
    total_players = Player.objects.count()
    total_uncapped_players = PlayerPressureStats.objects.filter(is_uncapped=True).count()
    total_matches = Match.objects.count()
    total_deliveries = BallByBall.objects.count()
    pressure_deliveries = BallByBall.objects.filter(is_pressure=True).count()

    def serialize_batter(rank, stat):
        return {
            'rank': rank,
            'player_id': stat.player.player_id,
            'player_name': stat.player.player_name,
            'is_uncapped': stat.is_uncapped,
            'ipl_team': stat.ipl_team or 'Uncontracted / Domestic',
            'is_in_ipl_team': stat.is_in_ipl_team,
            'batting_pressure_score': stat.batting_pressure_score,
            'normal_strike_rate': stat.normal_strike_rate,
            'pressure_strike_rate': stat.pressure_strike_rate,
            'pressure_sr_ratio': stat.pressure_sr_ratio,
            'total_runs': stat.total_runs_scored,
            'pressure_runs': stat.pressure_runs_scored,
            'pressure_balls': stat.pressure_balls_faced,
            'pressure_fours': stat.pressure_fours,
            'pressure_sixes': stat.pressure_sixes,
            'matches': stat.batting_matches,
        }

    def serialize_bowler(rank, stat):
        return {
            'rank': rank,
            'player_id': stat.player.player_id,
            'player_name': stat.player.player_name,
            'is_uncapped': stat.is_uncapped,
            'ipl_team': stat.ipl_team or 'Uncontracted / Domestic',
            'is_in_ipl_team': stat.is_in_ipl_team,
            'bowling_pressure_score': stat.bowling_pressure_score,
            'normal_economy': stat.normal_economy,
            'pressure_economy': stat.pressure_economy,
            'pressure_economy_ratio': stat.pressure_economy_ratio,
            'total_wickets': stat.total_wickets,
            'pressure_wickets': stat.pressure_wickets,
            'pressure_overs': round(stat.pressure_balls_bowled / 6.0, 1),
            'pressure_balls': stat.pressure_balls_bowled,
            'matches': stat.bowling_matches,
        }

    # Top 10 Uncapped Batters (All Uncapped)
    top_uncapped_batters_qs = PlayerPressureStats.objects.filter(
        batting_pressure_score__isnull=False,
        is_uncapped=True
    ).select_related('player').order_by('-batting_pressure_score')[:10]
    top_uncapped_batters = [serialize_batter(i + 1, s) for i, s in enumerate(top_uncapped_batters_qs)]

    # Top 10 Uncapped Bowlers (All Uncapped)
    top_uncapped_bowlers_qs = PlayerPressureStats.objects.filter(
        bowling_pressure_score__isnull=False,
        is_uncapped=True
    ).select_related('player').order_by('-bowling_pressure_score')[:10]
    top_uncapped_bowlers = [serialize_bowler(i + 1, s) for i, s in enumerate(top_uncapped_bowlers_qs)]

    # Top 10 Non-IPL Batters (Pure Uncontracted Domestic Prospects)
    top_non_ipl_batters_qs = PlayerPressureStats.objects.filter(
        batting_pressure_score__isnull=False,
        is_uncapped=True,
        is_in_ipl_team=False
    ).select_related('player').order_by('-batting_pressure_score')[:10]
    top_non_ipl_batters = [serialize_batter(i + 1, s) for i, s in enumerate(top_non_ipl_batters_qs)]

    # Top 10 Non-IPL Bowlers (Pure Uncontracted Domestic Prospects)
    top_non_ipl_bowlers_qs = PlayerPressureStats.objects.filter(
        bowling_pressure_score__isnull=False,
        is_uncapped=True,
        is_in_ipl_team=False
    ).select_related('player').order_by('-bowling_pressure_score')[:10]
    top_non_ipl_bowlers = [serialize_bowler(i + 1, s) for i, s in enumerate(top_non_ipl_bowlers_qs)]

    # Top 10 All Batters
    top_batters_qs = PlayerPressureStats.objects.filter(
        batting_pressure_score__isnull=False
    ).select_related('player').order_by('-batting_pressure_score')[:10]
    top_batters = [serialize_batter(i + 1, s) for i, s in enumerate(top_batters_qs)]

    # Top 10 All Bowlers
    top_bowlers_qs = PlayerPressureStats.objects.filter(
        bowling_pressure_score__isnull=False
    ).select_related('player').order_by('-bowling_pressure_score')[:10]
    top_bowlers = [serialize_bowler(i + 1, s) for i, s in enumerate(top_bowlers_qs)]

    return Response({
        'total_players': total_players,
        'total_uncapped_players': total_uncapped_players,
        'total_matches': total_matches,
        'total_deliveries': total_deliveries,
        'pressure_deliveries': pressure_deliveries,
        'ipl_teams': IPL_TEAMS_LIST,
        'top_uncapped_batters': top_uncapped_batters,
        'top_uncapped_bowlers': top_uncapped_bowlers,
        'top_non_ipl_batters': top_non_ipl_batters,
        'top_non_ipl_bowlers': top_non_ipl_bowlers,
        'top_batters': top_batters,
        'top_bowlers': top_bowlers,
    })


@api_view(['GET'])
def leaderboard_batting_view(request):
    """
    Returns top batters sorted by batting_pressure_score.
    Supports ?comp_id=&season=&limit=&uncapped=&exclude_ipl=&ipl_team=
    """
    comp_id = request.GET.get('comp_id')
    season = request.GET.get('season')
    limit = int(request.GET.get('limit', 25))
    uncapped = request.GET.get('uncapped', '').lower() in ['1', 'true', 'yes']
    exclude_ipl = request.GET.get('exclude_ipl', '').lower() in ['1', 'true', 'yes']
    ipl_team = request.GET.get('ipl_team', '').strip()

    # Pre-computed path (fast):
    if not comp_id and not season:
        qs = PlayerPressureStats.objects.filter(
            batting_pressure_score__isnull=False
        )
        if uncapped:
            qs = qs.filter(is_uncapped=True)
        if exclude_ipl:
            qs = qs.filter(is_in_ipl_team=False)
        if ipl_team:
            qs = qs.filter(ipl_team=ipl_team)

        qs = qs.select_related('player').order_by('-batting_pressure_score')[:limit]

        data = [
            {
                'rank': idx + 1,
                'player_id': s.player.player_id,
                'player_name': s.player.player_name,
                'is_uncapped': s.is_uncapped,
                'ipl_team': s.ipl_team or 'Uncontracted / Domestic',
                'is_in_ipl_team': s.is_in_ipl_team,
                'batting_pressure_score': s.batting_pressure_score,
                'pressure_strike_rate': s.pressure_strike_rate,
                'normal_strike_rate': s.normal_strike_rate,
                'pressure_sr_ratio': s.pressure_sr_ratio,
                'pressure_runs': s.pressure_runs_scored,
                'pressure_balls': s.pressure_balls_faced,
                'total_runs': s.total_runs_scored,
                'total_balls': s.total_balls_faced,
                'pressure_boundaries': s.pressure_fours + s.pressure_sixes,
                'matches': s.batting_matches,
            }
            for idx, s in enumerate(qs)
        ]
        return Response({'results': data, 'filtered': False, 'uncapped_only': uncapped, 'exclude_ipl': exclude_ipl})

    # Dynamic filtered path:
    match_qs = Match.objects.all()
    if comp_id:
        match_qs = match_qs.filter(competition_id=comp_id)
    if season:
        match_qs = match_qs.filter(competition__season=season)
    match_ids = list(match_qs.values_list('match_id', flat=True))

    balls = BallByBall.objects.filter(match_id__in=match_ids).exclude(extras_type='wide')
    
    striker_agg = balls.values('striker_id', 'striker_name').annotate(
        total_balls=Count('id'),
        total_runs=Sum('runs'),
        total_fours=Count('id', filter=Q(is_four=True)),
        total_sixes=Count('id', filter=Q(is_six=True)),
        p_balls=Count('id', filter=Q(is_pressure=True)),
        p_runs=Sum('runs', filter=Q(is_pressure=True)),
        p_fours=Count('id', filter=Q(is_pressure=True, is_four=True)),
        p_sixes=Count('id', filter=Q(is_pressure=True, is_six=True)),
        matches=Count('match_id', distinct=True)
    ).filter(p_balls__gte=15)

    player_dict = {p.player_id: p for p in Player.objects.all()}

    results = []
    for s in striker_agg:
        pid = s['striker_id']
        p_obj = player_dict.get(pid)
        is_unc = p_obj.is_uncapped if p_obj else determine_uncapped_status(pid, s['striker_name'])
        team_name = p_obj.ipl_team if p_obj else 'Uncontracted / Domestic'
        in_ipl = p_obj.is_in_ipl_team if p_obj else False

        if uncapped and not is_unc:
            continue
        if exclude_ipl and in_ipl:
            continue
        if ipl_team and team_name != ipl_team:
            continue

        t_b = s['total_balls'] or 0
        t_r = s['total_runs'] or 0
        p_b = s['p_balls'] or 0
        p_r = s['p_runs'] or 0
        p_f = s['p_fours'] or 0
        p_s = s['p_sixes'] or 0
        t_f = s['total_fours'] or 0
        t_s = s['total_sixes'] or 0

        norm_sr = round((t_r / t_b) * 100.0, 2) if t_b > 0 else 0
        pres_sr = round((p_r / p_b) * 100.0, 2) if p_b > 0 else 0
        sr_ratio = round(pres_sr / norm_sr, 3) if norm_sr > 0 else 1.0

        n_br = (t_f + t_s) / t_b if t_b > 0 else 0.0
        p_br = (p_f + p_s) / p_b if p_b > 0 else 0.0
        br_ratio = p_br / max(0.01, n_br)
        sample_w = min(1.0, p_b / 100.0)

        raw = (sr_ratio * 0.40) + (br_ratio * 0.30) + (sample_w * 0.30)
        score = round(raw * 70.0, 1)

        results.append({
            'player_id': pid,
            'player_name': s['striker_name'],
            'is_uncapped': is_unc,
            'ipl_team': team_name,
            'is_in_ipl_team': in_ipl,
            'batting_pressure_score': score,
            'pressure_strike_rate': pres_sr,
            'normal_strike_rate': norm_sr,
            'pressure_sr_ratio': sr_ratio,
            'pressure_runs': p_r,
            'pressure_balls': p_b,
            'total_runs': t_r,
            'total_balls': t_b,
            'pressure_boundaries': p_f + p_s,
            'matches': s['matches'],
        })

    results.sort(key=lambda x: x['batting_pressure_score'], reverse=True)
    for idx, r in enumerate(results[:limit]):
        r['rank'] = idx + 1

    return Response({'results': results[:limit], 'filtered': True, 'uncapped_only': uncapped, 'exclude_ipl': exclude_ipl})


@api_view(['GET'])
def leaderboard_bowling_view(request):
    """
    Returns top bowlers sorted by bowling_pressure_score.
    Supports ?comp_id=&season=&limit=&uncapped=&exclude_ipl=&ipl_team=
    """
    comp_id = request.GET.get('comp_id')
    season = request.GET.get('season')
    limit = int(request.GET.get('limit', 25))
    uncapped = request.GET.get('uncapped', '').lower() in ['1', 'true', 'yes']
    exclude_ipl = request.GET.get('exclude_ipl', '').lower() in ['1', 'true', 'yes']
    ipl_team = request.GET.get('ipl_team', '').strip()

    # Pre-computed path (fast):
    if not comp_id and not season:
        qs = PlayerPressureStats.objects.filter(
            bowling_pressure_score__isnull=False
        )
        if uncapped:
            qs = qs.filter(is_uncapped=True)
        if exclude_ipl:
            qs = qs.filter(is_in_ipl_team=False)
        if ipl_team:
            qs = qs.filter(ipl_team=ipl_team)

        qs = qs.select_related('player').order_by('-bowling_pressure_score')[:limit]

        data = [
            {
                'rank': idx + 1,
                'player_id': s.player.player_id,
                'player_name': s.player.player_name,
                'is_uncapped': s.is_uncapped,
                'ipl_team': s.ipl_team or 'Uncontracted / Domestic',
                'is_in_ipl_team': s.is_in_ipl_team,
                'bowling_pressure_score': s.bowling_pressure_score,
                'pressure_economy': s.pressure_economy,
                'normal_economy': s.normal_economy,
                'pressure_economy_ratio': s.pressure_economy_ratio,
                'pressure_wickets': s.pressure_wickets,
                'total_wickets': s.total_wickets,
                'pressure_overs': round(s.pressure_balls_bowled / 6.0, 1),
                'pressure_balls': s.pressure_balls_bowled,
                'matches': s.bowling_matches,
            }
            for idx, s in enumerate(qs)
        ]
        return Response({'results': data, 'filtered': False, 'uncapped_only': uncapped, 'exclude_ipl': exclude_ipl})

    # Dynamic filtered path:
    match_qs = Match.objects.all()
    if comp_id:
        match_qs = match_qs.filter(competition_id=comp_id)
    if season:
        match_qs = match_qs.filter(competition__season=season)
    match_ids = list(match_qs.values_list('match_id', flat=True))

    balls = BallByBall.objects.filter(match_id__in=match_ids)
    
    bowler_agg = balls.values('bowler_id', 'bowler_name').annotate(
        total_balls=Count('id', filter=~Q(extras_type__in=['wide', 'Overstep'])),
        total_runs=Sum('runs', filter=~Q(extras_type__in=['byes', 'legbyes'])) + Count('id', filter=Q(extras_type__in=['wide', 'Overstep'])),
        total_w=Count('id', filter=Q(is_wicket=True) & ~Q(dismissal_type__in=['RunOut', 'Retire Out'])),
        p_balls=Count('id', filter=Q(is_pressure=True) & ~Q(extras_type__in=['wide', 'Overstep'])),
        p_runs=Sum('runs', filter=Q(is_pressure=True) & ~Q(extras_type__in=['byes', 'legbyes'])) + Count('id', filter=Q(is_pressure=True, extras_type__in=['wide', 'Overstep'])),
        p_w=Count('id', filter=Q(is_pressure=True, is_wicket=True) & ~Q(dismissal_type__in=['RunOut', 'Retire Out'])),
        matches=Count('match_id', distinct=True)
    ).filter(p_balls__gte=25)

    player_dict = {p.player_id: p for p in Player.objects.all()}

    results = []
    for b in bowler_agg:
        pid = b['bowler_id']
        p_obj = player_dict.get(pid)
        is_unc = p_obj.is_uncapped if p_obj else determine_uncapped_status(pid, b['bowler_name'])
        team_name = p_obj.ipl_team if p_obj else 'Uncontracted / Domestic'
        in_ipl = p_obj.is_in_ipl_team if p_obj else False

        if uncapped and not is_unc:
            continue
        if exclude_ipl and in_ipl:
            continue
        if ipl_team and team_name != ipl_team:
            continue

        t_b = b['total_balls'] or 0
        t_r = b['total_runs'] or 0
        t_w = b['total_w'] or 0
        p_b = b['p_balls'] or 0
        p_r = b['p_runs'] or 0
        p_w = b['p_w'] or 0

        norm_econ = round(t_r / (t_b / 6.0), 2) if t_b > 0 else 0.0
        pres_econ = round(p_r / (p_b / 6.0), 2) if p_b > 0 else 0.0
        econ_ratio = round(norm_econ / pres_econ, 3) if pres_econ > 0 else 1.0

        p_w_rate = p_w / p_b if p_b > 0 else 0.0
        n_w_rate = t_w / t_b if t_b > 0 else 0.001
        w_impact = p_w_rate / max(0.001, n_w_rate)
        cons = min(1.0, p_b / 120.0)

        raw = (econ_ratio * 0.45) + (w_impact * 0.35) + (cons * 0.20)
        score = round(raw * 70.0, 1)

        results.append({
            'player_id': pid,
            'player_name': b['bowler_name'],
            'is_uncapped': is_unc,
            'ipl_team': team_name,
            'is_in_ipl_team': in_ipl,
            'bowling_pressure_score': score,
            'pressure_economy': pres_econ,
            'normal_economy': norm_econ,
            'pressure_economy_ratio': econ_ratio,
            'pressure_wickets': p_w,
            'total_wickets': t_w,
            'pressure_overs': round(p_b / 6.0, 1),
            'pressure_balls': p_b,
            'matches': b['matches'],
        })

    results.sort(key=lambda x: x['bowling_pressure_score'], reverse=True)
    for idx, r in enumerate(results[:limit]):
        r['rank'] = idx + 1

    return Response({'results': results[:limit], 'filtered': True, 'uncapped_only': uncapped, 'exclude_ipl': exclude_ipl})


@api_view(['GET'])
def players_list_view(request):
    """
    Search and filter players with pagination.
    Params: q, role, min_matches, uncapped, exclude_ipl, ipl_team, page, page_size
    """
    q = request.GET.get('q', '').strip()
    role = request.GET.get('role', '').strip().lower()
    min_matches = int(request.GET.get('min_matches', 0))
    uncapped = request.GET.get('uncapped', '').lower() in ['1', 'true', 'yes']
    exclude_ipl = request.GET.get('exclude_ipl', '').lower() in ['1', 'true', 'yes']
    ipl_team = request.GET.get('ipl_team', '').strip()
    page = int(request.GET.get('page', 1))
    page_size = int(request.GET.get('page_size', 25))

    stats_qs = PlayerPressureStats.objects.select_related('player')

    if uncapped:
        stats_qs = stats_qs.filter(is_uncapped=True)
    if exclude_ipl:
        stats_qs = stats_qs.filter(is_in_ipl_team=False)
    if ipl_team:
        stats_qs = stats_qs.filter(ipl_team=ipl_team)

    if q:
        stats_qs = stats_qs.filter(player__player_name__icontains=q)

    if role == 'batting':
        stats_qs = stats_qs.filter(batting_pressure_score__isnull=False).order_by('-batting_pressure_score')
    elif role == 'bowling':
        stats_qs = stats_qs.filter(bowling_pressure_score__isnull=False).order_by('-bowling_pressure_score')
    elif role == 'allrounder':
        stats_qs = stats_qs.filter(
            batting_pressure_score__isnull=False,
            bowling_pressure_score__isnull=False
        ).order_by('-batting_pressure_score')
    else:
        stats_qs = stats_qs.order_by('player__player_name')

    if min_matches > 0:
        stats_qs = stats_qs.filter(Q(batting_matches__gte=min_matches) | Q(bowling_matches__gte=min_matches))

    paginator = Paginator(stats_qs, page_size)
    page_obj = paginator.get_page(page)

    results = []
    for s in page_obj:
        results.append({
            'player_id': s.player.player_id,
            'player_name': s.player.player_name,
            'is_uncapped': s.is_uncapped,
            'ipl_team': s.ipl_team or 'Uncontracted / Domestic',
            'is_in_ipl_team': s.is_in_ipl_team,
            'batting_score': s.batting_pressure_score,
            'pressure_sr': s.pressure_strike_rate,
            'normal_sr': s.normal_strike_rate,
            'batting_matches': s.batting_matches,
            'bowling_score': s.bowling_pressure_score,
            'pressure_econ': s.pressure_economy,
            'normal_econ': s.normal_economy,
            'pressure_wickets': s.pressure_wickets,
            'bowling_matches': s.bowling_matches,
        })

    return Response({
        'total': paginator.count,
        'page': page,
        'total_pages': paginator.num_pages,
        'uncapped_only': uncapped,
        'exclude_ipl': exclude_ipl,
        'ipl_teams': IPL_TEAMS_LIST,
        'results': results,
    })


@api_view(['GET'])
def player_detail_view(request, player_id):
    """
    Returns full profile for one player.
    """
    try:
        player = Player.objects.get(player_id=player_id)
    except Player.DoesNotExist:
        return Response({'error': 'Player not found'}, status=404)

    stat = getattr(player, 'playerpressurestats', None)
    is_uncapped = stat.is_uncapped if stat else player.is_uncapped
    ipl_team = stat.ipl_team if stat else player.ipl_team

    bat_match_ids = BallByBall.objects.filter(striker_id=player_id).values_list('match_id', flat=True).distinct()
    bowl_match_ids = BallByBall.objects.filter(bowler_id=player_id).values_list('match_id', flat=True).distinct()
    all_match_ids = set(bat_match_ids).union(set(bowl_match_ids))

    matches = Match.objects.filter(match_id__in=all_match_ids).select_related('competition')
    comps = list({f"{m.competition.comp_name} ({m.competition.season})" for m in matches})

    recent_matches = matches.order_by('-match_date')[:5]
    match_list = [
        {
            'match_id': m.match_id,
            'date': str(m.match_date),
            'stage': m.stage,
            'vs': m.away_team if m.home_team in m.result else m.home_team,
            'result': m.result,
        }
        for m in recent_matches
    ]

    return Response({
        'player_id': player.player_id,
        'player_name': player.player_name,
        'is_uncapped': is_uncapped,
        'ipl_team': ipl_team or 'Uncontracted / Domestic',
        'is_in_ipl_team': player.is_in_ipl_team,
        'competitions': comps,
        'recent_matches': match_list,
        'batting': {
            'pressure_score': stat.batting_pressure_score if stat else None,
            'matches': stat.batting_matches if stat else 0,
            'total_balls': stat.total_balls_faced if stat else 0,
            'pressure_balls': stat.pressure_balls_faced if stat else 0,
            'total_runs': stat.total_runs_scored if stat else 0,
            'pressure_runs': stat.pressure_runs_scored if stat else 0,
            'normal_strike_rate': stat.normal_strike_rate if stat else None,
            'pressure_strike_rate': stat.pressure_strike_rate if stat else None,
            'pressure_sr_ratio': stat.pressure_sr_ratio if stat else None,
            'total_fours': stat.total_fours if stat else 0,
            'total_sixes': stat.total_sixes if stat else 0,
            'pressure_fours': stat.pressure_fours if stat else 0,
            'pressure_sixes': stat.pressure_sixes if stat else 0,
            'pressure_dismissals': stat.pressure_dismissals if stat else 0,
        },
        'bowling': {
            'pressure_score': stat.bowling_pressure_score if stat else None,
            'matches': stat.bowling_matches if stat else 0,
            'total_balls': stat.total_balls_bowled if stat else 0,
            'pressure_balls': stat.pressure_balls_bowled if stat else 0,
            'total_runs': stat.total_runs_conceded if stat else 0,
            'pressure_runs': stat.pressure_runs_conceded if stat else 0,
            'total_wickets': stat.total_wickets if stat else 0,
            'pressure_wickets': stat.pressure_wickets if stat else 0,
            'normal_economy': stat.normal_economy if stat else None,
            'pressure_economy': stat.pressure_economy if stat else None,
            'pressure_economy_ratio': stat.pressure_economy_ratio if stat else None,
        }
    })


@api_view(['GET'])
def player_matches_view(request, player_id):
    """
    Returns detailed match breakdown for a player.
    """
    try:
        player = Player.objects.get(player_id=player_id)
    except Player.DoesNotExist:
        return Response({'error': 'Player not found'}, status=404)

    bat_balls = BallByBall.objects.filter(striker_id=player_id)
    bowl_balls = BallByBall.objects.filter(bowler_id=player_id)

    match_ids = set(bat_balls.values_list('match_id', flat=True)).union(
        set(bowl_balls.values_list('match_id', flat=True))
    )

    matches = Match.objects.filter(match_id__in=match_ids).select_related('competition').order_by('-match_date')[:30]

    match_breakdown = []
    for m in matches:
        m_bat = bat_balls.filter(match_id=m.match_id)
        m_bowl = bowl_balls.filter(match_id=m.match_id)

        bat_runs = m_bat.aggregate(s=Sum('runs'))['s'] or 0
        bat_balls_cnt = m_bat.exclude(extras_type='wide').count()
        p_bat_runs = m_bat.filter(is_pressure=True).aggregate(s=Sum('runs'))['s'] or 0
        p_bat_balls = m_bat.filter(is_pressure=True).exclude(extras_type='wide').count()

        bowl_legal_balls = m_bowl.exclude(extras_type__in=['wide', 'Overstep']).count()
        bowl_runs = (m_bowl.exclude(extras_type__in=['byes', 'legbyes']).aggregate(s=Sum('runs'))['s'] or 0) + m_bowl.filter(extras_type__in=['wide', 'Overstep']).count()
        bowl_wickets = m_bowl.filter(is_wicket=True).exclude(dismissal_type__in=['RunOut', 'Retire Out']).count()

        p_bowl = m_bowl.filter(is_pressure=True)
        p_bowl_legal = p_bowl.exclude(extras_type__in=['wide', 'Overstep']).count()
        p_bowl_runs = (p_bowl.exclude(extras_type__in=['byes', 'legbyes']).aggregate(s=Sum('runs'))['s'] or 0) + p_bowl.filter(extras_type__in=['wide', 'Overstep']).count()
        p_bowl_wickets = p_bowl.filter(is_wicket=True).exclude(dismissal_type__in=['RunOut', 'Retire Out']).count()

        match_breakdown.append({
            'match_id': m.match_id,
            'date': str(m.match_date),
            'competition': m.competition.comp_name,
            'season': m.competition.season,
            'stage': m.stage,
            'teams': f"{m.home_team} vs {m.away_team}",
            'result': m.result,
            'batting': {
                'runs': bat_runs,
                'balls': bat_balls_cnt,
                'strike_rate': round((bat_runs / bat_balls_cnt) * 100, 1) if bat_balls_cnt > 0 else 0,
                'pressure_runs': p_bat_runs,
                'pressure_balls': p_bat_balls,
                'pressure_sr': round((p_bat_runs / p_bat_balls) * 100, 1) if p_bat_balls > 0 else 0,
            },
            'bowling': {
                'overs': f"{bowl_legal_balls // 6}.{bowl_legal_balls % 6}",
                'runs': bowl_runs,
                'wickets': bowl_wickets,
                'economy': round(bowl_runs / (bowl_legal_balls / 6.0), 2) if bowl_legal_balls > 0 else 0,
                'pressure_overs': f"{p_bowl_legal // 6}.{p_bowl_legal % 6}",
                'pressure_runs': p_bowl_runs,
                'pressure_wickets': p_bowl_wickets,
                'pressure_economy': round(p_bowl_runs / (p_bowl_legal / 6.0), 2) if p_bowl_legal > 0 else 0,
            }
        })

    return Response({
        'player_id': player.player_id,
        'player_name': player.player_name,
        'matches': match_breakdown,
    })


@api_view(['GET'])
def competitions_list_view(request):
    """
    Returns list of competitions and distinct seasons (Pakistani fixtures excluded).
    """
    comps = Competition.objects.all().order_by('-season', 'comp_name')
    data = [
        {
            'comp_id': c.comp_id,
            'comp_name': c.comp_name,
            'match_format': c.match_format,
            'season': c.season,
            'match_count': c.match_set.count(),
        }
        for c in comps
    ]
    seasons = list(Competition.objects.values_list('season', flat=True).distinct().order_by('-season'))

    return Response({
        'competitions': data,
        'seasons': seasons,
    })


@api_view(['GET'])
def methodology_view(request):
    """
    Returns the complete pressure methodology and scoring formulas.
    """
    return Response({
        'framework_name': 'SupeRR Situational Pressure Engine (SSPE)',
        'description': 'A quantitative framework designed for Rajasthan Royals scouting to identify domestic & global players who over-perform under game pressure, with explicit uncapped prospect and non-IPL franchise filtering.',
        'delivery_pressure_threshold': IS_PRESSURE_THRESHOLD,
        'delivery_rules': [
            {'category': 'Death Overs', 'condition': 'Overs 17 to 20 (overid >= 16)', 'weight': '+1.0'},
            {'category': 'Powerplay Closure', 'condition': 'Overs 5 to 6 (overid 4-5)', 'weight': '+0.5'},
            {'category': 'High RRR (Chase)', 'condition': 'Innings 2, Required Run Rate > 14', 'weight': '+2.0'},
            {'category': 'Chasing Stress', 'condition': 'Innings 2, RRR 12-14: +1.5 | RRR 10-12: +1.0 | RRR 8-10: +0.5', 'weight': 'Dynamic'},
            {'category': 'Close Game', 'condition': 'Runs needed <= 15 with <= 24 balls left', 'weight': '+0.5'},
            {'category': 'Wicket Collapse', 'condition': 'Wickets fallen >= 7 (+1.0) | Wickets fallen 5-6 (+0.5)', 'weight': 'Dynamic'},
            {'category': 'Knockout Multiplier', 'condition': 'Finals, Qualifiers, Eliminators, Semi-Finals', 'weight': '1.5x multiplier'},
            {'category': 'Maximum Delivery Pressure', 'condition': 'Capped at 4.0', 'weight': 'Max 4.0'}
        ],
        'uncapped_and_franchise_scouting': {
            'uncapped_rule': 'Players who have NEVER represented their senior national team in international tournaments (No T20I/ODI/Test appearances).',
            'non_ipl_filter': 'Allows excluding players already contracted to existing IPL teams (e.g. Punjab Kings, Gujarat Titans) to isolate uncontracted domestic free agents for Rajasthan Royals auction targets.'
        },
        'batting_score_formula': {
            'formula': 'Pressure Score = (Pressure SR Ratio * 0.40) + (Boundary Rate Ratio * 0.30) + (Sample Weight * 0.30)',
            'scaled_to': '0 to 100 Index (score * 70.0)',
            'qualification': 'Minimum 40 pressure balls faced and >= 5 matches'
        },
        'bowling_score_formula': {
            'formula': 'Pressure Score = (Pressure Economy Ratio * 0.45) + (Wicket Impact * 0.35) + (Consistency * 0.20)',
            'scaled_to': '0 to 100 Index (score * 70.0)',
            'qualification': 'Minimum 60 pressure balls (10 overs) and >= 5 matches'
        }
    })


@api_view(['GET'])
def compare_players_view(request):
    """
    Compares 2 or more players by their player_ids.
    ?ids=2756,8101
    """
    ids_str = request.GET.get('ids', '')
    if not ids_str:
        return Response({'error': 'Please provide ids parameter (e.g. ?ids=1,2)'}, status=400)

    try:
        player_ids = [int(x.strip()) for x in ids_str.split(',') if x.strip()]
    except ValueError:
        return Response({'error': 'Invalid player ID format'}, status=400)

    players = Player.objects.filter(player_id__in=player_ids).select_related('playerpressurestats')
    comparison = []

    for p in players:
        s = getattr(p, 'playerpressurestats', None)
        comparison.append({
            'player_id': p.player_id,
            'player_name': p.player_name,
            'is_uncapped': s.is_uncapped if s else p.is_uncapped,
            'ipl_team': s.ipl_team if s else p.ipl_team,
            'is_in_ipl_team': s.is_in_ipl_team if s else p.is_in_ipl_team,
            'batting': {
                'score': s.batting_pressure_score if s else None,
                'matches': s.batting_matches if s else 0,
                'pressure_sr': s.pressure_strike_rate if s else None,
                'normal_sr': s.normal_strike_rate if s else None,
                'sr_ratio': s.pressure_sr_ratio if s else None,
                'pressure_runs': s.pressure_runs_scored if s else 0,
                'pressure_balls': s.pressure_balls_faced if s else 0,
                'pressure_boundaries': (s.pressure_fours + s.pressure_sixes) if s else 0,
            },
            'bowling': {
                'score': s.bowling_pressure_score if s else None,
                'matches': s.bowling_matches if s else 0,
                'pressure_econ': s.pressure_economy if s else None,
                'normal_econ': s.normal_economy if s else None,
                'econ_ratio': s.pressure_economy_ratio if s else None,
                'pressure_wickets': s.pressure_wickets if s else 0,
                'total_wickets': s.total_wickets if s else 0,
                'pressure_overs': round(s.pressure_balls_bowled / 6.0, 1) if s else 0,
            }
        })

    return Response({'players': comparison})
