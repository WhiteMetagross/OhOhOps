import numpy as np
import logging
from pyod.models.iforest import IForest

logger = logging.getLogger("ohohops.anomaly.detector")

class AnomalyDetector:
    def __init__(self, contamination: float = 0.05):
        # We use a 5% contamination assuming anomalies are rare
        self.model = IForest(contamination=contamination, random_state=42)
        self.is_fitted = False
        self.history = []
        
    def add_data_point(self, cpu: float, memory: float, error_rate: float) -> bool:
        """
        Adds a 3D telemetry reading and returns True if it is classified as an anomaly.
        """
        point = [cpu, memory, error_rate]
        self.history.append(point)
        
        # Keep a rolling window of the last 1000 points (approx 30 mins at 2s intervals)
        if len(self.history) > 1000:
            self.history.pop(0)
            
        # We need at least 20 points to fit a meaningful Isolation Forest
        if len(self.history) < 20:
            return False
            
        # Re-fit the model periodically on the rolling window
        # To save CPU, we only refit every 10 new points
        if len(self.history) % 10 == 0:
            X_train = np.array(self.history)
            try:
                self.model.fit(X_train)
                self.is_fitted = True
            except Exception as e:
                logger.error(f"IForest fit error: {e}")
                
        if self.is_fitted:
            X_test = np.array([point])
            # predict() returns 1 for anomaly, 0 for normal
            prediction = self.model.predict(X_test)
            return bool(prediction[0] == 1)
            
        return False
