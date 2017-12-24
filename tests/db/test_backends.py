def test_postgis():
    # Backend does not have any behavior,
    # import to avoid Syntax Errors
    from heroku_connect.db.backends.postgis.base import DatabaseWrapper  # NoQA
