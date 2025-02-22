# gcp-resource-cleanup

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