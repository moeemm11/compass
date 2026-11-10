"""Map an unrounded overall score onto configured recommendation bands."""

from dataclasses import dataclass
from decimal import Decimal

from app.services.scoring import to_decimal


@dataclass
class RecommendationBand:
    name: str
    minimum_score: Decimal
    maximum_score: Decimal
    description: str = ""
    management_action: str = ""
    color: str = "#1B4F8A"
    priority: int = 0


CONTINUITY_TOLERANCE = Decimal("0.02")


class RecommendationConfigError(ValueError):
    pass


def validate_bands(bands: list[RecommendationBand]) -> None:
    if not bands:
        raise RecommendationConfigError("At least one recommendation band is required")
    ordered = sorted(bands, key=lambda band: (to_decimal(band.minimum_score), to_decimal(band.maximum_score)))
    first = ordered[0]
    last = ordered[-1]
    if to_decimal(first.minimum_score) != Decimal("0"):
        raise RecommendationConfigError("Recommendation bands must start at 0")
    if to_decimal(last.maximum_score) != Decimal("100"):
        raise RecommendationConfigError("Recommendation bands must end at 100")
    for current, nxt in zip(ordered, ordered[1:]):
        current_min = to_decimal(current.minimum_score)
        current_max = to_decimal(current.maximum_score)
        next_min = to_decimal(nxt.minimum_score)
        next_max = to_decimal(nxt.maximum_score)
        if current_min > current_max or next_min > next_max:
            raise RecommendationConfigError("A recommendation minimum cannot exceed its maximum")
        if next_min < current_max:
            raise RecommendationConfigError("Recommendation bands overlap")
        gap = next_min - current_max
        if gap > CONTINUITY_TOLERANCE:
            raise RecommendationConfigError("Recommendation bands must be continuous and cover 0 to 100")
    if to_decimal(last.minimum_score) > to_decimal(last.maximum_score):
        raise RecommendationConfigError("A recommendation minimum cannot exceed its maximum")


def match_recommendation(score: Decimal, bands: list[RecommendationBand]) -> RecommendationBand:
    """Match using full precision.

    Bands expressed as 70–84.99 and 85–100 are treated as continuous: a score
    belongs to a band from its minimum up to, but not including, the next
    band's minimum. The top band includes 100.
    """
    validate_bands(bands)
    ordered = sorted(bands, key=lambda band: to_decimal(band.minimum_score))
    value = to_decimal(score)
    if value < 0 or value > 100:
        raise RecommendationConfigError("Score must be between 0 and 100")
    for index, band in enumerate(ordered):
        is_last = index == len(ordered) - 1
        minimum = to_decimal(band.minimum_score)
        if is_last:
            if minimum <= value <= to_decimal(band.maximum_score):
                return band
            continue
        next_minimum = to_decimal(ordered[index + 1].minimum_score)
        if minimum <= value < next_minimum:
            return band
    raise RecommendationConfigError("Score did not match a recommendation band")
