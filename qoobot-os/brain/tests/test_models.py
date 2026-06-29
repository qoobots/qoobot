#!/usr/bin/env python3
"""
brain_models 验证测试套件

测试内容:
  1. 注册表完整性 — JSON schema, 必填字段, 模型依赖
  2. 路径解析 — 所有模型路径正确, 分类索引完整
  3. 文件状态 — LFS 占位符检测, 目录存在性, 文件计数
  4. 配置一致性 — versions.yaml 与 registry.json 的模型 ID 对齐
  5. 下载脚本 — download_models.py / convert_models.py CLI 可运行
  6. 路径集成 — 适配器默认路径与 registry 一致

离线模式 — 所有测试均无需真权重或 GPU。
"""

import json
import os
import sys
import unittest
from pathlib import Path

# ============================================================================
# 路径设置
# ============================================================================

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
BRAIN_MODELS_DIR = PROJECT_ROOT / "brain_models"
REGISTRY_FILE = BRAIN_MODELS_DIR / "model_registry.json"
VERSIONS_FILE = BRAIN_MODELS_DIR / "model_versions.yaml"

sys.path.insert(0, str(PROJECT_ROOT))


# ============================================================================
# Test 1: 注册表完整性
# ============================================================================

class TestRegistryIntegrity(unittest.TestCase):
    """模型注册表 JSON 结构和内容完整性"""

    @classmethod
    def setUpClass(cls):
        cls.registry = cls._load_registry()

    @classmethod
    def _load_registry(cls):
        if not REGISTRY_FILE.exists():
            raise AssertionError(f"Registry not found: {REGISTRY_FILE}")
        with open(REGISTRY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)

    def test_registry_exists_and_valid_json(self):
        """注册表文件存在且为有效 JSON"""
        self.assertIsInstance(self.registry, dict)
        self.assertIn("models", self.registry)
        self.assertIn("registry_version", self.registry)

    def test_models_count(self):
        """注册表包含所有 11 个模型"""
        models = self.registry.get("models", {})
        self.assertEqual(len(models), 11, f"Expected 11 models, got {len(models)}")

    def test_required_fields_per_model(self):
        """每个模型包含必填字段"""
        required = ["category", "name", "format", "local_path", "priority"]
        for model_id, info in self.registry["models"].items():
            for field in required:
                self.assertIn(field, info,
                              f"Model '{model_id}' missing required field '{field}'")

    def test_categories_valid(self):
        """模型分类在已知集合中"""
        valid_cats = {"llm", "cv", "asr", "slam", "vla", "simulation"}
        for model_id, info in self.registry["models"].items():
            cat = info.get("category", "")
            self.assertIn(cat, valid_cats,
                          f"Unknown category '{cat}' for model '{model_id}'")

    def test_formats_valid(self):
        """模型格式在已知集合中"""
        valid_fmts = {"tensorrt_engine", "onnx", "gguf", "pytorch_lora",
                      "ctranslate2", "fbow", "pytorch", "usd"}
        for model_id, info in self.registry["models"].items():
            fmt = info.get("format", "")
            self.assertIn(fmt, valid_fmts,
                          f"Unknown format '{fmt}' for model '{model_id}'")

    def test_priorities_valid(self):
        """优先级值为有效枚举"""
        valid = {"P0_critical", "P1_fallback", "P1_general", "P2_experimental"}
        for model_id, info in self.registry["models"].items():
            self.assertIn(info.get("priority", ""), valid,
                          f"Invalid priority for '{model_id}'")

    def test_huggingface_fields_when_needed(self):
        """需要下载的模型应有 huggingface 配置"""
        needs_download = ["onnx", "gguf", "tensorrt_engine", "ctranslate2", "pytorch_lora", "fbow"]
        for model_id, info in self.registry["models"].items():
            if info.get("format") in needs_download:
                hf = info.get("huggingface")
                if hf is not None:  # orb_vocab has placeholder
                    self.assertIn("repo", hf,
                                  f"Model '{model_id}' HF config missing 'repo'")
                    self.assertIn("files", hf,
                                  f"Model '{model_id}' HF config missing 'files'")

    def test_download_groups_reference_valid_models(self):
        """下载组引用已注册的模型"""
        all_ids = set(self.registry["models"].keys())
        for group_name, group in self.registry.get("download_groups", {}).items():
            for model_id in group["models"]:
                self.assertIn(model_id, all_ids,
                              f"Download group '{group_name}' references unknown model '{model_id}'")

    def test_fallback_chain_valid(self):
        """LLM 降级链引用有效的模型"""
        # 7B → 3B → 1.5B
        self.assertIn("fallback_for",
                      self.registry["models"]["qwen2.5-3b-instruct-int4"],
                      "3B model missing fallback_for")
        self.assertEqual(
            self.registry["models"]["qwen2.5-3b-instruct-int4"]["fallback_for"],
            "qwen2.5-7b-instruct-int4",
        )
        self.assertIn("fallback_for",
                      self.registry["models"]["qwen2.5-1.5b-instruct-gguf"],
                      "1.5B model missing fallback_for")

    def test_llm_models_have_context_length(self):
        """LLM 模型应定义 max_context_length"""
        for model_id, info in self.registry["models"].items():
            if info["category"] == "llm":
                self.assertIn("max_context_length", info,
                              f"LLM '{model_id}' missing max_context_length")
                self.assertGreater(info["max_context_length"], 0)

    def test_cv_models_have_input_shape(self):
        """CV 模型应定义 input/output shape（SAM2 在 parts 中定义）"""
        for model_id, info in self.registry["models"].items():
            if info["category"] == "cv" and info["format"] == "onnx":
                has_shape = (
                    "input_shape" in info
                    or any(
                        "input_shape" in part_info
                        for part_info in info.get("parts", {}).values()
                    )
                )
                self.assertTrue(has_shape,
                    f"CV model '{model_id}' missing input_shape in model or parts")

    def test_sam2_has_two_parts(self):
        """SAM2 应包含 encoder + decoder 两部分"""
        sam2 = self.registry["models"].get("sam2_hiera_tiny", {})
        self.assertIn("parts", sam2, "SAM2 missing 'parts'")
        self.assertIn("encoder", sam2["parts"])
        self.assertIn("decoder", sam2["parts"])


# ============================================================================
# Test 2: 路径解析器
# ============================================================================

class TestModelPathResolver(unittest.TestCase):
    """model_path_resolver.py 功能测试"""

    @classmethod
    def setUpClass(cls):
        from brain_models.model_path_resolver import ModelResolver
        # Force fresh load
        ModelResolver._instance = None
        cls.resolver = ModelResolver()

    def test_resolver_loads_all_models(self):
        """解析器加载全部 11 个模型"""
        models = self.resolver.list_models()
        self.assertEqual(len(models), 11, f"Expected 11 models, got {len(models)}: {models}")

    def test_category_indexing(self):
        """分类索引包含正确的模型数"""
        categories = {
            "llm": 3,
            "cv": 3,
            "asr": 1,
            "slam": 1,
            "vla": 1,
            "simulation": 2,
        }
        for cat, expected_count in categories.items():
            models = self.resolver.list_models(cat)
            self.assertEqual(len(models), expected_count,
                             f"Category '{cat}': expected {expected_count}, got {len(models)}")

    def test_resolve_each_model(self):
        """每个模型都能解析出路径"""
        for model_id in self.resolver.list_models():
            path = self.resolver.resolve(model_id)
            if model_id == "brain-vla-chinese-lora":
                # No engine_file defined
                self.assertIsNone(path, f"{model_id} should resolve to None (no engine_file)")
            else:
                self.assertIsNotNone(path,
                    f"Model '{model_id}' failed to resolve path")

    def test_resolve_sam2_has_two_files(self):
        """SAM2 模型解析出 2 个文件 (encoder + decoder)"""
        files = self.resolver.resolve_all("sam2_hiera_tiny")
        self.assertEqual(len(files), 2, f"SAM2 expected 2 parts, got {len(files)}")

    def test_whisper_is_directory_model(self):
        """Whisper 是目录型模型，路径指向目录"""
        path = self.resolver.resolve("whisper-large-v3-ct2")
        self.assertIsNotNone(path)
        # 目录可能不存在，但我们验证路径以 .../whisper-large-v3-ct2 结尾
        self.assertTrue(str(path).endswith("whisper-large-v3-ct2"),
                        f"Whisper path should end with whisper-large-v3-ct2, got {path}")

    def test_model_exists_detection(self):
        """model_exists 检测 0 字节 LFS 占位符"""
        # All model files are currently 0-byte LFS stubs, so exists should be False
        for model_id in self.resolver.list_models():
            exists = self.resolver.model_exists(model_id)
            # 所有模型当前都是 LFS 占位符或空目录 → should be False
            self.assertFalse(exists,
                f"Model '{model_id}' should not exist (LFS stubs). Got exists={exists}")

    def test_get_info_each_model(self):
        """get_info 返回每个模型的完整信息"""
        for model_id in self.resolver.list_models():
            info = self.resolver.get_info(model_id)
            self.assertIsNotNone(info, f"get_info({model_id}) returned None")
            self.assertEqual(info.model_id, model_id)
            self.assertIsInstance(info.name, str)
            self.assertIsInstance(info.category, str)

    def test_convenience_functions(self):
        """find_model() 和 resolve_model_path() 便捷函数"""
        from brain_models.model_path_resolver import find_model, resolve_model_path

        # 已知模型
        p = resolve_model_path("yolov11n")
        self.assertIsNotNone(p)
        self.assertTrue(str(p).endswith("yolov11n.onnx"))

        s = find_model("yolov11n")
        self.assertIsNotNone(s)
        self.assertIn("yolov11n.onnx", s)

        # 未知模型
        self.assertIsNone(resolve_model_path("nonexistent_model"))


# ============================================================================
# Test 3: 文件系统状态
# ============================================================================

class TestFileSystemState(unittest.TestCase):
    """文件系统和目录结构验证"""

    def test_brain_models_directory_exists(self):
        """brain_models 根目录存在"""
        self.assertTrue(BRAIN_MODELS_DIR.exists())
        self.assertTrue(BRAIN_MODELS_DIR.is_dir())

    def test_required_subdirs_exist(self):
        """必要的模型子目录存在"""
        required_dirs = [
            "llm/qwen2.5-7b-instruct-int4",
            "llm/qwen2.5-3b-instruct-int4",
            "llm/qwen2.5-1.5b-instruct-gguf",
            "cv",
            "asr/whisper-large-v3-ct2",
            "slam",
            "vla/brain-vla-chinese-lora",
        ]
        for subdir in required_dirs:
            full_path = BRAIN_MODELS_DIR / subdir
            self.assertTrue(full_path.exists(),
                            f"Required directory missing: {subdir}")

    def test_lfs_config_exists(self):
        """.gitattributes 存在且配置 LFS 模式"""
        attrs = BRAIN_MODELS_DIR / ".gitattributes"
        self.assertTrue(attrs.exists(), ".gitattributes not found")

        with open(attrs, "r", encoding="utf-8") as f:
            content = f.read()

        expected_patterns = ["*.onnx", "*.pt", "*.gguf", "*.engine", "*.fbow"]
        for pattern in expected_patterns:
            self.assertIn(pattern, content,
                          f".gitattributes missing pattern: {pattern}")

    def test_onnx_files_exist_as_stubs(self):
        """ONNX 文件存在（应为 LFS 占位符，0 字节）"""
        cv_dir = BRAIN_MODELS_DIR / "cv"
        onnx_files = [
            "yolov11n.onnx",
            "yolov11s.onnx",
            "sam2_hiera_tiny.encoder.onnx",
            "sam2_hiera_tiny.decoder.onnx",
        ]
        for fname in onnx_files:
            fpath = cv_dir / fname
            self.assertTrue(fpath.exists(),
                            f"ONNX file missing: {fname}")
            # LFS 占位符为 0 字节（未 git lfs pull 状态）
            size = fpath.stat().st_size
            self.assertIn(size, [0, 130],  # 0 bytes or standard LFS pointer
                          f"{fname}: expected 0-130 bytes (LFS stub), got {size}")

    def test_orb_vocab_exists_as_stub(self):
        """ORB 词汇文件存在"""
        fpath = BRAIN_MODELS_DIR / "slam" / "orb_vocab.fbow"
        self.assertTrue(fpath.exists(), "orb_vocab.fbow not found")

    def test_no_unexpected_directories(self):
        """brain_models 目录结构符合预期（无多余目录）"""
        # Walk brain_models and check dirs
        expected_dirs = {
            BRAIN_MODELS_DIR,
            BRAIN_MODELS_DIR / "asr",
            BRAIN_MODELS_DIR / "asr" / "whisper-large-v3-ct2",
            BRAIN_MODELS_DIR / "config",
            BRAIN_MODELS_DIR / "config" / "trt_llm",
            BRAIN_MODELS_DIR / "cv",
            BRAIN_MODELS_DIR / "llm",
            BRAIN_MODELS_DIR / "llm" / "qwen2.5-1.5b-instruct-gguf",
            BRAIN_MODELS_DIR / "llm" / "qwen2.5-3b-instruct-int4",
            BRAIN_MODELS_DIR / "llm" / "qwen2.5-7b-instruct-int4",
            BRAIN_MODELS_DIR / "scripts",
            BRAIN_MODELS_DIR / "slam",
            BRAIN_MODELS_DIR / "vla",
            BRAIN_MODELS_DIR / "vla" / "brain-vla-chinese-lora",
        }
        # Pycache is expected (Python bytecode)
        for root, dirs, files in os.walk(str(BRAIN_MODELS_DIR)):
            root_path = Path(root)
            # Skip Python bytecode cache
            if "__pycache__" in root_path.parts:
                continue
            if root_path != BRAIN_MODELS_DIR and root_path not in expected_dirs:
                self.fail(f"Unexpected directory in brain_models: {root_path}")


# ============================================================================
# Test 4: 配置一致性
# ============================================================================

class TestConfigConsistency(unittest.TestCase):
    """versions.yaml 与 registry.json 一致性"""

    @classmethod
    def setUpClass(cls):
        with open(REGISTRY_FILE, "r", encoding="utf-8") as f:
            cls.registry = json.load(f)

        try:
            import yaml
            with open(VERSIONS_FILE, "r", encoding="utf-8") as f:
                cls.versions = yaml.safe_load(f)
        except ImportError:
            cls.versions = None

    def test_versions_file_exists(self):
        """model_versions.yaml 存在"""
        self.assertTrue(VERSIONS_FILE.exists(), "model_versions.yaml not found")

    def test_versions_is_valid_yaml(self):
        """model_versions.yaml 为有效 YAML"""
        self.assertIsNotNone(self.versions, "YAML parsing failed (pyyaml not installed)")
        self.assertIsInstance(self.versions, dict)
        self.assertIn("models", self.versions)

    def test_all_models_in_versions(self):
        """registry 中的所有模型都应在 versions.yaml 中注册"""
        if self.versions is None:
            self.skipTest("pyyaml not available")

        registry_ids = set(self.registry["models"].keys())
        version_ids = set()

        for cat, models in self.versions.get("models", {}).items():
            for model_id in models:
                version_ids.add(model_id)

        missing = registry_ids - version_ids
        self.assertEqual(len(missing), 0,
                         f"Models in registry but not in versions.yaml: {missing}")

    def test_no_stale_versions(self):
        """versions.yaml 中无多余的已删除模型"""
        if self.versions is None:
            self.skipTest("pyyaml not available")

        registry_ids = set(self.registry["models"].keys())
        version_ids = set()

        for cat, models in self.versions.get("models", {}).items():
            for model_id in models:
                version_ids.add(model_id)

        extra = version_ids - registry_ids
        self.assertEqual(len(extra), 0,
                         f"Models in versions.yaml but not in registry: {extra}")


# ============================================================================
# Test 5: 脚本可运行性
# ============================================================================

class TestScriptsRunnable(unittest.TestCase):
    """下载/转换脚本 CLI 可运行性"""

    def test_download_scripts_exist(self):
        """下载脚本文件存在"""
        py_script = BRAIN_MODELS_DIR / "scripts" / "download_models.py"
        sh_script = BRAIN_MODELS_DIR / "scripts" / "download_models.sh"
        self.assertTrue(py_script.exists(), "download_models.py not found")
        self.assertTrue(sh_script.exists(), "download_models.sh not found")

    def test_download_py_has_no_syntax_error(self):
        """download_models.py 无语法错误"""
        script = BRAIN_MODELS_DIR / "scripts" / "download_models.py"
        with open(script, "r", encoding="utf-8") as f:
            source = f.read()
        try:
            compile(source, str(script), "exec")
        except SyntaxError as e:
            self.fail(f"download_models.py has syntax error: {e}")

    def test_convert_py_has_no_syntax_error(self):
        """convert_models.py 无语法错误"""
        script = BRAIN_MODELS_DIR / "scripts" / "convert_models.py"
        with open(script, "r", encoding="utf-8") as f:
            source = f.read()
        try:
            compile(source, str(script), "exec")
        except SyntaxError as e:
            self.fail(f"convert_models.py has syntax error: {e}")

    def test_download_py_cli_help(self):
        """download_models.py --help 可正常执行"""
        import subprocess
        result = subprocess.run(
            [sys.executable, str(BRAIN_MODELS_DIR / "scripts" / "download_models.py"), "--help"],
            capture_output=True, text=True, timeout=15,
        )
        self.assertEqual(result.returncode, 0,
                         f"download_models.py --help failed: {result.stderr}")
        self.assertIn("usage", result.stdout.lower())

    def test_convert_py_cli_help(self):
        """convert_models.py --help 可正常执行"""
        import subprocess
        result = subprocess.run(
            [sys.executable, str(BRAIN_MODELS_DIR / "scripts" / "convert_models.py"), "--help"],
            capture_output=True, text=True, timeout=15,
        )
        self.assertEqual(result.returncode, 0,
                         f"convert_models.py --help failed: {result.stderr}")
        self.assertIn("usage", result.stdout.lower())

    def test_download_py_list(self):
        """download_models.py --list 正常输出"""
        import subprocess
        result = subprocess.run(
            [sys.executable, str(BRAIN_MODELS_DIR / "scripts" / "download_models.py"), "--list"],
            capture_output=True, text=True, timeout=15,
        )
        self.assertEqual(result.returncode, 0,
                         f"download_models.py --list failed: {result.stderr}")
        self.assertIn("yolov11n", result.stdout)
        self.assertIn("P0_critical", result.stdout)

    def test_convert_py_check(self):
        """convert_models.py --check 正常输出"""
        import subprocess
        result = subprocess.run(
            [sys.executable, str(BRAIN_MODELS_DIR / "scripts" / "convert_models.py"), "--check"],
            capture_output=True, text=True, timeout=15,
        )
        self.assertEqual(result.returncode, 0,
                         f"convert_models.py --check failed: {result.stderr}")
        self.assertIn("模型状态", result.stdout)
        self.assertIn("总结", result.stdout)


# ============================================================================
# Test 6: 路径集成
# ============================================================================

class TestPathIntegration(unittest.TestCase):
    """适配器默认路径与 registry 一致性"""

    def test_slam_vocab_path_consistent(self):
        """SLAM 适配器默认 vocab_path 与 registry 一致"""
        # Check scene_aggregator.py uses "orb_vocab.fbow" not "ORBvoc.txt"
        scene_agg = PROJECT_ROOT / "brain_ai" / "brain_ai" / "perception" / "scene_aggregator.py"
        with open(scene_agg, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("orb_vocab.fbow", content,
                      "scene_aggregator.py should reference 'orb_vocab.fbow'")
        self.assertNotIn('"ORBvoc.txt"', content,
                         "scene_aggregator.py should NOT reference 'ORBvoc.txt'")

    def test_segmentor_path_consistent(self):
        """SAM2 分割器示例使用正确的文件名"""
        segmentor = PROJECT_ROOT / "brain_ai" / "brain_ai" / "perception" / "segmentor.py"
        with open(segmentor, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("sam2_hiera_tiny.encoder.onnx", content,
                      "segmentor.py should reference sam2_hiera_tiny.encoder.onnx")
        self.assertNotIn('"sam2_b.onnx"', content,
                         "segmentor.py should NOT reference 'sam2_b.onnx'")

    def test_asr_resolves_whisper_path(self):
        """ASR 引擎尝试从 registry 解析 whisper-large-v3-ct2"""
        asr_engine = PROJECT_ROOT / "brain_ai" / "brain_ai" / "voice_io" / "asr_engine.py"
        with open(asr_engine, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("_resolve_whisper_path", content,
                      "asr_engine.py should have _resolve_whisper_path method")
        self.assertIn("whisper-large-v3-ct2", content,
                      "asr_engine.py should reference whisper-large-v3-ct2")

    def test_model_path_resolver_importable(self):
        """model_path_resolver 可从项目根目录导入"""
        try:
            from brain_models.model_path_resolver import ModelResolver
            self.assertIsNotNone(ModelResolver)
        except ImportError as e:
            self.fail(f"model_path_resolver not importable: {e}")


# ============================================================================
# 入口
# ============================================================================

if __name__ == "__main__":
    # 设置无缓冲输出
    unittest.main(verbosity=2, buffer=False)
