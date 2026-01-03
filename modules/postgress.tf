
resource "google_project_service" "sqladmin_api" {
  service            = "sqladmin.googleapis.com"
  disable_on_destroy = false
}

# Create a Cloud SQL instance for PostgreSQL
resource "google_sql_database_instance" "postgres_instance" {
  name             = "pg-instance-via-tf"
  database_version = "POSTGRES_15" # Specify the desired PostgreSQL version
  region           = "us-central1"

  settings {
    # The tier for the Cloud SQL instance, determines CPU and memory
    tier = "db-f1-micro"

    # Set disk size and enable disk auto-resize
    disk_size       = 10
    disk_autoresize = true

    # Network configuration for private IP
    # If you need public IP, adjust authorized_networks
    ip_configuration {
      authorized_networks {
        value = "0.0.0.0/0"
      }
    }
  }

  # Prevents accidental deletion of the instance
  deletion_protection = false
  depends_on          = [google_project_service.sqladmin_api]
}

# Generate a random password for the default user
resource "random_password" "db_password" {
  length           = 16
  special          = true
  override_special = "!#$%*()_-+="

  keepers = {
    rotatation_version = "2"
  }
}

# Create a database user
resource "google_sql_user" "db_user" {
  name     = "sirius"
  instance = google_sql_database_instance.postgres_instance.name
  password = random_password.db_password.result
}

# Create the initial database
resource "google_sql_database" "database" {
  name     = "n8ndb"
  instance = google_sql_database_instance.postgres_instance.name
}

# Output the connection name and generated password
output "instance_connection_name" {
  value       = google_sql_database_instance.postgres_instance.connection_name
  description = "The connection name of the instance, used for the Cloud SQL Proxy"
}

output "database_user_password" {
  value     = random_password.db_password.result
  sensitive = true
}
