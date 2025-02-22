provider "google-beta" {
  project = "terraform-437400"
  zone = "us-west1-a"
}

resource "google_compute_network" "net" {
  provider = google-beta
  name                    = "my-network"
  auto_create_subnetworks = true
}

resource "google_compute_subnetwork" "subnet" {
  provider = google-beta
  name          = "my-subnetwork"
  network       = google_compute_network.net.id
  ip_cidr_range = "10.0.0.0/16"
  region        = "us-central1"
}

resource "google_compute_router" "router" {
  provider = google-beta
  name    = "my-router"
  region  = google_compute_subnetwork.subnet.region
  network = google_compute_network.net.id
}

resource "google_compute_router_route_policy" "rp-export" {
  provider = google-beta
  router = google_compute_router.router.name
  region = google_compute_router.router.region
    name = "my-rp1"
    type = "ROUTE_POLICY_TYPE_EXPORT"
    terms {
    priority = 1
    match {
      expression = "destination == '10.0.0.0/12'"
      }
    actions {
      expression = "accept()"
    }
  }
}
