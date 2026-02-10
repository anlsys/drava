from huggingface_hub import hf_hub_download

# Local output directory
local_dir = "./PtychoNN_data_partial"

# Download X_test.npy
x_test_path = hf_hub_download(
    repo_id="mcherukara/PtychoNN_data",
    repo_type="dataset",
    filename="X_test.npy",
    local_dir=local_dir,
    local_dir_use_symlinks=False,
)

# Download min_epoch.npy
min_epoch_path = hf_hub_download(
    repo_id="mcherukara/PtychoNN_data",
    repo_type="dataset",
    filename="wts4/min_epoch.npy",
    local_dir=local_dir,
    local_dir_use_symlinks=False,
)

# Download a specific weight file
weights_path = hf_hub_download(
    repo_id="mcherukara/PtychoNN_data",
    repo_type="dataset",
    filename="wts4/weights.66.hdf5",
    local_dir=local_dir,
    local_dir_use_symlinks=False,
)

print("Downloaded:")
print(" -", x_test_path)
print(" -", min_epoch_path)
print(" -", weights_path)
