from beam_calc import BeamInput, beta1, design_flexure, design_shear


def make(**kw):
    base = dict(b=25, h=50, cover=3, fc=240, fy=4000, fyt=2400, Mu=15, Vu=12)
    base.update(kw)
    return BeamInput(**base)


def test_beta1():
    assert beta1(240) == 0.85
    assert abs(beta1(350) - 0.80) < 1e-9
    assert beta1(1000) == 0.65


def test_flexure_typical_beam_passes():
    r = design_flexure(make())
    assert abs(r.d - 45.1) < 1e-6
    assert r.rho_min <= r.rho_req <= r.rho_max
    assert r.As_prov >= r.As_req
    assert r.phiMn >= 15
    assert r.ok


def test_flexure_minimum_steel_governs_small_moment():
    r = design_flexure(make(Mu=1))
    assert abs(r.As_req - r.rho_min * 25 * r.d) < 1e-9


def test_flexure_oversized_moment_fails():
    r = design_flexure(make(Mu=80))
    assert not r.ok
    assert r.messages


def test_shear_typical_beam():
    s = design_shear(make())
    assert s.ok
    assert s.phiVn >= 12
    assert s.s_use <= s.s_max


def test_shear_too_large_fails():
    assert not design_shear(make(Vu=150)).ok
