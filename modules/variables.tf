variable "github_token" {
  description = "GitHub token"
  sensitive   = true
  type        = string
  default     = ""
}

variable "github_org" {
  description = "GitHub organization"
  type        = string
  default     = ""
}

variable "github_repository" {
  description = "GitHub repository"
  type        = string
  default     = ""
}

variable "project_id" { 
  type = string 
  description = "Gcloud project id"
}


variable "namespace" { 
  type = string 
  default = "cnpg-system" 
}

  variable "ksa_name" {
  type = string 
  default = "cnpg-backup-sa" 
}

variable "gcs_bucket_name" {
  type = string 
}  
