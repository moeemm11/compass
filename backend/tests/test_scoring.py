from decimal import Decimal

from app.services.financials import CommercialInputs, calculate_commercial
from app.services.recommendation import RecommendationBand, match_recommendation, validate_bands
from app.services.scoring import CriterionInput, SubcriterionInput, overall_score, score_criterion
from app.services.weights import WeightValidationError, validate_weight_total


DEFAULT_BANDS = [
    RecommendationBand("Proceed with the opportunity", Decimal("85"), Decimal("100")),
    RecommendationBand("Proceed subject to closing identified gaps", Decimal("70"), Decimal("84.99")),
    RecommendationBand("Limit commitment and conduct further due diligence", Decimal("55"), Decimal("69.99")),
    RecommendationBand("Reconsider scope, partnership or commercial model", Decimal("40"), Decimal("54.99")),
    RecommendationBand("Do not commit under current conditions", Decimal("0"), Decimal("39.99")),
]


def test_specification_example_scores_77_and_recommends_conditional_proceeding():
    weights_and_scores = [
        (Decimal("15"), Decimal("5")),
        (Decimal("10"), Decimal("4")),
        (Decimal("20"), Decimal("3")),
        (Decimal("15"), Decimal("4")),
        (Decimal("20"), Decimal("4")),
        (Decimal("10"), Decimal("3")),
        (Decimal("10"), Decimal("4")),
    ]
    results = [score_criterion(CriterionInput(weight=weight, selected_score=score), Decimal("5")) for weight, score in weights_and_scores]
    total, complete = overall_score(results)
    assert complete
    assert total == Decimal("77")
    assert match_recommendation(total, DEFAULT_BANDS).name == "Proceed subject to closing identified gaps"


def test_subcriteria_roll_up_to_the_parent_weight():
    criterion = CriterionInput(
        weight=Decimal("20"),
        subcriteria=[
            SubcriterionInput(Decimal("25"), Decimal("3")),
            SubcriterionInput(Decimal("20"), Decimal("3")),
            SubcriterionInput(Decimal("15"), Decimal("3")),
            SubcriterionInput(Decimal("15"), Decimal("3")),
            SubcriterionInput(Decimal("15"), Decimal("3")),
            SubcriterionInput(Decimal("10"), Decimal("3")),
        ],
    )
    result = score_criterion(criterion, Decimal("5"))
    assert result.complete
    assert result.weighted_score == Decimal("12")


def test_missing_scores_are_not_treated_as_zero():
    result = score_criterion(
        CriterionInput(
            weight=Decimal("20"),
            subcriteria=[SubcriterionInput(Decimal("50"), Decimal("5")), SubcriterionInput(Decimal("50"), None)],
        ),
        Decimal("5"),
    )
    assert result.complete is False
    assert result.weighted_score is None


def test_recommendation_boundaries_use_unrounded_scores():
    assert match_recommendation(Decimal("84.99"), DEFAULT_BANDS).name.startswith("Proceed subject")
    assert match_recommendation(Decimal("85"), DEFAULT_BANDS).name == "Proceed with the opportunity"
    assert match_recommendation(Decimal("70"), DEFAULT_BANDS).name.startswith("Proceed subject")
    assert match_recommendation(Decimal("69.995"), DEFAULT_BANDS).name.startswith("Limit commitment")
    assert match_recommendation(Decimal("0"), DEFAULT_BANDS).name.startswith("Do not commit")
    assert match_recommendation(Decimal("100"), DEFAULT_BANDS).name == "Proceed with the opportunity"
    assert match_recommendation(Decimal("39.995"), DEFAULT_BANDS).name.startswith("Do not commit")
    assert match_recommendation(Decimal("40"), DEFAULT_BANDS).name.startswith("Reconsider")


def test_weight_total_must_equal_100():
    validate_weight_total([Decimal("15"), Decimal("10"), Decimal("20"), Decimal("15"), Decimal("20"), Decimal("10"), Decimal("10")])
    try:
        validate_weight_total([Decimal("90")])
        raised = False
    except WeightValidationError:
        raised = True
    assert raised


def test_overlapping_bands_are_rejected():
    try:
        validate_bands(
            [
                RecommendationBand("Low", Decimal("0"), Decimal("60")),
                RecommendationBand("High", Decimal("40"), Decimal("100")),
            ]
        )
        raised = False
    except Exception:
        raised = True
    assert raised


def test_financial_formula_matches_the_specification():
    result = calculate_commercial(
        CommercialInputs(
            contract_value=Decimal("4800000"),
            internal_cost=Decimal("2200000"),
            partner_cost=Decimal("900000"),
            travel_cost=Decimal("80000"),
            third_party_cost=Decimal("60000"),
            licensing_cost=Decimal("120000"),
            other_cost=Decimal("40000"),
            contingency=Decimal("150000"),
            bid_cost=Decimal("75000"),
            probability_of_winning=Decimal("60"),
        )
    )
    assert result.total_cost == Decimal("3550000")
    assert result.gross_profit == Decimal("1250000")
    assert result.gross_margin == Decimal("26.04")
    assert result.expected_revenue == Decimal("2880000")
    assert result.expected_contribution == Decimal("675000")
    assert result.partner_cost_percentage == Decimal("25.35")
