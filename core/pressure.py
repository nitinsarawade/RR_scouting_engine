"""
Pressure Engine for SupeRR Selector
Quantifies delivery-level pressure in T20 cricket.
"""

IS_PRESSURE_THRESHOLD = 1.5


def compute_pressure_score(innings, overid, innings_ball_num, 
                           runs_so_far, wickets_fallen, 
                           total_balls_in_innings, target=None,
                           is_knockout=False):
    """
    Computes situational pressure score for a delivery in a T20 match.
    Returns float capped at 4.0.
    A delivery is classified as pressure if score >= 1.5.
    """
    score = 0.0
    balls_remaining = total_balls_in_innings - innings_ball_num
    
    # Death overs pressure (overs 17-20 = overid 16-20)
    if overid >= 16:
        score += 1.0
    # Powerplay end pressure (overs 5-6 = overid 4-5)
    elif overid in [4, 5]:
        score += 0.5
    
    # Chasing innings pressure (innings 2)
    if innings == 2 and target:
        runs_needed = target - runs_so_far
        if balls_remaining > 0 and runs_needed > 0:
            rrr = (runs_needed * 6.0) / balls_remaining
            if rrr > 14:
                score += 2.0
            elif rrr > 12:
                score += 1.5
            elif rrr > 10:
                score += 1.0
            elif rrr > 8:
                score += 0.5
        # Close game: within 15 runs with <= 24 balls
        if 0 < runs_needed <= 15 and 0 < balls_remaining <= 24:
            score += 0.5
    
    # Wickets pressure
    if wickets_fallen >= 7:
        score += 1.0
    elif wickets_fallen >= 5:
        score += 0.5
    
    # Knockout multiplier
    if is_knockout:
        score *= 1.5
    
    return min(score, 4.0)
