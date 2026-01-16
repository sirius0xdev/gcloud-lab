resource "google_container_node_pool" "gpu_pool" {
  name       = "gpu-pool-l4"
  location   = "us-central1-a"
  cluster    = google_container_cluster.primary.name
  
  initial_node_count = 0 

  autoscaling {
    min_node_count = 0
    max_node_count = 5
    }

  node_config {
    machine_type = "g2-standard-8" # Optimized for NVIDIA L4

    guest_accelerator {
      type  = "nvidia-l4"
      count = 1
    }

    # Use SPOT instances to save ~60-90% on GPU costs
    spot = true

    oauth_scopes = [
      "https://www.googleapis.com/auth/cloud-platform"
    ]

    labels = {
      workload = "llm-analyst"
    }

    taint {
      key    = "nvidia.com/gpu"
      value  = "present"
      effect = "NO_SCHEDULE"
    }
  }

  management {
    auto_repair  = true
    auto_upgrade = true
  }
}
