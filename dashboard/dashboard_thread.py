import threading
from dashboard.dashboard import Dashboard
from dashboard.dahsboard_settings import DashboardSettings

class DashboardThread(threading.Thread):
    dashboard : Dashboard

    def __init__(self, settings : DashboardSettings, name = 'dashboard thread', host = '127.0.0.1', port = '8007'):
        self.dashboard = Dashboard(settings)
        
        kwargs = { 'host': host, 'port' : port }
        threading.Thread.__init__(
            self,
            target = self.dashboard.app.run,
            kwargs=kwargs
        )
        self.name = name

    