#!/bin/bash
set -e

PROJECT_ID=$(gcloud config get-value project)
REGION="us-central1"
CLUSTER_NAME="building-permit-cluster"
REPO_NAME="building-permit"
GCP_SA_NAME="build-permit-sa"
K8S_SA_NAME="build-permit-ksa"
NAMESPACE="building-permit"

echo "Using Project ID: $PROJECT_ID"

# 1. Create a Workload Identity bound Kubernetes Service Account
echo "Creating GKE Cluster (Autopilot) to support Workload Identity..."
gcloud container clusters create-auto $CLUSTER_NAME \
    --region $REGION \
    --project $PROJECT_ID || echo "Cluster may already exist"

# Update kubeconfig
gcloud container clusters get-credentials $CLUSTER_NAME --region $REGION --project $PROJECT_ID

# 2. Setup Workload Identity
echo "Setting up namespace and workload identity bindings..."
kubectl apply -f namespace.yaml

kubectl create serviceaccount $K8S_SA_NAME \
    --namespace $NAMESPACE || echo "KSA may already exist"

gcloud iam service-accounts add-iam-policy-binding \
    $GCP_SA_NAME@$PROJECT_ID.iam.gserviceaccount.com \
    --role roles/iam.workloadIdentityUser \
    --member "serviceAccount:$PROJECT_ID.svc.id.goog[$NAMESPACE/$K8S_SA_NAME]"

kubectl annotate serviceaccount $K8S_SA_NAME \
    --namespace $NAMESPACE \
    iam.gke.io/gcp-service-account=$GCP_SA_NAME@$PROJECT_ID.iam.gserviceaccount.com

# 3. Build & Push Docker images using Cloud Build
echo "Building Agent image..."
gcloud builds submit ../agent -t ${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/building-permit-agent:latest

echo "Building API image..."
gcloud builds submit ../api -t ${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/building-permit-api:latest

echo "Building Frontend image..."
gcloud builds submit ../frontend -t ${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/building-permit-frontend:latest

# 4. Deploy Manifests
echo "Applying Kubernetes manifests..."
kubectl apply -f configmap.yaml
kubectl apply -f agent.yaml
kubectl apply -f api.yaml
kubectl apply -f frontend.yaml

echo "Deploy commands complete. Run 'kubectl get services -n building-permit' to get your external IPs for API and Frontend."
