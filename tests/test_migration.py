import os
import tempfile

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect


def test_alembic_migration_upgrade_and_downgrade():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test_migration.db")
        db_url = f"sqlite:///{db_path}"

        alembic_cfg = Config("alembic.ini")
        alembic_cfg.set_main_option("sqlalchemy.url", db_url)

        # 1. Upgrade to head
        command.upgrade(alembic_cfg, "head")

        engine = create_engine(db_url)
        inspector = inspect(engine)

        tables = inspector.get_table_names()
        assert "jobs" in tables
        assert "certificates" in tables

        # Verify jobs columns
        job_columns = {col["name"]: col for col in inspector.get_columns("jobs")}
        expected_job_cols = {
            "id",
            "event_name",
            "issue_date",
            "status",
            "total_count",
            "success_count",
            "failure_count",
            "created_at",
            "updated_at",
            "completed_at",
        }
        assert expected_job_cols.issubset(job_columns.keys())

        # Verify certificates columns
        cert_columns = {col["name"]: col for col in inspector.get_columns("certificates")}
        expected_cert_cols = {
            "id",
            "job_id",
            "recipient_name",
            "recipient_email",
            "status",
            "file_path",
            "error_message",
            "created_at",
            "updated_at",
            "generated_at",
        }
        assert expected_cert_cols.issubset(cert_columns.keys())
        assert cert_columns["recipient_email"]["nullable"] is True

        # Verify indexes
        job_indexes = {idx["name"] for idx in inspector.get_indexes("jobs")}
        assert "ix_jobs_status" in job_indexes
        assert "ix_jobs_created_at" in job_indexes

        cert_indexes = {idx["name"] for idx in inspector.get_indexes("certificates")}
        assert "ix_certificates_job_id" in cert_indexes
        assert "ix_certificates_job_status" in cert_indexes

        # Verify foreign keys
        fks = inspector.get_foreign_keys("certificates")
        assert len(fks) >= 1
        fk = fks[0]
        assert fk["referred_table"] == "jobs"
        assert fk["referred_columns"] == ["id"]

        engine.dispose()

        # 2. Downgrade to base
        command.downgrade(alembic_cfg, "base")

        engine_downgraded = create_engine(db_url)
        inspector_downgraded = inspect(engine_downgraded)
        remaining_tables = inspector_downgraded.get_table_names()
        assert "jobs" not in remaining_tables
        assert "certificates" not in remaining_tables
        engine_downgraded.dispose()

        # 3. Upgrade back to head to verify idempotency
        command.upgrade(alembic_cfg, "head")
        engine_reupgraded = create_engine(db_url)
        reupgraded_tables = inspect(engine_reupgraded).get_table_names()
        assert "jobs" in reupgraded_tables
        assert "certificates" in reupgraded_tables
        engine_reupgraded.dispose()
