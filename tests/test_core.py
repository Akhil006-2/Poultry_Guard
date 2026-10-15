from app.risk import assess_event
from app.analysis import density_score, motion_ratio
import numpy as np

def test_urgent_risk_for_multiple_deaths():
    assert assess_event([], deaths=2)['risk_level'] == 'urgent'
def test_watch_for_reduced_feed():
    assert assess_event([], feed_change='decreased')['risk_level'] == 'watch'
def test_routine_when_no_signs():
    assert assess_event([])['risk_level'] == 'routine'
def test_density_bounded():
    assert 0 <= density_score([], 100, 100) <= 1
def test_motion_zero_for_identical_frames():
    a=np.zeros((30,30),dtype=np.uint8)
    assert motion_ratio(a,a) == 0
