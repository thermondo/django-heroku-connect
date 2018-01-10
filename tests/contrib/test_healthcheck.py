from heroku_connect.contrib.health_check import HerokuConnectHealthCheck
from heroku_connect.test.utils import heroku_cli


def test_healthcheck_connection():
    success_output = """Connection [7976d2d4-2483 / herokuconnect-asymmetrical] (IDLE)
           --> Contact (DATA_SYNCED)"""
    with heroku_cli(success_output, exit_code=0):
        health_check_status = HerokuConnectHealthCheck().check_status()
    
    assert(health_check_status)
