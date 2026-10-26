"""Day 22 tests — config must fail at the door, never at 2 AM.

No network, no wall-clock, no real environment mutation: every test
passes an explicit env mapping. stdlib only.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from problem_01_env_not_code import ConfigError, load_config
from problem_02_typed_settings import Settings
from problem_03_precedence import deep_merge, parse_yaml, resolve
from problem_04_secrets_never_logged import Secret, mask_config, parse_dotenv
from problem_05_config_pipeline import Pipeline, build_pipeline_config

FULL_ENV = {"DB_HOST": "db.prod.internal", "API_KEY": "sk-live-123",
            "BATCH_SIZE": "500", "DRY_RUN": "true"}


# --- Problem 1: env, not code ----------------------------------------------

def test_load_config_coerces_types():
    cfg = load_config(FULL_ENV)
    assert cfg == {"DB_HOST": "db.prod.internal", "BATCH_SIZE": 500,
                   "DRY_RUN": True, "API_KEY": "sk-live-123"}


def test_load_config_defaults_apply():
    cfg = load_config({"DB_HOST": "localhost", "API_KEY": "k"})
    assert cfg["BATCH_SIZE"] == 1000 and cfg["DRY_RUN"] is False


def test_load_config_missing_required_names_the_key():
    with pytest.raises(ConfigError, match="DB_HOST"):
        load_config({"API_KEY": "k"})
    with pytest.raises(ConfigError, match="API_KEY"):
        load_config({"DB_HOST": "h"})


def test_load_config_bad_int_and_bool_fail_loudly():
    with pytest.raises(ConfigError, match="BATCH_SIZE"):
        load_config({"DB_HOST": "h", "API_KEY": "k", "BATCH_SIZE": "lots"})
    with pytest.raises(ConfigError, match="DRY_RUN"):
        load_config({"DB_HOST": "h", "API_KEY": "k", "DRY_RUN": "maybe"})


def test_load_config_ignores_unrelated_keys():
    cfg = load_config({**FULL_ENV, "PATH": "/usr/bin", "HOME": "/root"})
    assert cfg["DB_HOST"] == "db.prod.internal"


# --- Problem 2: typed settings --------------------------------------------

def test_settings_validates_and_freezes():
    s = Settings(db_host="db.prod.internal", batch_size=500,
                 environment="prod", api_key="sk-live-123")
    assert s.db_host == "db.prod.internal" and s.batch_size == 500
    with pytest.raises(AttributeError):
        s.batch_size = 1


def test_settings_rejects_bad_values_at_construction():
    with pytest.raises(ConfigError):
        Settings(db_host="  ")
    with pytest.raises(ConfigError):
        Settings(db_host="h", batch_size=0)
    with pytest.raises(ConfigError):
        Settings(db_host="h", batch_size=True)
    with pytest.raises(ConfigError):
        Settings(db_host="h", timeout_seconds=-1)
    with pytest.raises(ConfigError):
        Settings(db_host="h", environment="qa")


def test_settings_rejects_unknown_fields_like_typos():
    with pytest.raises(TypeError):
        Settings(db_host="h", batch_sise=500)


def test_settings_from_env_and_repr_masks_secret():
    s = Settings.from_env(FULL_ENV)
    assert s.db_host == "db.prod.internal" and s.batch_size == 500
    assert "sk-live-123" not in repr(s) and "***" in repr(s)


# --- Problem 3: precedence -----------------------------------------------

def test_deep_merge_does_not_wipe_sibling_keys():
    merged = deep_merge({"database": {"host": "a", "port": 1}},
                        {"database": {"port": 2}})
    assert merged == {"database": {"host": "a", "port": 2}}


def test_deep_merge_does_not_mutate_inputs():
    base = {"a": {"x": 1}}
    deep_merge(base, {"a": {"y": 2}})
    assert base == {"a": {"x": 1}}


def test_parse_yaml_subset():
    parsed = parse_yaml("""
# shared defaults
database:
  host: db.yaml.internal
  port: 5433
batch:
  size: 250
debug: false
name: "my pipeline"
""")
    assert parsed == {"database": {"host": "db.yaml.internal", "port": 5433},
                      "batch": {"size": 250}, "debug": False,
                      "name": "my pipeline"}


def test_parse_yaml_rejects_bad_indent_and_bad_lines():
    with pytest.raises(ConfigError):
        parse_yaml("a:\n   b: 1\n")
    with pytest.raises(ConfigError):
        parse_yaml("not-a-mapping\n")


def test_resolve_precedence_defaults_lt_yaml_lt_env_lt_secrets():
    defaults = {"database": {"host": "localhost", "port": 5432},
                "batch": {"size": 1000}}
    merged = resolve(defaults,
                     yaml_text="database:\n  host: db.yaml.internal\n",
                     env={"DATABASE_PORT": 5433},
                     secrets={"DATABASE_HOST": "db.vault.internal"})
    assert merged["database"] == {"host": "db.vault.internal", "port": 5433}
    assert merged["batch"] == {"size": 1000}


# --- Problem 4: secrets ---------------------------------------------------

def test_parse_dotenv():
    values = parse_dotenv("""
# never commit this file
export DB_HOST=db.local
API_KEY="sk-test-1"
EMPTY=''
""")
    assert values == {"DB_HOST": "db.local", "API_KEY": "sk-test-1", "EMPTY": ""}


def test_parse_dotenv_rejects_malformed_lines():
    with pytest.raises(ConfigError):
        parse_dotenv("THIS_HAS_NO_EQUALS\n")


def test_mask_config_masks_by_key_name_and_copies():
    config = {"database": {"host": "h", "password": "hunter2"},
              "api_key": "sk-1", "batch": {"size": 10}}
    masked = mask_config(config)
    assert masked["database"]["password"] == "***"
    assert masked["api_key"] == "***" and masked["batch"]["size"] == 10
    assert config["database"]["password"] == "hunter2"  # original untouched


def test_secret_never_prints():
    secret = Secret("sk-live-123")
    assert str(secret) == "***" and repr(secret) == "Secret('***')"
    assert "sk-live-123" not in str(secret) and secret.reveal() == "sk-live-123"


# --- Problem 5: pipeline end to end --------------------------------------

def test_same_code_dev_and_prod_only_config_changes():
    dev_settings, _ = build_pipeline_config(
        env={"DATABASE_HOST": "db.dev.internal", "BATCH_SIZE": "2",
             "ENVIRONMENT": "dev", "API_KEY": "sk-dev"})
    prod_settings, _ = build_pipeline_config(
        env={"DATABASE_HOST": "db.prod.internal", "BATCH_SIZE": "2",
             "ENVIRONMENT": "prod", "API_KEY": "sk-prod"})
    rows = [{"amount": 10}, {"amount": 20}, {"amount": 30},
            {"amount": 40}, {"amount": 50}]
    dev, prod = Pipeline(dev_settings), Pipeline(prod_settings)
    assert dev.run(rows) == prod.run(rows) == 150.0
    assert dev.batches_run == prod.batches_run == 3  # 5 rows / batch 2
    assert dev.settings.db_host != prod.settings.db_host


def test_bad_config_fails_before_any_row_is_touched():
    with pytest.raises(ConfigError):
        build_pipeline_config(env={"DATABASE_HOST": "h", "BATCH_SIZE": "0",
                                   "ENVIRONMENT": "prod"})
    with pytest.raises(ConfigError):
        build_pipeline_config(env={"DATABASE_HOST": "h", "BATCH_SIZE": "lots"})


def test_pipeline_needs_validated_settings():
    with pytest.raises(ConfigError):
        Pipeline({"db_host": "h"})


def test_pipeline_describe_never_leaks_the_key():
    settings, masked = build_pipeline_config(
        env={"DATABASE_HOST": "db.prod.internal", "API_KEY": "sk-live-123"})
    assert "sk-live-123" not in Pipeline(settings).describe()
    assert "sk-live-123" not in str(masked)


def test_yaml_defaults_flow_into_the_pipeline():
    settings, _ = build_pipeline_config(
        yaml_text="database:\n  host: db.yaml.internal\nbatch:\n  size: 7\n",
        env={"DATABASE_HOST": "db.env.internal"},
        secrets={"API_KEY": "sk-vault"})
    assert settings.db_host == "db.env.internal"  # env beats YAML
    assert settings.batch_size == 7  # YAML beats the code default
    assert settings.environment == "dev"
