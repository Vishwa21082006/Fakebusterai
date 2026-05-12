#!/usr/bin/env python3
"""
FakeBuster AI — Automated Test Suite
Runs 5 test cases against the live API + ML detector.
"""
import sys, json, time, requests

BASE = "http://localhost:8000/api/v1"
EMAIL = "testrunner@fakebuster.ai"
PASSWORD = "TestRunner2026!"

# Test images
IMAGES = {
    "ai_face_hq": "/home/vishwa/Downloads/AI-face-detection-Dataset/AI/0_20241130135552_A_close-up_shot_of_a_middle-aged_genderqueer_perso.jpg",
    "ai_face_2": "/home/vishwa/Downloads/AI-face-detection-Dataset/AI/100_20241130141829_A_close-up_shot_of_a_middle-aged_male_person_of_Na.jpg",
    "real_face_small": "/home/vishwa/Downloads/AI-face-detection-Dataset/real/child-1367.png",
    "ds1_fake": "/home/vishwa/Downloads/Dataset/Test/Fake/fake_0.jpg",
    "ds1_real": "/home/vishwa/Downloads/Dataset/Test/Real/real_0.jpg",
}

passed = 0
failed = 0


def test(name, condition, detail=""):
    global passed, failed
    if condition:
        passed += 1
        print(f"  ✅ PASS: {name}")
    else:
        failed += 1
        print(f"  ❌ FAIL: {name}")
    if detail:
        print(f"         {detail}")


def main():
    global passed, failed

    print("=" * 60)
    print("  FakeBuster AI — Test Suite (5 Test Cases)")
    print("=" * 60)

    # ─────────────────────────────────────────────
    # TEST 1: Authentication Pipeline
    # ─────────────────────────────────────────────
    print("\n─── TEST 1: Authentication Pipeline ───")

    # Register
    r = requests.post(f"{BASE}/auth/register", json={
        "email": EMAIL, "password": PASSWORD
    })
    if r.status_code == 422 or "already" in r.text.lower():
        print("  (User already exists, skipping registration)")
    else:
        test("Register new user", r.status_code in (200, 201),
             f"Status: {r.status_code}")

    # Login
    r = requests.post(f"{BASE}/auth/login", json={
        "email": EMAIL, "password": PASSWORD
    })
    test("Login returns JWT token",
         r.status_code == 200 and "access_token" in r.json(),
         f"Status: {r.status_code}")

    token = r.json().get("access_token", "")
    headers = {"Authorization": f"Bearer {token}"}

    # Auth check
    r = requests.get(f"{BASE}/auth/me", headers=headers)
    test("Auth verify (GET /me)",
         r.status_code == 200 and r.json().get("email") == EMAIL,
         f"Email: {r.json().get('email', 'N/A')}")

    # Token expiry check
    expires_in = requests.post(f"{BASE}/auth/login", json={
        "email": EMAIL, "password": PASSWORD
    }).json().get("expires_in", 0)
    test("JWT expiry = 24 hours",
         expires_in == 86400,
         f"expires_in: {expires_in}s ({expires_in//3600}h)")

    # ─────────────────────────────────────────────
    # TEST 2: Upload & Detection — AI-generated Face (DS2)
    # ─────────────────────────────────────────────
    print("\n─── TEST 2: AI-Generated Face Detection (DS2) ───")

    with open(IMAGES["ai_face_hq"], "rb") as f:
        r = requests.post(f"{BASE}/upload", headers=headers,
                          files={"file": ("ai_face.jpg", f, "image/jpeg")})

    test("Upload AI image succeeds", r.status_code in (200, 202),
         f"Status: {r.status_code}")

    analysis_id = r.json().get("id", "")
    time.sleep(3)

    r = requests.get(f"{BASE}/analysis/{analysis_id}", headers=headers)
    data = r.json()
    score = data.get("result_score", 0)
    status = data.get("status", "")
    verdict = data.get("result_detail", {}).get("verdict", "")

    test("Analysis completes", status == "done",
         f"Status: {status}")
    test("AI image detected as fake (score > 0.7)", score > 0.7,
         f"Score: {score:.4f} | {verdict[:60]}")

    # ─────────────────────────────────────────────
    # TEST 3: Upload & Detection — Real Face (DS2)
    # ─────────────────────────────────────────────
    print("\n─── TEST 3: Real Face Detection (DS2, 150×150 PNG) ───")

    with open(IMAGES["real_face_small"], "rb") as f:
        r = requests.post(f"{BASE}/upload", headers=headers,
                          files={"file": ("real_face.png", f, "image/png")})

    test("Upload PNG image succeeds", r.status_code in (200, 202),
         f"Status: {r.status_code}")

    analysis_id = r.json().get("id", "")
    time.sleep(3)

    r = requests.get(f"{BASE}/analysis/{analysis_id}", headers=headers)
    data = r.json()
    score = data.get("result_score", 0)
    verdict = data.get("result_detail", {}).get("verdict", "")

    test("Real image detected as real (score < 0.4)", score < 0.4,
         f"Score: {score:.4f} | {verdict[:60]}")

    # ─────────────────────────────────────────────
    # TEST 4: Upload & Detection — DS1 Images
    # ─────────────────────────────────────────────
    print("\n─── TEST 4: DS1 Image Detection (256×256 JPG) ───")

    # Fake image
    with open(IMAGES["ds1_fake"], "rb") as f:
        r = requests.post(f"{BASE}/upload", headers=headers,
                          files={"file": ("fake.jpg", f, "image/jpeg")})
    aid_fake = r.json().get("id", "")

    # Real image
    with open(IMAGES["ds1_real"], "rb") as f:
        r = requests.post(f"{BASE}/upload", headers=headers,
                          files={"file": ("real.jpg", f, "image/jpeg")})
    aid_real = r.json().get("id", "")

    time.sleep(3)

    # Check fake
    r = requests.get(f"{BASE}/analysis/{aid_fake}", headers=headers)
    fake_score = r.json().get("result_score", 0)
    fake_verdict = r.json().get("result_detail", {}).get("verdict", "")

    # Check real
    r = requests.get(f"{BASE}/analysis/{aid_real}", headers=headers)
    real_score = r.json().get("result_score", 0)
    real_verdict = r.json().get("result_detail", {}).get("verdict", "")

    test("DS1 fake scored higher than real",
         fake_score > real_score,
         f"Fake: {fake_score:.4f} vs Real: {real_score:.4f}")
    test("DS1 scores have separation > 0.05",
         abs(fake_score - real_score) > 0.05,
         f"Δ = {abs(fake_score - real_score):.4f}")

    # ─────────────────────────────────────────────
    # TEST 5: Analysis History & Error Handling
    # ─────────────────────────────────────────────
    print("\n─── TEST 5: API Robustness ───")

    # List analyses
    r = requests.get(f"{BASE}/analysis", headers=headers)
    resp_data = r.json()
    test("List analyses returns data",
         r.status_code == 200 and (isinstance(resp_data, list) or isinstance(resp_data, dict)),
         f"Count: {len(r.json())} analyses")

    # Invalid analysis ID
    r = requests.get(f"{BASE}/analysis/00000000-0000-0000-0000-000000000000",
                     headers=headers)
    test("Invalid analysis ID returns 404",
         r.status_code == 404,
         f"Status: {r.status_code}")

    # Unauthenticated request
    r = requests.post(f"{BASE}/upload",
                      files={"file": ("test.jpg", b"fake", "image/jpeg")})
    test("Unauthenticated upload rejected",
         r.status_code in (401, 403),
         f"Status: {r.status_code}")

    # Health check
    r = requests.get(f"{BASE}/health")
    test("Health endpoint returns OK",
         r.status_code == 200,
         f"Response: {r.text[:60]}")

    # ─────────────────────────────────────────────
    # SUMMARY
    # ─────────────────────────────────────────────
    total = passed + failed
    print(f"\n{'=' * 60}")
    print(f"  RESULTS: {passed}/{total} passed, {failed} failed")
    print(f"{'=' * 60}")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
