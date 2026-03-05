"""
FakeBuster AI — ML Detector Stub
Returns synthetic detection results. Will be replaced by real ensemble in Phase 3.

Interface contract:
    detect(file_path: str) → DetectionResult
    - result_score: float (0.0 = real, 1.0 = fake)
    - result_detail: dict with per-layer breakdown
    - model_version: str
"""

import random
from dataclasses import dataclass, field


MODEL_VERSION = "stub-v0.1.0"


@dataclass
class DetectionResult:
    """Structured output from the detection pipeline."""
    result_score: float
    result_detail: dict = field(default_factory=dict)
    model_version: str = MODEL_VERSION


def detect(file_path: str) -> DetectionResult:
    """
    Stub detector — produces realistic-looking synthetic results.
    In production, this calls the real ensemble pipeline.
    """
    # Simulated per-layer scores
    spatial_score = round(random.uniform(0.1, 0.9), 4)
    frequency_score = round(random.uniform(0.1, 0.9), 4)
    texture_score = round(random.uniform(0.1, 0.9), 4)
    ensemble_score = round(random.uniform(0.15, 0.85), 4)

    # Simulate a weighted ensemble
    overall = round(
        0.35 * spatial_score
        + 0.30 * frequency_score
        + 0.20 * texture_score
        + 0.15 * ensemble_score,
        4,
    )

    detail = {
        "layers": {
            "spatial_cnn": {
                "score": spatial_score,
                "model": "EfficientNet-B4 (stub)",
                "weight": 0.35,
            },
            "frequency_analysis": {
                "score": frequency_score,
                "model": "FFT/DCT Analyzer (stub)",
                "weight": 0.30,
            },
            "skin_texture": {
                "score": texture_score,
                "model": "Texture Anomaly Net (stub)",
                "weight": 0.20,
            },
            "ensemble_vit": {
                "score": ensemble_score,
                "model": "ViT-Base (stub)",
                "weight": 0.15,
            },
        },
        "faces_detected": random.randint(1, 3),
        "confidence": round(abs(overall - 0.5) * 2, 4),  # 0=uncertain, 1=confident
        "trust_score": round(1.0 - overall, 4),
        "warning": "STUB DETECTOR — results are synthetic",
    }

    return DetectionResult(
        result_score=overall,
        result_detail=detail,
        model_version=MODEL_VERSION,
    )
