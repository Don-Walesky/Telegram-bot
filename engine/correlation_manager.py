"""
Correlation Defense & Exposure Management Module
Enforces hard intra-match single selection rules (conflict graph) and evaluates
portfolio league/sport exposure penalties to preserve event independence.
"""

from collections import Counter
from typing import List, Set, Tuple
from engine.contracts import BetCandidate


class CorrelationManager:
    @staticmethod
    def are_conflicting(cand_a: BetCandidate, cand_b: BetCandidate) -> bool:
        """
        Determines if two candidate selections conflict (i.e. share the same event or teams).
        """
        if cand_a.candidate_id == cand_b.candidate_id:
            return True

        # 1. Same Event ID
        if cand_a.event_id and cand_b.event_id and cand_a.event_id == cand_b.event_id:
            return True

        # 2. Same Home and Away teams
        teams_a = {cand_a.home_team.lower().strip(), cand_a.away_team.lower().strip()}
        teams_b = {cand_b.home_team.lower().strip(), cand_b.away_team.lower().strip()}
        if teams_a and teams_b and (teams_a == teams_b or teams_a.intersection(teams_b)):
            return True

        return False

    @classmethod
    def deduplicate_intra_match_candidates(cls, candidates: List[BetCandidate]) -> List[BetCandidate]:
        """
        Iterates over candidates sorted by composite score, retaining only the single highest-scoring
        selection per match event.
        """
        seen_events: Set[str] = set()
        seen_team_pairs: Set[Tuple[str, str]] = set()
        independent_candidates: List[BetCandidate] = []

        for cand in candidates:
            event_key = cand.event_id
            pair_key = (cand.home_team.lower().strip(), cand.away_team.lower().strip())
            rev_pair_key = (cand.away_team.lower().strip(), cand.home_team.lower().strip())

            if event_key and event_key in seen_events:
                continue
            if pair_key in seen_team_pairs or rev_pair_key in seen_team_pairs:
                continue

            if event_key:
                seen_events.add(event_key)
            seen_team_pairs.add(pair_key)
            independent_candidates.append(cand)

        return independent_candidates

    @classmethod
    def calculate_exposure_penalty(
        cls,
        selected_candidates: List[BetCandidate],
        max_league_pct: float = 0.40,
        max_sport_pct: float = 0.70,
    ) -> float:
        """
        Computes a soft penalty score in [0.0, 0.30] if a single league or sport exceeds exposure bounds.
        """
        if not selected_candidates or len(selected_candidates) < 3:
            return 0.0

        n = len(selected_candidates)
        penalty = 0.0

        # League concentration
        leagues = [c.league for c in selected_candidates if c.league]
        if leagues:
            league_counts = Counter(leagues)
            max_league_count = max(league_counts.values())
            league_ratio = max_league_count / n
            if league_ratio > max_league_pct:
                excess = league_ratio - max_league_pct
                penalty += excess * 0.20

        # Sport concentration
        sports = [c.sport for c in selected_candidates if c.sport]
        if sports:
            sport_counts = Counter(sports)
            max_sport_count = max(sport_counts.values())
            sport_ratio = max_sport_count / n
            if sport_ratio > max_sport_pct:
                excess = sport_ratio - max_sport_pct
                penalty += excess * 0.10

        return round(min(0.30, penalty), 4)

    @classmethod
    def validate_slip_independence(cls, selected_candidates: List[BetCandidate]) -> Tuple[bool, str]:
        """
        Hard verification that no two selections in a slip share an event or team.
        """
        seen_events: Set[str] = set()
        seen_teams: Set[str] = set()

        for cand in selected_candidates:
            if cand.event_id:
                if cand.event_id in seen_events:
                    return False, f"Duplicate event ID detected in slip: {cand.event_id}"
                seen_events.add(cand.event_id)

            h_team = cand.home_team.lower().strip()
            a_team = cand.away_team.lower().strip()

            if h_team and h_team in seen_teams:
                return False, f"Team '{cand.home_team}' appears multiple times in slip."
            if a_team and a_team in seen_teams:
                return False, f"Team '{cand.away_team}' appears multiple times in slip."

            if h_team:
                seen_teams.add(h_team)
            if a_team:
                seen_teams.add(a_team)

        return True, ""
