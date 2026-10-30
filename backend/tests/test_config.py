from sqlalchemy.engine import make_url


def test_database_configuration(test_database_url):
    url = make_url(test_database_url)
    assert url.database is not None
    assert url.database.endswith("_test")
