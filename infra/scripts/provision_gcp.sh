#!/usr/bin/env bash
# Sovereign Infrastructure Provisioning for Block 1
# Region: asia-south1 (Mumbai)
# Project: workkbot

set -euo pipefail

PROJECT_ID="workkbot"
REGION="asia-south1"
ZONE="asia-south1-a"
VPC_NAME="workkbot-sovereign-vpc"
SUBNET_NAME="workkbot-mumbai-subnet"
SUBNET_RANGE="10.10.0.0/24"
PSA_RANGE_NAME="workkbot-psa-range"
DB_INSTANCE_NAME="workkbot-db"
DB_NAME="workkbot"
BASTION_NAME="workkbot-bastion"

echo "=== 1. Setting active project and region ==="
gcloud config set project "${PROJECT_ID}"
gcloud config set compute/region "${REGION}"
gcloud config set compute/zone "${ZONE}"

echo "=== 2. Enabling Required GCP APIs ==="
gcloud services enable \
    compute.googleapis.com \
    servicenetworking.googleapis.com \
    sqladmin.googleapis.com \
    iap.googleapis.com \
    run.googleapis.com \
    cloudbuild.googleapis.com \
    identitytoolkit.googleapis.com

echo "=== 3. Creating Dedicated Sovereign VPC & Subnet ==="
if ! gcloud compute networks describe "${VPC_NAME}" >/dev/null 2>&1; then
    gcloud compute networks create "${VPC_NAME}" --subnet-mode=custom
fi

if ! gcloud compute networks subnets describe "${SUBNET_NAME}" --region="${REGION}" >/dev/null 2>&1; then
    gcloud compute networks subnets create "${SUBNET_NAME}" \
        --network="${VPC_NAME}" \
        --region="${REGION}" \
        --range="${SUBNET_RANGE}" \
        --enable-private-ip-google-access
fi

echo "=== 4. Setting up Private Services Access (PSA) for Cloud SQL ==="
if ! gcloud compute addresses describe "${PSA_RANGE_NAME}" --global >/dev/null 2>&1; then
    gcloud compute addresses create "${PSA_RANGE_NAME}" \
        --global \
        --purpose=VPC_PEERING \
        --prefix-length=16 \
        --network="${VPC_NAME}"
fi

gcloud services vpc-peerings connect \
    --service=servicenetworking.googleapis.com \
    --ranges="${PSA_RANGE_NAME}" \
    --network="${VPC_NAME}" || true

echo "=== 5. Provisioning Private IP Cloud SQL PostgreSQL 16 ==="
if ! gcloud sql instances describe "${DB_INSTANCE_NAME}" >/dev/null 2>&1; then
    gcloud sql instances create "${DB_INSTANCE_NAME}" \
        --database-version=POSTGRES_16 \
        --tier=db-custom-2-7680 \
        --region="${REGION}" \
        --network="projects/${PROJECT_ID}/global/networks/${VPC_NAME}" \
        --no-assign-ip \
        --database-flags=cloudsql.iam_authentication=on
fi

# Ensure default database exists
if ! gcloud sql databases describe "${DB_NAME}" --instance="${DB_INSTANCE_NAME}" >/dev/null 2>&1; then
    gcloud sql databases create "${DB_NAME}" --instance="${DB_INSTANCE_NAME}"
fi

echo "=== 6. Configuring IAP Bastion Firewall and VM ==="
if ! gcloud compute firewall-rules describe allow-iap-ssh-tunnel >/dev/null 2>&1; then
    gcloud compute firewall-rules create allow-iap-ssh-tunnel \
        --network="${VPC_NAME}" \
        --allow=tcp:22 \
        --source-ranges=35.235.240.0/20 \
        --target-tags=iap-bastion
fi

if ! gcloud compute instances describe "${BASTION_NAME}" --zone="${ZONE}" >/dev/null 2>&1; then
    gcloud compute instances create "${BASTION_NAME}" \
        --zone="${ZONE}" \
        --machine-type=e2-micro \
        --subnet="${SUBNET_NAME}" \
        --tags=iap-bastion \
        --no-address \
        --metadata=enable-oslogin=TRUE
fi

echo "=== Infrastructure Provisioning Complete ==="
echo "To tunnel port 5432 from your local machine to Cloud SQL private IP via IAP:"
echo "DB_PRIVATE_IP=\$(gcloud sql instances describe ${DB_INSTANCE_NAME} --format='value(ipAddresses[0].ipAddress)')"
echo "gcloud compute start-iap-tunnel ${BASTION_NAME} 5432 --zone=${ZONE} --local-host-port=localhost:5432"
