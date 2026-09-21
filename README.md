# SignalLens AI — Automated SIGINT & Pure-NumPy DSP Backend (v3.0)

SignalLens AI is an automated **signal intelligence (SIGINT) and digital signal processing (DSP) workbench** built for spectrum monitoring, defense, aerospace, and RF engineering analysis.

---

## ⚡ Architectural Core

- **Pure-NumPy DSP & ML Core (`signalens/`)**: Zero runtime dependency on `scipy` or `scikit-learn`. Custom FFT, Welch PSD, STFT Spectrogram, 11-D feature extraction, FastICA, and Random Forest classifier hand-implemented on pure NumPy arrays for instant cold-starts on serverless deployments.
- **FastAPI Backend (`api/`)**: High-performance asynchronous API with Pydantic v2 schemas (`camelCase` aliased), JWT Access (15m) + HttpOnly cookie Refresh (7d) rotation, and fail-fast environment validation.
- **3-Tier Commercial Model**:
  1. **Base Hunter (Free)**: ≤25 MB, `.wav`/`.ogg` formats, core DSP visualizations, basic modulation classification, and text report export.
  2. **Cyber Pro (₹2,499/mo | $29/mo)**: ≤500 MB, raw `.iq`/`.raw`/`.cf32`/`.cs16` SDR captures, full 11-D ML classifier, and Suite A + Suite B (core).
  3. **Ultra Pro Max — Sovereign Defense (₹16,999/mo | $199/mo)**: Multi-GB captures, all 18 advanced intelligence modules (FastICA BSS, TDoA Hyperbolic Trilateration, Micro-Doppler, Stego sniffer, and Symbolic demodulator sandbox).

---

## 📁 Repository Structure

```
.
├── api/
│   ├── config/env.py                  # Pydantic v2 Settings (fail-fast validation)
│   ├── middleware/                    # Security headers, CORS, rate limiting, error formatting
│   ├── database/                      # Async SQLite / PostgreSQL ORM & repositories
│   ├── schemas/                       # Pydantic v2 models (1:1 sync with frontend TS interfaces)
│   ├── routes/                        # /health, /ready, /auth/*, /analyze, /analyze/tdoa, /billing/*
│   ├── services/                      # Auth, DSP, Billing, and Storage services
│   └── main.py                        # FastAPI entrypoint with lifespan model preloading
│
├── signalens/                         # Pure-NumPy DSP & ML Engine (Zero Scipy/Scikit-learn)
│   ├── loaders.py                     # WAV, OGG, and raw IQ (uint8, complex64, cf32, cs16) loaders
│   ├── preprocessing.py               # DC offset removal, mono downmix, peak normalization
│   ├── features.py                    # Time metrics, Welch PSD, FFT, STFT, IQ metrics, 11-D feature vector
│   ├── classifier.py                  # Pure-NumPy Random Forest & StandardScalerNP
│   ├── analysis.py                    # Pipeline orchestrator & intelligence dossier generator
│   ├── fingerprint.py                 # Suite A (Feat 2): CFO drift (ppm), IQ imbalance, HW classification
│   ├── anti_spoof.py                  # Suite A (Feat 4): RF Authenticity score & replay anomaly detection
│   ├── demod.py                       # Suite A (Feat 5): Morse CW envelope to ASCII text decoder
│   ├── doppler.py                     # Suite B (Feat 7): Doppler drift (Hz/s) & orbital velocity
│   ├── subnoise.py                    # Suite B (Feat 8): Stochastic resonance & coherent averaging
│   ├── ionosphere.py                  # Suite B (Feat 9 & 16): Group delay dispersion & skip distance proxy
│   ├── tdoa.py                        # Suite B (Feat 10): Multi-receiver TDoA hyperbolic trilateration
│   ├── chirp.py                       # Suite B (Feat 11): Quadratic phase fit & time-bandwidth product
│   ├── entropy.py                     # Suite B (Feat 12): Shannon entropy & spectral kurtosis
│   ├── bss.py                         # Suite C (Feat 13): FastICA blind source separation (pure NumPy)
│   ├── stego.py                       # Suite C (Feat 14): Sub-noise floor residual anomaly sniffer
│   ├── microdoppler.py                # Suite C (Feat 15): Blade radar signature & rotor RPM estimator
│   ├── quantum_entropy.py             # Suite C (Feat 17): Composite anomaly index (entropy + kurtosis)
│   └── symbolic_demod.py              # Suite C (Feat 18): Cyclostationary symbol clock & raw hex dump
│
├── models/
│   └── rf_classifier.json             # Serialized pure-NumPy Random Forest model weights
├── postman/
│   ├── collection.json                # Complete Postman Collection with automated test scripts
│   └── environment.json               # Postman Environment template
├── tests/                             # Pytest automated test suite (27 passing tests)
├── requirements.txt
├── train_model.py                     # Synthetic signal training script
└── .env.example
```

---

## 🚀 Quickstart & Local Setup

### 1. Environment & Dependencies

```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
```

### 3. Train or Verify the Pure-NumPy Random Forest

```bash
python3 train_model.py
```
*Generates `models/rf_classifier.json` in under 1 second with >99% test accuracy.*

### 4. Run the Automated Test Suite

```bash
PYTHONPATH=. pytest tests/ -v
```

### 5. Launch the FastAPI Server

```bash
uvicorn api.main:app --host 0.0.0.0 --port 5000 --reload
```

---

## 📡 API Endpoints Overview

| Method | Endpoint | Description | Auth / Tier |
|---|---|---|---|
| `GET` | `/health` | Liveness probe (cheap and fast) | Public |
| `GET` | `/ready` | Readiness probe (verifies database connectivity) | Public |
| `POST` | `/api/v1/auth/register` | Register new user account + set refresh cookie | Public |
| `POST` | `/api/v1/auth/login` | Login + set HttpOnly refresh cookie | Public |
| `POST` | `/api/v1/auth/refresh` | Rotate refresh token and issue fresh access token | Refresh Cookie |
| `POST` | `/api/v1/auth/logout` | Revoke session and clear refresh cookie | Bearer Auth |
| `GET` | `/api/v1/users/me` | Fetch authenticated user profile & tier | Bearer Auth |
| `POST` | `/api/v1/analyze` | Multipart signal upload (WAV, OGG, IQ) & tier-gated DSP pipeline | Optional (Base if anon) |
| `POST` | `/api/v1/analyze/tdoa` | Multi-receiver TDoA hyperbolic trilateration (≥3 receivers) | Sovereign Tier |
| `GET` | `/api/v1/billing/tiers` | Pricing matrix and commercial tier specifications | Public |
| `POST` | `/api/v1/billing/checkout`| Create Stripe / UPI checkout session | Bearer Auth |
| `GET` | `/api/v1/billing/me` | Current subscription status and usage meters | Bearer Auth |
| `GET` | `/api/v1/files/{path}` | Stream stored private capture file | Public / Signed |

---

## 📮 Postman Collection

Import `postman/collection.json` and `postman/environment.json` into Postman.
- The collection pre-request script automatically handles token refresh.
- Automated tests verify status codes and capture tokens/IDs dynamically.
