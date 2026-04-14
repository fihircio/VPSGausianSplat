# VPS Cloud Portal - Demo Walkthrough

This document provides a structured narrative for demonstrating the VPS + Gaussian Splatting platform to CMOs, investors, and technical partners.

## 🎙️ The 3-Minute Narrative

### 1. Introduction (The Problem)
*"Today, creating AR experiences that 'stick' to the real world is either locked into closed ecosystems like Google/Apple or requires massive manual alignment. We've built an open, high-precision Spatial Cloud that turns any space into a photorealistic AR-ready environment in minutes."*

### 2. The Loop: Scan & Process (Page A & B)
*"Let's start with a simple video scan of a retail floor. We upload it to our **Scene Manager**. Behind the scenes, we extract frames, estimate camera poses using COLMAP, and simultaneously train a Gaussian Splatting model. Traditionally, this took days of photogrammetry; our pipeline automates the entire flow from raw pixel to spatial index."*

### 3. The Power: VPS Localization (Page C)
*"Now that our scene is 'Ready', any AR device can query it. Watch as I upload a single query image. The system identifies unique features, matches them against our global FAISS index, and returns a 6DoF pose with sub-centimeter accuracy. This is the 'Anchor' that allows AR objects to stay perfectly in place for every user."*

### 4. The Moat: Performance Benchmarks (Page D)
*"Finally, we don't just guess accuracy—we measure it. Our **Investor Dashboard** shows a parameter sweep across ORB feature densities. We can consistently achieve >90% success rates with <10cm translation error. This data is our moat, allowing us to optimize for any hardware from mobile phones to high-end AR glasses."*

---

## 🛠️ Running the Demo

### Prerequisites
- Node.js 20+ (recommended)
- Docker (for Backend DB/Redis)

### Steps

1. **Setup Backend**
   ```bash
   # From root
   cd backend
   docker compose up -d
   # Initialize DB
   python3 -m backend.utils.db
   ```

2. **Setup Frontend**
   ```bash
   cd frontend
   npm install
   cp .env.example .env.local
   npm run dev
   ```

3. **Access Portal**
   Open [http://localhost:3000](http://localhost:3000)

### Demo Mode (Offline)
If you are presenting without a live GPU worker, the **Investor Dashboard** automatically engages **Demo Mode**, pre-loading a high-fidelity evaluation report from `lib/api.ts` to showcase the visualization capabilities.

---

## 🎬 Essential Key Visuals
- **Upload Page**: Clean, drag-and-drop interface.
- **Monitor Timeline**: Dynamic progress tracking from Uploaded to Ready.
- **KPI Cards**: Bold, high-contrast metrics for "Success Rate" and "Mean Accuracy".
