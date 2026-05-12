#!/usr/bin/env python3
"""
FakeBuster AI — Dataset Accuracy Benchmark
Tests the detector against the user's Real/Fake dataset.
"""
import sys, os, time, random
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[0]))
from detector_stub import detect

DATASET_PATH = Path("/home/vishwa/Downloads/Dataset")

def benchmark(split="Test", sample_size=50):
    """Run detector on a sample from the dataset."""
    fake_dir = DATASET_PATH / split / "Fake"
    real_dir = DATASET_PATH / split / "Real"
    
    fake_files = list(fake_dir.glob("*.jpg"))
    real_files = list(real_dir.glob("*.jpg"))
    
    print(f"\n  {split} set: {len(fake_files)} fake, {len(real_files)} real")
    print(f"  Sampling {sample_size} from each class")
    
    random.seed(42)
    fake_sample = random.sample(fake_files, min(sample_size, len(fake_files)))
    real_sample = random.sample(real_files, min(sample_size, len(real_files)))
    
    # Test FAKE images
    fake_scores = []
    fake_correct = 0
    t0 = time.time()
    for f in fake_sample:
        result = detect(str(f))
        score = result.result_score
        fake_scores.append(score)
        if score > 0.50:
            fake_correct += 1
    fake_time = time.time() - t0
    
    # Test REAL images
    real_scores = []
    real_correct = 0
    t0 = time.time()
    for f in real_sample:
        result = detect(str(f))
        score = result.result_score
        real_scores.append(score)
        if score < 0.50:
            real_correct += 1
    real_time = time.time() - t0
    
    total_correct = fake_correct + real_correct
    total = len(fake_sample) + len(real_sample)
    accuracy = total_correct / total * 100
    
    fake_avg = sum(fake_scores) / len(fake_scores)
    real_avg = sum(real_scores) / len(real_scores)
    
    print(f"\n  {'─' * 55}")
    print(f"  RESULTS ({split})")
    print(f"  {'─' * 55}")
    print(f"    FAKE images: {fake_correct}/{len(fake_sample)} correct ({fake_correct/len(fake_sample)*100:.1f}%)")
    print(f"      Avg score: {fake_avg:.3f} (target > 0.50)")
    print(f"      Score range: [{min(fake_scores):.3f}, {max(fake_scores):.3f}]")
    print(f"      Time: {fake_time:.1f}s ({fake_time/len(fake_sample)*1000:.0f}ms/image)")
    print(f"    REAL images: {real_correct}/{len(real_sample)} correct ({real_correct/len(real_sample)*100:.1f}%)")
    print(f"      Avg score: {real_avg:.3f} (target < 0.50)")
    print(f"      Score range: [{min(real_scores):.3f}, {max(real_scores):.3f}]")
    print(f"      Time: {real_time:.1f}s ({real_time/len(real_sample)*1000:.0f}ms/image)")
    print(f"    OVERALL: {total_correct}/{total} ({accuracy:.1f}%)")
    print(f"    Separation: fake_avg - real_avg = {fake_avg - real_avg:.3f}")
    
    return {
        "split": split,
        "accuracy": accuracy,
        "fake_acc": fake_correct / len(fake_sample) * 100,
        "real_acc": real_correct / len(real_sample) * 100,
        "fake_avg": fake_avg,
        "real_avg": real_avg,
    }

if __name__ == "__main__":
    print("=" * 60)
    print("  FakeBuster AI — Dataset Benchmark")
    print(f"  Dataset: {DATASET_PATH}")
    print("=" * 60)
    
    if not DATASET_PATH.exists():
        print("  ✗ Dataset not found!")
        sys.exit(1)
    
    results = []
    for split in ["Test", "Validation"]:
        r = benchmark(split, sample_size=50)
        results.append(r)
    
    print(f"\n{'=' * 60}")
    print(f"  FINAL SUMMARY")
    print(f"{'=' * 60}")
    for r in results:
        print(f"  {r['split']:12s}: {r['accuracy']:.1f}% overall | Fake: {r['fake_acc']:.1f}% | Real: {r['real_acc']:.1f}%")
    print()
