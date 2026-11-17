import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models.visual_model import get_visual_model

vm = get_visual_model()
print("weights_loaded:", getattr(vm, "weights_loaded", False))
print("model_path:", getattr(vm, "model_path", "not set"))

# Also check if the weights file exists
candidates = [
    "violence_resnet18_rlvs.pth",
    "models/violence_resnet18_rlvs.pth",
    os.path.join(os.path.expanduser("~"), "Downloads", "violence_resnet18_rlvs.pth"),
]
print("\nSearching for weights file:")
for p in candidates:
    exists = os.path.exists(p)
    print(f"  {'FOUND' if exists else 'not found'} — {p}")

# Full search
print("\nSearching entire downloads folder:")
downloads = os.path.join(os.path.expanduser("~"), "Downloads")
for root, dirs, files in os.walk(downloads):
    for f in files:
        if f.endswith(".pth"):
            print(f"  FOUND: {os.path.join(root, f)}")
