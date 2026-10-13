from dynamic_pricing.price_optimizer import recommend_price


def test_markup_when_demand_exceeds_stock():
    r = recommend_price("S", 100, forecasted_demand=200, current_stock=100, elasticity=-0.5)
    assert r.recommended_price > 100
    assert r.pct_change <= 0.15


def test_markdown_when_stock_outpaces_demand():
    r = recommend_price("S", 100, forecasted_demand=20, current_stock=100, elasticity=-0.5)
    assert r.recommended_price < 100
    assert r.pct_change >= -0.30


def test_no_change_when_balanced():
    r = recommend_price("S", 100, forecasted_demand=100, current_stock=100, elasticity=-1)
    assert r.recommended_price == 100


def test_zero_stock_leaves_price_unchanged():
    r = recommend_price("S", 100, forecasted_demand=500, current_stock=0, elasticity=-1)
    assert r.recommended_price == 100


def test_elastic_products_move_less():
    inelastic = recommend_price("S", 100, 300, 100, elasticity=-0.5)
    elastic = recommend_price("S", 100, 300, 100, elasticity=-3.0)
    assert abs(elastic.pct_change) <= abs(inelastic.pct_change)


def test_unreliable_positive_elasticity_holds_the_price():
    r = recommend_price("S", 100, forecasted_demand=500, current_stock=100, elasticity=0.4)
    assert r.recommended_price == 100 and r.pct_change == 0
