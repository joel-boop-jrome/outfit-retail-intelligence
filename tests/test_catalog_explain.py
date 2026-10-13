import xml.etree.ElementTree as ET

import pytest

from frontend.catalog import COLORS, PRODUCTS, parse_recommendation, product_card
from frontend.explain import (elasticity_sentence, fit_label, revenue_outlook,
                              stock_position, verdict)


def test_parse_recommendation():
    assert parse_recommendation("wrap_dress (mustard)") == ("wrap_dress", "mustard")
    assert parse_recommendation("dark_top_light_bottom (cream)") == ("dark_top_light_bottom", "cream")
    assert parse_recommendation("v_neck_top") == ("v_neck_top", None)


def test_every_recommended_style_has_a_product():
    from cv_vto.style_recommender import BODY_SHAPE_STYLE_MAP
    for styles in BODY_SHAPE_STYLE_MAP.values():
        for s in styles:
            assert s in PRODUCTS


@pytest.mark.parametrize("style", sorted(PRODUCTS))
def test_every_preview_is_valid_svg(style):
    for color in ("mustard", "navy", "cream", None):
        svg = product_card(style, color)["svg"]
        ET.fromstring(svg)  # raises if malformed


def test_all_palette_colors_exist():
    from cv_vto.style_recommender import COLOR_TONE_PALETTE
    for names in COLOR_TONE_PALETTE.values():
        for n in names:
            assert n in COLORS


def test_tryon_link_only_for_tops_with_a_shirt_file():
    assert product_card("v_neck_top", "mustard")["tryon_file"] == "tshirt_mustard.png"
    assert product_card("v_neck_top", "emerald")["tryon_file"] is None
    assert product_card("wrap_dress", "mustard")["tryon_file"] is None


def test_elasticity_sentence_numbers_and_sign():
    assert "2%" in elasticity_sentence(-0.2)
    assert "strongly" in elasticity_sentence(-1.7)
    assert "caution" in elasticity_sentence(0.3)


def test_fit_label():
    assert fit_label(0.1) == "weak" and fit_label(0.45) == "moderate" and fit_label(0.8) == "strong"


def test_verdict_text():
    assert verdict(100, 115, 0.15).startswith("Raise the price 15%")
    assert verdict(100, 80, -0.2).startswith("Lower the price 20%")
    assert verdict(100, 100, 0.0).startswith("Keep the price")


def test_revenue_outlook_caps_units_at_stock():
    r = revenue_outlook(price=100, forecast=200, stock=100, recommended_price=115, elasticity=-0.5)
    assert r["units_now"] == 100            # sold out either way
    assert r["revenue_new"] > r["revenue_now"]
    assert r["units_new"] <= 100


def test_revenue_outlook_unreliable_when_elasticity_positive():
    assert revenue_outlook(100, 200, 100, 115, 0.3) is None


def test_stock_position_messages():
    assert "sell out" in stock_position(200, 100)
    assert "clear it" in stock_position(20, 100)
    assert "balance" in stock_position(100, 100)
