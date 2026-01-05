
resource "google_container_node_pool" "cluster" {
  name     = "devops-lab-nodepool"
  location = "us-central1-a"
  cluster  = google_container_cluster.primary.name

  network_config {
    pod_range = "pod-ranges-ext"
  }
  initial_node_count = 2

  autoscaling {
    min_node_count = 1
    max_node_count = 16
  }

  node_config {
    machine_type = "e2-standard-2"
    disk_size_gb = 25
    disk_type    = "pd-ssd"
    oauth_scopes = [
      "https://www.googleapis.com/auth/cloud-platform"
    ]
  }
  depends_on = [google_container_cluster.primary]

}
