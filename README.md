# gcp-resource-cleanup

This tool generates a bash script to wipe all GCP resources under a gcloud project. Adding new resources is as simple as adding the resource type to the list of resources in the script. 

## Usage

1. Generate a GCP credentials json file Ex: gcp-keys.json

```bash
# this will give you the iam-account name which is the email 

gcloud iam service-accounts list
```

```bash
gcloud iam service-accounts keys create gcp-keys.json --iam-account=<iam-account-from-above>
```

2. Scan your resources and generate cleanup bash script

```bash
python base_gen_deletion_script.py -k gcp-keys.json > cleanup-script.sh

chmod a+x cleanup-script.sh
```

3. Double check the cleanup script

```bash
./cleanup-script.sh
```

## Background

Say you have a bunch of resources under a GCP project and you want to delete them.
In GCP, there is no easy way to do this. You have to manually find each resource and delete it. 

In Azure, one could delete the AZ resource group and all the resources under it would be deleted. 
However, GCP does "soft deletes" when deleting a gcp project. The project is marked for deletion and then deleted after 30 days which can be a pain.

This tool is a way to automate the process of finding and deleting all the resources under a project, inspired by [SafeScrub](https://github.com/doitintl/SafeScrub).
