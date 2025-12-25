import gevent.monkey

# Patching must be done before any other imports
gevent.monkey.patch_all()

from tests.performance.metrics import setup_locust_metrics
from tests.performance.metrics import start_metrics_server
from tests.performance.users import EvaStressUser
from tests.performance.users import EvaUser

# Initialize metrics
setup_locust_metrics()
start_metrics_server()

# Expose Users for Locust to find
__all__ = ["EvaUser", "EvaStressUser"]
