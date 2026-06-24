"""
brain_ai/utils/config.py — Configuration loader (YAML + env override).
"""
from __future__ import annotations

import logging
import os
from typing import Any, Optional

logger = logging.getLogger(__name__)

_DEFAULT_CONFIG_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),  # brain_ai/
    "config",
)


def _deep_merge(base: dict, override: dict) -> dict:
    result = dict(base)
    for k, v in override.items():
        if k in result and isinstance(result[k], dict) and isinstance(v, dict):
            result[k] = _deep_merge(result[k], v)
        else:
            result[k] = v
    return result


def load_config(
    path: Optional[str] = None,
    config_dir: Optional[str] = None,
    env_prefix: str = "BRAIN_AI_",
) -> dict:
    """
    Load configuration from YAML file, then overlay matching env vars.

    Env var override format:  BRAIN_AI_MODEL_RUNTIME__BACKEND=ds3_cloud
    (double underscore = nested key separator)

    Args:
        path:       Explicit YAML path. If None, looks for brain_ai.yaml in config_dir.
        config_dir: Directory to look for config files.
        env_prefix: Prefix for env var overrides.

    Returns:
        Merged config dict.
    """
    cfg: dict = {}

    # Load base YAML
    yaml_path = path
    if yaml_path is None:
        cdir = config_dir or _DEFAULT_CONFIG_DIR
        yaml_path = os.path.join(cdir, "brain_ai.yaml")

    if os.path.isfile(yaml_path):
        try:
            import yaml  # type: ignore
            with open(yaml_path, encoding="utf-8") as f:
                cfg = yaml.safe_load(f) or {}
            logger.debug(f"Config loaded from {yaml_path}")
        except ImportError:
            logger.warning("PyYAML not installed — using empty base config.")
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"Config load failed ({yaml_path}): {exc}")
    else:
        logger.debug(f"Config file not found: {yaml_path} (using defaults)")

    # Apply env var overrides
    for key, value in os.environ.items():
        if not key.startswith(env_prefix):
            continue
        sub_key = key[len(env_prefix):].lower()
        parts   = sub_key.split("__")
        node    = cfg
        for part in parts[:-1]:
            if part not in node or not isinstance(node[part], dict):
                node[part] = {}
            node = node[part]
        node[parts[-1]] = _parse_env_value(value)

    return cfg


def _parse_env_value(value: str) -> Any:
    """Try to parse env value as int/float/bool before returning as string."""
    lower = value.lower()
    if lower in ("true",  "yes", "1"): return True
    if lower in ("false", "no",  "0"): return False
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        pass
    return value


def get(config: dict, *keys: str, default: Any = None) -> Any:
    """Safe nested key access: get(cfg, 'model_runtime', 'backend', default='ds3_cloud')"""
    node = config
    for key in keys:
        if not isinstance(node, dict) or key not in node:
            return default
        node = node[key]
    return node
