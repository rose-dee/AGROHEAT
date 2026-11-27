"""Uji integrasi dataset sintetis sari kedelai dan pipeline pelatihan ML."""
import tempfile
from pathlib import Path

import config
from database import db_manager as db
from ml import preprocessing as pp, train_model
from services import simulation


def main():
    original_db, original_models = config.DB_PATH, config.MODEL_DIR
    with tempfile.TemporaryDirectory() as tmp:
        config.DB_PATH = Path(tmp) / "agroheat_test.db"
        config.MODEL_DIR = Path(tmp) / "models"
        db.init_db()

        created = simulation.seed_demo_dataset(n_batches=8, seed=42)
        table = pp.build_training_table(db.get_all_readings())

        assert created == 8, f"Seharusnya membuat 8 batch, aktual {created}"
        assert table["batch_id"].nunique() == 8
        assert set(table["material_type"]) == {"Sari Kedelai"}
        assert set(table["target_temperature"]) == {80.0}

        ready, message = train_model.check_readiness(table)
        assert ready, message
        meta = train_model.train_and_evaluate(table)

        assert meta["best_model"] in {"Linear Regression", "Random Forest"}
        assert meta["includes_simulation"] is True
        assert set(meta["cv_rmse"]) == {"Linear Regression", "Random Forest"}
        assert len(meta["per_batch_mae"]) >= 1
        assert (config.MODEL_DIR / train_model.META_FILE).exists()
        assert (config.MODEL_DIR / train_model.TEST_PRED_FILE).exists()

        print("OK  8 batch sintetis sari kedelai, target 80°C")
        print("OK  GroupKFold model selection dan holdout test per batch")
        print("OK  artefak model, metadata, dan prediksi tersimpan")
        print("Model terpilih:", meta["best_model"])
        print("Test metrics:", meta["results"])

    config.DB_PATH, config.MODEL_DIR = original_db, original_models


if __name__ == "__main__":
    main()
