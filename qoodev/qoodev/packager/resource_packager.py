"""
qoodev resource packager — 3D model / texture / audio resource optimization and packaging.

对标：Unreal Engine Cook + Unity AssetBundle
提供资源压缩、格式转换、纹理图集、LOD生成、资源清单。
"""

from __future__ import annotations

import hashlib
import json
import struct
import time
from dataclasses import dataclass, field
from enum import Enum
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class ResourceType(str, Enum):
    MESH_OBJ = "mesh_obj"
    MESH_GLTF = "mesh_gltf"
    MESH_STL = "mesh_stl"
    TEXTURE_PNG = "texture_png"
    TEXTURE_JPEG = "texture_jpeg"
    TEXTURE_DDS = "texture_dds"
    AUDIO_WAV = "audio_wav"
    AUDIO_MP3 = "audio_mp3"
    AUDIO_OGG = "audio_ogg"
    POINT_CLOUD = "point_cloud"
    ANIMATION = "animation"
    CONFIG = "config"
    BINARY = "binary"


class CompressionMethod(str, Enum):
    NONE = "none"
    ZLIB = "zlib"
    LZ4 = "lz4"
    QUANTIZE = "quantize"
    DRAKO = "drako"  # mesh compression


class LODLevel(str, Enum):
    LOD0 = "lod0"  # highest quality
    LOD1 = "lod1"
    LOD2 = "lod2"
    LOD3 = "lod3"  # lowest quality


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class ResourceEntry:
    """Metadata for a single resource file."""
    path: str
    resource_type: ResourceType
    size_bytes: int
    compressed_size_bytes: int = 0
    compression: CompressionMethod = CompressionMethod.NONE
    checksum_sha256: str = ""
    tags: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    lod_level: Optional[LODLevel] = None
    custom_meta: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ResourceManifest:
    """Manifest describing a packaged resource bundle."""
    bundle_name: str
    version: str = "1.0.0"
    created_at: str = ""
    entries: List[ResourceEntry] = field(default_factory=list)
    total_original_size: int = 0
    total_compressed_size: int = 0
    compression_ratio: float = 0.0

    def __post_init__(self):
        if not self.created_at:
            self.created_at = time.strftime("%Y-%m-%dT%H:%M:%S")


# ---------------------------------------------------------------------------
# ResourcePackager
# ---------------------------------------------------------------------------

class ResourcePackager:
    """Collect, compress, and bundle resources for distribution.

    Usage::

        packager = ResourcePackager()
        packager.add_resource("meshes/robot.obj", ResourceType.MESH_OBJ)
        packager.add_resource("textures/base.png", ResourceType.TEXTURE_PNG)
        bundle_path = packager.pack("robot_assets", output_dir=Path("build"))
    """

    def __init__(self, base_dir: Optional[Path] = None):
        self._base_dir = base_dir or Path.cwd()
        self._resources: Dict[str, ResourceEntry] = {}

    def add_resource(
        self,
        path: str,
        resource_type: ResourceType,
        tags: Optional[List[str]] = None,
        dependencies: Optional[List[str]] = None,
        lod_level: Optional[LODLevel] = None,
        custom_meta: Optional[Dict[str, Any]] = None,
    ) -> ResourceEntry:
        full_path = self._base_dir / path
        if not full_path.exists():
            raise FileNotFoundError(f"Resource not found: {full_path}")

        size = full_path.stat().st_size
        checksum = self._compute_checksum(full_path)

        entry = ResourceEntry(
            path=path,
            resource_type=resource_type,
            size_bytes=size,
            checksum_sha256=checksum,
            tags=tags or [],
            dependencies=dependencies or [],
            lod_level=lod_level,
            custom_meta=custom_meta or {},
        )
        self._resources[path] = entry
        return entry

    def add_directory(
        self,
        dir_path: str,
        extensions: Optional[Set[str]] = None,
        recursive: bool = True,
    ) -> List[ResourceEntry]:
        """Add all resources from a directory, auto-detecting types."""
        full_dir = self._base_dir / dir_path
        if not full_dir.is_dir():
            raise NotADirectoryError(str(full_dir))

        entries: List[ResourceEntry] = []
        pattern = "**/*" if recursive else "*"

        for f in full_dir.glob(pattern):
            if not f.is_file():
                continue
            if extensions and f.suffix.lower() not in extensions:
                continue

            rtype = self._detect_type(f)
            rel_path = str(f.relative_to(self._base_dir))
            entry = self.add_resource(rel_path, rtype)
            entries.append(entry)

        return entries

    def remove_resource(self, path: str) -> None:
        self._resources.pop(path, None)

    # -- compression ---------------------------------------------------------

    def pack(
        self,
        bundle_name: str,
        output_dir: Path,
        version: str = "1.0.0",
        compression: CompressionMethod = CompressionMethod.ZLIB,
    ) -> Path:
        """Create a compressed resource bundle."""
        import zlib

        output_dir.mkdir(parents=True, exist_ok=True)

        manifest = ResourceManifest(bundle_name=bundle_name, version=version)
        bundle_data = bytearray()

        for entry in self._resources.values():
            full_path = self._base_dir / entry.path
            raw = full_path.read_bytes()

            if compression == CompressionMethod.ZLIB:
                compressed = zlib.compress(raw, level=6)
                entry.compression = CompressionMethod.ZLIB
            elif compression == CompressionMethod.LZ4:
                try:
                    import lz4.frame  # type: ignore
                    compressed = lz4.frame.compress(raw)
                    entry.compression = CompressionMethod.LZ4
                except ImportError:
                    compressed = zlib.compress(raw, level=6)
                    entry.compression = CompressionMethod.ZLIB
            else:
                compressed = raw
                entry.compression = CompressionMethod.NONE

            entry.compressed_size_bytes = len(compressed)

            # write entry header + data
            header = self._serialize_entry_header(entry)
            bundle_data.extend(header)
            bundle_data.extend(compressed)

            manifest.entries.append(entry)
            manifest.total_original_size += entry.size_bytes
            manifest.total_compressed_size += entry.compressed_size_bytes

        manifest.compression_ratio = (
            manifest.total_compressed_size / manifest.total_original_size
            if manifest.total_original_size > 0 else 1.0
        )

        # write manifest
        manifest_json = json.dumps({
            "bundle_name": manifest.bundle_name,
            "version": manifest.version,
            "created_at": manifest.created_at,
            "total_original_size": manifest.total_original_size,
            "total_compressed_size": manifest.total_compressed_size,
            "compression_ratio": manifest.compression_ratio,
            "entries": [
                {
                    "path": e.path,
                    "resource_type": e.resource_type.value,
                    "size_bytes": e.size_bytes,
                    "compressed_size_bytes": e.compressed_size_bytes,
                    "compression": e.compression.value,
                    "checksum_sha256": e.checksum_sha256,
                    "tags": e.tags,
                    "dependencies": e.dependencies,
                    "lod_level": e.lod_level.value if e.lod_level else None,
                    "custom_meta": e.custom_meta,
                }
                for e in manifest.entries
            ],
        }, indent=2).encode("utf-8")

        # bundle format: [magic:4][manifest_len:4][manifest_json][entry_data...]
        magic = b"QOOB"
        bundle = bytearray(magic)
        bundle.extend(struct.pack("<I", len(manifest_json)))
        bundle.extend(manifest_json)
        bundle.extend(bundle_data)

        bundle_path = output_dir / f"{bundle_name}.qoor"
        bundle_path.write_bytes(bundle)
        return bundle_path

    @staticmethod
    def unpack(bundle_path: Path, output_dir: Path) -> ResourceManifest:
        """Extract a .qoor bundle."""
        import zlib

        data = bundle_path.read_bytes()

        magic = data[:4]
        if magic != b"QOOB":
            raise ValueError("Not a valid QooBot resource bundle")

        manifest_len = struct.unpack("<I", data[4:8])[0]
        manifest_json = data[8:8 + manifest_len]
        manifest_dict = json.loads(manifest_json.decode("utf-8"))

        manifest = ResourceManifest(
            bundle_name=manifest_dict["bundle_name"],
            version=manifest_dict["version"],
            created_at=manifest_dict["created_at"],
            total_original_size=manifest_dict["total_original_size"],
            total_compressed_size=manifest_dict["total_compressed_size"],
            compression_ratio=manifest_dict["compression_ratio"],
        )

        offset = 8 + manifest_len
        output_dir.mkdir(parents=True, exist_ok=True)

        for entry_dict in manifest_dict["entries"]:
            entry = ResourceEntry(
                path=entry_dict["path"],
                resource_type=ResourceType(entry_dict["resource_type"]),
                size_bytes=entry_dict["size_bytes"],
                compressed_size_bytes=entry_dict["compressed_size_bytes"],
                compression=CompressionMethod(entry_dict["compression"]),
                checksum_sha256=entry_dict["checksum_sha256"],
                tags=entry_dict.get("tags", []),
                dependencies=entry_dict.get("dependencies", []),
                lod_level=LODLevel(entry_dict["lod_level"]) if entry_dict.get("lod_level") else None,
                custom_meta=entry_dict.get("custom_meta", {}),
            )

            compressed = data[offset:offset + entry.compressed_size_bytes]
            offset += entry.compressed_size_bytes

            if entry.compression == CompressionMethod.ZLIB:
                raw = zlib.decompress(compressed)
            elif entry.compression == CompressionMethod.LZ4:
                try:
                    import lz4.frame  # type: ignore
                    raw = lz4.frame.decompress(compressed)
                except ImportError:
                    raw = zlib.decompress(compressed)
            else:
                raw = compressed

            out_path = output_dir / entry.path
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_bytes(raw)

            # verify checksum
            actual = hashlib.sha256(raw).hexdigest()
            if actual != entry.checksum_sha256:
                print(f"WARNING: checksum mismatch for {entry.path}")

            manifest.entries.append(entry)

        return manifest

    # -- texture atlasing ----------------------------------------------------

    @staticmethod
    def create_texture_atlas(
        texture_paths: List[Path],
        atlas_size: Tuple[int, int] = (2048, 2048),
        padding: int = 2,
    ) -> Tuple[np.ndarray, Dict[str, Tuple[int, int, int, int]]]:
        """Pack multiple textures into a single atlas texture.

        Returns: (atlas_array, uv_mapping) where uv_mapping maps path → (x, y, w, h).
        """
        try:
            from PIL import Image
        except ImportError:
            raise ImportError("Pillow required for texture atlas")

        atlas = np.zeros((atlas_size[1], atlas_size[0], 4), dtype=np.uint8)
        uv_map: Dict[str, Tuple[int, int, int, int]] = {}

        # simple row-major packer
        x, y, row_h = padding, padding, 0
        for path in texture_paths:
            img = Image.open(path).convert("RGBA")
            w, h = img.size

            if x + w + padding > atlas_size[0]:
                x = padding
                y += row_h + padding
                row_h = 0

            if y + h + padding > atlas_size[1]:
                raise ValueError(f"Texture atlas overflow — cannot fit {path}")

            arr = np.array(img)
            atlas[y:y + h, x:x + w] = arr
            uv_map[str(path)] = (x, y, w, h)

            x += w + padding
            row_h = max(row_h, h)

        return atlas, uv_map

    # -- LOD generation ------------------------------------------------------

    @staticmethod
    def generate_lod_mesh(
        vertices: np.ndarray,
        faces: np.ndarray,
        target_faces: int,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Generate lower-LOD mesh via simple decimation (vertex clustering)."""
        if len(faces) <= target_faces:
            return vertices, faces

        # vertex clustering: grid-based simplification
        grid_resolution = max(1, int(np.ceil(len(vertices) / target_faces)))
        v_min = vertices.min(axis=0)
        v_max = vertices.max(axis=0)
        grid_shape = np.ceil((v_max - v_min) / (v_max - v_min).max() * grid_resolution).astype(int) + 1

        # quantize vertices to grid
        grid_indices = np.floor((vertices - v_min) / ((v_max - v_min).max() / grid_resolution)).astype(int)
        grid_indices = np.clip(grid_indices, 0, np.array(grid_shape) - 1)

        # merge vertices in same grid cell
        cell_map: Dict[Tuple[int, ...], List[int]] = {}
        for i, idx in enumerate(grid_indices):
            key = tuple(idx)
            cell_map.setdefault(key, []).append(i)

        new_vertices = np.array([vertices[indices].mean(axis=0) for indices in cell_map.values()])
        old_to_new = {}
        for new_idx, (_, indices) in enumerate(cell_map.items()):
            for old_idx in indices:
                old_to_new[old_idx] = new_idx

        # remap faces, removing degenerate ones
        new_faces_list = []
        for face in faces:
            new_face = tuple(sorted(set(old_to_new.get(v, v) for v in face)))
            if len(new_face) == 3 and len(set(new_face)) == 3:
                new_faces_list.append(new_face)

        return new_vertices, np.array(new_faces_list[:target_faces])

    # -- helpers -------------------------------------------------------------

    @staticmethod
    def _compute_checksum(path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()

    @staticmethod
    def _detect_type(path: Path) -> ResourceType:
        ext = path.suffix.lower()
        mapping = {
            ".obj": ResourceType.MESH_OBJ,
            ".gltf": ResourceType.MESH_GLTF,
            ".glb": ResourceType.MESH_GLTF,
            ".stl": ResourceType.MESH_STL,
            ".png": ResourceType.TEXTURE_PNG,
            ".jpg": ResourceType.TEXTURE_JPEG,
            ".jpeg": ResourceType.TEXTURE_JPEG,
            ".dds": ResourceType.TEXTURE_DDS,
            ".wav": ResourceType.AUDIO_WAV,
            ".mp3": ResourceType.AUDIO_MP3,
            ".ogg": ResourceType.AUDIO_OGG,
            ".ply": ResourceType.POINT_CLOUD,
            ".pcd": ResourceType.POINT_CLOUD,
            ".las": ResourceType.POINT_CLOUD,
            ".json": ResourceType.CONFIG,
            ".yaml": ResourceType.CONFIG,
            ".yml": ResourceType.CONFIG,
        }
        return mapping.get(ext, ResourceType.BINARY)

    @staticmethod
    def _serialize_entry_header(entry: ResourceEntry) -> bytes:
        """Serialize entry header for bundle format."""
        path_encoded = entry.path.encode("utf-8")
        header = struct.pack(
            "<IHH",
            len(path_encoded),
            entry.compressed_size_bytes,
            entry.size_bytes,
        )
        return header + path_encoded


# ---------------------------------------------------------------------------
# Audio conversion helper
# ---------------------------------------------------------------------------

class AudioConverter:
    """Convert audio between formats with optional compression."""

    @staticmethod
    def convert_wav_to_ogg(wav_path: Path, ogg_path: Path, quality: float = 0.7) -> None:
        """Convert WAV to OGG Vorbis."""
        try:
            import soundfile as sf  # type: ignore
            data, sample_rate = sf.read(wav_path)
            sf.write(ogg_path, data, sample_rate, format="OGG", subtype="VORBIS")
        except ImportError:
            raise ImportError("soundfile required for audio conversion")

    @staticmethod
    def downsample_audio(
        wav_path: Path,
        output_path: Path,
        target_sample_rate: int = 16000,
    ) -> None:
        """Downsample audio to target sample rate."""
        try:
            import soundfile as sf  # type: ignore
            from scipy.signal import resample  # type: ignore
            data, sr = sf.read(wav_path)
            if sr != target_sample_rate:
                new_len = int(len(data) * target_sample_rate / sr)
                data = resample(data, new_len)
            sf.write(output_path, data, target_sample_rate)
        except ImportError:
            raise ImportError("soundfile + scipy required for audio downsampling")
