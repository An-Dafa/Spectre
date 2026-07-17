import os
import random
import shutil

def smart_split(source_img_dir, source_lab_dir, dest_root):
    # 1. Identifikasi semua file gambar (support jpg, jpeg, png)
    valid_extensions = ('.jpg', '.jpeg', '.png')
    all_image_files = [f for f in os.listdir(source_img_dir) if f.lower().endswith(valid_extensions)]
    
    # Ambil base name (nama tanpa ekstensi) dan simpan ekstensinya
    # Contoh: {'ktp_asli_1': '.jpg', 'paspor_synth_0': '.png'}
    file_map = {f.rsplit('.', 1)[0]: f.rsplit('.', 1)[1] for f in all_image_files}
    all_base_names = list(file_map.keys())
    
    asli_files = [f for f in all_base_names if "_asli_" in f]
    synth_files = [f for f in all_base_names if "_synth_" in f]

    print(f"--- Dataset Discovery ---")
    print(f"Data Asli    : {len(asli_files)}")
    print(f"Data Sintetis: {len(synth_files)}")
    print(f"Total        : {len(all_base_names)}")
    print("-" * 25)

    random.shuffle(asli_files)
    random.shuffle(synth_files)

    # 2. Distribusi Strategis untuk Track A
    # Kita prioritaskan data asli di Test Set untuk pembuktian Robustness
    asli_total = len(asli_files)
    asli_test = asli_files[:int(asli_total * 0.7)]
    asli_val = asli_files[int(asli_total * 0.7):int(asli_total * 0.85)]
    asli_train = asli_files[int(asli_total * 0.85):]

    synth_total = len(synth_files)
    synth_train = synth_files[:int(synth_total * 0.8)]
    synth_val = synth_files[int(synth_total * 0.8):int(synth_total * 0.95)]
    synth_test = synth_files[int(synth_total * 0.95):]

    final_splits = {
        "train_data": asli_train + synth_train,
        "val_data": asli_val + synth_val,
        "test_data": asli_test + synth_test
    }

    def move_pairs(file_list, split_name):
        img_dest = os.path.join(dest_root, split_name, "images")
        lab_dest = os.path.join(dest_root, split_name, "labels")
        os.makedirs(img_dest, exist_ok=True)
        os.makedirs(lab_dest, exist_ok=True)

        count = 0
        for base_name in file_list:
            ext = file_map[base_name] # Ambil ekstensi asli (jpg/png)
            img_src = os.path.join(source_img_dir, f"{base_name}.{ext}")
            lab_src = os.path.join(source_lab_dir, f"{base_name}.txt")
            
            if os.path.exists(img_src) and os.path.exists(lab_src):
                shutil.move(img_src, os.path.join(img_dest, f"{base_name}.{ext}"))
                shutil.move(lab_src, os.path.join(lab_dest, f"{base_name}.txt"))
                count += 1
        return count

    # 3. Eksekusi Perulangan (Looping)
    for split, files in final_splits.items():
        c = move_pairs(files, split)
        print(f"Susun {split.ljust(10)}: {str(c).rjust(4)} pasang")

if __name__ == "__main__":
    source_images = "datasets/gen_code/temp/images"
    source_labels = "datasets/gen_code/temp/labels"
    target_destination = "datasets"

    smart_split(source_images, source_labels, target_destination)