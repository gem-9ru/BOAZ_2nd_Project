from server.engine.uncertainty import beta_interval, prob_better, straddles


def test_ovenlog_ctr_prob_b_better():
    assert abs(prob_better(13, 837, 17, 985) - 0.60) < 0.02     # 링크 CTR A 1.55% vs B 1.73%


def test_prob_better_is_deterministic_and_symmetric():
    assert prob_better(13, 837, 17, 985) == prob_better(13, 837, 17, 985)
    assert abs(prob_better(17, 985, 13, 837) - (1 - prob_better(13, 837, 17, 985))) < 0.02


def test_interval_contains_rate_and_narrows_with_n():
    lo, hi = beta_interval(13, 837)
    assert lo < 13 / 837 < hi
    lo2, hi2 = beta_interval(130, 8370)
    assert (hi2 - lo2) < (hi - lo)


def test_interval_zero_trials_is_whole_range():
    assert beta_interval(0, 0) == (0.0, 1.0)


def test_straddles():
    assert straddles(0.006, 0.012, 0.008) and not straddles(0.009, 0.012, 0.008)
