# Catatan Implementasi Machine Learning AGROHEAT

## Perubahan pada versi ini

1. `services/simulation.py`
   - Dataset demo difokuskan pada sari kedelai dengan target 80°C.
   - Volume batch divariasikan (250–750 mL), suhu awal divariasikan, serta kondisi pengadukan dibuat bergantian.
   - Gangguan acak dan kuantisasi 0,0625°C ditambahkan sebagai pendekatan sederhana resolusi DS18B20.
   - Seluruh data tetap diberi label `data_source='simulation'`.
   - Kurva pemanasan masih berupa model eksponensial sederhana. Parameter bukan hasil identifikasi eksperimen sari kedelai.

2. `ml/train_model.py`
   - Pemisahan train/test tetap dilakukan berdasarkan `batch_id`.
   - Pemilihan antara Linear Regression dan Random Forest dilakukan menggunakan `GroupKFold` hanya pada batch train.
   - Batch test holdout tidak dipakai untuk memilih model; batch tersebut dipakai untuk evaluasi akhir.
   - Metadata menyimpan CV RMSE, test MAE/RMSE, batch train/test, dan MAE per batch.

3. `views/machine_learning.py`
   - Dashboard menampilkan CV RMSE, test MAE, test RMSE, dan MAE per batch untuk model terpilih.
   - Keterangan keterbatasan diperbarui.

4. `config.py`
   - Suhu target default diubah menjadi 80°C sesuai skenario prototipe sari kedelai AGROHEAT.

5. `tests/test_ml_synthetic.py`
   - Uji integrasi untuk membuat 8 batch sintetis, membangun label, melatih model, dan memeriksa artefak hasil.

## Hasil uji yang dijalankan

Lingkungan uji lokal menggunakan 8 batch sintetis, 663 baris berlabel, dan pemisahan 6 batch train / 2 batch test.

| Model | CV RMSE train (detik) | Test MAE (detik) | Test RMSE (detik) |
|---|---:|---:|---:|
| Linear Regression | 128,3 | 45,9 | 48,5 |
| Random Forest | 59,4 | 25,1 | 35,1 |

Pada satu seed simulasi ini, Random Forest terpilih. Angka tersebut hanya membuktikan pipeline dapat dilatih dan dievaluasi pada data sintetis. Angka tersebut **bukan** estimasi akurasi pada proses pemanasan sari kedelai aktual.

## Menjalankan

```bash
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Buka halaman Dataset Management dan buat dataset demo, kemudian buka Machine Learning, pilih `Simulated Data`, lalu jalankan pelatihan.

Untuk pengujian:

```bash
python tests/test_ml_synthetic.py
python tests/test_backend.py
python tests/smoke_views.py
```

Tidak ada dependensi ML baru. API ESP32, skema database, dan jalur prediksi pada Live Monitoring dipertahankan.
