"""Commercial feasibility calculations. Currency conversion is intentionally not applied."""

from dataclasses import dataclass
from decimal import Decimal

from app.services.scoring import display_score, to_decimal


@dataclass
class CommercialInputs:
    contract_value: Decimal
    internal_cost: Decimal = Decimal("0")
    partner_cost: Decimal = Decimal("0")
    travel_cost: Decimal = Decimal("0")
    third_party_cost: Decimal = Decimal("0")
    licensing_cost: Decimal = Decimal("0")
    other_cost: Decimal = Decimal("0")
    contingency: Decimal = Decimal("0")
    bid_cost: Decimal = Decimal("0")
    probability_of_winning: Decimal = Decimal("0")


@dataclass
class CommercialResult:
    total_cost: Decimal
    gross_profit: Decimal
    gross_margin: Decimal | None
    expected_revenue: Decimal
    expected_contribution: Decimal
    partner_cost_percentage: Decimal | None


def calculate_commercial(inputs: CommercialInputs) -> CommercialResult:
    costs = [
        inputs.internal_cost,
        inputs.partner_cost,
        inputs.travel_cost,
        inputs.third_party_cost,
        inputs.licensing_cost,
        inputs.other_cost,
        inputs.contingency,
    ]
    total_cost = sum((to_decimal(cost) for cost in costs), Decimal("0"))
    contract_value = to_decimal(inputs.contract_value)
    gross_profit = contract_value - total_cost
    gross_margin = None
    if contract_value > 0:
        gross_margin = display_score(gross_profit / contract_value * Decimal("100"))
    probability = to_decimal(inputs.probability_of_winning) / Decimal("100")
    expected_revenue = contract_value * probability
    expected_contribution = expected_revenue - (total_cost * probability) - to_decimal(inputs.bid_cost)
    partner_cost_percentage = None
    if total_cost > 0:
        partner_cost_percentage = display_score(to_decimal(inputs.partner_cost) / total_cost * Decimal("100"))
    return CommercialResult(
        total_cost=total_cost,
        gross_profit=gross_profit,
        gross_margin=gross_margin,
        expected_revenue=expected_revenue,
        expected_contribution=expected_contribution,
        partner_cost_percentage=partner_cost_percentage,
    )
