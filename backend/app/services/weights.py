from decimal import Decimal

from app.services.scoring import to_decimal


class WeightValidationError(ValueError):
    pass


def _quantize(value: Decimal) -> Decimal:
    return to_decimal(value).quantize(Decimal("0.01"))


def validate_weight_total(weights: list[Decimal], label: str = "Criterion weights") -> None:
    if not weights:
        raise WeightValidationError(f"{label} must include at least one active item")
    total = sum((to_decimal(weight) for weight in weights), Decimal("0"))
    if _quantize(total) != Decimal("100.00"):
        raise WeightValidationError(f"{label} must total 100%. Current total is {_quantize(total)}%")
    for weight in weights:
        if to_decimal(weight) < 0:
            raise WeightValidationError(f"{label} cannot contain a negative weight")
