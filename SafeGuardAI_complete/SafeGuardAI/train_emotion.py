# ============================================================
# SafeGuard AI — Emotion CNN Training Script
# Dataset : RAVDESS (Audio_Speech_Actors_01-24)
# Input   : Mel spectrograms (1 × 64 × 128)
# Output  : 6-class emotion classifier
#           anger / fear / happiness / excitement / sadness / neutral
# Target  : ~75-80% test accuracy
# Usage   : python train_emotion.py
# ============================================================

import os, sys, time, random, glob
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ── Config ────────────────────────────────────────────────
DATASET_DIR  = os.path.join("datasets", "emotion")
WEIGHTS_OUT  = "emotion_cnn.pth"
BATCH_SIZE   = 32
EPOCHS       = 40
LR           = 1e-3
VAL_SPLIT    = 0.15
TEST_SPLIT   = 0.15
N_MELS       = 64
HOP_LENGTH   = 512
N_FFT        = 1024
MAX_FRAMES   = 128       # fixed width of mel spectrogram
SR           = 22050
SEED         = 42

EMOTION_LABELS = ["anger", "fear", "happiness", "excitement", "sadness", "neutral"]

# RAVDESS emotion code → our label
RAVDESS_MAP = {
    "01": "neutral",     # neutral
    "02": "neutral",     # calm
    "03": "happiness",   # happy
    "04": "sadness",     # sad
    "05": "anger",       # angry
    "06": "fear",        # fearful
    "07": "anger",       # disgust → anger
    "08": "excitement",  # surprised → excitement
}

# ── Imports ───────────────────────────────────────────────
try:
    import torch
    import torch.nn as nn
    import torch.optim as optim
    from torch.utils.data import Dataset, DataLoader
    print(f"PyTorch {torch.__version__}  |  CUDA: {torch.cuda.is_available()}")
except ImportError:
    print("ERROR: PyTorch not installed. Run: pip install torch")
    sys.exit(1)

try:
    import librosa
    print(f"librosa {librosa.__version__}")
except ImportError:
    print("ERROR: librosa not installed. Run: pip install librosa")
    sys.exit(1)

random.seed(SEED); np.random.seed(SEED); torch.manual_seed(SEED)
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"Device: {device}\n")


# ════════════════════════════════════════════════════════════
# 1. PARSE DATASET
# ════════════════════════════════════════════════════════════
def parse_ravdess(dataset_dir: str):
    """Return list of (wav_path, label_idx) from RAVDESS folder structure."""
    samples = []
    wav_files = glob.glob(os.path.join(dataset_dir, "**", "*.wav"), recursive=True)

    if not wav_files:
        print(f"ERROR: No .wav files found in {dataset_dir}")
        sys.exit(1)

    skipped = 0
    for path in wav_files:
        fname  = os.path.basename(path)
        parts  = fname.replace(".wav", "").split("-")
        if len(parts) < 3:
            skipped += 1
            continue
        code = parts[2]  # 3rd segment = emotion code
        if code not in RAVDESS_MAP:
            skipped += 1
            continue
        label     = RAVDESS_MAP[code]
        label_idx = EMOTION_LABELS.index(label)
        samples.append((path, label_idx))

    print(f"Found {len(samples)} samples  ({skipped} skipped)")

    # Class distribution
    from collections import Counter
    dist = Counter(EMOTION_LABELS[i] for _, i in samples)
    for label, count in sorted(dist.items()):
        print(f"  {label:<12} {count}")
    print()
    return samples


# ════════════════════════════════════════════════════════════
# 2. MEL SPECTROGRAM EXTRACTION
# ════════════════════════════════════════════════════════════
def wav_to_mel(wav_path: str) -> np.ndarray:
    """Load wav → mel spectrogram (n_mels × max_frames), normalized."""
    y, sr = librosa.load(wav_path, sr=SR, mono=True)

    mel = librosa.feature.melspectrogram(
        y=y, sr=sr, n_fft=N_FFT, hop_length=HOP_LENGTH,
        n_mels=N_MELS, fmax=8000,
    )
    mel_db = librosa.power_to_db(mel, ref=np.max)

    # Pad or truncate to fixed width
    if mel_db.shape[1] < MAX_FRAMES:
        mel_db = np.pad(mel_db, ((0, 0), (0, MAX_FRAMES - mel_db.shape[1])),
                        mode="constant", constant_values=-80)
    else:
        mel_db = mel_db[:, :MAX_FRAMES]

    # Normalize to [0, 1]
    mel_db = (mel_db - mel_db.min()) / (mel_db.max() - mel_db.min() + 1e-8)
    return mel_db.astype(np.float32)


# ════════════════════════════════════════════════════════════
# 3. DATASET CLASS
# ════════════════════════════════════════════════════════════
class EmotionDataset(Dataset):
    def __init__(self, samples, augment=False):
        self.samples = samples
        self.augment = augment

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        path, label = self.samples[idx]
        mel = wav_to_mel(path)

        if self.augment:
            # Time shift ±10%
            shift = int(mel.shape[1] * random.uniform(-0.1, 0.1))
            mel = np.roll(mel, shift, axis=1)
            # Frequency mask (SpecAugment-lite)
            f_start = random.randint(0, N_MELS - 8)
            mel[f_start:f_start + random.randint(2, 8), :] = 0
            # Time mask
            t_start = random.randint(0, MAX_FRAMES - 16)
            mel[:, t_start:t_start + random.randint(4, 16)] = 0
            # Gaussian noise
            mel += np.random.normal(0, 0.005, mel.shape).astype(np.float32)
            mel = np.clip(mel, 0, 1)

        # Shape: (1, n_mels, max_frames)
        tensor = torch.FloatTensor(mel).unsqueeze(0)
        return tensor, label


# ════════════════════════════════════════════════════════════
# 4. MODEL  (matches EmotionCNN in emotion_model.py)
# ════════════════════════════════════════════════════════════
class EmotionCNN(nn.Module):
    def __init__(self, num_classes=6):
        super().__init__()
        self.features = nn.Sequential(
            nn.Conv2d(1, 32, kernel_size=3, padding=1), nn.ReLU(), nn.BatchNorm2d(32),
            nn.Conv2d(32, 32, kernel_size=3, padding=1), nn.ReLU(),
            nn.MaxPool2d(2, 2), nn.Dropout2d(0.25),

            nn.Conv2d(32, 64, kernel_size=3, padding=1), nn.ReLU(), nn.BatchNorm2d(64),
            nn.Conv2d(64, 64, kernel_size=3, padding=1), nn.ReLU(),
            nn.MaxPool2d(2, 2), nn.Dropout2d(0.25),

            nn.Conv2d(64, 128, kernel_size=3, padding=1), nn.ReLU(),
            nn.AdaptiveAvgPool2d((4, 4)),
        )
        self.classifier = nn.Sequential(
            nn.Flatten(),
            nn.Linear(128 * 4 * 4, 256), nn.ReLU(), nn.Dropout(0.5),
            nn.Linear(256, num_classes),
        )

    def forward(self, x):
        return self.classifier(self.features(x))


# ════════════════════════════════════════════════════════════
# 5. TRAIN / EVAL HELPERS
# ════════════════════════════════════════════════════════════
def train_epoch(model, loader, criterion, optimizer):
    model.train()
    total_loss, correct, total = 0.0, 0, 0
    for x, y in loader:
        x, y = x.to(device), y.to(device)
        optimizer.zero_grad()
        out  = model(x)
        loss = criterion(out, y)
        loss.backward()
        optimizer.step()
        total_loss += loss.item() * x.size(0)
        correct    += (out.argmax(1) == y).sum().item()
        total      += x.size(0)
    return total_loss / total, correct / total


def eval_epoch(model, loader, criterion):
    model.eval()
    total_loss, correct, total = 0.0, 0, 0
    with torch.no_grad():
        for x, y in loader:
            x, y = x.to(device), y.to(device)
            out  = model(x)
            loss = criterion(out, y)
            total_loss += loss.item() * x.size(0)
            correct    += (out.argmax(1) == y).sum().item()
            total      += x.size(0)
    return total_loss / total, correct / total


def evaluate_full(model, loader):
    """Per-class accuracy on test set."""
    model.eval()
    all_preds, all_labels = [], []
    with torch.no_grad():
        for x, y in loader:
            x = x.to(device)
            preds = model(x).argmax(1).cpu().numpy()
            all_preds.extend(preds)
            all_labels.extend(y.numpy())

    all_preds  = np.array(all_preds)
    all_labels = np.array(all_labels)
    overall    = (all_preds == all_labels).mean()

    print(f"\n{'─'*40}")
    print(f"  Overall test accuracy: {overall*100:.2f}%")
    print(f"{'─'*40}")
    for i, label in enumerate(EMOTION_LABELS):
        mask = all_labels == i
        if mask.sum() == 0:
            print(f"  {label:<12}  no samples")
            continue
        acc = (all_preds[mask] == all_labels[mask]).mean()
        bar = "█" * int(acc * 20)
        print(f"  {label:<12}  {acc*100:5.1f}%  {bar}")
    print(f"{'─'*40}\n")
    return overall


# ════════════════════════════════════════════════════════════
# 6. MAIN
# ════════════════════════════════════════════════════════════
def main():
    print("=" * 50)
    print("  SafeGuard AI — Emotion CNN Training")
    print("=" * 50)

    # Parse dataset
    samples = parse_ravdess(DATASET_DIR)

    # Shuffle + split
    random.shuffle(samples)
    n       = len(samples)
    n_test  = int(n * TEST_SPLIT)
    n_val   = int(n * VAL_SPLIT)
    n_train = n - n_test - n_val

    train_s = samples[:n_train]
    val_s   = samples[n_train:n_train + n_val]
    test_s  = samples[n_train + n_val:]

    print(f"Split  →  train: {len(train_s)}  val: {len(val_s)}  test: {len(test_s)}\n")

    # Datasets + loaders
    train_ds = EmotionDataset(train_s, augment=True)
    val_ds   = EmotionDataset(val_s,   augment=False)
    test_ds  = EmotionDataset(test_s,  augment=False)

    train_loader = DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True,  num_workers=0)
    val_loader   = DataLoader(val_ds,   batch_size=BATCH_SIZE, shuffle=False, num_workers=0)
    test_loader  = DataLoader(test_ds,  batch_size=BATCH_SIZE, shuffle=False, num_workers=0)

    # Model
    model     = EmotionCNN(num_classes=len(EMOTION_LABELS)).to(device)
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=LR, weight_decay=1e-4)
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(
        optimizer, mode="max", factor=0.5, patience=5
    )

    total_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(f"Model parameters: {total_params:,}\n")

    # Training loop
    best_val_acc  = 0.0
    best_epoch    = 0
    no_improve    = 0

    print(f"{'Epoch':>6}  {'Train Loss':>10}  {'Train Acc':>9}  {'Val Loss':>8}  {'Val Acc':>8}  {'LR':>8}")
    print("─" * 62)

    for epoch in range(1, EPOCHS + 1):
        t0 = time.time()

        train_loss, train_acc = train_epoch(model, train_loader, criterion, optimizer)
        val_loss,   val_acc   = eval_epoch(model,  val_loader,   criterion)

        scheduler.step(val_acc)
        lr = optimizer.param_groups[0]["lr"]
        elapsed = time.time() - t0

        marker = "  ← best" if val_acc > best_val_acc else ""
        print(f"{epoch:>6}  {train_loss:>10.4f}  {train_acc*100:>8.2f}%  "
              f"{val_loss:>8.4f}  {val_acc*100:>7.2f}%  {lr:>8.6f}{marker}")

        if val_acc > best_val_acc:
            best_val_acc = val_acc
            best_epoch   = epoch
            no_improve   = 0
            torch.save(model.state_dict(), WEIGHTS_OUT)
        else:
            no_improve += 1
            if no_improve >= 10:
                print(f"\nEarly stopping at epoch {epoch} (no improvement for 10 epochs)")
                break

    print(f"\nBest val accuracy: {best_val_acc*100:.2f}% at epoch {best_epoch}")
    print(f"Weights saved → {WEIGHTS_OUT}\n")

    # Load best weights and evaluate on test set
    model.load_state_dict(torch.load(WEIGHTS_OUT, map_location=device))
    test_acc = evaluate_full(model, test_loader)

    print(f"Training complete.")
    print(f"Copy {WEIGHTS_OUT} to your SafeGuardAI project root.")
    print(f"The emotion model will auto-load it on next startup.\n")


if __name__ == "__main__":
    main()
