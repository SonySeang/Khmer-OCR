#!/bin/bash
# ══════════════════════════════════════════════════════════════════
# deploy.sh  —  Deploy Khmer OCR to Google Cloud Run
#
# BEFORE RUNNING:
#   1. Install gcloud CLI: https://cloud.google.com/sdk/docs/install
#   2. Login:  gcloud auth login
#   3. Set project: gcloud config set project YOUR_PROJECT_ID
#   4. Enable APIs:
#        gcloud services enable run.googleapis.com
#        gcloud services enable cloudbuild.googleapis.com
#        gcloud services enable containerregistry.googleapis.com
#   5. Set your API keys below (or export them before running)
# ══════════════════════════════════════════════════════════════════

set -e  # Stop on any error

# ── Configuration ────────────────────────────────────────────────────
SERVICE_NAME="khmer-ocr"
REGION="asia-southeast1"          # Same region as AksarDoc
PROJECT_ID=$(gcloud config get-value project 2>/dev/null)
IMAGE="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

# ── API Keys (set these or export them in your shell) ────────────────
GOOGLE_API_KEY="${GOOGLE_API_KEY:-}"
ANTHROPIC_API_KEY="${ANTHROPIC_API_KEY:-}"

# ── Validate ─────────────────────────────────────────────────────────
if [ -z "$PROJECT_ID" ]; then
  echo "❌ No GCP project set. Run: gcloud config set project YOUR_PROJECT_ID"
  exit 1
fi

if [ -z "$GOOGLE_API_KEY" ] || [ -z "$ANTHROPIC_API_KEY" ]; then
  echo "❌ API keys not set. Export them first:"
  echo "   export GOOGLE_API_KEY=your-key"
  echo "   export ANTHROPIC_API_KEY=your-key"
  exit 1
fi

echo ""
echo "═══════════════════════════════════════════"
echo "  🚀 Deploying Khmer OCR to Cloud Run"
echo "  Project : ${PROJECT_ID}"
echo "  Service : ${SERVICE_NAME}"
echo "  Region  : ${REGION}"
echo "  Image   : ${IMAGE}"
echo "═══════════════════════════════════════════"
echo ""

# ── Step 1: Build & push Docker image via Cloud Build ───────────────
echo "📦 Step 1/2: Building image (this takes ~3-5 minutes)..."
gcloud builds submit --tag "${IMAGE}" .

# ── Step 2: Deploy to Cloud Run ──────────────────────────────────────
echo ""
echo "☁️  Step 2/2: Deploying to Cloud Run..."
gcloud run deploy "${SERVICE_NAME}" \
  --image "${IMAGE}" \
  --platform managed \
  --region "${REGION}" \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 2 \
  --timeout 300 \
  --concurrency 10 \
  --min-instances 0 \
  --max-instances 5 \
  --set-env-vars "GOOGLE_API_KEY=${GOOGLE_API_KEY},ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY},FLASK_ENV=production"

# ── Done ─────────────────────────────────────────────────────────────
echo ""
echo "✅ Deployment complete!"
echo ""
SERVICE_URL=$(gcloud run services describe "${SERVICE_NAME}" \
  --region "${REGION}" \
  --format 'value(status.url)' 2>/dev/null)
echo "🌐 Your app is live at: ${SERVICE_URL}"
echo ""
