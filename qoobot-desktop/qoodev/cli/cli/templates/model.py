"""
Model project template.

Creates a QooBot AI model project for training/inference.
"""

from __future__ import annotations

from pathlib import Path
from typing import List


class ModelTemplate:
    """Generates a QooBot model project."""

    QOO_TOML = '''\
[project]
name = "{name}"
type = "model"
version = "0.1.0"
description = "A QooBot AI model"
python_version = "{python_version}"

[model]
framework = "pytorch"
input_type = "image"
output_type = "tensor"

[dependencies]
python = [
    "torch>=2.0",
    "qoobot-sdk>=0.1.0",
]
'''

    MODEL_PY = '''\
"""
{name} - QooBot AI Model

Model definition and training script.
"""

import torch
import torch.nn as nn


class {class_name}(nn.Module):
    """Neural network model for {name}."""

    def __init__(self):
        super().__init__()
        # Define your model layers here
        self.conv1 = nn.Conv2d(3, 64, kernel_size=3, padding=1)
        self.relu = nn.ReLU()
        self.fc = nn.Linear(64, 10)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Forward pass."""
        x = self.conv1(x)
        x = self.relu(x)
        x = x.mean(dim=[2, 3])
        x = self.fc(x)
        return x


def train():
    """Training script placeholder."""
    model = {class_name}()
    print(f"Model: {{model.__class__.__name__}}")
    print(f"Parameters: {{sum(p.numel() for p in model.parameters())}}")
    return model


if __name__ == "__main__":
    train()
'''

    TRAIN_PY = '''\
"""Training script for {name} model."""

import torch
from src.model import {class_name}


def main():
    model = {class_name}()
    print(f"Training {{model.__class__.__name__}}...")
    # Add training logic here


if __name__ == "__main__":
    main()
'''

    TEST_MODEL = '''\
"""Tests for {name} model."""

import torch
import pytest
from src.model import {class_name}


def test_model_creation():
    """Test model instantiation."""
    model = {class_name}()
    assert isinstance(model, torch.nn.Module)


def test_forward_pass():
    """Test forward pass with dummy input."""
    model = {class_name}()
    x = torch.randn(1, 3, 64, 64)
    y = model(x)
    assert y.shape[0] == 1
'''

    def generate(
        self, name: str, target_path: Path, python_version: str
    ) -> List[Path]:
        class_name = self._to_class_name(name)
        created = []

        dirs = [
            target_path,
            target_path / "src",
            target_path / "tests",
            target_path / "data",
            target_path / "checkpoints",
        ]
        for d in dirs:
            d.mkdir(parents=True, exist_ok=True)
            created.append(d)

        # qoo.toml
        f = target_path / "qoo.toml"
        f.write_text(self.QOO_TOML.format(name=name, python_version=python_version))
        created.append(f)

        # src/model.py
        f = target_path / "src" / "__init__.py"
        f.write_text('"""Model source package."""\n')
        created.append(f)

        f = target_path / "src" / "model.py"
        f.write_text(self.MODEL_PY.format(name=name, class_name=class_name))
        created.append(f)

        # train.py
        f = target_path / "train.py"
        f.write_text(self.TRAIN_PY.format(name=name, class_name=class_name))
        created.append(f)

        # tests
        f = target_path / "tests" / "__init__.py"
        f.write_text('"""Test package."""\n')
        created.append(f)

        f = target_path / "tests" / "test_model.py"
        f.write_text(self.TEST_MODEL.format(name=name, class_name=class_name))
        created.append(f)

        # .gitignore
        f = target_path / ".gitignore"
        f.write_text(
            "__pycache__/\n*.pyc\nbuild/\ndist/\n*.egg-info/\n"
            "checkpoints/*.pt\ndata/\n"
        )
        created.append(f)

        return created

    @staticmethod
    def _to_class_name(name: str) -> str:
        return "".join(word.capitalize() for word in name.replace("-", "_").split("_"))
