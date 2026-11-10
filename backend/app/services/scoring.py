"""Authoritative weighted scoring. Criteria, weights, and scales come from the caller."""

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP


def to_decimal(value) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def display_score(value: Decimal) -> Decimal:
    return to_decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


@dataclass
class SubcriterionInput:
    weight: Decimal
    selected_score: Decimal | None
    is_active: bool = True


@dataclass
class CriterionInput:
    weight: Decimal
    is_active: bool = True
    selected_score: Decimal | None = None
    subcriteria: list[SubcriterionInput] | None = None


@dataclass
class CriterionResult:
    normalized_score: Decimal | None
    weighted_score: Decimal | None
    selected_score: Decimal | None
    complete: bool


def normalize(selected: Decimal, maximum: Decimal) -> Decimal:
    if maximum <= 0:
        raise ValueError("Scoring scale maximum must be greater than zero")
    return to_decimal(selected) / to_decimal(maximum)


def score_criterion(criterion: CriterionInput, maximum: Decimal) -> CriterionResult:
    """Score one criterion.

    When active subcriteria exist, the parent normalized score is the sum of
    (subcriterion normalized score × subcriterion weight). Missing active
    subcriteria leave the parent incomplete. Weights are not redistributed and
    missing scores are not treated as zero.
    """
    active_subs = [sub for sub in (criterion.subcriteria or []) if sub.is_active]
    if active_subs:
        parent_normalized = Decimal("0")
        for sub in active_subs:
            if sub.selected_score is None:
                return CriterionResult(None, None, None, False)
            parent_normalized += normalize(sub.selected_score, maximum) * (to_decimal(sub.weight) / Decimal("100"))
        weighted = parent_normalized * to_decimal(criterion.weight)
        return CriterionResult(
            normalized_score=parent_normalized,
            weighted_score=weighted,
            selected_score=parent_normalized * to_decimal(maximum),
            complete=True,
        )

    if criterion.selected_score is None:
        return CriterionResult(None, None, None, False)
    normalized = normalize(criterion.selected_score, maximum)
    weighted = normalized * to_decimal(criterion.weight)
    return CriterionResult(
        normalized_score=normalized,
        weighted_score=weighted,
        selected_score=to_decimal(criterion.selected_score),
        complete=True,
    )


def overall_score(criterion_results: list[CriterionResult]) -> tuple[Decimal, bool]:
    """Sum weighted scores of completed criteria only. Returns (score, all_complete)."""
    total = Decimal("0")
    all_complete = True
    for result in criterion_results:
        if not result.complete or result.weighted_score is None:
            all_complete = False
            continue
        total += result.weighted_score
    return total, all_complete and len(criterion_results) > 0
