# Training Deteksi Dokumen PrivAI

Folder ini berisi pipeline untuk membuat dataset sintetis, augmentasi data asli, training model YOLO, dan inference deteksi dokumen.

## Tujuan

Model dilatih untuk mendeteksi beberapa kelas dokumen dan informasi penting:

- `ktp`
- `sim`
- `paspor`
- `teks_sensitif`
- `wajah`
- `plat_nomor`
- `kk`
- `kartu_atm`
- `resi`

## Alur Dataset

Dataset berasal dari tiga sumber:

- Data asli dari folder `data_asli`.
- Data augmentasi dari folder `data_augmentasi`.
- Data sintetis dari generator `datagen_*.py`.

Notebook `training_deteksi.ipynb` akan menggabungkan dataset secara otomatis ke folder `datasets/privai_combined`, lalu membaginya menjadi:

- `train` untuk proses pembelajaran model.
- `val` untuk validasi selama training.
- `test` untuk evaluasi akhir.

Augmentasi horizontal flip dimatikan supaya teks, nomor kartu, nomor plat, dan nomor dokumen tidak menjadi terbalik.

## Model Training

Training menggunakan YOLO26n karena ringan, cepat, dan cocok untuk inference portable. Konfigurasi utama:

- Ukuran gambar: `640`.
- Maksimal epoch: `200`.
- Early stopping: berhenti jika performa tidak membaik selama `25` epoch.
- Checkpoint disimpan setiap `5` epoch.
- `last.pt` selalu menyimpan weight terbaru.
- `best.pt` menyimpan weight dengan performa validasi terbaik.

Hasil training tersimpan di:

- `runs/detect/privai_yolo26n/weights/best.pt`
- `runs/detect/privai_yolo26n/weights/last.pt`
- `runs/detect/privai_yolo26n/results.csv`

## Inference

Inference dilakukan melalui `inference.ipynb`. Notebook ini memuat:

```text
runs/detect/privai_yolo26n/weights/best.pt
```

File tersebut adalah weight terbaik dari hasil training. Notebook dapat digunakan untuk:

- Prediksi satu gambar.
- Prediksi satu folder gambar.
- Prediksi video.
- Prediksi webcam.
- Menampilkan bounding box dan blur pada area sensitif.

Contoh gambar uji default menggunakan:

```text
image.png
```

## Catatan Penggunaan

Jalankan notebook dari folder proyek ini:

```powershell
cd D:\Spectre\Training
jupyter lab training_deteksi.ipynb
```

Untuk inference:

```powershell
cd D:\Spectre\Training
jupyter lab inference.ipynb
```

Pastikan package `ultralytics`, `torch`, `opencv-python`, `pandas`, dan `jupyter` sudah terpasang di environment yang digunakan.
