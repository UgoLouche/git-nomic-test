"""Live QA: deliberate failure, repair before voting opens."""
def test_live_pytest_gate():
    assert False, "Intentional live gate validation failure"
