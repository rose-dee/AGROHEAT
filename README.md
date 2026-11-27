# AGROHEAT — Smart Food Heating Monitoring System

Dashboard monitoring pemanasan bahan pangan cair (air, sari buah) berbasis **ESP32 + DS18B20**, dengan
prediksi **sisa waktu menuju suhu target** memakai Machine Learning yang berjalan **lokal di laptop**
(Streamlit · SQLite · scikit-learn · Plotly). Tanpa cloud.

> Sistem ini memantau suhu dan waktu pemanasan. Ia **tidak** menilai keamanan pangan atau keberhasilan pasteurisasi.

## 1. Instalasi (Windows)

Butuh Python 3.10+ (centang *Add Python to PATH* saat instalasi). Di folder `AgroHeat`, buka PowerShell/CMD:

```
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Dashboard terbuka di http://localhost:8501. Database `data/agroheat.db` dibuat otomatis.
(Jika PowerShell menolak `activate`: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, atau pakai CMD.)

## 2. Coba dulu tanpa perangkat (Mode Demo)

1. Sidebar → **Mode data: Demo / Simulation**.
2. **Dataset Management → Buat dataset demo** (8 batch berlabel *Simulated Data*).
3. **Machine Learning** → pilih sumber `Simulated Data` → **Latih & evaluasi**. Halaman akan menandai bahwa metrik berasal dari data simulasi.
4. **Batch Management** → buat batch → **Live Monitoring** → *Mulai sesi*. Grafik bergerak otomatis (data simulasi, berlabel).

Mode **Real Sensor** dan **Manual Input** memakai batch dengan sumber masing-masing; data ketiga mode tidak pernah tercampur.

## 3. Menghubungkan ESP32

Dua proses berjalan bersamaan (dua terminal, keduanya dengan `.venv` aktif):

```
python -m streamlit run app.py     # terminal 1: dashboard
python run_api.py                  # terminal 2: penerima data ESP32 (port 8000)
```

1. Laptop dan ESP32 di **Wi-Fi yang sama**. Cari IP laptop di *System Settings* (atau `ipconfig` → IPv4 Address).
2. Windows Firewall: izinkan Python pada jaringan **Private** (atau buka port 8000 inbound).
3. Buka `esp32/agroheat_esp32.ino` di Arduino IDE, isi `WIFI_SSID`, `WIFI_PASS`, dan `SERVER` (`http://IP_LAPTOP:8000`), lalu upload.
4. Di dashboard: mode **Real Sensor** → buat batch → **Mulai sesi**. ESP32 bertanya `GET /api/batches/active`, lalu mengirim
   `POST /api/readings` tiap interval.

Contoh payload (`elapsed_seconds` dan `timestamp` opsional; jika kosong dihitung dari waktu mulai batch / jam laptop):

```json
{"batch_id": "SOY-001", "timestamp": "2026-11-18T10:00:00+07:00",
 "temperature_c": 32.5, "elapsed_seconds": 60, "sensor_status": "connected"}
```

Tes tanpa ESP32 (PowerShell, setelah batch Real Sensor berstatus Heating):
`Invoke-RestMethod -Method Post -Uri http://localhost:8000/api/readings -ContentType "application/json" -Body '{"batch_id":"SOY-001","temperature_c":32.5}'`

Status **ESP32 Online** hanya muncul bila ada data `real_sensor` yang benar-benar masuk dalam batas waktu; selain itu tampil Offline / Belum pernah terhubung.

## 4. Machine Learning

- Target: `remaining_seconds` = waktu aktual suhu pertama kali ≥ target − elapsed. Label hanya dari pengukuran, bukan prediksi model.
- Fitur: suhu saat ini, suhu awal, suhu target, elapsed, laju kenaikan suhu (60 dtk ke belakang), volume, jenis bahan, kondisi pemanasan.
- Model: Linear Regression (baseline) vs Random Forest. Split train/test **per batch**; metrik MAE & RMSE dihitung dari batch uji.
- Syarat minimal: 4 batch berlabel (≥3 latih + 1 uji) dan 40 baris. Di bawah itu model dinyatakan belum siap dan tidak ada metrik/prediksi ML yang ditampilkan.
- Estimasi **heuristik** (selisih suhu ÷ laju) selalu diberi label terpisah dari prediksi ML.

## 5. Struktur proyek

```
app.py  config.py  ui.py  run_api.py  requirements.txt
database/  schema.sql, db_manager.py
views/     overview, live_monitoring, batch_management, data_history, machine_learning,
           analytics, alerts, dataset_management, system_settings
ml/        preprocessing, train_model, predict, evaluation
services/  sensor_service, api_service, alert_service, simulation, dataset_service
esp32/     agroheat_esp32.ino
tests/     test_backend.py, smoke_views.py
data/  models/  assets/
```

Catatan: folder halaman bernama `views/` (bukan `pages/`) karena Streamlit otomatis membuat menu sendiri dari folder `pages/` dan akan bentrok dengan sidebar kustom.
Backend ESP32 memakai pustaka standar Python (tanpa FastAPI/Flask) agar instalasi ringan.

## 6. Pengujian & keterbatasan 

Sudah diuji otomatis (`python tests/test_backend.py`): database & relasi, validasi payload, endpoint HTTP (lewat server sungguhan),
alarm, pemisahan sumber data, split per batch, dan perilaku "model belum siap". `python tests/smoke_views.py` menjalankan semua halaman
dengan Streamlit palsu untuk mendeteksi error Python.

**Belum diuji:** tampilan visual di browser (Streamlit/Plotly tidak terpasang di lingkungan pengembangan), integrasi dengan ESP32 dan
DS18B20 sungguhan, kompilasi firmware di Arduino IDE, serta akurasi model pada data sensor nyata. Metrik pada data demo berasal dari
data simulasi dan tidak mencerminkan performa nyata. Satu sesi aktif pada satu waktu. Uji tampilan pertama kali di laptop Anda.
