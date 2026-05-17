from pyfolio_performance import Security


def test_mostrecentvalue():
    security = Security.get_security_by_isin("DE0005190003")
    security.get_most_recent_value()
    assert True
