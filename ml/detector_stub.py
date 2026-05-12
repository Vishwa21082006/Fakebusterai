"""
FakeBuster AI — ML Detector (Enhanced)
Production-grade detection using multiple real analysis techniques:
  1. FFT Frequency Analysis — spectral slope & high-freq energy
  2. Edge Coherence Analysis — Sobel-based edge density & consistency
  3. Texture Analysis — local variance, entropy, smoothness artifacts
  4. Color & Statistical Analysis — histogram uniformity, noise patterns

Interface contract:
    detect(file_path: str) → DetectionResult
    - result_score: float (0.0 = real, 1.0 = fake)
    - result_detail: dict with per-layer breakdown
    - model_version: str
"""

import os
import math
import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

try:
    import numpy as np
    from PIL import Image, ImageFilter
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False
    logger.warning("numpy/Pillow not available — using fallback detection")

MODEL_VERSION = "forensic-v2.0.0"

# Analysis resolution — balance between accuracy and speed
ANALYSIS_SIZE = 256

# ── Trained ML Model (loaded once at import time) ──
_ML_MODEL = None
_ML_SCALER = None
_ML_PCA = None
_ML_IMG_SIZE = 128

def _load_ml_model():
    """Load the trained classifier model if available."""
    global _ML_MODEL, _ML_SCALER, _ML_PCA, _ML_IMG_SIZE, MODEL_VERSION
    model_path = os.path.join(os.path.dirname(__file__), "trained_model.pkl")
    if os.path.exists(model_path):
        try:
            import joblib
            data = joblib.load(model_path)
            _ML_MODEL = data["model"]
            _ML_SCALER = data["scaler"]
            _ML_PCA = data.get("pca")
            _ML_IMG_SIZE = data.get("img_size", 128)
            MODEL_VERSION = data.get("version", MODEL_VERSION)
            logger.info(f"ML model loaded: {MODEL_VERSION} (val_acc={data.get('val_accuracy', '?')}%)")
            return True
        except Exception as e:
            logger.warning(f"Failed to load ML model: {e}")
    return False

# Try to load on import
if NUMPY_AVAILABLE:
    _load_ml_model()


@dataclass
class DetectionResult:
    """Structured output from the detection pipeline."""
    result_score: float
    result_detail: dict = field(default_factory=dict)
    model_version: str = MODEL_VERSION


# ═══════════════════════════════════════
# Layer 1: FFT Frequency Analysis
# ═══════════════════════════════════════
def _analyze_fft(img_gray: 'np.ndarray') -> dict:
    """
    Analyze frequency domain characteristics.
    AI-generated images often have:
    - Steeper spectral slope (less high-freq detail)
    - Periodic artifacts from upsampling layers
    - Unnatural frequency distribution
    """
    try:
        # 2D FFT
        f = np.fft.fft2(img_gray.astype(np.float64))
        fshift = np.fft.fftshift(f)
        magnitude = np.abs(fshift)
        magnitude[magnitude == 0] = 1e-10
        log_magnitude = np.log(magnitude)

        h, w = img_gray.shape
        cy, cx = h // 2, w // 2

        # Azimuthal averaging — compute radial power spectrum
        Y, X = np.ogrid[:h, :w]
        R = np.sqrt((X - cx) ** 2 + (Y - cy) ** 2).astype(int)
        max_r = min(cx, cy)

        radial_profile = np.zeros(max_r)
        for r in range(1, max_r):
            mask = R == r
            if np.any(mask):
                radial_profile[r] = np.mean(log_magnitude[mask])

        # Compute spectral slope (log-log regression)
        valid = radial_profile[1:] > 0
        r_vals = np.arange(1, max_r)
        if np.sum(valid) > 10:
            log_r = np.log(r_vals[valid])
            log_p = radial_profile[1:][valid]
            # Linear fit in log-log space
            coeffs = np.polyfit(log_r, log_p, 1)
            spectral_slope = coeffs[0]
        else:
            spectral_slope = -1.2

        # CALIBRATED from real data: slopes range -0.85 (rich HF) to -1.56 (smooth)
        # Steeper negative slope = less high-freq detail = more likely AI
        # Real photos with lots of texture: ~ -0.85 to -1.1
        # AI-generated faces: ~ -1.3 to -1.6
        slope_score = np.clip((abs(spectral_slope) - 0.9) / 0.7, 0.0, 1.0)

        # High-frequency energy ratio
        low_r = max_r // 4
        high_r = max_r * 3 // 4
        low_mask = R <= low_r
        high_mask = (R >= high_r) & (R < max_r)

        low_energy = np.mean(magnitude[low_mask]) if np.any(low_mask) else 1.0
        high_energy = np.mean(magnitude[high_mask]) if np.any(high_mask) else 0.0

        hf_ratio = high_energy / (low_energy + 1e-10)

        # CALIBRATED: real HF ratios range 0.03-0.15
        # Lower ratio = less high-freq energy = more likely AI
        # Real textured images: 0.06-0.15, AI smooth faces: 0.03-0.05
        hf_score = np.clip(1.0 - (hf_ratio - 0.03) / 0.12, 0.0, 1.0)

        # Check for periodic artifacts (peaks in radial spectrum)
        if len(radial_profile) > 20:
            detrended = radial_profile[5:] - np.convolve(
                radial_profile[5:], np.ones(5) / 5, mode='same'
            )
            peak_std = np.std(detrended)
            artifact_score = np.clip(peak_std / 1.0, 0.0, 1.0)
        else:
            artifact_score = 0.0

        # Combined FFT score
        combined = 0.40 * slope_score + 0.40 * hf_score + 0.20 * artifact_score

        return {
            "score": round(float(combined), 4),
            "spectral_slope": round(float(spectral_slope), 4),
            "hf_ratio": round(float(hf_ratio), 6),
            "artifact_indicator": round(float(artifact_score), 4),
        }

    except Exception as e:
        logger.error(f"FFT analysis error: {e}")
        return {"score": 0.5, "error": str(e)}


# ═══════════════════════════════════════
# Layer 2: Edge Coherence Analysis
# ═══════════════════════════════════════
def _analyze_edges(img_gray: 'np.ndarray') -> dict:
    """
    Analyze edge patterns using Sobel filters.
    AI-generated images often have:
    - Smoother edges (less sharp transitions)
    - More uniform edge density (real photos have variable regions)
    - Unnatural edge orientation distributions
    """
    try:
        img_f = img_gray.astype(np.float64)

        # Sobel filters
        sobel_x = np.array([[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]], dtype=np.float64)
        sobel_y = np.array([[-1, -2, -1], [0, 0, 0], [1, 2, 1]], dtype=np.float64)

        # Manual convolution using numpy
        from numpy.lib.stride_tricks import sliding_window_view
        windows = sliding_window_view(img_f, (3, 3))
        gx = np.sum(windows * sobel_x, axis=(-2, -1))
        gy = np.sum(windows * sobel_y, axis=(-2, -1))

        edge_magnitude = np.sqrt(gx**2 + gy**2)
        edge_direction = np.arctan2(gy, gx)

        # Overall edge density
        edge_density = np.mean(edge_magnitude) / 255.0

        # Edge variance — how uniform are edges across the image
        h, w = edge_magnitude.shape
        block_size = max(h // 4, 1)
        block_variances = []
        for i in range(0, h - block_size, block_size):
            for j in range(0, w - block_size, block_size):
                block = edge_magnitude[i:i+block_size, j:j+block_size]
                block_variances.append(np.var(block))

        if block_variances:
            edge_uniformity = 1.0 - min(np.std(block_variances) / (np.mean(block_variances) + 1e-10), 1.0)
        else:
            edge_uniformity = 0.5

        # Edge direction histogram — check for unnatural orientations
        direction_hist, _ = np.histogram(edge_direction.flatten(), bins=36, range=(-np.pi, np.pi))
        direction_hist = direction_hist / (direction_hist.sum() + 1e-10)
        direction_entropy = -np.sum(direction_hist[direction_hist > 0] * np.log2(direction_hist[direction_hist > 0]))
        max_entropy = np.log2(36)
        direction_uniformity = direction_entropy / max_entropy

        # CALIBRATED: edge_density ranges 0.15-0.60
        # Real textured photos: 0.30-0.60, AI faces: 0.15-0.25
        density_score = np.clip(1.0 - (edge_density - 0.12) / 0.40, 0.0, 1.0)
        # Soften uniformity — real photos can also have uniform areas
        uniformity_score = edge_uniformity * 0.8
        direction_score = np.clip((direction_uniformity - 0.93) / 0.05, 0.0, 1.0)

        combined = 0.45 * density_score + 0.30 * uniformity_score + 0.25 * direction_score

        return {
            "score": round(float(combined), 4),
            "edge_density": round(float(edge_density), 4),
            "edge_uniformity": round(float(edge_uniformity), 4),
            "direction_diversity": round(float(direction_uniformity), 4),
        }

    except Exception as e:
        logger.error(f"Edge analysis error: {e}")
        return {"score": 0.5, "error": str(e)}


# ═══════════════════════════════════════
# Layer 3: Texture & Noise Analysis
# ═══════════════════════════════════════
def _analyze_texture(img_gray: 'np.ndarray') -> dict:
    """
    Analyze texture patterns and noise characteristics.
    AI images often have:
    - Lower local variance in smooth regions
    - Different noise distribution than camera sensor noise
    - Over-smoothed textures with periodic patterns
    """
    try:
        img_f = img_gray.astype(np.float64)

        # Local variance (3x3 blocks)
        from numpy.lib.stride_tricks import sliding_window_view
        windows = sliding_window_view(img_f, (3, 3))
        local_var = np.var(windows, axis=(-2, -1))

        # Separate smooth vs textured regions
        smooth_threshold = np.percentile(local_var, 25)
        textured_threshold = np.percentile(local_var, 75)

        smooth_regions = local_var[local_var < smooth_threshold]
        textured_regions = local_var[local_var > textured_threshold]

        # CALIBRATED: smooth_mean ranges 0.07-30
        # Real textured: 1.7-30, AI smooth: 0.07-1.7
        if len(smooth_regions) > 0:
            smooth_mean = np.mean(smooth_regions)
            # Higher threshold: only flag extremely smooth regions
            smoothness_score = np.clip(1.0 - smooth_mean / 15.0, 0.0, 1.0)
        else:
            smoothness_score = 0.5

        # Texture consistency — check if texture is unnaturally uniform
        if len(textured_regions) > 0:
            tex_cv = np.std(textured_regions) / (np.mean(textured_regions) + 1e-10)
            texture_uniformity = np.clip(1.0 - tex_cv / 2.0, 0.0, 1.0)
        else:
            texture_uniformity = 0.5

        # Noise estimation using Laplacian
        laplacian_kernel = np.array([[0, 1, 0], [1, -4, 1], [0, 1, 0]], dtype=np.float64)
        lap_windows = sliding_window_view(img_f, (3, 3))
        laplacian = np.abs(np.sum(lap_windows * laplacian_kernel, axis=(-2, -1)))

        noise_level = np.median(laplacian) / (np.mean(laplacian) + 1e-10)
        # CALIBRATED: noise_ratio ranges 0.17-0.68
        # Real photos with natural noise: 0.55-0.68
        # AI-generated (clean): 0.17-0.42
        noise_score = np.clip(1.0 - (noise_level - 0.15) / 0.55, 0.0, 1.0)

        # Local entropy approximation
        hist, _ = np.histogram(img_gray, bins=64, range=(0, 256))
        hist_norm = hist / (hist.sum() + 1e-10)
        global_entropy = -np.sum(hist_norm[hist_norm > 0] * np.log2(hist_norm[hist_norm > 0]))
        max_entropy = np.log2(64)

        # Very low or very high entropy can indicate manipulation
        entropy_ratio = global_entropy / max_entropy
        entropy_score = np.clip(abs(entropy_ratio - 0.80) * 5, 0.0, 1.0)

        combined = (0.30 * smoothness_score + 0.25 * texture_uniformity +
                    0.25 * noise_score + 0.20 * entropy_score)

        return {
            "score": round(float(combined), 4),
            "smoothness": round(float(smoothness_score), 4),
            "texture_uniformity": round(float(texture_uniformity), 4),
            "noise_pattern": round(float(noise_score), 4),
            "entropy_ratio": round(float(entropy_ratio), 4),
        }

    except Exception as e:
        logger.error(f"Texture analysis error: {e}")
        return {"score": 0.5, "error": str(e)}


# ═══════════════════════════════════════
# Layer 4: Color & Statistical Analysis
# ═══════════════════════════════════════
def _analyze_color(img_rgb: 'np.ndarray') -> dict:
    """
    Analyze color patterns and statistical distributions.
    AI-generated images often have:
    - Unnatural color channel correlations
    - Overly smooth color gradients
    - Atypical histogram shapes
    """
    try:
        # Channel correlation analysis
        r, g, b = img_rgb[:, :, 0].astype(float), img_rgb[:, :, 1].astype(float), img_rgb[:, :, 2].astype(float)

        # Cross-channel correlation
        rg_corr = np.corrcoef(r.flatten(), g.flatten())[0, 1]
        rb_corr = np.corrcoef(r.flatten(), b.flatten())[0, 1]
        gb_corr = np.corrcoef(g.flatten(), b.flatten())[0, 1]

        # CALIBRATED: avg_corr ranges 0.70-0.98
        # Real diverse scenes: 0.70-0.80, AI faces/portraits: 0.92-0.98
        avg_corr = (abs(rg_corr) + abs(rb_corr) + abs(gb_corr)) / 3
        corr_score = np.clip((avg_corr - 0.75) / 0.20, 0.0, 1.0)

        # Per-channel histogram smoothness
        channel_scores = []
        for ch in [r, g, b]:
            hist, _ = np.histogram(ch.flatten(), bins=256, range=(0, 256))
            hist_smooth = np.convolve(hist, np.ones(5) / 5, mode='same')
            roughness = np.mean(np.abs(hist - hist_smooth)) / (np.mean(hist) + 1e-10)
            # AI images often have smoother histograms
            channel_scores.append(np.clip(1.0 - roughness * 1.5, 0.0, 1.0))
        hist_score = np.mean(channel_scores)

        # Color saturation analysis
        max_rgb = np.maximum(np.maximum(r, g), b)
        min_rgb = np.minimum(np.minimum(r, g), b)
        saturation = (max_rgb - min_rgb) / (max_rgb + 1e-10)

        sat_mean = np.mean(saturation)
        sat_std = np.std(saturation)

        # AI images can have unnaturally uniform saturation
        sat_uniformity = np.clip(1.0 - sat_std / 0.25, 0.0, 1.0)

        # Gradient smoothness in color space
        r_grad = np.diff(r, axis=1)
        g_grad = np.diff(g, axis=1)
        b_grad = np.diff(b, axis=1)

        n_samp = min(2000, len(r_grad.flatten()))
        grad_consistency = np.mean([
            np.corrcoef(r_grad.flatten()[:n_samp], g_grad.flatten()[:n_samp])[0, 1],
            np.corrcoef(r_grad.flatten()[:n_samp], b_grad.flatten()[:n_samp])[0, 1],
        ])
        grad_score = np.clip((abs(grad_consistency) - 0.2) / 0.6, 0.0, 1.0) if not np.isnan(grad_consistency) else 0.5

        combined = 0.35 * corr_score + 0.20 * hist_score + 0.20 * sat_uniformity + 0.25 * grad_score

        return {
            "score": round(float(combined), 4),
            "channel_correlation": round(float(avg_corr), 4),
            "histogram_smoothness": round(float(hist_score), 4),
            "saturation_uniformity": round(float(sat_uniformity), 4),
            "gradient_consistency": round(float(grad_score), 4),
        }

    except Exception as e:
        logger.error(f"Color analysis error: {e}")
        return {"score": 0.5, "error": str(e)}


# ═══════════════════════════════════════
# Layer 5: JPEG Compression Artifact Detection
# ═══════════════════════════════════════
def _detect_jpeg_artifacts(img_gray: 'np.ndarray') -> float:
    """
    Detect JPEG 8x8 block compression artifacts.
    Real photos compressed as JPEG have visible block boundaries.
    AI-generated images typically lack these artifacts.
    Returns a score: higher = more JPEG artifacts detected = more likely real.
    """
    try:
        h, w = img_gray.shape
        # Check for 8x8 block boundary discontinuities
        block_diffs_h = []
        block_diffs_v = []
        for i in range(8, h - 1, 8):
            diff = np.mean(np.abs(img_gray[i, :].astype(float) - img_gray[i-1, :].astype(float)))
            inner_diff = np.mean(np.abs(img_gray[i-1, :].astype(float) - img_gray[i-2, :].astype(float)))
            if inner_diff > 0:
                block_diffs_h.append(diff / (inner_diff + 1e-10))
        for j in range(8, w - 1, 8):
            diff = np.mean(np.abs(img_gray[:, j].astype(float) - img_gray[:, j-1].astype(float)))
            inner_diff = np.mean(np.abs(img_gray[:, j-1].astype(float) - img_gray[:, j-2].astype(float)))
            if inner_diff > 0:
                block_diffs_v.append(diff / (inner_diff + 1e-10))

        all_ratios = block_diffs_h + block_diffs_v
        if all_ratios:
            # Ratio > 1.0 means block boundaries have higher discontinuity
            avg_ratio = np.mean(all_ratios)
            # JPEG artifacts: ratio typically 1.05-1.5+
            # No artifacts: ratio ~1.0
            jpeg_score = np.clip((avg_ratio - 1.0) / 0.3, 0.0, 1.0)
            return float(jpeg_score)
        return 0.0
    except Exception:
        return 0.0


# ═══════════════════════════════════════
# ML Model Feature Extraction
# ═══════════════════════════════════════
def _extract_ml_features(file_path: str) -> 'np.ndarray':
    """
    Extract the same feature vector used during training.
    Must match train_model.py's extract_features() exactly.
    """
    try:
        img = Image.open(file_path).convert('RGB')
        small = img.resize((_ML_IMG_SIZE, _ML_IMG_SIZE), Image.LANCZOS)
        arr = np.array(small, dtype=np.float32) / 255.0
        gray = np.mean(arr, axis=2)
        features = []

        # 1. Color histograms (96)
        for ch in range(3):
            hist, _ = np.histogram(arr[:, :, ch], bins=32, range=(0, 1))
            features.extend((hist / (hist.sum() + 1e-10)).tolist())

        # 2. Per-channel stats (15)
        for ch in range(3):
            c = arr[:, :, ch]
            m, s = float(np.mean(c)), float(np.std(c)) + 1e-10
            features.extend([
                m, s, float(np.median(c)),
                float(np.mean(((c - m) / s) ** 3)),
                float(np.mean(((c - m) / s) ** 4)),
            ])

        # 3. Gradient features (8)
        dx = np.diff(gray, axis=1)
        dy = np.diff(gray, axis=0)
        features.extend([
            float(np.mean(np.abs(dx))), float(np.std(dx)),
            float(np.mean(np.abs(dy))), float(np.std(dy)),
            float(np.mean(dx ** 2)), float(np.mean(dy ** 2)),
            float(np.percentile(np.abs(dx), 95)),
            float(np.percentile(np.abs(dy), 95)),
        ])

        # 4. FFT radial spectrum (20)
        f = np.fft.fft2(gray)
        fshift = np.fft.fftshift(f)
        mag = np.log(np.abs(fshift) + 1e-10)
        h, w = gray.shape
        cy, cx = h // 2, w // 2
        Y, X = np.ogrid[:h, :w]
        R = np.sqrt((X - cx) ** 2 + (Y - cy) ** 2).astype(int)
        max_r = min(cx, cy)
        edges = np.linspace(0, max_r, 21).astype(int)
        for i in range(20):
            mask = (R >= edges[i]) & (R < edges[i + 1])
            features.append(float(np.mean(mag[mask])) if np.any(mask) else 0.0)

        # 5. Spatial block stats (32)
        bh, bw = h // 4, w // 4
        for bi in range(4):
            for bj in range(4):
                block = gray[bi * bh:(bi + 1) * bh, bj * bw:(bj + 1) * bw]
                features.extend([float(np.mean(block)), float(np.std(block))])

        # 6. Color correlations (3)
        r_flat = arr[:, :, 0].flatten()
        g_flat = arr[:, :, 1].flatten()
        b_flat = arr[:, :, 2].flatten()
        for ch_a, ch_b in [(r_flat, g_flat), (r_flat, b_flat), (g_flat, b_flat)]:
            cc = np.corrcoef(ch_a, ch_b)[0, 1]
            features.append(float(cc) if not np.isnan(cc) else 0.0)

        # 7. Noise residual stats (6)
        blurred = np.array(small.filter(ImageFilter.GaussianBlur(2)), dtype=np.float32) / 255.0
        noise = arr - blurred
        for ch in range(3):
            n = noise[:, :, ch]
            features.extend([float(np.mean(np.abs(n))), float(np.std(n))])

        # 8. Laplacian sharpness (3)
        from numpy.lib.stride_tricks import sliding_window_view
        lap_k = np.array([[0, 1, 0], [1, -4, 1], [0, 1, 0]], dtype=np.float32)
        windows = sliding_window_view(gray, (3, 3))
        lap = np.abs(np.sum(windows * lap_k, axis=(-2, -1)))
        features.extend([float(np.mean(lap)), float(np.std(lap)), float(np.median(lap))])

        # 9. Downsampled pixels (768)
        tiny = np.array(img.resize((16, 16), Image.LANCZOS), dtype=np.float32) / 255.0
        features.extend(tiny.flatten().tolist())

        result = np.array(features, dtype=np.float64)
        return np.nan_to_num(result, nan=0.0, posinf=1.0, neginf=-1.0)
    except Exception as e:
        logger.warning(f"ML feature extraction failed: {e}")
        return None


def _predict_ml(file_path: str) -> float:
    """
    Run the trained ML model on an image.
    Returns probability of being fake (0.0-1.0), or None if model unavailable.
    """
    if _ML_MODEL is None:
        return None

    features = _extract_ml_features(file_path)
    if features is None:
        return None

    try:
        X = features.reshape(1, -1)
        X_scaled = _ML_SCALER.transform(X)
        if _ML_PCA is not None:
            X_scaled = _ML_PCA.transform(X_scaled)

        if hasattr(_ML_MODEL, 'predict_proba'):
            prob = _ML_MODEL.predict_proba(X_scaled)[0][1]  # P(fake)
        else:
            # For models without predict_proba (e.g., LinearSVC)
            pred = _ML_MODEL.predict(X_scaled)[0]
            prob = float(pred)

        return float(prob)
    except Exception as e:
        logger.warning(f"ML prediction failed: {e}")
        return None


# ═══════════════════════════════════════
# Image Loading & Preprocessing
# ═══════════════════════════════════════
def _load_image(file_path: str) -> tuple:
    """Load and preprocess image. Returns (gray_array, rgb_array) or (None, None)."""
    try:
        img = Image.open(file_path)
        # Handle various modes
        if img.mode == 'RGBA':
            # Composite onto white background
            bg = Image.new('RGB', img.size, (255, 255, 255))
            bg.paste(img, mask=img.split()[3])
            img = bg
        elif img.mode != 'RGB':
            img = img.convert('RGB')

        img = img.resize((ANALYSIS_SIZE, ANALYSIS_SIZE), Image.LANCZOS)
        rgb_array = np.array(img)
        gray_array = np.mean(rgb_array, axis=2).astype(np.float64)

        return gray_array, rgb_array
    except Exception as e:
        logger.error(f"Image load error: {e}")
        return None, None


def _extract_video_frames(file_path: str, max_frames: int = 5) -> list:
    """Extract key frames from video for analysis."""
    frames = []
    try:
        # Try using PIL for GIF/animated formats
        img = Image.open(file_path)
        if hasattr(img, 'n_frames') and img.n_frames > 1:
            step = max(img.n_frames // max_frames, 1)
            for i in range(0, img.n_frames, step):
                if len(frames) >= max_frames:
                    break
                img.seek(i)
                frame = img.copy().convert('RGB').resize((ANALYSIS_SIZE, ANALYSIS_SIZE), Image.LANCZOS)
                frames.append(np.array(frame))
    except Exception:
        pass

    if not frames:
        # For video formats PIL can't handle, try to read just the first frame
        try:
            img = Image.open(file_path).convert('RGB').resize(
                (ANALYSIS_SIZE, ANALYSIS_SIZE), Image.LANCZOS
            )
            frames.append(np.array(img))
        except Exception as e:
            logger.warning(f"Could not extract video frames: {e}")

    return frames


# ═══════════════════════════════════════
# Main Detection Entry Point
# ═══════════════════════════════════════
def detect(file_path: str) -> DetectionResult:
    """
    Run full forensic analysis pipeline on an image or video file.
    Returns a DetectionResult with overall score and per-layer breakdown.
    """
    if not NUMPY_AVAILABLE:
        return DetectionResult(
            result_score=0.5,
            result_detail={
                "error": "numpy/Pillow not available",
                "verdict": "Unable to analyze — dependencies missing",
            },
        )

    if not os.path.exists(file_path):
        return DetectionResult(
            result_score=0.5,
            result_detail={
                "error": f"File not found: {file_path}",
                "verdict": "Unable to analyze — file not found",
            },
        )

    # Determine if image or video
    ext = os.path.splitext(file_path)[1].lower()
    is_video = ext in {'.mp4', '.webm', '.avi', '.mov', '.mkv', '.gif'}

    if is_video:
        return _detect_video(file_path)
    else:
        return _detect_image(file_path)


def _detect_image(file_path: str) -> DetectionResult:
    """Run full analysis on a single image."""
    gray, rgb = _load_image(file_path)

    if gray is None or rgb is None:
        return DetectionResult(
            result_score=0.5,
            result_detail={
                "error": "Could not load image",
                "verdict": "Unable to analyze — image could not be loaded",
            },
        )

    # Run all analysis layers (always needed for explainability)
    fft_result = _analyze_fft(gray)
    edge_result = _analyze_edges(gray)
    texture_result = _analyze_texture(gray)
    color_result = _analyze_color(rgb)

    # Detect JPEG artifacts — real photos often have these, AI images don't
    jpeg_artifact_score = _detect_jpeg_artifacts(gray)

    # Heuristic ensemble
    weights = {
        "frequency_analysis": 0.35,
        "edge_coherence": 0.20,
        "texture_analysis": 0.25,
        "color_statistics": 0.20,
    }

    scores = {
        "frequency_analysis": fft_result.get("score", 0.5),
        "edge_coherence": edge_result.get("score", 0.5),
        "texture_analysis": texture_result.get("score", 0.5),
        "color_statistics": color_result.get("score", 0.5),
    }

    heuristic_score = sum(scores[k] * weights[k] for k in weights)

    # ── ML Model prediction (primary scorer when available) ──
    ml_score = _predict_ml(file_path)

    if ml_score is not None:
        # Blend: ML model dominates, heuristics provide small adjustment
        overall = 0.85 * ml_score + 0.15 * heuristic_score
        scores["ml_classifier"] = round(ml_score, 4)
    else:
        overall = heuristic_score

    # Apply heuristic corrections ONLY when ML model is not available
    # (These were calibrated for heuristics and interfere with ML predictions)
    if ml_score is None and jpeg_artifact_score > 0.2:
        correction = jpeg_artifact_score * 0.20
        overall = max(0.0, overall - correction)

    # Camera noise fingerprint (heuristic only — skip when ML model active)
    if ml_score is None:
        try:
            from numpy.lib.stride_tricks import sliding_window_view
            smooth_kernel = np.ones((5, 5)) / 25.0
            windows = sliding_window_view(gray, (5, 5))
            smoothed = np.mean(windows, axis=(-2, -1))
            noise_residual = gray[2:-2, 2:-2] - smoothed
            h, w = noise_residual.shape
            block_sz = 16
            block_stds = []
            for bi in range(0, h - block_sz, block_sz):
                for bj in range(0, w - block_sz, block_sz):
                    block_stds.append(np.std(noise_residual[bi:bi+block_sz, bj:bj+block_sz]))
            if len(block_stds) > 4:
                noise_cv = np.std(block_stds) / (np.mean(block_stds) + 1e-10)
                if noise_cv > 0.5:
                    overall = max(0.0, overall - 0.08)
                elif noise_cv < 0.2:
                    overall = min(1.0, overall + 0.05)
        except Exception:
            pass

    overall = round(float(overall), 4)

    # Confidence: how much agreement between layers
    score_values = list(scores.values())
    score_std = float(np.std(score_values))
    confidence = round(max(0.0, min(1.0, 1.0 - score_std * 2)), 4)

    # Generate human-readable verdict
    verdict = _generate_verdict(overall, confidence, "image")

    detail = {
        "layers": {
            "frequency_analysis": {
                "score": fft_result["score"],
                "model": "FFT Spectral Analysis",
                "weight": weights["frequency_analysis"],
                "details": {k: v for k, v in fft_result.items() if k != "score"},
            },
            "edge_coherence": {
                "score": edge_result["score"],
                "model": "Sobel Edge Coherence",
                "weight": weights["edge_coherence"],
                "details": {k: v for k, v in edge_result.items() if k != "score"},
            },
            "texture_analysis": {
                "score": texture_result["score"],
                "model": "Texture & Noise Forensics",
                "weight": weights["texture_analysis"],
                "details": {k: v for k, v in texture_result.items() if k != "score"},
            },
            "color_statistics": {
                "score": color_result["score"],
                "model": "Color Statistical Analysis",
                "weight": weights["color_statistics"],
                "details": {k: v for k, v in color_result.items() if k != "score"},
            },
        },
        "confidence": confidence,
        "trust_score": round(1.0 - overall, 4),
        "verdict": verdict,
        "media_type": "image",
        "analysis_resolution": f"{ANALYSIS_SIZE}x{ANALYSIS_SIZE}",
    }

    return DetectionResult(
        result_score=overall,
        result_detail=detail,
        model_version=MODEL_VERSION,
    )


def _detect_video(file_path: str) -> DetectionResult:
    """Run analysis on video by sampling frames."""
    frames = _extract_video_frames(file_path, max_frames=5)

    if not frames:
        # Fall back to trying image detection
        return _detect_image(file_path)

    # Analyze each frame
    frame_scores = []
    frame_details = []

    for i, frame_rgb in enumerate(frames):
        gray = np.mean(frame_rgb, axis=2).astype(np.float64)

        fft_result = _analyze_fft(gray)
        edge_result = _analyze_edges(gray)
        texture_result = _analyze_texture(gray)
        color_result = _analyze_color(frame_rgb)

        frame_score = (
            0.30 * fft_result.get("score", 0.5) +
            0.25 * edge_result.get("score", 0.5) +
            0.25 * texture_result.get("score", 0.5) +
            0.20 * color_result.get("score", 0.5)
        )
        frame_scores.append(frame_score)
        frame_details.append({
            "frame": i,
            "score": round(frame_score, 4),
            "fft": fft_result.get("score", 0.5),
            "edge": edge_result.get("score", 0.5),
            "texture": texture_result.get("score", 0.5),
            "color": color_result.get("score", 0.5),
        })

    # Use median to reduce outlier influence
    overall = round(float(np.median(frame_scores)), 4)
    consistency = round(float(1.0 - np.std(frame_scores) * 2), 4)
    confidence = round(max(0.0, min(1.0, consistency)), 4)

    verdict = _generate_verdict(overall, confidence, "video")

    # Use first frame for detailed layer breakdown
    gray_first = np.mean(frames[0], axis=2).astype(np.float64)
    fft_result = _analyze_fft(gray_first)
    edge_result = _analyze_edges(gray_first)
    texture_result = _analyze_texture(gray_first)
    color_result = _analyze_color(frames[0])

    detail = {
        "layers": {
            "frequency_analysis": {
                "score": fft_result["score"],
                "model": "FFT Spectral Analysis",
                "weight": 0.30,
            },
            "edge_coherence": {
                "score": edge_result["score"],
                "model": "Sobel Edge Coherence",
                "weight": 0.25,
            },
            "texture_analysis": {
                "score": texture_result["score"],
                "model": "Texture & Noise Forensics",
                "weight": 0.25,
            },
            "color_statistics": {
                "score": color_result["score"],
                "model": "Color Statistical Analysis",
                "weight": 0.20,
            },
        },
        "confidence": confidence,
        "trust_score": round(1.0 - overall, 4),
        "verdict": verdict,
        "media_type": "video",
        "frames_analyzed": len(frames),
        "frame_scores": frame_details,
        "frame_consistency": round(float(consistency), 4),
    }

    return DetectionResult(
        result_score=overall,
        result_detail=detail,
        model_version=MODEL_VERSION,
    )


# ═══════════════════════════════════════
# Human-Readable Verdict Generator
# ═══════════════════════════════════════
def _generate_verdict(score: float, confidence: float, media_type: str) -> str:
    """
    Generate a clear, user-friendly verdict string.
    Examples:
      "This image is probably 87% AI-generated"
      "This video appears to be authentic (92% confidence)"
    """
    fake_pct = round(score * 100)
    real_pct = round((1.0 - score) * 100)
    conf_pct = round(confidence * 100)

    media = media_type.capitalize()

    if score >= 0.85:
        return f"This {media_type} is very likely AI-generated ({fake_pct}% fake probability, {conf_pct}% confidence)"
    elif score >= 0.65:
        return f"This {media_type} is probably {fake_pct}% AI-generated ({conf_pct}% confidence)"
    elif score >= 0.45:
        return f"This {media_type} shows mixed signals — {fake_pct}% fake probability. Manual review recommended."
    elif score >= 0.25:
        return f"This {media_type} appears to be mostly authentic ({real_pct}% real probability, {conf_pct}% confidence)"
    else:
        return f"This {media_type} appears to be authentic ({real_pct}% real probability, {conf_pct}% confidence)"
