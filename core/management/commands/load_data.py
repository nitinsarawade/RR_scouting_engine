import os
import shutil
import time
from pathlib import Path
import pandas as pd
import numpy as np

from django.core.management.base import BaseCommand
from django.conf import settings
from django.db import transaction

from core.models import Competition, Team, Player, Match, BallByBall, PlayerPressureStats
from core.pressure import compute_pressure_score, IS_PRESSURE_THRESHOLD
from core.metrics import determine_uncapped_status


class Command(BaseCommand):
    help = "Loads cricket data from CSVs, computes ball pressure scores, and aggregates player pressure stats."

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force reload data even if database is already populated.',
        )

    def handle(self, *args, **options):
        start_time = time.time()
        self.stdout.write(self.style.MIGRATE_HEADING("=== SupeRR Selector: Data Loader ==="))

        base_dir = Path(settings.BASE_DIR)
        data_dir = base_dir / "data"
        temp_dir = Path("C:/Users/saraw/AppData/Local/Temp")
        data_dir.mkdir(parents=True, exist_ok=True)

        csv_files = [
            "competitions.csv",
            "teams.csv",
            "competition_team_player_mapping.csv",
            "matches.csv",
            "playing_eleven.csv",
            "ball_by_ball.csv",
        ]

        # Step 1: Ensure CSVs exist in data_dir, copy from temp_dir if needed
        self.stdout.write("1. Verifying and syncing CSV datasets in data/ ...")
        for fname in csv_files:
            dst = data_dir / fname
            src = temp_dir / fname
            if not dst.exists() and src.exists():
                self.stdout.write(f"   Copying {fname} from Temp to data/...")
                shutil.copy2(src, dst)
            elif dst.exists():
                pass
            else:
                self.stdout.write(self.style.WARNING(f"   Warning: {fname} not found in {src} or {dst}"))

        force = options.get('force', False)
        if not force and BallByBall.objects.count() >= 200000:
            self.stdout.write(self.style.SUCCESS("Database is already loaded with 200k+ deliveries. Use --force to reload."))
            return

        # Step 2: Clear existing data if reloading
        self.stdout.write("2. Clearing old records for clean ingestion...")
        PlayerPressureStats.objects.all().delete()
        BallByBall.objects.all().delete()
        Match.objects.all().delete()
        Player.objects.all().delete()
        Team.objects.all().delete()
        Competition.objects.all().delete()

        # Step 3: Load Competitions
        self.stdout.write("3. Loading Competitions...")
        comp_csv = data_dir / "competitions.csv"
        comp_df = pd.read_csv(comp_csv).drop_duplicates(subset=['comp_id'])
        comp_objs = [
            Competition(
                comp_id=int(r['comp_id']),
                comp_name=str(r['comp_name']),
                match_format=str(r['match_format']),
                season=str(r['season']),
            )
            for _, r in comp_df.iterrows()
        ]
        Competition.objects.bulk_create(comp_objs, batch_size=1000)
        self.stdout.write(self.style.SUCCESS(f"   Loaded {len(comp_objs)} competitions."))

        # Step 4: Load Teams
        self.stdout.write("4. Loading Teams...")
        team_csv = data_dir / "teams.csv"
        team_df = pd.read_csv(team_csv).drop_duplicates(subset=['team_id'])
        team_objs = [
            Team(
                team_id=int(r['team_id']),
                team_name=str(r['team_name']),
            )
            for _, r in team_df.iterrows()
        ]
        Team.objects.bulk_create(team_objs, batch_size=1000)
        self.stdout.write(self.style.SUCCESS(f"   Loaded {len(team_objs)} teams."))

        # Step 5: Load Players
        self.stdout.write("5. Loading Players...")
        player_csv = data_dir / "competition_team_player_mapping.csv"
        player_df = pd.read_csv(player_csv).drop_duplicates(subset=['player_id'])
        player_objs = [
            Player(
                player_id=int(r['player_id']),
                player_name=str(r['player_name']),
                is_uncapped=determine_uncapped_status(int(r['player_id']), str(r['player_name'])),
            )
            for _, r in player_df.iterrows()
        ]
        Player.objects.bulk_create(player_objs, batch_size=1000)
        self.stdout.write(self.style.SUCCESS(f"   Loaded {len(player_objs)} players."))

        # Step 6: Load Matches
        self.stdout.write("6. Loading Matches...")
        match_csv = data_dir / "matches.csv"
        match_df = pd.read_csv(match_csv).drop_duplicates(subset=['match_id'])
        
        match_objs = []
        for _, r in match_df.iterrows():
            m_date = str(r['match_date']).strip() if pd.notna(r['match_date']) else None
            m_num = int(r['match_number']) if pd.notna(r['match_number']) else None
            win_t = int(r['win_team_id']) if pd.notna(r['win_team_id']) else None
            is_ko = bool(r['knock_out'] or str(r['stage']).strip() in ['Final', 'Semi Final', 'Qualifier', 'Eliminator'])

            match_objs.append(
                Match(
                    match_id=int(r['match_id']),
                    competition_id=int(r['comp_id']),
                    match_number=m_num,
                    match_date=m_date,
                    stage=str(r['stage']) if pd.notna(r['stage']) else 'League',
                    venue_country=str(r['venue_country']) if pd.notna(r['venue_country']) else '',
                    home_team=str(r['home_team']) if pd.notna(r['home_team']) else '',
                    away_team=str(r['away_team']) if pd.notna(r['away_team']) else '',
                    win_team_id=win_t,
                    result=str(r['result']) if pd.notna(r['result']) else '',
                    knock_out=is_ko,
                )
            )
        Match.objects.bulk_create(match_objs, batch_size=1000)
        self.stdout.write(self.style.SUCCESS(f"   Loaded {len(match_objs)} matches."))

        # Step 7: Load Ball-by-ball and compute pressure
        self.stdout.write("7. Processing Ball-by-Ball data and computing situational pressure...")
        bbb_csv = data_dir / "ball_by_ball.csv"
        df_b = pd.read_csv(bbb_csv)

        # Vectorized Pressure computation
        ko_matches = set(match_df[(match_df['knock_out'] == 1) | (match_df['stage'].isin(['Final', 'Semi Final', 'Qualifier', 'Eliminator']))]['match_id'])
        df_b['is_ko'] = df_b['match_id'].isin(ko_matches)

        # extras calculation
        df_b['extra_run'] = np.where(df_b['extras_type'].notna() & (df_b['extras_type'] != 'None') & (df_b['extras_type'] != ''), 1, 0)
        df_b['total_delivery_runs'] = df_b['runs'] + df_b['extra_run']

        # Innings 1 total runs per match
        inn1_runs = df_b[df_b['innings'] == 1].groupby('match_id')['total_delivery_runs'].sum()
        targets = (inn1_runs + 1).to_dict()

        # Cumulative runs and wickets within each match and innings
        df_b['cum_runs'] = df_b.groupby(['match_id', 'innings'])['total_delivery_runs'].cumsum() - df_b['total_delivery_runs']
        df_b['is_wicket_int'] = df_b['is_wicket'].astype(int)
        df_b['cum_wickets'] = df_b.groupby(['match_id', 'innings'])['is_wicket_int'].cumsum() - df_b['is_wicket_int']

        # Scheduled balls
        revised_map = match_df.set_index('match_id')['second_inn_revised_overs'].dropna().to_dict()
        df_b['revised_balls'] = df_b['match_id'].map(revised_map)
        df_b['scheduled_balls'] = np.where(df_b['innings'] == 2, df_b['revised_balls'].fillna(120), 120)

        balls_rem = np.maximum(0, df_b['scheduled_balls'] - df_b['innings_ball_num'])
        overid = df_b['overid']

        score = np.zeros(len(df_b), dtype=np.float32)
        score += np.where(overid >= 16, 1.0, 0.0)
        score += np.where((overid == 4) | (overid == 5), 0.5, 0.0)

        is_inn2 = df_b['innings'] == 2
        target = df_b['match_id'].map(targets).fillna(0)
        runs_needed = target - df_b['cum_runs']

        with np.errstate(divide='ignore', invalid='ignore'):
            rrr = np.where((is_inn2) & (balls_rem > 0) & (runs_needed > 0), (runs_needed * 6.0) / balls_rem, 0.0)

        rrr_score = np.where(rrr > 14, 2.0,
                    np.where(rrr > 12, 1.5,
                    np.where(rrr > 10, 1.0,
                    np.where(rrr > 8, 0.5, 0.0))))
        score += np.where(is_inn2, rrr_score, 0.0)
        score += np.where(is_inn2 & (runs_needed <= 15) & (runs_needed > 0) & (balls_rem <= 24) & (balls_rem > 0), 0.5, 0.0)
        score += np.where(df_b['cum_wickets'] >= 7, 1.0, np.where(df_b['cum_wickets'] >= 5, 0.5, 0.0))
        score = np.where(df_b['is_ko'], score * 1.5, score)
        score = np.minimum(score, 4.0)

        df_b['pressure_score'] = np.round(score, 2)
        df_b['is_pressure'] = score >= IS_PRESSURE_THRESHOLD

        p_count = df_b['is_pressure'].sum()
        self.stdout.write(f"   Calculated pressure for {len(df_b)} balls: {p_count} pressure balls ({p_count / len(df_b) * 100:.1f}%).")

        # Step 8: Bulk insert BallByBall
        self.stdout.write("8. Bulk inserting ball deliveries into database in batches of 5000...")
        total_rows = len(df_b)
        batch_size = 5000

        # Pre-convert NaN and types for fast object instantiation
        df_b['non_striker_id'] = df_b['non_striker_id'].where(df_b['non_striker_id'].notna(), None)
        df_b['non_striker_name'] = df_b['non_striker_name'].fillna('')
        df_b['batting_type'] = df_b['batting_type'].fillna('')
        df_b['bowling_type'] = df_b['bowling_type'].fillna('')
        df_b['batting_order'] = df_b['batting_order'].where(df_b['batting_order'].notna(), None)
        df_b['dismissal_type'] = df_b['dismissal_type'].fillna('')
        df_b['dismissed_player_id'] = df_b['dismissed_player_id'].where(df_b['dismissed_player_id'].notna(), None)
        df_b['extras_type'] = df_b['extras_type'].fillna('None')
        df_b['extras1_runs'] = df_b['extras1_runs'].fillna(0).astype(int)
        df_b['extras_2_runs'] = df_b['extras_2_runs'].fillna(0).astype(int)
        df_b['pace_or_spin'] = df_b['pace_or_spin'].fillna('')

        def to_int(val):
            if pd.notna(val) and val is not None:
                try:
                    return int(float(val))
                except (ValueError, TypeError):
                    return None
            return None

        records = df_b.to_dict('records')
        for i in range(0, total_rows, batch_size):
            chunk = records[i:i + batch_size]
            ball_objs = [
                BallByBall(
                    match_id=int(r['match_id']),
                    innings=int(r['innings']),
                    overid=int(r['overid']),
                    over_ball_num=int(r['over_ball_num']),
                    innings_ball_num=int(r['innings_ball_num']),
                    batting_team_id=int(r['batting_team_id']),
                    bowling_team_id=int(r['bowling_team_id']),
                    striker_id=int(r['striker_id']),
                    striker_name=str(r['striker_name']),
                    non_striker_id=to_int(r.get('non_striker_id')),
                    non_striker_name=str(r.get('non_striker_name', '') or ''),
                    bowler_id=int(r['bowler_id']),
                    bowler_name=str(r['bowler_name']),
                    batting_type=str(r.get('batting_type', '') or ''),
                    bowling_type=str(r.get('bowling_type', '') or ''),
                    batting_order=to_int(r.get('batting_order')),
                    runs=int(r['runs']) if pd.notna(r['runs']) else 0,
                    is_four=bool(r['is_four']) if pd.notna(r['is_four']) else False,
                    is_six=bool(r['is_six']) if pd.notna(r['is_six']) else False,
                    is_wicket=bool(r['is_wicket']) if pd.notna(r['is_wicket']) else False,
                    dismissal_type=str(r.get('dismissal_type', '') or '') if pd.notna(r.get('dismissal_type')) else '',
                    dismissed_player_id=to_int(r.get('dismissed_player_id')),
                    extras_type=str(r.get('extras_type', 'None') or 'None') if pd.notna(r.get('extras_type')) else 'None',
                    extras1_runs=to_int(r.get('extras1_runs')) or 0,
                    extras_2_runs=to_int(r.get('extras_2_runs')) or 0,
                    pace_or_spin=str(r.get('pace_or_spin', '') or '') if pd.notna(r.get('pace_or_spin')) else '',
                    pressure_score=float(r['pressure_score']),
                    is_pressure=bool(r['is_pressure']),
                )
                for r in chunk
            ]
            BallByBall.objects.bulk_create(ball_objs, batch_size=batch_size)
            if (i + batch_size) % 50000 == 0 or (i + batch_size) >= total_rows:
                self.stdout.write(f"   Inserted {min(i + batch_size, total_rows)} / {total_rows} deliveries...")

        self.stdout.write(self.style.SUCCESS(f"   Successfully inserted {total_rows} deliveries."))

        # Step 9: Compute PlayerPressureStats Aggregates
        self.stdout.write("9. Computing PlayerPressureStats aggregates...")
        
        # Batting aggregation
        bat_mask = df_b['extras_type'].isna() | (df_b['extras_type'] == 'None') | (df_b['extras_type'] != 'wide')
        bat_df = df_b[bat_mask]

        bat_grp = bat_df.groupby('striker_id').agg(
            batting_matches=('match_id', 'nunique'),
            total_balls_faced=('runs', 'count'),
            total_runs_scored=('runs', 'sum'),
            total_fours=('is_four', 'sum'),
            total_sixes=('is_six', 'sum'),
            total_dismissals=('is_wicket', 'sum')
        )

        p_bat_df = bat_df[bat_df['is_pressure']]
        p_bat_grp = p_bat_df.groupby('striker_id').agg(
            pressure_balls_faced=('runs', 'count'),
            pressure_runs_scored=('runs', 'sum'),
            pressure_fours=('is_four', 'sum'),
            pressure_sixes=('is_six', 'sum'),
            pressure_dismissals=('is_wicket', 'sum')
        )

        bat_all = bat_grp.join(p_bat_grp, how='left').fillna(0)

        # Bowling aggregation
        is_wide_or_nb = df_b['extras_type'].isin(['wide', 'Overstep'])
        df_b['bowler_runs'] = df_b['runs'] + np.where(is_wide_or_nb, 1, 0)
        df_b['is_legal_bowl'] = ~is_wide_or_nb
        df_b['is_bowler_wicket'] = df_b['is_wicket'] & ~df_b['dismissal_type'].isin(['RunOut', 'Retire Out'])

        bowl_grp = df_b.groupby('bowler_id').agg(
            bowling_matches=('match_id', 'nunique'),
            total_balls_bowled=('is_legal_bowl', 'sum'),
            total_runs_conceded=('bowler_runs', 'sum'),
            total_wickets=('is_bowler_wicket', 'sum')
        )

        p_bowl_df = df_b[df_b['is_pressure']]
        p_bowl_grp = p_bowl_df.groupby('bowler_id').agg(
            pressure_balls_bowled=('is_legal_bowl', 'sum'),
            pressure_runs_conceded=('bowler_runs', 'sum'),
            pressure_wickets=('is_bowler_wicket', 'sum')
        )

        bowl_all = bowl_grp.join(p_bowl_grp, how='left').fillna(0)

        all_player_ids = set(Player.objects.values_list('player_id', flat=True))
        player_dict = {p.player_id: p for p in Player.objects.all()}
        stats_objs = []
        qualified_batters = 0
        qualified_bowlers = 0

        for pid in all_player_ids:
            p_obj = player_dict.get(pid)
            p_name = p_obj.player_name if p_obj else ''
            is_unc = p_obj.is_uncapped if p_obj else determine_uncapped_status(pid, p_name)

            # Batting
            b_row = bat_all.loc[pid] if pid in bat_all.index else None
            if b_row is not None:
                t_bf = int(b_row['total_balls_faced'])
                p_bf = int(b_row['pressure_balls_faced'])
                t_rs = int(b_row['total_runs_scored'])
                p_rs = int(b_row['pressure_runs_scored'])
                t_f = int(b_row['total_fours'])
                t_s = int(b_row['total_sixes'])
                p_f = int(b_row['pressure_fours'])
                p_s = int(b_row['pressure_sixes'])
                t_d = int(b_row['total_dismissals'])
                p_d = int(b_row['pressure_dismissals'])
                b_m = int(b_row['batting_matches'])

                norm_sr = round((t_rs / t_bf) * 100.0, 2) if t_bf > 0 else None
                pres_sr = round((p_rs / p_bf) * 100.0, 2) if p_bf > 0 else None
                pres_sr_ratio = round(pres_sr / norm_sr, 3) if norm_sr and pres_sr and norm_sr > 0 else None

                # Batting Qualification: >= 40 pressure balls & >= 5 matches
                if p_bf >= 40 and b_m >= 5 and norm_sr and pres_sr_ratio:
                    n_br = (t_f + t_s) / t_bf if t_bf > 0 else 0.0
                    p_br = (p_f + p_s) / p_bf if p_bf > 0 else 0.0
                    br_ratio = p_br / max(0.01, n_br)
                    sample_w = min(1.0, p_bf / 150.0)
                    raw_bat = (pres_sr_ratio * 0.40) + (br_ratio * 0.30) + (sample_w * 0.30)
                    bat_score = round(raw_bat * 70.0, 1)
                    qualified_batters += 1
                else:
                    bat_score = None
            else:
                t_bf = p_bf = t_rs = p_rs = t_f = t_s = p_f = p_s = t_d = p_d = b_m = 0
                norm_sr = pres_sr = pres_sr_ratio = bat_score = None

            # Bowling
            bw_row = bowl_all.loc[pid] if pid in bowl_all.index else None
            if bw_row is not None:
                t_bb = int(bw_row['total_balls_bowled'])
                p_bb = int(bw_row['pressure_balls_bowled'])
                t_rc = int(bw_row['total_runs_conceded'])
                p_rc = int(bw_row['pressure_runs_conceded'])
                t_w = int(bw_row['total_wickets'])
                p_w = int(bw_row['pressure_wickets'])
                bw_m = int(bw_row['bowling_matches'])

                norm_econ = round(t_rc / (t_bb / 6.0), 2) if t_bb > 0 else None
                pres_econ = round(p_rc / (p_bb / 6.0), 2) if p_bb > 0 else None
                pres_econ_ratio = round(norm_econ / pres_econ, 3) if norm_econ and pres_econ and pres_econ > 0 else None

                # Bowling Qualification: >= 60 pressure balls (10 overs) & >= 5 matches
                if p_bb >= 60 and bw_m >= 5 and norm_econ and pres_econ_ratio and t_w > 0:
                    p_w_rate = p_w / p_bb if p_bb > 0 else 0.0
                    n_w_rate = t_w / t_bb if t_bb > 0 else 0.001
                    w_impact = p_w_rate / max(0.001, n_w_rate)
                    cons = min(1.0, p_bb / 200.0)
                    raw_bowl = (pres_econ_ratio * 0.45) + (w_impact * 0.35) + (cons * 0.20)
                    bowl_score = round(raw_bowl * 70.0, 1)
                    qualified_bowlers += 1
                else:
                    bowl_score = None
            else:
                t_bb = p_bb = t_rc = p_rc = t_w = p_w = bw_m = 0
                norm_econ = pres_econ = pres_econ_ratio = bowl_score = None

            stats_objs.append(
                PlayerPressureStats(
                    player_id=pid,
                    is_uncapped=is_unc,
                    total_balls_faced=t_bf,
                    pressure_balls_faced=p_bf,
                    total_runs_scored=t_rs,
                    pressure_runs_scored=p_rs,
                    total_fours=t_f,
                    total_sixes=t_s,
                    pressure_fours=p_f,
                    pressure_sixes=p_s,
                    total_dismissals=t_d,
                    pressure_dismissals=p_d,
                    normal_strike_rate=norm_sr,
                    pressure_strike_rate=pres_sr,
                    pressure_sr_ratio=pres_sr_ratio,
                    batting_pressure_score=bat_score,
                    batting_matches=b_m,
                    total_balls_bowled=t_bb,
                    pressure_balls_bowled=p_bb,
                    total_runs_conceded=t_rc,
                    pressure_runs_conceded=p_rc,
                    total_wickets=t_w,
                    pressure_wickets=p_w,
                    normal_economy=norm_econ,
                    pressure_economy=pres_econ,
                    pressure_economy_ratio=pres_econ_ratio,
                    bowling_pressure_score=bowl_score,
                    bowling_matches=bw_m,
                )
            )

        PlayerPressureStats.objects.bulk_create(stats_objs, batch_size=1000)
        self.stdout.write(self.style.SUCCESS(
            f"   Saved pressure stats for {len(stats_objs)} players: "
            f"{qualified_batters} qualified batters, {qualified_bowlers} qualified bowlers."
        ))

        elapsed = time.time() - start_time
        self.stdout.write(self.style.SUCCESS(f"=== Complete! Data pipeline finished in {elapsed:.1f} seconds ==="))
