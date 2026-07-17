import os
import matplotlib.pyplot as plt
import pandas as pd

# 1. Load data log YOLO Anda ke dalam DataFrame Pandas
# Membaca file results.csv yang berada di direktori yang sama dengan skrip ini
file_path = os.path.join(os.path.dirname(__file__), "results.csv")
df = pd.read_csv(file_path, sep=",")  # Ganti path jika file berada di lokasi lain

# 2. Mengatur tata letak jendela grafik (1 baris, 2 kolom)
fig, axes = plt.subplots(1, 2, figsize=(14, 5))

# --- GRAFIK 1: Perbandingan Train vs Val Loss ---
axes[0].plot(
    df["epoch"],
    df["train/box_loss"],
    label="Train Box Loss",
    marker="o",
    color="blue",
)
axes[0].plot(
    df["epoch"],
    df["val/box_loss"],
    label="Val Box Loss",
    marker="s",
    color="lightblue",
    linestyle="--",
)
axes[0].plot(
    df["epoch"],
    df["train/cls_loss"],
    label="Train Cls Loss",
    marker="o",
    color="orange",
)
axes[0].plot(
    df["epoch"],
    df["val/cls_loss"],
    label="Val Cls Loss",
    marker="s",
    color="moccasin",
    linestyle="--",
)

axes[0].set_title("Tren Loss (Semakin Rendah Semakin Baik)")
axes[0].set_xlabel("Epoch")
axes[0].set_ylabel("Nilai Loss")
axes[0].set_xticks(df["epoch"])
axes[0].grid(True, linestyle=":", alpha=0.6)
axes[0].legend()

# --- GRAFIK 2: Metrik Akurasi Validasi (mAP) ---
axes[1].plot(
    df["epoch"],
    df["metrics/mAP50(B)"],
    label="mAP@0.50",
    marker="^",
    color="green",
)
axes[1].plot(
    df["epoch"],
    df["metrics/mAP50-95(B)"],
    label="mAP@0.50:0.95",
    marker="v",
    color="red",
)
axes[1].plot(
    df["epoch"],
    df["metrics/precision(B)"],
    label="Precision",
    marker=".",
    color="purple",
    alpha=0.5,
)
axes[1].plot(
    df["epoch"],
    df["metrics/recall(B)"],
    label="Recall",
    marker=".",
    color="brown",
    alpha=0.5,
)

axes[1].set_title("Metrik Akurasi Model (Semakin Tinggi Semakin Baik)")
axes[1].set_xlabel("Epoch")
axes[1].set_ylabel("Skor (0 - 1)")
axes[1].set_xticks(df["epoch"])
axes[1].set_ylim(0.4, 1.0)  # Menyesuaikan skala visual akurasi data Anda
axes[1].grid(True, linestyle=":", alpha=0.6)
axes[1].legend()

# 3. Menampilkan grafik keseluruhan
plt.tight_layout()
plt.show()
