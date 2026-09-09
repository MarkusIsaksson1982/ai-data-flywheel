"""Resume-capable model download (run detached; poll the log)."""
from huggingface_hub import snapshot_download

p = snapshot_download("Qwen/Qwen2.5-1.5B-Instruct",
                      allow_patterns=["*.json", "*.safetensors", "*.txt", "*.model"])
print("DOWNLOAD COMPLETE:", p, flush=True)
