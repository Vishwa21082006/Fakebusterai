#!/usr/bin/env python3
"""
FakeBuster AI — Multi-Dataset Model Training
Trains on BOTH datasets for maximum generalization:
  - Dataset 1: 140k Real & Fake Faces (256×256 JPG)
  - Dataset 2: AI-face-detection (768×768 AI JPG + 150×150 real PNG)

Usage:
    python train_model.py
    python train_model.py --samples 10000
"""
import sys, time, random, warnings, argparse
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter
import joblib

warnings.filterwarnings("ignore")

# Dataset paths
DS1_PATH = Path("/home/vishwa/Downloads/Dataset")
DS2_PATH = Path("/home/vishwa/Downloads/AI-face-detection-Dataset")
MODEL_OUTPUT = Path(__file__).resolve().parent / "trained_model.pkl"
IMG_SIZE = 128


def extract_features(file_path: str) -> np.ndarray:
    """
    Extract comprehensive feature vector from an image.
    Handles RGB, RGBA, LA, and grayscale images.
    Returns ~951 features.
    """
    try:
        img = Image.open(file_path)
        # Convert any mode to RGB
        if img.mode != 'RGB':
            img = img.convert('RGB')

        small = img.resize((IMG_SIZE, IMG_SIZE), Image.LANCZOS)
        arr = np.array(small, dtype=np.float32) / 255.0
        gray = np.mean(arr, axis=2)

        features = []

        # ── 1. Color histograms (3 × 32 = 96) ──
        for ch in range(3):
            hist, _ = np.histogram(arr[:, :, ch], bins=32, range=(0, 1))
            features.extend((hist / (hist.sum() + 1e-10)).tolist())

        # ── 2. Per-channel statistics (3 × 5 = 15) ──
        for ch in range(3):
            c = arr[:, :, ch]
            m, s = np.mean(c), np.std(c) + 1e-10
            features.extend([
                float(m), float(s), float(np.median(c)),
                float(np.mean(((c - m) / s) ** 3)),  # skewness
                float(np.mean(((c - m) / s) ** 4)),  # kurtosis
            ])

        # ── 3. Gradient features (8) ──
        dx = np.diff(gray, axis=1)
        dy = np.diff(gray, axis=0)
        features.extend([
            np.mean(np.abs(dx)), np.std(dx),
            np.mean(np.abs(dy)), np.std(dy),
            np.mean(dx ** 2), np.mean(dy ** 2),
            np.percentile(np.abs(dx), 95),
            np.percentile(np.abs(dy), 95),
        ])

        # ── 4. FFT radial spectrum (20) ──
        f = np.fft.fft2(gray)
        fshift = np.fft.fftshift(f)
        mag = np.log(np.abs(fshift) + 1e-10)
        h, w = gray.shape
        cy, cx = h // 2, w // 2
        Y, X = np.ogrid[:h, :w]
        R = np.sqrt((X - cx) ** 2 + (Y - cy) ** 2).astype(int)
        max_r = min(cx, cy)
        n_bins = 20
        edges = np.linspace(0, max_r, n_bins + 1).astype(int)
        for i in range(n_bins):
            mask = (R >= edges[i]) & (R < edges[i + 1])
            features.append(float(np.mean(mag[mask])) if np.any(mask) else 0.0)

        # ── 5. Spatial block stats (4×4 grid × 2 = 32) ──
        bh, bw = h // 4, w // 4
        for bi in range(4):
            for bj in range(4):
                block = gray[bi * bh:(bi + 1) * bh, bj * bw:(bj + 1) * bw]
                features.extend([float(np.mean(block)), float(np.std(block))])

        # ── 6. Color correlations (3) ──
        r_flat = arr[:, :, 0].flatten()
        g_flat = arr[:, :, 1].flatten()
        b_flat = arr[:, :, 2].flatten()
        for ch_a, ch_b in [(r_flat, g_flat), (r_flat, b_flat), (g_flat, b_flat)]:
            cc = np.corrcoef(ch_a, ch_b)[0, 1]
            features.append(float(cc) if not np.isnan(cc) else 0.0)

        # ── 7. Noise residual stats (6) ──
        blurred = np.array(small.filter(ImageFilter.GaussianBlur(2)), dtype=np.float32) / 255.0
        noise = arr - blurred
        for ch in range(3):
            n = noise[:, :, ch]
            features.extend([float(np.mean(np.abs(n))), float(np.std(n))])

        # ── 8. Laplacian sharpness (3) ──
        from numpy.lib.stride_tricks import sliding_window_view
        lap_k = np.array([[0, 1, 0], [1, -4, 1], [0, 1, 0]], dtype=np.float32)
        windows = sliding_window_view(gray, (3, 3))
        lap = np.abs(np.sum(windows * lap_k, axis=(-2, -1)))
        features.extend([float(np.mean(lap)), float(np.std(lap)), float(np.median(lap))])

        # ── 9. Downsampled pixels (16×16×3 = 768) ──
        tiny = np.array(img.resize((16, 16), Image.LANCZOS), dtype=np.float32) / 255.0
        features.extend(tiny.flatten().tolist())

        result = np.array(features, dtype=np.float64)
        return np.nan_to_num(result, nan=0.0, posinf=1.0, neginf=-1.0)
    except Exception as e:
        return None


def collect_files(path: Path, exts=("*.jpg", "*.jpeg", "*.png", "*.webp")):
    """Collect all image files from a directory."""
    files = []
    for ext in exts:
        files.extend(sorted(path.glob(ext)))
    return files


def load_multi_dataset(n_per_class: int, seed=42):
    """
    Load training data from BOTH datasets.
    Allocates samples proportionally based on dataset size.
    """
    random.seed(seed)

    # Dataset 1: Train split
    ds1_fake = collect_files(DS1_PATH / "Train" / "Fake")
    ds1_real = collect_files(DS1_PATH / "Train" / "Real")

    # Dataset 2: AI-face-detection
    ds2_fake = collect_files(DS2_PATH / "AI")
    ds2_real = collect_files(DS2_PATH / "real")

    print(f"  DS1 Train: {len(ds1_fake)} fake, {len(ds1_real)} real")
    print(f"  DS2: {len(ds2_fake)} AI-fake, {len(ds2_real)} real")

    # Use ALL of DS2 (it's small) + sample from DS1
    ds2_fake_sample = ds2_fake  # all 1001
    ds2_real_sample = ds2_real  # all 2202

    remaining_fake = max(0, n_per_class - len(ds2_fake_sample))
    remaining_real = max(0, n_per_class - len(ds2_real_sample))

    ds1_fake_sample = random.sample(ds1_fake, min(remaining_fake, len(ds1_fake)))
    ds1_real_sample = random.sample(ds1_real, min(remaining_real, len(ds1_real)))

    all_fake = ds2_fake_sample + ds1_fake_sample
    all_real = ds2_real_sample + ds1_real_sample
    random.shuffle(all_fake)
    random.shuffle(all_real)

    print(f"  Combined: {len(all_fake)} fake, {len(all_real)} real")

    X, y, errors = [], [], 0
    t0 = time.time()

    for i, f in enumerate(all_fake):
        feat = extract_features(str(f))
        if feat is not None:
            X.append(feat)
            y.append(1)
        else:
            errors += 1
        if (i + 1) % 2000 == 0:
            print(f"    Fake: {i+1}/{len(all_fake)}")

    for i, f in enumerate(all_real):
        feat = extract_features(str(f))
        if feat is not None:
            X.append(feat)
            y.append(0)
        else:
            errors += 1
        if (i + 1) % 2000 == 0:
            print(f"    Real: {i+1}/{len(all_real)}")

    elapsed = time.time() - t0
    print(f"  ✓ {len(X)} samples in {elapsed:.0f}s ({errors} errors)")
    return np.array(X), np.array(y)


def load_validation(n_per_class=500, seed=99):
    """Load validation data from DS1 validation split + DS2 holdout."""
    random.seed(seed)

    # DS1 validation
    ds1_fake = collect_files(DS1_PATH / "Validation" / "Fake")
    ds1_real = collect_files(DS1_PATH / "Validation" / "Real")

    # For DS2, use 20% as validation (holdout from training)
    ds2_fake = collect_files(DS2_PATH / "AI")
    ds2_real = collect_files(DS2_PATH / "real")
    random.seed(seed)
    ds2_fake_val = random.sample(ds2_fake, min(200, len(ds2_fake)))
    ds2_real_val = random.sample(ds2_real, min(400, len(ds2_real)))

    fake_sample = random.sample(ds1_fake, min(n_per_class - len(ds2_fake_val), len(ds1_fake)))
    real_sample = random.sample(ds1_real, min(n_per_class - len(ds2_real_val), len(ds1_real)))

    all_fake = ds2_fake_val + fake_sample
    all_real = ds2_real_val + real_sample

    X, y, errors = [], [], 0
    t0 = time.time()

    for f in all_fake:
        feat = extract_features(str(f))
        if feat is not None:
            X.append(feat)
            y.append(1)
        else:
            errors += 1
    for f in all_real:
        feat = extract_features(str(f))
        if feat is not None:
            X.append(feat)
            y.append(0)
        else:
            errors += 1

    elapsed = time.time() - t0
    print(f"  ✓ Val: {len(X)} samples in {elapsed:.0f}s ({errors} errors)")
    return np.array(X), np.array(y)


def main():
    parser = argparse.ArgumentParser(description="Train FakeBuster model")
    parser.add_argument("--samples", type=int, default=8000,
                        help="Target samples per class for training")
    args = parser.parse_args()

    print("=" * 60)
    print("  FakeBuster AI — Multi-Dataset Training")
    print("=" * 60)

    # Load combined training data
    print(f"\n  Loading TRAINING data (~{args.samples}/class)...")
    X_train, y_train = load_multi_dataset(args.samples)

    print(f"\n  Loading VALIDATION data...")
    X_val, y_val = load_validation(n_per_class=800)

    n_feat = X_train.shape[1]
    print(f"\n  Features: {n_feat} | Train: {X_train.shape[0]} | Val: {X_val.shape[0]}")
    print(f"  Train balance: {sum(y_train==1)} fake / {sum(y_train==0)} real")
    print(f"  Val balance:   {sum(y_val==1)} fake / {sum(y_val==0)} real")

    from sklearn.preprocessing import StandardScaler
    from sklearn.decomposition import PCA
    from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import accuracy_score, classification_report

    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_val_s = scaler.transform(X_val)

    n_comp = min(300, n_feat - 1, X_train.shape[0] - 1)
    print(f"\n  PCA → {n_comp} components...")
    pca = PCA(n_components=n_comp, random_state=42)
    X_train_pca = pca.fit_transform(X_train_s)
    X_val_pca = pca.transform(X_val_s)
    print(f"  Variance captured: {sum(pca.explained_variance_ratio_)*100:.1f}%")

    models = {
        "GradientBoosting": GradientBoostingClassifier(
            n_estimators=400, max_depth=6, learning_rate=0.08,
            subsample=0.8, min_samples_leaf=5, random_state=42,
        ),
        "RandomForest": RandomForestClassifier(
            n_estimators=500, max_depth=20, min_samples_leaf=3,
            random_state=42, n_jobs=-1, class_weight='balanced',
        ),
        "LogisticRegression": LogisticRegression(
            max_iter=3000, C=0.5, random_state=42,
        ),
    }

    best_name, best_acc, best_clf = None, 0, None
    for name, clf in models.items():
        print(f"\n  Training {name}...")
        t0 = time.time()
        clf.fit(X_train_pca, y_train)
        train_acc = accuracy_score(y_train, clf.predict(X_train_pca)) * 100
        val_acc = accuracy_score(y_val, clf.predict(X_val_pca)) * 100
        print(f"    Train: {train_acc:.1f}% | Val: {val_acc:.1f}% ({time.time()-t0:.1f}s)")
        if val_acc > best_acc:
            best_acc = val_acc
            best_name = name
            best_clf = clf

    print(f"\n{'─' * 55}")
    print(f"  BEST: {best_name} — {best_acc:.1f}% validation accuracy")
    print(f"{'─' * 55}")
    y_pred = best_clf.predict(X_val_pca)
    print(classification_report(y_val, y_pred, target_names=["Real", "Fake"]))

    # Save
    model_data = {
        "model": best_clf,
        "scaler": scaler,
        "pca": pca,
        "img_size": IMG_SIZE,
        "n_features": n_feat,
        "val_accuracy": best_acc,
        "version": f"v4-{best_name.lower()}-multi",
    }
    joblib.dump(model_data, MODEL_OUTPUT, compress=3)
    print(f"  ✓ Saved: {MODEL_OUTPUT} ({MODEL_OUTPUT.stat().st_size//1024} KB)")
    print()


if __name__ == "__main__":
    main()
