# GCP Infrastructure for NYC Transit Analytics
# Terraform configuration

terraform {
  required_version = ">= 1.0"
  
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
  zone    = var.zone
}

# Variables
variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "region" {
  description = "GCP Region"
  type        = string
  default     = "us-central1"
}

variable "zone" {
  description = "GCP Zone"
  type        = string
  default     = "us-central1-a"
}

variable "environment" {
  description = "Environment (dev, staging, prod)"
  type        = string
  default     = "dev"
}

# Enable required APIs
resource "google_project_service" "required_apis" {
  for_each = toset([
    "cloudfunctions.googleapis.com",
    "cloudbuild.googleapis.com",
    "run.googleapis.com",
    "dataproc.googleapis.com",
    "storage-component.googleapis.com",
    "bigquery.googleapis.com",
    "sql-component.googleapis.com",
    "redis.googleapis.com",
    "cloudscheduler.googleapis.com",
    "secretmanager.googleapis.com",
  ])

  service = each.value
  project = var.project_id

  disable_dependent_services = false
  disable_on_destroy         = false
}

# Cloud Storage Buckets
resource "google_storage_bucket" "raw_data" {
  name          = "${var.project_id}-nyc-transit-raw"
  location      = var.region
  force_destroy = var.environment != "prod"

  versioning {
    enabled = var.environment == "prod"
  }

  lifecycle_rule {
    condition {
      age = 30 # days
    }
    action {
      type = "Delete"
    }
  }
}

resource "google_storage_bucket" "staging" {
  name          = "${var.project_id}-nyc-transit-staging"
  location      = var.region
  force_destroy = var.environment != "prod"

  versioning {
    enabled = var.environment == "prod"
  }
}

# Cloud SQL (PostgreSQL)
resource "google_sql_database_instance" "main" {
  name             = "nyc-transit-db-${var.environment}"
  database_version = "POSTGRES_15"
  region           = var.region

  settings {
    tier              = var.environment == "prod" ? "db-n1-standard-1" : "db-f1-micro"
    availability_type = var.environment == "prod" ? "REGIONAL" : "ZONAL"
    
    backup_configuration {
      enabled    = var.environment == "prod"
      start_time = "03:00"
    }
    
    ip_configuration {
      ipv4_enabled                                  = false
      private_network                               = null
      enable_private_path_for_google_cloud_services = true
    }
  }

  deletion_protection = var.environment == "prod"
}

resource "google_sql_database" "main" {
  name     = "nyc_transit"
  instance = google_sql_database_instance.main.name
}

# Memorystore (Redis)
resource "google_redis_instance" "main" {
  name           = "nyc-transit-redis-${var.environment}"
  display_name   = "NYC Transit Redis"
  memory_size_gb = var.environment == "prod" ? 5 : 1
  region         = var.region
  redis_version  = "REDIS_7_0"

  authorized_network = null # Use VPC for production
}

# BigQuery Dataset
resource "google_bigquery_dataset" "main" {
  dataset_id    = "nyc_transit"
  friendly_name = "NYC Transit Analytics"
  description   = "NYC Transit GTFS-RT data warehouse"
  location      = var.region

  labels = {
    environment = var.environment
    project     = "nyc-transit"
  }
}

# Service Account for Cloud Functions/Cloud Run
resource "google_service_account" "etl" {
  account_id   = "nyc-transit-etl"
  display_name = "NYC Transit ETL Service Account"
}

# Grant permissions to service account
resource "google_project_iam_member" "etl_storage" {
  project = var.project_id
  role    = "roles/storage.admin"
  member  = "serviceAccount:${google_service_account.etl.email}"
}

resource "google_project_iam_member" "etl_bigquery" {
  project = var.project_id
  role    = "roles/bigquery.dataEditor"
  member  = "serviceAccount:${google_service_account.etl.email}"
}

resource "google_project_iam_member" "etl_dataproc" {
  project = var.project_id
  role    = "roles/dataproc.worker"
  member  = "serviceAccount:${google_service_account.etl.email}"
}

# Secret Manager secrets (placeholders - set values manually)
resource "google_secret_manager_secret" "mta_api_key" {
  secret_id = "mta-api-key"

  replication {
    auto {}
  }
}

# Outputs
output "project_id" {
  value = var.project_id
}

output "raw_bucket" {
  value = google_storage_bucket.raw_data.name
}

output "staging_bucket" {
  value = google_storage_bucket.staging.name
}

output "database_connection_name" {
  value = google_sql_database_instance.main.connection_name
}

output "redis_host" {
  value = google_redis_instance.main.host
}

output "bigquery_dataset" {
  value = google_bigquery_dataset.main.dataset_id
}

output "service_account_email" {
  value = google_service_account.etl.email
}

