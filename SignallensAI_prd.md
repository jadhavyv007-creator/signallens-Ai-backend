# Product Requirements Document — SignalLens AI

### Master Enterprise, Aerospace & Defense SIGINT Specification

> **Version:** 3.0 — adds 3-tier commercial model, 18 advanced feature suites, and pricing/checkout UI on top of the v2.0 as-built architecture
> **Status:** v2.0 subsystems (Sections 1–3, 7, 9, 11, 12, 14, 15) are implemented and unchanged by this revision. This revision expands Sections 4, 5, 6, 8, 10, 13, and 17, and adds new Sections 18–19 for tiering and pricing.
> **Stack:** Python (FastAPI, pure NumPy DSP/ML) + React 19/TypeScript/Vite frontend + Supabase (Postgres + Storage + Auth)
> **Document snapshot:** Dependency version numbers are not authoritative; verify at implementation time.

---

## ⚠️ A Note on Engineering Feasibility (Read First)

This revision folds in a large "Suite B / Suite C" feature list (Sections 5.2–5.3, 18) spanning aerospace telemetry and speculative "next-gen EW / sci-fi SIGINT" capabilities. Before implementation, each item needs to be sorted into one of three buckets — done explicitly below so the roadmap doesn't silently promise physics that doesn't exist:

- **🟢 Implementable in pure NumPy, real technique:** Doppler shift estimation, chirp-rate/time-bandwidth analysis, Shannon entropy scoring, blind source separation (via ICA-style unmixing), micro-Doppler spectral signatures, HF skip-distance estimation from timing, CFO/IQ-imbalance fingerprinting, TDoA trilateration from multi-receiver timestamps.
- **🟡 Real concept, but requires hardware/data SignalLens doesn't have:** TDoA and trilateration need **multiple synchronized receivers** with known geographic positions — a single uploaded file cannot be trilaterated. Doppler *velocity* requires a known carrier frequency and *orbital* Doppler requires ephemeris data. These are implementable as features **given the right multi-sensor input**, not from one arbitrary signal file.
- **🔴 Not physically implementable as named — flagged, not built as literal science:** "Relativistic" Doppler at RF-detectable velocities, "gravitational lensing drift" on a terrestrial/SDR-captured signal, "quantum entropy collapse" distinguishing "artificial vs natural thermodynamic cosmic noise," and a demodulator claiming to decode "unknown/alien signals" via "zero-shot symbol sync" are not established DSP capabilities. These are documented below as **product copy / UI treatment only** — SignalLens will ship the UI, the badge, the visual — backed by the nearest real, honestly-labeled metric (e.g., "Chirp Rate Analysis" badged as "Gravitational Lensing Drift" is cosmetic branding on a real chirp-rate calculation, not a new physical measurement).

Section 18 marks every one of the 18 features with 🟢/🟡/🔴 so implementers know exactly what they're building versus branding.

---

## Table of Contents

1. [Product Overview](#1-product-overview)
2. [Tech Stack (As Built)](#2-tech-stack-as-built)
3. [High-Level Architecture](#3-high-level-architecture)
4. [Sitemap / Pages Architecture](#4-sitemap--pages-architecture)
5. [Feature Hierarchy](#5-feature-hierarchy)
6. [Repository Structure (As Built + New Modules)](#6-repository-structure-as-built--new-modules)
7. [Python DSP & ML Core (`signalens/`)](#7-python-dsp--ml-core-signalens)
8. [FastAPI Backend (`api/`)](#8-fastapi-backend-api)
9. [Database & Storage Schema (Supabase)](#9-database--storage-schema-supabase)
10. [Frontend Application (`src/`)](#10-frontend-application-src)
11. [Supported Formats & Ingestion Matrix](#11-supported-formats--ingestion-matrix)
12. [Environment Variables](#12-environment-variables)
13. [API Documentation Standard](#13-api-documentation-standard)
14. [Testing (As Built)](#14-testing-as-built)
15. [Security Checklist](#15-security-checklist)
16. [Master Build / Extension Prompt](#16-master-build--extension-prompt)
17. [Roadmap — Next Subsystems](#17-roadmap--next-subsystems)
18. [18 Advanced Feature Suites — Full Breakdown](#18-18-advanced-feature-suites--full-breakdown)
19. [Commercial Tiering & Pricing Specification](#19-commercial-tiering--pricing-specification)

---

## 1. Product Overview

**SignalLens AI** is an automated **signal intelligence and digital signal processing (DSP) workbench** built for intelligence agencies, spectrum monitoring teams, and defense/telecom analysts who capture raw RF signals via Software Defined Radios (RTL-SDR, HackRF, USRP) as `.WAV` audio or `.IQ`/raw binary I/Q samples.

**The problem it solves:** manually identifying modulation schemes, carrier frequencies, bandwidths, spectral anomalies, and RF characteristics from raw captures requires specialized RF engineering expertise and is slow.

**The solution, as built (v2.0 core, unchanged by this revision):**
1. Ingests `.WAV`, `.OGG`, `.IQ`/raw binary files, or live microphone capture.
2. Runs a full DSP pipeline: time-domain analysis, FFT magnitude spectrum, Welch PSD, STFT spectrogram, and I/Q phase/constellation analysis.
3. Extracts an 11-dimensional feature vector and classifies modulation type via a pure-NumPy Random Forest model.
4. Returns an interactive dashboard: visualizations, scalar metrics, AI classification with confidence/anomaly scoring, and an exportable text intelligence report.
5. Persists files, features, predictions, and reports to Supabase (Postgres + Storage) when configured — and degrades gracefully to client-side-only operation when it isn't.

**New in v3.0:** a 3-tier commercial model (Base Hunter / Cyber Pro / Ultra Pro Max Sovereign Defense) gating 18 advanced feature suites spanning forensic audio processing, aerospace telemetry, and next-gen electronic-warfare analysis (see Sections 18–19), plus a full pricing/checkout UI.

**Distinguishing architectural trait (unchanged):** the entire DSP and ML inference path is implemented in **pure NumPy with zero runtime dependency on `scipy` or `scikit-learn`**, specifically to keep cold-starts fast on serverless deployment (Vercel). This constraint is preserved and extended to all new v3.0 modules — see the Architectural Guardrails below.

---

### Architectural Guardrails (Non-Negotiable, Preserved From v2.0)

| # | Guardrail | Applies to |
|---|---|---|
| 1 | `signalens/` core engine remains strictly pure-NumPy — zero `scipy`/`scikit-learn` runtime dependencies | All new DSP logic (Doppler, entropy, chirp-rate, BSS, micro-Doppler) — see Section 7.7 |
| 2 | `api/schemas.py` (Pydantic v2, camelCase-aliased) and `src/types/signal.ts` remain in exact 1:1 sync | Every new API response field added in this revision |
| 3 | Frontend dual-mode fallback preserved — FastAPI backend preferred, Web Audio API client-side fallback if backend unreachable | New Pro/Sovereign features are backend-only by nature (heavier compute) but the fallback path must degrade gracefully, not break — see Section 10.4 |
| 4 | Existing high-density UI layout and metrics fidelity for Sections 01–08 on `DashboardPage.tsx` is maintained | New tiered panels are **added alongside**, not a replacement of, Sections 01–08 — see Section 10.2 |

---

## 2. Tech Stack (As Built)

| Layer | Choice | Notes |
|---|---|---|
| **DSP/ML engine** | Python + pure NumPy | No `scipy`/`scikit-learn` at runtime — custom Welch PSD, STFT, FFT-windowing, Random Forest inference, and (new in v3.0) Doppler/entropy/BSS math all hand-implemented on NumPy arrays |
| **Backend API** | FastAPI | Serverless-compatible (`api/main.py`), lifespan-managed model loading |
| **Validation** | Pydantic v2 | camelCase-aliased schemas matching the frontend TS interfaces exactly |
| **Frontend framework** | React 19 + TypeScript + Vite | |
| **Styling** | Tailwind CSS v4 | |
| **Animation** | Framer Motion | Landing page oscilloscope, step transitions, pricing page confetti/glassmorphism motion |
| **Charts** | Recharts | Waveform, FFT, PSD, constellation, entropy/telemetry line charts |
| **3D rendering (new)** | Three.js / WebGL | 3D polar constellation (Feature 6), TDoA orbital trajectory globe (Feature 10) |
| **Custom canvas rendering** | HTML5 Canvas | Spectrogram heatmap, live mic oscilloscope (60 FPS), spectrogram lasso/bounding-box isolator (Feature 3) |
| **Payments (new)** | Stripe (card) + UPI QR (India) | Checkout modal on `/pricing` — see Section 19 |
| **Database** | Supabase (Postgres) | 6 relational tables + new `subscriptions`/`billing_events` tables (Section 9) |
| **Object storage** | Supabase Storage | Private `signal-files` bucket, 100 MB limit (tier-dependent, see Section 19) |
| **Auth (DB layer)** | Supabase Auth | `users` table synced from `auth.users` via trigger; extended with `tier` claim |
| **Client-side DSP fallback** | Web Audio API + custom Cooley-Tukey Radix-2 FFT (TypeScript) | Runs the Base-tier pipeline in-browser when the backend is unreachable; Pro/Sovereign features require the backend and are unavailable in fallback mode (see Section 10.4) |
| **Testing** | `pytest` + FastAPI `TestClient` | 19 existing integration tests + new tests for tier-gating and new endpoints |
| **Deploy: Frontend** | Vercel | |
| **Deploy: Backend** | Vercel serverless (`api/` as function) | Pure-NumPy design chosen specifically for this |
| **Deploy: DB/Storage** | Supabase | |

---

## 3. High-Level Architecture

```
User (Browser)
   │
   ├─ Upload file / Record mic ──▶ React 19 + Vite Frontend
   │                                     │
   │                    ┌────────────────┴────────────────┐
   │                    ▼                                  ▼
   │          FastAPI Backend (api/main.py)      Client-side DSP fallback
   │                    │                          (signal-analyzer.ts —
   │                    │                           Base-tier features only,
   │                    │                           see Section 10.4)
   │                    ▼
   │            Tier Gate (billing.ts state + backend entitlement check)
   │                    │
   │      ┌─────────────┼──────────────────────────────────┐
   │      ▼             ▼                                   ▼
   │  signalens/    signalens/ (Suite A/B — Pro)      signalens/ (Suite C — Sovereign)
   │  core v2.0      audioFilter, orbitalMath          defenseDsp: BSS, steganography,
   │  (loaders,      modules — CFO, Doppler,           micro-Doppler, entropy collapse
   │  features,      entropy, chirp-rate               (compute-heavy, Sovereign-tier
   │  classifier)                                       rate-limited)
   │                    │
   │                    ▼
   │            database.py (Supabase Postgres + Storage + subscriptions)
   │                    │
   │                    ▼
   │            JSON API Response (tier-scoped fields)
   │                    │
   ▼                    ▼
DashboardPage.tsx Sections 01–08 (unchanged, all tiers)
   + Section 09 (Suite A/B Pro panels, tier-gated)
   + Section 10 (Suite C Sovereign panels, tier-gated)
   + PricingPage.tsx (/pricing — checkout, tier switcher)
```

**Key design decision — dual-mode operation (preserved):** the frontend prefers the FastAPI backend but transparently falls back to a full in-browser DSP pipeline if the backend is offline. **New in v3.0:** the fallback pipeline only ever runs Base-tier analysis — Pro and Sovereign features require the backend and are visually disabled (not silently degraded) when running in fallback mode, so a user never sees a fake "Doppler estimate" computed client-side.

---

## 4. Sitemap / Pages Architecture

```
========================================================================================================================
                                SIGNALLENS AI — PAGES / SITEMAP ARCHITECTURE (v3.0)
========================================================================================================================

                                            ┌───────────────┐
                                            │     Pages     │
                                            └───────┬───────┘
         ┌──────────────┬───────────────────┬───────────────────┬──────────────────┬─────────────────────┐
         ▼              ▼                   ▼                   ▼                  ▼                     ▼
   [ Landing ]    [ Upload Page ]    [ Live Mic Page ]   [ Dashboard Page ]   [ Pricing Page ]      [ Account /
         │              │                   │                   │                  │                Billing ]
   ┌─────┴─────┐        │                   │        ┌──────────┴──────────┐       │                     │
   ▼           ▼        ▼                   ▼        ▼                     ▼       ▼                     ▼
[Header]   [Animated  Drag & Drop      getUserMedia  Sections 01–08:  Sections 09–10:  Currency/Billing  Current Tier
 Nav]       SVG        Upload Zone     Live Capture  (unchanged,      NEW Pro/Sovereign  Toggle (₹/$,   Badge, Usage
[Footer]    Oscilloscope Tier-scoped    (Base: ≤15s,   all tiers)     panels — Suite A/B/C  Monthly/       Meter,
            + tier      max size &      Pro: ≤60s,     Waveform,      (tier-gated,        Annual −20%)   Upgrade/
            preview     format gate     Sovereign:     FFT, PSD,      badges + locked       │              Downgrade,
            badges                      continuous)    Spectrogram,   state for lower       ▼              Invoice
                                                        Constellation, tiers, see 10.3)   3 Tier Cards      History
                                                        AI Class.,                        (Base/Cyber Pro/
                                                        Features,                          Sovereign) +
                                                        Report                             Checkout Modal
                                                                                            (UPI QR / Stripe
                                                                                             Card, Simulate
                                                                                             Payment → Confetti)
```

### Page-level breakdown

| Page | Key components | Purpose | Tier gating |
|---|---|---|---|
| **Landing Page** | `Header`, animated SVG oscilloscope, `Footer`; nav to Upload/Live Mic/Pricing | Entry point, product framing | Public |
| **Upload Page** | Drag-and-drop zone (format/size gated by tier), real-time progress bar, animated step indicators | File-based ingestion | Format/size limits vary by tier — see Section 19 |
| **Live Mic Page** | `getUserMedia` capture (duration capped by tier), 60 FPS canvas oscilloscope, recording review + format inspector | Real-time capture ingestion | Duration cap varies by tier |
| **Dashboard Page** | Sections 01–08 (unchanged core) + **NEW** Sections 09 (Suite A/B Pro panels) and 10 (Suite C Sovereign panels) | Core analysis output surface | Sections 09–10 render as locked/upsell cards for lower tiers, not hidden entirely (see 10.3) |
| **Pricing Page (NEW)** | `PricingPage.tsx` — currency toggle, billing-cycle toggle, 3 tier cards, checkout modal | Commercial conversion surface | Public |
| **Account / Billing (NEW)** | Tier badge, usage meter (uploads this month, storage used), upgrade/downgrade, invoice history | Subscription self-service | Requires login |

---

## 5. Feature Hierarchy

```
========================================================================================================================
                                SIGNALLENS AI — SYSTEM FEATURES HIERARCHY (v3.0)
========================================================================================================================

                                            ┌───────────────┐
                                            │   Features    │
                                            └───────┬───────┘
         ┌─────────────┬─────────────┬──────────────┬──────────────┬───────────────┬──────────────────┐
         ▼             ▼             ▼              ▼              ▼               ▼                  ▼
[Ingestion Engine] [DSP Pipeline] [ML Classification] [Visualization] [Persistence]  [Suite A/B — Pro]  [Suite C — Sovereign]
 (v2.0, unchanged,  (v2.0,         (v2.0,             Suite (v2.0,    & Reports      Forensic Audio &   Next-Gen EW &
 tier-scoped         unchanged)    unchanged)         unchanged,      (v2.0 +        Deep-Space         Sci-Fi SIGINT
 limits only)                                          Sections       subscriptions/  Telemetry          (Section 18.3,
                                                        01–08)         billing_events  (Section 18.1–18.2, 🔴-flagged
                                                                       tables)          🟢/🟡-flagged      items are
                                                                                        items are real)    branding-only)
                                                                                              │                   │
                                                                    ┌─────────────────────────┴─────┐  ┌─────────┴────────┐
                                                                    ▼                                ▼  ▼                   ▼
                                                        1) Cockpit A/B Player          4) Anti-Spoof Matrix  13) Blind Source
                                                        2) RF Fingerprinting/DNA       5) Live Demod→Text/   Separation (5 stems)
                                                        3) Spectrogram Lasso Isolator     Audio Transcript   14) Steganography Sniffer
                                                        6) 3D Polar Constellation       7) Doppler Estimator  15) UAV Micro-Doppler
                                                           + EVM Stress-Map             8) Sub-Noise Extract  16) Ionospheric Bounce
                                                                                        9) Ionospheric Corr.      Trilateration
                                                                                        10) TDoA 3D Map        17) Quantum Entropy
                                                                                        11) Chirp/Drift Analysis   Collapse (🔴 branding)
                                                                                        12) Entropy Engine     18) Universal Symbolic
                                                                                                                    Demodulator Sandbox
```

### Feature-level detail

| Module | Sub-features | Status |
|---|---|---|
| **Ingestion Engine** | Multi-format loader, file validation, unified auto-detecting loader, client-side DSP fallback (Base tier only) | v2.0, unchanged — now tier-scoped for size/format/duration |
| **DSP Pipeline** | Time-domain, FFT, Welch PSD, STFT spectrogram, IQ metrics, preprocessing | v2.0, unchanged |
| **ML Classification** | 11-D feature extraction, pure-NumPy scaler + Random Forest | v2.0, unchanged |
| **Visualization Suite** | Sections 01–08 (Waveform, FFT, PSD, Spectrogram, Constellation, Metrics, AI Analysis, Feature Inspector, Report) | v2.0, unchanged |
| **Persistence & Reports** | Supabase schema (6 tables) + new `subscriptions`, `billing_events` tables | v2.0 core + v3.0 billing extension |
| **Suite A — Forensic Audio Pipeline** | Features 1–6 (Section 18.1) — Cyber Pro tier | New, 🟢/🟡 implementable |
| **Suite B — Deep-Space & Aerospace Telemetry** | Features 7–12 (Section 18.2) — split across Cyber Pro (RF fingerprinting-adjacent) and Sovereign tiers | New, mixed 🟢/🟡/🔴 — see Section 18 |
| **Suite C — Next-Gen EW & Sci-Fi SIGINT** | Features 13–18 (Section 18.3) — Sovereign tier only | New, mixed 🟢/🟡/🔴 — see Section 18 |

---

## 6. Repository Structure (As Built + New Modules)

```
SignalLens-AI-main/
├── api/
│   ├── main.py                 # + new tier-gated endpoint groups (Section 8)
│   ├── schemas.py               # + new Pydantic models for Suite A/B/C responses
│   ├── database.py              # + subscription/entitlement queries
│   └── __init__.py
│
├── signalens/                   # Core DSP & ML engine (pure NumPy) — v2.0 unchanged
│   ├── loaders.py
│   ├── preprocessing.py
│   ├── features.py
│   ├── classifier.py
│   ├── analysis.py
│   └── __init__.py
│
├── train_model.py
│
├── supabase/
│   ├── schema.sql                 # + subscriptions, billing_events tables (Section 9)
│   └── storage.sql
│
├── src/
│   ├── App.tsx                     # + /pricing route
│   ├── main.tsx
│   ├── pages/
│   │   ├── LandingPage.tsx
│   │   ├── UploadPage.tsx
│   │   ├── LiveMicPage.tsx
│   │   ├── DashboardPage.tsx        # + Sections 09–10 (tier-gated panels)
│   │   ├── PricingPage.tsx          # NEW — full pricing & checkout matrix (Section 19)
│   │   └── AccountPage.tsx          # NEW — billing/usage self-service
│   ├── components/
│   │   ├── layout/ (unchanged)
│   │   ├── dashboard/ (unchanged: MetricsPanel, AIAnalysisPanel, FeatureInspector, ReportPanel, VisualizationPanel)
│   │   ├── visualizations/ (unchanged: WaveformChart, FFTChart, PSDChart, SpectrogramChart, ConstellationChart)
│   │   ├── pro/                     # NEW — Suite A/B components
│   │   │   ├── CockpitPlayer.tsx           # Feature 1
│   │   │   ├── EmitterFingerprintPanel.tsx # Feature 2
│   │   │   ├── SpectrogramLassoTool.tsx    # Feature 3
│   │   │   ├── AntiSpoofMatrix.tsx         # Feature 4
│   │   │   ├── LiveTranscriptPanel.tsx     # Feature 5
│   │   │   ├── PolarConstellation3D.tsx    # Feature 6 (Three.js)
│   │   │   ├── DopplerPanel.tsx            # Feature 7
│   │   │   ├── SubNoiseExtractPanel.tsx    # Feature 8
│   │   │   ├── IonosphericCorrectionPanel.tsx # Feature 9
│   │   │   ├── TDoATrajectoryMap.tsx       # Feature 10 (Three.js)
│   │   │   ├── ChirpDriftPanel.tsx         # Feature 11
│   │   │   └── EntropyEnginePanel.tsx      # Feature 12
│   │   ├── sovereign/               # NEW — Suite C components
│   │   │   ├── BlindSourceSeparationPanel.tsx # Feature 13
│   │   │   ├── SteganographySnifferPanel.tsx  # Feature 14
│   │   │   ├── UAVMicroDopplerPanel.tsx       # Feature 15
│   │   │   ├── IonosphericBouncePanel.tsx     # Feature 16
│   │   │   ├── EntropyCollapsePanel.tsx       # Feature 17 (🔴 branding-layer only)
│   │   │   └── SymbolicDemodSandbox.tsx       # Feature 18
│   │   ├── pricing/                 # NEW
│   │   │   ├── TierCard.tsx
│   │   │   ├── CheckoutModal.tsx
│   │   │   ├── CurrencyToggle.tsx
│   │   │   └── BillingCycleToggle.tsx
│   │   └── common/
│   │       └── TierGate.tsx         # NEW — wraps any panel, shows locked/upsell state
│   ├── lib/
│   │   ├── api.ts
│   │   ├── signal-analyzer.ts       # unchanged — Base-tier fallback only
│   │   ├── storage.ts
│   │   ├── supabase.ts
│   │   ├── upload-utils.ts
│   │   ├── mock-data.ts
│   │   └── utils.ts
│   ├── utils/                        # NEW
│   │   ├── audioFilter.ts             # Client-side Web Audio API filters & crossfader engine (Feature 1)
│   │   ├── orbitalMath.ts             # Doppler, stochastic SNR, Shannon entropy algorithms (Features 7, 8, 12)
│   │   └── defenseDsp.ts              # Blind source separation, steganography, micro-Doppler logic (Features 13–15)
│   ├── services/                     # NEW
│   │   └── billing.ts                 # Subscription tier gating and payment state machine
│   ├── types/
│   │   └── signal.ts                  # + new interfaces for Suite A/B/C response fields
│   └── index.css
│
├── tests/
│   └── test_api.py                    # + tier-gating tests, new endpoint tests
│
├── requirements.txt
├── package.json
├── vite.config.ts
├── vercel.json
└── README.md
```

**New rules for v3.0 (in addition to the v2.0 rules, which still apply):**
- `src/utils/orbitalMath.ts` and `src/utils/defenseDsp.ts` contain **client-side preview/mock computations only** for UI responsiveness (e.g., a live-updating chirp estimate while scrubbing a timeline) — the **authoritative** Suite A/B/C calculation always runs server-side in `signalens/`, mirroring the existing dual-mode pattern. Client-side math in these files must never be presented as the final analysis result.
- `TierGate.tsx` is the single, shared mechanism for locking UI — no panel implements its own ad hoc "upgrade to unlock" logic. This keeps entitlement logic auditable in one place.
- Any 🔴-flagged feature (Section 18) must render its badge/copy clearly as a named "signature index" or "composite score" derived from real, disclosed inputs (e.g., "Cosmic Anomaly Index — derived from entropy variance and spectral kurtosis") — never as a claim of detecting a physical phenomenon SignalLens cannot actually measure.

---

## 7. Python DSP & ML Core (`signalens/`)

Sections 7.1–7.6 (loaders, preprocessing, features, classifier, analysis, train_model) are **unchanged from v2.0** — see the prior revision for full detail. Summarized:

| Module | Responsibility |
|---|---|
| `loaders.py` | WAV/IQ decoders, unified `load_signal()`, file validation |
| `preprocessing.py` | Mono mix, DC-offset removal |
| `features.py` | Time/FFT/Welch-PSD/Spectrogram/IQ metrics, 11-D ML feature extractor |
| `classifier.py` | `RandomForestModel`, `StandardScalerNP`, model I/O, synthetic generators |
| `analysis.py` | Pipeline orchestrator, report generator |
| `train_model.py` | Trains the Random Forest on synthetic generators |

### 7.7 New in v3.0 — Suite A/B/C server-side modules

All new modules below are **pure NumPy**, consistent with Guardrail #1. They are new files inside `signalens/`, orchestrated by an extended `analysis.py` that accepts a `tier` parameter and conditionally runs the additional pipelines.

| New module | Implements | Feasibility |
|---|---|---|
| `signalens/fingerprint.py` | CFO drift (ppm), I/Q imbalance phase error, emitter hardware-class matching against a reference library (Feature 2) | 🟢 Real — standard RF fingerprinting technique |
| `signalens/anti_spoof.py` | RF Authenticity Score (0–100%) from replay-artifact and spectral-consistency checks (Feature 4) | 🟢 Real technique, 🟡 accuracy claims must be validated empirically before shipping a numeric score |
| `signalens/demod.py` | Morse-to-text decoding (CW envelope timing → dit/dah → text); hook for a speech-to-text model for AM/FM voice (Feature 5) | 🟢 Morse decode is straightforward DSP; 🟡 speech transcription likely needs a model dependency — see note below |
| `signalens/doppler.py` | Doppler shift estimate from carrier drift over time; drift rate in Hz/s (Feature 7) | 🟢 Real, given a known/assumed nominal carrier frequency. **Velocity in km/s requires the true carrier frequency as an input the user supplies** — cannot be derived from the signal alone |
| `signalens/subnoise.py` | Stochastic-resonance-style weak-signal recovery via coherent averaging / matched filtering | 🟡 Real class of technique; "-20 dB above cosmic noise floor" is a claim that depends entirely on integration time and SNR assumptions — must not be presented as a fixed guarantee |
| `signalens/ionosphere.py` | Plasma dispersion phase-shift proxy from group-delay-vs-frequency slope | 🟡 Real physics, but a **proxy metric**, not a calibrated TEC measurement (that requires reference GNSS data SignalLens doesn't have) |
| `signalens/chirp.py` | Chirp rate (α, Hz/s) via quadratic phase fit; time-bandwidth product | 🟢 Real, standard technique. "Gravitational lensing drift" label is 🔴 branding on this real chirp-rate number — see guardrail in Section 6 |
| `signalens/entropy.py` | Shannon entropy of the signal's symbol/amplitude distribution (0.000–1.000) | 🟢 Real, well-defined |
| `signalens/bss.py` | Blind source separation via FastICA-style algorithm implemented in pure NumPy | 🟢 Real technique. **5 fixed output stems is a UI/product decision, not a DSP guarantee** — actual separable source count depends on the input; the pipeline should report however many components it can separate and the UI should label them generically (Voice/Telemetry/Jammer/Noise/Beacon are suggested labels, not guaranteed outputs) |
| `signalens/stego.py` | Micro-phase / residual anomaly detector flagging statistically anomalous sub-noise-floor patterns | 🟢 Real anomaly-detection technique; framed as "anomaly flag," not "covert channel confirmed" |
| `signalens/microdoppler.py` | Periodic modulation detection in the Doppler spectrum (rotor blade-passing frequency) → RPM estimate | 🟢 Real, established radar technique, applicable if the capture actually contains a rotating-reflector signature |
| `signalens/tdoa.py` | Multi-receiver TDoA trilateration math | 🟡 Real math, **requires multiple synchronized input streams with known receiver coordinates** — not derivable from a single uploaded file; API must require this input explicitly (Section 8.3) |
| `signalens/orbital_velocity.py` | "Doppler velocity" and "relativistic" labeled outputs | 🔴 The underlying Doppler math is real (see `doppler.py`); "relativistic" framing is marketing — RF-observable Doppler velocities in this product's use cases are non-relativistic. This module simply re-labels `doppler.py` output for the Sovereign UI; no new physics |
| `signalens/quantum_entropy.py` | "Quantum-Resistant Entropy" and "Entropy Collapse" scores | 🔴 These are **rebrands of `entropy.py`'s Shannon entropy output** plus a spectral-kurtosis composite. No quantum computation occurs. Documented honestly in the API as `compositeAnomalyIndex`, displayed in the UI under the feature's marketing name |
| `signalens/symbolic_demod.py` | Blind symbol-rate/clock estimation + hex/binary dump of the sample stream at the estimated symbol clock | 🟢 Symbol-rate estimation (via cyclostationary analysis) and hex-dumping are real; 🔴 there is no "universal" decoder for arbitrary/unknown protocols — output is a **best-effort raw bit/hex stream at the estimated clock**, not a semantic decode |

> **Implementation note on Guardrail #1:** `bss.py` (ICA-style separation) and `microdoppler.py` (spectral peak-picking) are both achievable with NumPy alone (eigendecomposition via `numpy.linalg`, FFT via `numpy.fft`) — no `scipy.signal` or `sklearn.decomposition.FastICA` needed. This has been verified as feasible during spec design; implementers should still confirm at build time per the Version Safety Rule (Section 16).

> **Implementation note on speech transcription (Feature 5):** a real speech-to-text model (Whisper-class) is **not** a pure-NumPy-implementable component — it requires a trained model and typically a framework like PyTorch or ONNX Runtime. This is a deliberate, disclosed exception to Guardrail #1, isolated to a separate optional service call (not inside `signalens/` core) so it doesn't compromise the core engine's cold-start property. See Section 8.3.

---

## 8. FastAPI Backend (`api/`)

### 8.1 `main.py` — v2.0 endpoints (unchanged)

| Endpoint | Detail |
|---|---|
| `GET /`, `GET /health` | Service status, uptime, DB connection state |
| `POST /analyze` | Multipart upload; runs core DSP + ML pipeline; now additionally accepts a `tier`-scoped feature request (Section 8.2) |
| `GET /files/{storage_path}` | Downloads a stored signal file |
| `GET /files/{storage_path}/url` | Signed URL, 1-hour expiration |

### 8.2 New in v3.0 — Tier gating on `POST /analyze`

```
POST /analyze now accepts an optional `features` array in the multipart form,
e.g. features=["doppler","entropy","bss"]. The backend:
  1. Resolves the caller's tier from their auth session (or IP-based anonymous
     Base-tier default for the public demo path).
  2. Filters the requested `features` list down to what that tier is entitled to.
  3. Runs signalens/analysis.py's core pipeline (always, all tiers) plus any
     entitled Suite A/B/C modules from Section 7.7.
  4. Returns a response where locked features are present but marked
     { "locked": true, "requiredTier": "CYBER_PRO" } rather than omitted —
     so the frontend can render a consistent upsell state without a second
     request (see TierGate.tsx, Section 6).
```

### 8.3 New endpoints

| Method | Path | Description | Tier |
|---|---|---|---|
| `POST` | `/analyze/tdoa` | Accepts **multiple** signal files + receiver coordinates; runs `tdoa.py` trilateration | Sovereign only — rejects single-file requests with a clear `400` explaining TDoA needs multi-receiver input |
| `POST` | `/analyze/transcribe` | Optional separate call for speech-to-text (Feature 5, voice modulations) | Cyber Pro+ — isolated from the core pure-NumPy engine per the note in Section 7.7 |
| `GET` | `/billing/tiers` | Returns the current tier/pricing matrix (source of truth for `PricingPage.tsx`) | Public |
| `POST` | `/billing/checkout` | Creates a Stripe/UPI checkout session | Requires login |
| `POST` | `/billing/webhook` | Payment provider webhook → updates `subscriptions` table | Server-to-server (signed) |
| `GET` | `/billing/me` | Current user's tier, usage this period, renewal date | Requires login |

### 8.4 `schemas.py`

New Pydantic v2 models added (camelCase-aliased, kept in sync with `signal.ts` per Guardrail #2): `EmitterFingerprint`, `AntiSpoofResult`, `DopplerEstimate`, `EntropyResult`, `BSSResult`, `MicroDopplerResult`, `TDoARequest`/`TDoAResult`, `TierEntitlement`, `LockedFeature`, `SubscriptionStatus`, `CheckoutSession`.

### 8.5 `database.py`

Extended with subscription/entitlement read helpers (`get_user_tier`, `check_feature_entitlement`, `record_usage_event`) — follows the existing graceful-no-op pattern: if Supabase isn't configured, all users are treated as Base tier and billing endpoints return a clear "not configured" response rather than crashing.

---

## 9. Database & Storage Schema (Supabase)

Section 9.1's 6 core tables (`users`, `files`, `analyses`, `features`, `predictions`, `reports`) are **unchanged from v2.0**.

### 9.2 New tables (v3.0)

| Table | Purpose |
|---|---|
| `subscriptions` | `user_id`, `tier` (`base`/`cyber_pro`/`sovereign`), `billing_cycle`, `status`, `current_period_end`, `payment_provider`, `provider_subscription_id` |
| `billing_events` | Append-only log of checkout attempts, successful payments, webhook events — `user_id`, `event_type`, `amount`, `currency`, `raw_payload` (JSON), `created_at` |
| `usage_meters` | `user_id`, `period_start`, `uploads_count`, `storage_bytes_used`, `sovereign_compute_seconds_used` — for enforcing tier limits and displaying the Account page usage meter |

**RLS:** all three new tables scoped to `user_id = auth.uid()` for reads; writes restricted to the service role (billing events are never client-writable).

### 9.3 Storage

`signal-files` bucket limits become **tier-dependent** rather than a single global 100 MB cap:
- Base: 25 MB per file
- Cyber Pro: 500 MB per file
- Sovereign: multi-GB, chunked/resumable upload required (see Section 17 roadmap — resumable upload is not yet implemented, flagged as a build item)

---

## 10. Frontend Application (`src/`)

### 10.1 Dual-mode architecture (unchanged principle, extended scope)

1. **Backend mode** — preferred, all tiers, all features.
2. **Client-side DSP fallback** (`signal-analyzer.ts`) — **Base-tier core pipeline only.** Per Guardrail #3, this fallback is preserved exactly as in v2.0 and is **not** extended with Suite A/B/C logic. When the backend is unreachable, Pro/Sovereign panels show a distinct "Backend required for this feature" state (not the tier-lock state) so users don't confuse an outage with a paywall.

### 10.2 Dashboard Page — Sections 01–08 (unchanged) + new Sections 09–10

Per Guardrail #4, **Sections 01–08 render exactly as in v2.0** — same components, same layout, same data. This revision **appends**:

| Section | Content | Tier |
|---|---|---|
| **09 — Forensic & Telemetry Suite** | Cockpit A/B Player, RF Fingerprinting panel, Spectrogram Lasso tool, Anti-Spoof Matrix, Live Transcript panel, 3D Polar Constellation, Doppler panel, Sub-Noise Extraction panel, Ionospheric Correction panel, TDoA map, Chirp/Drift panel, Entropy Engine panel | Cyber Pro (some panels partially visible/teased on Base as locked cards) |
| **10 — Sovereign EW Suite** | Blind Source Separation panel, Steganography Sniffer, UAV Micro-Doppler panel, Ionospheric Bounce Trilateration, Entropy Collapse panel, Symbolic Demodulator Sandbox | Sovereign only |

### 10.3 `TierGate.tsx` — shared locking component

```
Wraps any Section 09/10 panel. Given the user's current tier (from billing.ts
state) and the panel's requiredTier:
  - If entitled: renders children normally.
  - If not entitled: renders a blurred/dimmed preview of the panel's layout
    (using placeholder data, clearly labeled "Preview") with an "Unlock with
    Cyber Pro" / "Unlock with Sovereign Defense" CTA linking to /pricing.
  - Never silently hides a panel — the existence of every Suite A/B/C feature
    is always visible, which is the upsell mechanism.
```

### 10.4 New utility modules

| File | Role | Guardrail note |
|---|---|---|
| `utils/audioFilter.ts` | Web Audio API filter chain + crossfader engine for the Cockpit A/B Player (Feature 1) | Client-side preview only — the "Cleaned DSP Audio" side of the crossfader is fetched from the backend's actual denoising output, not computed client-side, to keep a single source of truth |
| `utils/orbitalMath.ts` | Live-scrubbing preview math for Doppler/entropy/chirp panels (e.g., updating a number as the user drags a timeline before the backend recomputes) | Explicitly a **preview/interpolation layer** — final values always come from `signalens/` server-side; this file must never be the value actually submitted in a report |
| `utils/defenseDsp.ts` | Client-side preview stubs for BSS/steganography/micro-Doppler panels (loading-state placeholders, not real separation) | Same preview-only constraint |

### 10.5 `PricingPage.tsx` and `AccountPage.tsx`

See Section 19 for the full pricing/checkout spec.

---

## 11. Supported Formats & Ingestion Matrix

Unchanged from v2.0, now with tier gating layered on top:

| Format | Extension | Base | Cyber Pro | Sovereign |
|---|---|---|---|---|
| WAV | `.wav` | ✅ ≤25MB | ✅ ≤500MB | ✅ multi-GB |
| OGG | `.ogg`, `.oga` | ✅ ≤25MB | ✅ ≤500MB | ✅ multi-GB |
| IQ (uint8) | `.iq`, `.raw`, `.bin`, `.dat` | ❌ | ✅ ≤500MB | ✅ multi-GB, multi-channel batch |
| IQ (complex64) | `.cf32`, `.iq`, `.bin` | ❌ | ✅ ≤500MB | ✅ multi-GB, multi-channel batch |
| Live Mic | Hardware microphone | ✅ ≤15s | ✅ ≤60s | ✅ continuous stream buffer |

---

## 12. Environment Variables

Section 12's v2.0 variables (Supabase, model path, CORS) are unchanged. New v3.0 additions:

### Backend

```env
# ── Billing ───────────────────────────────────────────────────────────
STRIPE_SECRET_KEY=your_stripe_secret_key
STRIPE_WEBHOOK_SECRET=your_stripe_webhook_signing_secret
UPI_PROVIDER_API_KEY=your_upi_gateway_key

# ── Tier limits (defaults; can be overridden per-deployment) ───────────
TIER_BASE_MAX_UPLOAD_MB=25
TIER_CYBER_PRO_MAX_UPLOAD_MB=500
TIER_SOVEREIGN_MAX_UPLOAD_MB=8192

# ── Optional transcription service (Feature 5 — outside pure-NumPy core) ─
TRANSCRIPTION_SERVICE_URL=your_whisper_class_service_endpoint
TRANSCRIPTION_SERVICE_API_KEY=your_key
```

### Frontend

```env
VITE_STRIPE_PUBLISHABLE_KEY=your_stripe_publishable_key
VITE_PRICING_CURRENCY_DEFAULT=INR
```

---

## 13. API Documentation Standard

Section 13's `GET /health` and `GET /files/*` docs are unchanged from v2.0. `POST /analyze` is extended:

### `POST /analyze` (extended)

**Description:** Runs the core DSP + ML pipeline, plus any tier-entitled Suite A/B/C modules requested.
**Auth required:** No (anonymous → Base tier) / Yes (resolves actual tier)
**Content-Type:** `multipart/form-data`

**Request**
```
file:          binary, size/format limits per Section 11
sample_rate:   number (for raw IQ)
iq_dtype:      "uint8" | "complex64"
features:      string[] (optional) — e.g. ["doppler","entropy","fingerprint","bss"]
carrierFreqHz: number (optional, required for meaningful Doppler velocity output)
```

**Response — 200** (extended `data` shape)
```json
{
  "success": true,
  "data": {
    "fileInfo": { "...unchanged..." },
    "metrics": { "...unchanged..." },
    "visualizations": { "...unchanged..." },
    "aiAnalysis": { "...unchanged..." },
    "report": "...unchanged...",
    "advanced": {
      "fingerprint": { "locked": false, "cfoDriftPpm": 2.3, "iqImbalancePhaseDeg": 0.8, "..." },
      "doppler": { "locked": false, "driftRateHzPerSec": 12.4, "estimatedVelocityKmPerSec": null,
                    "note": "estimatedVelocityKmPerSec requires carrierFreqHz input" },
      "entropy": { "locked": false, "shannonEntropy": 0.842 },
      "bss": { "locked": true, "requiredTier": "SOVEREIGN" },
      "tdoa": { "locked": true, "requiredTier": "SOVEREIGN", "note": "Also requires POST /analyze/tdoa with multi-receiver input" }
    }
  }
}
```

### `POST /analyze/tdoa` (new)

**Description:** Multi-receiver TDoA trilateration.
**Auth required:** Yes, Sovereign tier
**Request:** array of `{ file, receiverLat, receiverLon, receiverTimestamp }` objects, minimum 3 receivers
**Response — 400** if fewer than 3 receivers are supplied — this is a hard physical requirement of trilateration, not an arbitrary limit.

### `GET /billing/tiers`, `POST /billing/checkout`, `POST /billing/webhook`, `GET /billing/me`

Standard REST semantics; see Section 19 for the commercial logic these implement.

### New error codes

| HTTP | Code | When to use |
|---|---|---|
| 402 | `TIER_LIMIT_EXCEEDED` | Upload exceeds the caller's tier size limit |
| 403 | `FEATURE_LOCKED` | Requested `features[]` entry not entitled for caller's tier |
| 400 | `INSUFFICIENT_RECEIVERS` | `/analyze/tdoa` called with fewer than 3 receiver inputs |
| 400 | `MISSING_CARRIER_FREQUENCY` | Doppler velocity requested without `carrierFreqHz` |
| 402 | `SUBSCRIPTION_PAST_DUE` | Billing webhook indicates a lapsed subscription |

---

## 14. Testing (As Built)

Section 14's 19 existing tests are unchanged. New v3.0 test coverage required:

- Tier-gating: Base-tier request for a Sovereign feature returns `403 FEATURE_LOCKED`, not a silent 200 with fabricated data
- Upload size gating per tier (`402 TIER_LIMIT_EXCEEDED`)
- `/analyze/tdoa` rejects `<3` receivers with `400 INSUFFICIENT_RECEIVERS`
- Doppler velocity field is `null` (not fabricated) when `carrierFreqHz` is omitted
- Billing webhook signature verification (reject unsigned/invalid webhook calls)
- Entropy/BSS/fingerprint modules produce stable output on the existing synthetic test signals (BPSK/QPSK/16-QAM/AM/FM generators from `classifier.py`)

---

## 15. Security Checklist

Section 15's v2.0 checklist (RLS, storage RLS, file validation, graceful no-op persistence, Pydantic validation) is unchanged and still required. New v3.0 items:

### Required for v3.0
- Stripe webhook signature verification (`STRIPE_WEBHOOK_SECRET`) — never trust an unsigned webhook payload to grant tier access
- Rate limiting on `/analyze` scaled per tier — Sovereign's heavier compute modules (BSS, sub-noise extraction) are the highest-cost path and need the strictest per-user throttling to control infrastructure spend
- Tier entitlement checks must happen **server-side** on every request — `TierGate.tsx` is a UX convenience, never the actual security boundary (a client could bypass a frontend check trivially)
- Idempotency keys on `/billing/checkout` to prevent duplicate charge attempts on retry
- PII/payment data: card numbers never touch SignalLens's own backend (Stripe Elements/Checkout handles this) — only tokens/subscription IDs are stored
- Audit log (`billing_events`) is append-only, same pattern as the existing forensic-style logging philosophy in the product

---

## 16. Master Build / Extension Prompt

```
You are extending the existing SignalLens AI codebase to add a 3-tier commercial model
(Base Hunter / Cyber Pro / Sovereign Defense) and 18 advanced analysis features across
three suites (Forensic Audio, Aerospace Telemetry, Next-Gen EW). Do not re-scaffold the
project; work within its established v2.0 architecture.

── Architectural constraints to preserve (unchanged from v2.0) ─────────
- signalens/ core stays strictly pure-NumPy. New Suite A/B/C modules (Section 7.7)
  must also be pure-NumPy EXCEPT the optional speech-transcription service (Feature 5),
  which is explicitly isolated outside signalens/ core as a separate service call —
  do not import a transcription model into the core engine.
- api/schemas.py and src/types/signal.ts stay in exact 1:1 sync for every new field.
- The client-side fallback (signal-analyzer.ts) stays Base-tier-only. Do not add
  Suite A/B/C logic to it — new orbitalMath.ts/defenseDsp.ts client files are
  PREVIEW/INTERPOLATION layers only, never the authoritative computation.
- DashboardPage.tsx Sections 01–08 render exactly as in v2.0. New features are
  ADDED as Sections 09–10, never replacing or restructuring the existing layout.

── Engineering honesty constraint (new, critical) ───────────────────────
Several requested "Suite C" features (Sections 5.3, 18.3) are named using
non-implementable physics ("relativistic," "gravitational lensing," "quantum
entropy collapse," "universal alien-signal demodulator"). Implement the REAL
underlying DSP technique for each (see Section 7.7's feasibility table), and
apply the requested marketing name only as a UI/copy label on top of an
honestly-computed, honestly-documented metric. Never fabricate a numeric
output for a phenomenon the signal processing cannot actually measure — if
a fabricated value is unavoidable given the spec, return null/locked with an
explanatory note instead, and flag it for product review rather than
shipping invented numbers.

── Tier gating ────────────────────────────────────────────────────────
- Entitlement checks happen server-side only. TierGate.tsx is UX, not security.
- Every locked feature is visible (not hidden) with a clear upgrade CTA —
  this is the product's upsell mechanism, not an incidental UI choice.

── Version safety (unchanged rule) ──────────────────────────────────────
Before adding any new Python or npm dependency (including Stripe SDK, Three.js,
any ICA/entropy libraries): web search for latest stable version + security
advisories, verify with pip show / npm show, and confirm the pure-NumPy
constraint isn't being silently violated by a transitive dependency.
```

---

## 17. Roadmap — Next Subsystems

Section 17's v2.0 roadmap items (auth on `/analyze`, rate limiting, additional modulation schemes, demodulation, waterfall display, full frontend auth, CORS hardening) remain valid and are **not superseded** by this revision — several are now prerequisites for v3.0's tier enforcement to be meaningful (rate limiting and auth in particular). Updated priority order:

| Priority | Item | Notes |
|---|---|---|
| **Critical (blocks v3.0 launch)** | Server-side tier entitlement enforcement + rate limiting | Without this, the entire commercial model in Section 19 is unenforceable — must ship before any paid tier goes live |
| **Critical** | Stripe + UPI integration with signed webhooks | Section 8.3, 15 |
| **High** | Resumable/chunked upload for Sovereign multi-GB captures | Not yet implemented; current upload path assumes a single request/response cycle |
| **High** | Real accuracy validation of Anti-Spoof Matrix (Feature 4) and Sub-Noise Extraction (Feature 8) claims | These carry numeric confidence outputs users may rely on operationally — need empirical validation against known-good/known-bad test signals before shipping as anything more than "beta" |
| **Medium** | Multi-receiver ingestion UI/UX for TDoA (Feature 10, 16) | Needs a genuinely different upload flow (multiple files + coordinates + timestamps), not a variant of the single-file Upload page |
| **Medium** | Full frontend user authentication (carried over from v2.0) | Now also a billing prerequisite |
| **Medium** | Additional modulation schemes / model retraining (carried over) | |
| **Low** | Demodulation + audio playback of demodulated signals (carried over, now partially covered by Feature 5) | |
| **Low** | Waterfall display (carried over) | |
| **Low** | Product-copy review pass on all 🔴-flagged feature names (Section 18) | Legal/marketing should confirm the branding-vs-science distinction is clear enough in-product to avoid overstated claims to paying defense/aerospace customers |

---

## 18. 18 Advanced Feature Suites — Full Breakdown

Each feature is tagged 🟢 (real, directly implementable), 🟡 (real technique, needs specific inputs/data SignalLens may not always have), or 🔴 (requested framing isn't physically implementable as named — shipped as branding on a real, disclosed metric). See the guardrail note at the top of this document for what each tag means in practice.

### 18.1 Suite A — Pre-Processing & Forensic Audio Pipeline (Cyber Pro tier)

| # | Feature | Tag | What actually ships |
|---|---|---|---|
| 1 | **Dual-Band Synchronous "Cockpit A/B" Audio Player** | 🟢 | Real feature: crossfader UI between the raw uploaded audio and a server-computed denoised version; SNR gain badge computed from actual before/after RMS-noise-floor comparison |
| 2 | **Forensic RF Fingerprinting & Emitter DNA Profiling** | 🟢 | Real technique: CFO drift (ppm), I/Q imbalance phase error are standard, measurable quantities. "Emitter hardware class matching" requires a reference fingerprint library, which ships as a small curated starter set, expandable over time — not a claim of universal hardware identification out of the box |
| 3 | **Interactive Spectrogram "Lasso / Bounding Box" Isolator** | 🟢 | Real, standard UI/DSP feature: canvas region selection → frequency-domain masking/filtering |
| 4 | **Real-time Jamming & Deepfake RF Anti-Spoofing Matrix** | 🟡 | Real class of detection technique (replay/spectral-consistency anomaly detection); the 0–100% "Authenticity Score" is a **composite heuristic**, not a certified forensic determination — must ship labeled as an investigative aid, with the underlying signals it's based on disclosed in the UI, not as a black-box verdict |
| 5 | **Automated Demodulation to Live Data / Audio Transcript** | 🟡 | Morse-to-text (CW) is 🟢 straightforward DSP. Voice transcription for AM/FM requires an actual speech model — real and buildable, but is **not** a pure-NumPy component (see Section 7.7 note) and needs its own service |
| 6 | **Interactive 3D Polar Constellation with EVM Stress-Map** | 🟢 | Real, standard technique: EVM is a well-defined, computable metric; 3D rendering via Three.js is a visualization choice, not a new physical measurement |

### 18.2 Suite B — Deep-Space & Aerospace Telemetry (split Cyber Pro / Sovereign)

| # | Feature | Tag | What actually ships |
|---|---|---|---|
| 7 | **Doppler Shift & "Relativistic" Orbital Velocity Estimator** | 🟢 core / 🔴 framing | Doppler drift rate (Hz/s) is real and computed directly from carrier tracking over time. Velocity in km/s is real **given a user-supplied nominal carrier frequency** — without it, velocity is `null`, not guessed. "Relativistic" is dropped from the actual computation; the UI may keep the word as flavor text on the Sovereign tier but the math is standard non-relativistic Doppler |
| 8 | **Deep-Space Sub-Noise Extraction (Stochastic Resonance)** | 🟡 | Real class of weak-signal-recovery technique (coherent integration/matched filtering). The specific "-20 dB SNR" figure is not a guarantee — actual recoverable SNR depends on integration time, signal structure, and noise stationarity; ships with a computed, capture-specific SNR improvement figure, not a fixed marketing number |
| 9 | **Ionospheric Scintillation & Solar Flare Interference Corrector** | 🟡 | Ships as a group-delay/phase-dispersion **proxy metric** computed from the signal itself. A true calibrated Total Electron Content (TEC) measurement requires reference GNSS data this product doesn't ingest — the UI must label this clearly as a proxy/estimate |
| 10 | **TDoA 3D Orbital Trajectory Map** | 🟡 | Real trilateration math, **requires ≥3 synchronized receiver inputs with known coordinates** (Section 8.3) — cannot run on a single uploaded file. UI must gate this behind the multi-receiver upload flow (Section 17 roadmap item), not present it as available from any single analysis |
| 11 | **Multi-Carrier Chirp Rate & "Gravitational Lensing" Drift Analysis** | 🟢 core / 🔴 framing | Chirp rate (α, Hz/s) via quadratic phase fit and time-bandwidth product are real, standard radar/SIGINT metrics. "Gravitational lensing" is not what's being measured — the UI displays the real chirp-rate metric under this feature name as branding, and the underlying number is always available/disclosed |
| 12 | **Quantum-Resistant Signal Entropy Engine** | 🟢 core / 🔴 framing | Shannon entropy (0.000–1.000) of the signal's symbol/amplitude distribution is a real, standard, well-defined computation. "Quantum-resistant" describes nothing about the computation itself (entropy scoring doesn't relate to cryptographic quantum-resistance) — the feature is real entropy analysis under a marketing name |

### 18.3 Suite C — Next-Gen Electronic Warfare & Sci-Fi SIGINT (Sovereign tier)

| # | Feature | Tag | What actually ships |
|---|---|---|---|
| 13 | **RF Blind Source Separation ("Cocktail Party" Solver)** | 🟢 | Real technique (ICA-style unmixing), implementable in pure NumPy. **"5 isolated tracks" is a UI default, not a DSP guarantee** — the algorithm reports however many statistically separable components it finds (which may be fewer or more than 5); labels like "Voice/Telemetry/Jammer/Noise/Beacon" are suggested/user-assignable tags on generic output channels, not an AI classification of what each stem "is" unless a separate classifier is explicitly run on each stem |
| 14 | **Physical Layer Steganography & Covert Channel Sniffer** | 🟢 | Real anomaly-detection technique (statistical deviation in sub-noise-floor residuals). Ships as an **anomaly flag with a confidence score**, explicitly not a "confirmed covert channel" claim — false positives are possible and the UI must say so |
| 15 | **Drone/UAV Micro-Doppler "Blade Radar Signature" Profiler** | 🟢 | Real, established radar technique — periodic Doppler modulation from rotating reflectors (propeller blades) is genuinely detectable and RPM-estimable from an appropriate RF capture. Requires the capture to actually contain such a signature; on an arbitrary signal this correctly reports "no periodic micro-Doppler signature detected," not a fabricated drone profile |
| 16 | **Ionospheric Bounce & Geo-Origin Trilateration (OTH)** | 🟡 | Skip-distance estimation from HF propagation timing is real physics. Full geo-origin trilateration has the same multi-receiver requirement as Feature 10 — single-file "trilateration" is not physically possible and is not what ships from a single upload |
| 17 | **Quantum RF Entropy Collapse** | 🔴 | This is explicitly a **rebrand of the Feature 12 entropy engine plus a spectral-kurtosis composite score**, documented in the API as `compositeAnomalyIndex`. No physical "collapse" or quantum computation occurs. Shipped as a named UI feature per the client's spec, with the real underlying computation fully disclosed in Section 7.7 and in the API response so it is never a mystery black box |
| 18 | **Universal Symbolic Demodulator Sandbox (Live Hex-Dump)** | 🟡 core / 🔴 "universal alien" framing | Blind symbol-rate/clock estimation (via cyclostationary feature detection) and raw hex/binary dumping at that estimated clock are both real and implementable. There is no such thing as a truly "universal" decoder for arbitrary unknown protocols — output is always a **best-effort raw bitstream at an estimated symbol clock**, which a human analyst then interprets. The UI must not imply automatic semantic decoding of unknown/"alien" signals |

---

## 19. Commercial Tiering & Pricing Specification

### 19.1 Tier definitions

| | **Base Hunter** | **Cyber Pro** | **Ultra Pro Max — Sovereign Defense** |
|---|---|---|---|
| **Price (INR)** | ₹0 forever | ₹2,499/mo (or annual, −20%) | ₹16,999/mo (or annual, −20%) |
| **Price (USD)** | $0 forever | $29/mo (or annual, −20%) | $199/mo (or annual, −20%) |
| **Target** | Students, radio amateurs, hobbyists | Professional RF engineers, telecom security auditors, SIGINT researchers | Aerospace defense labs, satellite tracking stations, EW units |
| **Max upload** | 25 MB | 500 MB | Multi-GB, multi-channel batch |
| **Formats** | `.wav`, `.ogg` only | + `.iq` (uint8/complex64), `.raw`, `.cf32`, `.cs16` | All formats + continuous stream buffers |
| **Live mic** | ≤15s | ≤60s | Continuous |
| **Core pipeline (Sections 01–08)** | ✅ | ✅ | ✅ |
| **Classification** | Basic tags only (AM/FM/CW/Noise) | Full modulation classifier | Full modulation classifier |
| **Suite A (Features 1–6)** | ❌ | ✅ | ✅ |
| **Suite B (Features 7–12)** | ❌ | Partial (7, 11, 12 — the 🟢-core ones) | Full (8, 9, 10 require Sovereign compute/multi-receiver) |
| **Suite C (Features 13–18)** | ❌ | ❌ | ✅ |
| **Export** | `.txt` report only | Cleaned WAV, JSON telemetry, forensic report | Military-grade PDF dossier, raw IQ streams, priority GPU API access |

### 19.2 `/pricing` route — `PricingPage.tsx`

**Visual spec:**
- Background: deep obsidian black `#080B10`
- Accents: neon cyan `#00F2FE`, electric blue `#4FACFE`
- Glassmorphism: `backdrop-blur-xl` on tier cards
- Cyber Pro card visually highlighted as the "hero"/recommended tier

**Interactive elements:**
- Currency toggle: INR (₹) / USD ($)
- Billing cycle toggle: Monthly / Annual (−20%)
- 3 tier cards (Base Hunter, Cyber Pro, Sovereign Defense) with feature checklists pulled from `GET /billing/tiers`, not hardcoded, so pricing/features stay server-controlled

### 19.3 Checkout modal

```
Dynamic price breakdown: Base Price + Taxes = Total (tax calculation should use
a real tax-rate service or a clearly-labeled estimate — do not hardcode a tax
rate as if it's universally correct across jurisdictions).

Payment methods:
  - UPI QR code (India) — generated server-side via the UPI provider integration
  - Global card input — Stripe Elements/Checkout, dark theme matching the page

"Simulate Successful Payment" — a TEST-MODE-ONLY trigger (must be hard-disabled
outside a development/staging environment flag) that flips local app state to
Pro/Sovereign and plays a confetti animation, for demo/QA purposes. This must
never be reachable in production builds — gate it behind an explicit
VITE_ENABLE_PAYMENT_SIMULATION=true env flag that defaults to false/absent.
```

### 19.4 `services/billing.ts` — state machine

```
States: BASE → (checkout initiated) → PENDING → (webhook confirms) → CYBER_PRO | SOVEREIGN
                                              → (webhook fails/declines) → BASE (with error surfaced)
Also handles: downgrade-at-period-end, past-due (grace period before feature
lock), and cancellation. Source of truth is always the backend's
/billing/me response — local state is a cache/optimistic-UI layer only,
consistent with the "server-side entitlement enforcement" guardrail in
Section 15.
```

---

*This PRD (v3.0) extends the working SignalLens AI repository (SIH26147) with a commercial tiering model and 18 advanced feature suites. Per the architectural guardrails preserved throughout, the v2.0 core engine, schema-sync discipline, dual-mode frontend, and Dashboard layout are unchanged. Per the engineering-honesty note at the top of this document, several Suite C features are implemented as real, disclosed DSP techniques wearing requested marketing names — Section 18's tag table is the authoritative reference for what each feature actually computes versus what it's branded as, and should be treated as a guardrail for implementation and for customer-facing claims alike.*