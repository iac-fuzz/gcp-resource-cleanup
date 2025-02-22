import re
import sys
import json
import argparse
import subprocess
from typing import List, Any


def flatten_list(a: List[Any]) -> List[Any]: # type: ignore
    """
    Flatten a list of lists
    # input: [1,2,[1,4],2]
    # output: [1,2,1,4,2]
    """
    ret = []
    for item in a:
        if isinstance(item, list):
            ret.extend(flatten_list(item))
        else:
            ret.extend(item.split())
    return ret


def run_command(command: List[str]) -> str:
    """Run a shell command and return the output."""
    command = flatten_list(command)
    result = subprocess.run(command, capture_output=True, text=True, input="\n")
    if result.returncode != 0:
        print(f"Error running command: {' '.join(command)}", file=sys.stderr)
        # print(result.stderr, file=sys.stderr)
        # sys.exit(1)
    # print(f"Return code: {result.returncode}")
    # print(f"stdout: {result.stdout}")  # Debug print
    # print(f"stderr: {result.stderr}")   # Debug print
    ret = {
        "stdout": result.stdout,
        "stderr": result.stderr,
        "returncode": result.returncode
    }
    return ret 

def clean_text(input_text: str) -> str:
    """
    Cleans the input text by removing ANSI escape sequences and formatting codes.

    Args:
        input_text (str): Text containing ANSI escape sequences.

    Returns:
        str: Cleaned text without escape sequences.
    """
    # Regex pattern to match ANSI escape sequences
    ansi_escape_pattern = re.compile(r'\x1b\[[0-9;]*m')
    cleaned_text = ansi_escape_pattern.sub('', input_text)
    return cleaned_text


def parse_help_texts_block(help_text: str, block_name: str, 
                          cmd_indent: int = 5, desc_indent: int = 8,
                          verbose: bool = False) -> dict:
    """
    Extracts a specific block of text from the help text based on the block name.

    Args:
        help_text (str): The entire help text from the gcloud command.
        block_name (str): The name of the block to extract.

    Returns:
        dict: {arg_name: arg_description}
    """
    args_desc = {}

    in_block = False
    for line in clean_text(help_text).split("\n"):
        # print(line)

        # if the line starts with the block name
        if line.startswith(block_name): 
            in_block = True
        elif in_block and line.isupper(): 
            # check stop condition, when the line starts with all capital letters
            in_block = False
            break
        
        # print if in block and not new line
        if in_block and line != "": 
            if verbose: print(line)
            if line.startswith(" "*cmd_indent) and line[cmd_indent] != " ":
                tmp_arg = line.strip()
                # print(tmp_arg)
                args_desc[tmp_arg] = None
            elif line.startswith(" "*desc_indent) and tmp_arg != None:
                # remove front and back spaces
                args_desc[tmp_arg] = line.strip()
                tmp_arg = None
    return args_desc


def get_sub_resources(gcloud_cmds: List[str], included_cmds: List[str]=["create", "delete", "list"],
                      uri_supported: bool=True, verbose: bool=False) -> list:
    """
    Get sub-resources for a given GCP resource type.

    Args:
        gcloud_component (str): The GCP component (e.g., "compute", "sql", "pubsub")
        resource_type (str): The specific resource type (e.g., "networks", "instances")

    Returns:
        dict: {sub_resource1: {}, sub_resource2: {}}
    """
    ret_list = []
    
    # use help to get the sub-resources from "GROUP"
    out_dict = run_command(gcloud_cmds + ["--help"])
    # print(out_dict["stdout"])
    help_text = out_dict["stdout"]
    group_dict = parse_help_texts_block(help_text, "GROUPS")
    # print(group_dict)
    
    for k, v in group_dict.items():
        group_help_text = run_command(gcloud_cmds + [k, "--help"])["stdout"]
        group_cmd = parse_help_texts_block(group_help_text, "COMMANDS").keys()
        # print(group_cmd)
        if all(cmd in group_cmd for cmd in included_cmds):
            if uri_supported:
                # check cmd + "list --help" 
                list_help_text = run_command(gcloud_cmds + [k, "list", "--help"])["stdout"]
                list_flags = parse_help_texts_block(list_help_text, "LIST COMMAND FLAGS").keys()
                if "--uri" in list_flags:
                    ret_list.append(f"{gcloud_cmds[-1]} {k}")
            else:
                ret_list.append(f"{gcloud_cmds[-1]} {k}")
    return ret_list


def filter_resources_by_other_delete_args(cmd_path: List[str]) -> bool:
    cmd_path.append("delete")
    cmd_path.append("--help")
    out_dict = run_command(cmd_path)
    help_text = out_dict["stdout"]
    return parse_help_texts_block(help_text, "REQUIRED")


def login(key_file: str, project_id: str):
    run_command(["gcloud", "-q", "auth", "activate-service-account", "--key-file", key_file])
    run_command(["gcloud", "-q", "config", "set", "project", project_id])


def list_resources(gcloud_component: str, resource_type: str, use_uri: bool, filter_expression: str) -> List[str]:
    command = ["gcloud", gcloud_component]
    if resource_type:
        resource_type = resource_type.split()
        command.extend(resource_type)
    command.append("list")
    if filter_expression:
        command += ["--filter", filter_expression]
    command.append("--uri" if use_uri else "--format=table[no-heading](name)")
    output_dict = run_command(command)
    
    # check stdout and stderr
    output = output_dict["stdout"]
    print(output_dict["stdout"]+output_dict["stderr"], file=sys.stderr)
    return output.splitlines() if output else []


# def create_deletion_code(gcloud_component: str, resource_types: List[str], use_uri: bool, project_id: str, filter_expression: str, async_mode: bool):
#     for resource_type in resource_types:
#         print(f"Listing {gcloud_component} {resource_type}", file=sys.stderr)
#         resources = list_resources(gcloud_component, resource_type, use_uri, filter_expression)

#         if resources:
#             print(f"Listed {len(resources)} {gcloud_component} {resource_type}", file=sys.stderr)

#         for resource in resources:
#             delete_command = ["gcloud", gcloud_component, resource_type, "delete", "--project", project_id, "-q", resource]
#             if async_mode:
#                 delete_command.append("--async")
#             print(' '.join(delete_command))

def create_deletion_code(gcloud_component: str, resource_types: List[str], use_uri: bool, project_id: str, filter_expression: str, async_mode: bool):
    for resource_type in resource_types:
        
        # Recursively delete sub-resources first
        sub_resources = get_sub_resources(["gcloud", gcloud_component, resource_type])
        print(f"<{gcloud_component} {resource_type}> sub-resources: {sub_resources}", file=sys.stderr)
        if sub_resources:
            create_deletion_code(gcloud_component, sub_resources, use_uri, project_id, filter_expression, async_mode)

        print(f"Listing {gcloud_component} {resource_type}", file=sys.stderr)
        resources = list_resources(gcloud_component, resource_type, use_uri, filter_expression)

        if resources:
            print(f"Listed {len(resources)} {gcloud_component} {resource_type}\n", file=sys.stderr)

        for resource in resources:
            delete_command = ["gcloud", gcloud_component, resource_type, "delete", "--project", project_id, "-q", resource]
            if async_mode:
                delete_command.append("--async")
            print(' '.join(delete_command))


def list_buckets(filter_expression: str) -> List[str]:
    output_dict = run_command(["gsutil", "ls"])
    output = output_dict["stdout"]
    buckets = output.splitlines()

    if filter_expression.startswith("labels."):
        key, val = filter_expression[7:].split("=", 1)
        filtered_buckets = [bucket for bucket in buckets if val in run_command(["gsutil", "label", "get", bucket])["stdout"]]
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
    # parser.add_argument("-p", "--project", required=True, help="GCP project ID")
    parser.add_argument("-k", "--key-file", default="keys/gcp-keys.json", help="Service account key file")
    parser.add_argument("-f", "--filter", default="", help="Filter expression")
    parser.add_argument("-b", "--background", action="store_true", help="Run deletion commands asynchronously")

    args = parser.parse_args()

    with open(args.key_file, "r") as f:
        key_data = json.load(f)
        
    project_id = key_data["project_id"]
    login(args.key_file, project_id)

    compute_resource_types = [
        "instances", "addresses", "target-http-proxies", "target-https-proxies", "target-grpc-proxies",
        "url-maps", "backend-services", "firewall-rules", "forwarding-rules", "health-checks",
        "http-health-checks", "https-health-checks", "instance-templates", "routes",
        "routers", "target-pools", "target-tcp-proxies", "networks"
    ]

    print("set -x")  # Easier tracking when running the script
    create_deletion_code("container", ["clusters"], True, project_id, args.filter, args.background)
    create_deletion_code("compute", compute_resource_types, True, project_id, args.filter, args.background)
    create_deletion_code("sql", ["instances"], False, project_id, args.filter, args.background)
    create_deletion_code("app", ["services", "firewall-rules"], True, project_id, args.filter, args.background)
    create_deletion_code("pubsub", ["subscriptions", "topics", "snapshots"], True, project_id, args.filter, args.background)
    create_deletion_code("functions", [""], False, project_id, args.filter, args.background)

    create_bucket_deletion_code(args.filter, args.background)


if __name__ == "__main__":
    main()
