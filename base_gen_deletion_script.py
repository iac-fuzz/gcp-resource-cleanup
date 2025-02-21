import argparse
import subprocess
import sys
import json
from typing import List


def run_command(command: List[str]) -> str:
    """Run a shell command and return the output."""
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error running command: {' '.join(command)}")
        print(result.stderr)
        # sys.exit(1)
    print(f"Command output (stdout): '{result.stdout}'")  # Debug print
    print(f"Command error (stderr): '{result.stderr}'")   # Debug print
    print(f"Return code: {result.returncode}")          
    return result.stdout.strip()

def login(key_file: str, project_id: str):
    run_command(["gcloud", "-q", "auth", "activate-service-account", "--key-file", key_file])
    run_command(["gcloud", "-q", "config", "set", "project", project_id])


def list_resources(gcloud_component: str, resource_type: str, use_uri: bool, filter_expression: str) -> List[str]:
    command = ["gcloud", gcloud_component]
    if resource_type:
        command.append(resource_type)
    command.append("list")
    if filter_expression:
        command += ["--filter", filter_expression]
    command.append("--uri" if use_uri else "--format=table[no-heading](name)")
    output = run_command(command)
    print(output)
    return output.splitlines() if output else []


def create_deletion_code(gcloud_component: str, resource_types: List[str], use_uri: bool, project_id: str, filter_expression: str, async_mode: bool):
    for resource_type in resource_types:
        print(f"Listing {gcloud_component} {resource_type}", file=sys.stderr)
        resources = list_resources(gcloud_component, resource_type, use_uri, filter_expression)

        if resources:
            print(f"Listed {len(resources)} {gcloud_component} {resource_type}", file=sys.stderr)

        for resource in resources:
            delete_command = ["gcloud", gcloud_component, resource_type, "delete", "--project", project_id, "-q", resource]
            if async_mode:
                delete_command.append("--async")
            print(' '.join(delete_command))


def list_buckets(filter_expression: str) -> List[str]:
    output = run_command(["gsutil", "ls"])
    buckets = output.splitlines()

    if filter_expression.startswith("labels."):
        key, val = filter_expression[7:].split("=", 1)
        filtered_buckets = [bucket for bucket in buckets if val in run_command(["gsutil", "label", "get", bucket])]
        return filtered_buckets
    
    return buckets


def create_bucket_deletion_code(filter_expression: str, async_mode: bool):
    buckets = list_buckets(filter_expression)
    if buckets:
        print(f"Listed {len(buckets)} buckets", file=sys.stderr)

    for bucket in buckets:
        command = ["gsutil", "rm", "-r", bucket]
        if async_mode:
            command.append("&")
        print(' '.join(command))


def main():
    parser = argparse.ArgumentParser(description="Generate GCP resource deletion script.")
    parser.add_argument("-p", "--project", required=True, help="GCP project ID")
    parser.add_argument("-k", "--key-file", default="project-viewer-credentials.json", help="Service account key file")
    parser.add_argument("-f", "--filter", default="", help="Filter expression")
    parser.add_argument("-b", "--background", action="store_true", help="Run deletion commands asynchronously")

    args = parser.parse_args()

    login(args.key_file, args.project)

    compute_resource_types = [
        "instances", "addresses", "target-http-proxies", "target-https-proxies", "target-grpc-proxies",
        "url-maps", "backend-services", "firewall-rules", "forwarding-rules", "health-checks",
        "http-health-checks", "https-health-checks", "instance-templates", "networks", "routes",
        "routers", "target-pools", "target-tcp-proxies"
    ]

    print("set -x")  # Easier tracking when running the script
    create_deletion_code("container", ["clusters"], True, args.project, args.filter, args.background)
    create_deletion_code("compute", compute_resource_types, True, args.project, args.filter, args.background)
    create_deletion_code("sql", ["instances"], False, args.project, args.filter, args.background)
    create_deletion_code("app", ["services", "firewall-rules"], True, args.project, args.filter, args.background)
    create_deletion_code("pubsub", ["subscriptions", "topics", "snapshots"], True, args.project, args.filter, args.background)
    create_deletion_code("functions", [""], False, args.project, args.filter, args.background)

    create_bucket_deletion_code(args.filter, args.background)


if __name__ == "__main__":
    main()
