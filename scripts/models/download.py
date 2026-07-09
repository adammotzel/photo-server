"""Download efficientnet-b0."""

from huggingface_hub import snapshot_download

snapshot_download(
    repo_id="google/efficientnet-b0",
    local_dir="models/efficientnet-b0",
    local_dir_use_symlinks=False,
)
