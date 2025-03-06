import pandas as pd
from datetime import datetime
import pytz 

class WeatherDataCache:
    def __init__(self):
        self.data = pd.DataFrame()

    def upsert(self, new_data):
        """Upsert new data into the cache."""
        # Combine and remove duplicates
        self.data = pd.concat([self.data, new_data]).drop_duplicates(subset='datetime', keep='last')
        self.clean()

    def clean(self):
        """Remove entries older than the current day."""
        # Create `today` as a timezone-aware datetime in UTC
        today_utc = datetime.now(pytz.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        self.data = self.data[self.data['datetime'] >= today_utc]

    def get_data(self):
        """Fetch the current cache, ensuring it's cleaned."""
        self.clean()
        return self.data