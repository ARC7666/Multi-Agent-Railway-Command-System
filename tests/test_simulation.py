import pytest
from simulation import TrainSimulation

@pytest.fixture
def sim():
    return TrainSimulation()

def test_initial_state(sim):
    assert sim.time_step == 0
    assert len(sim.trains) == 10
    assert not sim.is_running

def test_inject_hazard(sim):
    u = "Howrah (HWH)"
    v = "Bandel (BDC)"
    line = "UP1"
    
    success = sim.inject_hazard(u, v, line)
    assert success is True
    assert len(sim.emergencies) == 1
    assert sim.network[u][v]['tracks'][line] == 'broken'
    
    # Try invalid hazard
    success = sim.inject_hazard(u, v, "INVALID_LINE")
    assert success is False
