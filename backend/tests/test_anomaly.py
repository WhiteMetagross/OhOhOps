import pytest
from app.anomaly.detector import AnomalyDetector

def test_anomaly_detector_warmup():
    detector = AnomalyDetector(contamination=0.05)
    # Sending less than 20 points should always return False (warmup phase)
    for i in range(10):
        is_anomaly = detector.add_data_point(50.0, 50.0, 0.1)
        assert not is_anomaly

def test_anomaly_detector_detects_spike():
    detector = AnomalyDetector(contamination=0.05)

    # Warmup with normal traffic that has realistic small variance. (An Isolation
    # Forest trained on perfectly identical points degenerates and can't score —
    # real telemetry always jitters, so we model that here.)
    for i in range(30):
        cpu = 30.0 + (i % 5)        # 30–34%
        mem = 40.0 + (i % 3)        # 40–42%
        err = 0.05 + (i % 4) * 0.01  # 0.05–0.08
        detector.add_data_point(cpu, mem, err)

    # Send a massive spike well outside the learned envelope.
    is_anomaly = detector.add_data_point(100.0, 99.0, 0.99)
    assert is_anomaly
