resource "google_container_node_pool" "h100_node_pool" {
  name       = "h100-analyst-pool"
  location   = "us-central1-a" 
  cluster    = google_container_cluster.primary.name
  
  initial_node_count = 0
  autoscaling {
    min_node_count = 0
    max_node_count = 1 
  }
  
  node_config {
    machine_type = "a3-highgpu-1g"

    guest_accelerator {
      type  = "nvidia-h100-80gb"
      count = 1 
      
      gpu_driver_installation_config {
        gpu_driver_version = "LATEST"
      }
    }

    taint {
      key    = "nvidia.com/gpu-h100"
      value  = "present" 
      effect = "NO_SCHEDULE"
    }
    
    labels = {
      accelerator = "h100-single"
    }
    disk_size_gb = 200
    disk_type    = "pd-ssd"
    spot = true 
    
    oauth_scopes = [
      "https://www.googleapis.com/auth/cloud-platform"]

    metadata = {
      disable-legacy-endpoints = "true"
    }
  }

  management {
    auto_repair  = true
    auto_upgrade = true
  }
}
