
resource "google_storage_bucket" "backup_bucket" {
  name     = "customer1_db_backup"
  location = "US"
  storage_class = "STANDARD"
  uniform_bucket_level_access = true 
  
versioning {
    enabled = true
  }

  lifecycle {
    prevent_destroy = true
  }
}

resource "google_service_account" "cnpg_backup_sa" {
  account_id   = "cnpg-backup-sa"
  display_name = "CNPG PostgreSQL GCS Backup SA"
  description  = "Used by CNPG operator pods for GCS backup access via Workload Identity"
}

# Grant minimal Storage permissions (adjust as needed)
resource "google_project_iam_member" "cnpg_backup_sa_storage" {
  project = var.project_id
  role    = "roles/storage.objectAdmin"  # Or finer: roles/storage.objectCreator + roles/storage.objectViewer + roles/storage.legacyBucketReader
  member  = "serviceAccount:${google_service_account.cnpg_backup_sa.email}"
}

resource "google_service_account_iam_binding" "workload_identity_binding" {
  service_account_id = google_service_account.cnpg_backup_sa.name
  role               = "roles/iam.workloadIdentityUser"

  members = [
    "serviceAccount:${var.project_id}.svc.id.goog[${var.namespace}/${var.ksa_name}]"
  ]
}

# Outputs (useful for cross-reference or verification)
output "gcp_sa_email" {
  value = google_service_account.cnpg_backup_sa.email
}

resource "google_service_account_iam_member" "token_creator_binding" {
  service_account_id = google_service_account.cnpg_backup_sa.name
  role               = "roles/iam.serviceAccountTokenCreator"
  
  # This allows the GSA to generate tokens for itself when called by the pod
  member             = "serviceAccount:${google_service_account.cnpg_backup_sa.email}"
}

