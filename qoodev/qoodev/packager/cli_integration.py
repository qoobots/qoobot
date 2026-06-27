"""打包器 CLI 集成 — qoo package 命令"""

from pathlib import Path
from typer import Typer, Option, Argument
from typing import Optional

from qoodev.packager.package_format import (
    PackageBuilder,
    PackageReader,
    PackageValidator,
    SkillCategory,
    PackageManifest,
)
from qoodev.packager.dependency import DependencyResolver, ConflictError
from qoodev.packager.signing import CodeSigner, SignatureVerifier, SigningConfig, SigningAlgorithm

app = Typer(name="package", help="Package and distribute skills (.qooskills)")


@app.command("build")
def build(
    project_dir: str = Argument(".", help="Project root directory"),
    output: Optional[str] = Option(None, "--output", "-o", help="Output directory"),
    include_cpp: bool = Option(False, "--cpp", help="Include C++ code"),
    include_models: bool = Option(False, "--models", help="Include compiled models"),
    skip_resources: bool = Option(False, "--no-resources", help="Skip resource files"),
    compression: int = Option(8, "--compression", help="ZIP compression level (0-9)"),
):
    """Build a .qooskills package from the current project"""
    project_path = Path(project_dir).resolve()
    output_path = Path(output) if output else None

    builder = PackageBuilder(project_path, output_path)

    try:
        manifest = builder.load_manifest()
        print(f"📦 Building: {manifest.name} v{manifest.version}")
        print(f"   Category: {manifest.category.value}")
        print(f"   Runtime:  {manifest.runtime.value}")

        pkg_path = builder.build(
            include_cpp=include_cpp,
            include_models=include_models,
            include_resources=not skip_resources,
            compression=compression,
        )

        print(f"\n📦 Package: {pkg_path}")
        return pkg_path
    except FileNotFoundError as e:
        print(f"❌ Error: {e}")
        raise SystemExit(1)


@app.command("inspect")
def inspect(
    package_path: str = Argument(..., help="Path to .qooskills file"),
    list_files: bool = Option(False, "--files", "-f", help="List all files in package"),
    verify: bool = Option(False, "--verify", "-v", help="Verify checksums"),
):
    """Inspect a .qooskills package"""
    pkg = Path(package_path)
    if not pkg.exists():
        print(f"❌ Package not found: {package_path}")
        raise SystemExit(1)

    reader = PackageReader(pkg)

    try:
        manifest = reader.read_manifest()
    except Exception as e:
        print(f"❌ Invalid package: {e}")
        raise SystemExit(1)

    print(f"📦 {manifest.display_name}")
    print(f"   ID:      {manifest.name}")
    print(f"   Version: {manifest.version}")
    print(f"   Author:  {manifest.author} <{manifest.author_email}>")
    print(f"   Runtime: {manifest.runtime.value}")
    print(f"   Entry:   {manifest.entry_point}")
    print(f"   License: {manifest.license}")
    print()

    if manifest.dependencies:
        print("Dependencies:")
        for dep in manifest.dependencies:
            print(f"   - {dep['name']} {dep.get('version', '*')}")
    if manifest.python_dependencies:
        print("Python deps:")
        for dep in manifest.python_dependencies:
            print(f"   - {dep}")
    if manifest.permissions:
        print("Permissions:")
        for perm in manifest.permissions:
            print(f"   - {perm}")

    if list_files:
        print("\nFiles:")
        for name in sorted(reader.list_files()):
            print(f"   {name}")

    if verify:
        print()
        reader.verify_checksums()


@app.command("validate")
def validate(
    package_path: str = Argument(..., help="Path to .qooskills file"),
):
    """Validate a .qooskills package"""
    pkg = Path(package_path)
    result = PackageValidator.full_validate(pkg)

    if result["errors"]:
        print("❌ Errors:")
        for e in result["errors"]:
            print(f"   - {e}")

    if result["warnings"]:
        print("⚠️  Warnings:")
        for w in result["warnings"]:
            print(f"   - {w}")

    if result["manifest"]:
        print(f"\n📋 Manifest: {result['manifest']['name']} v{result['manifest']['version']}")

    if not result["errors"] and not result["warnings"]:
        print("✅ Package is valid")


@app.command("extract")
def extract(
    package_path: str = Argument(..., help="Path to .qooskills file"),
    output_dir: str = Argument("./extracted", help="Output directory"),
):
    """Extract a .qooskills package"""
    pkg = Path(package_path)
    out = Path(output_dir)

    reader = PackageReader(pkg)
    extracted = reader.extract(out)
    print(f"✅ Extracted to: {extracted}")


@app.command("sign")
def sign(
    package_path: str = Argument(..., help="Path to .qooskills file"),
    key_path: str = Option(..., "--key", "-k", help="Private key file path"),
    cert_path: str = Option(..., "--cert", "-c", help="Certificate file path"),
    algorithm: str = Option("ed25519", "--algorithm", "-a", help="Signing algorithm"),
):
    """Sign a .qooskills package"""
    config = SigningConfig(
        key_path=Path(key_path),
        cert_path=Path(cert_path),
        algorithm=SigningAlgorithm(algorithm),
    )

    signer = CodeSigner(config)
    signer.load_certificate()
    signer.sign_package(Path(package_path))


@app.command("verify")
def verify(
    package_path: str = Argument(..., help="Path to .qooskills file"),
    cert_path: Optional[str] = Option(None, "--cert", "-c", help="Trusted certificate path"),
):
    """Verify a signed .qooskills package"""
    from qoodev.packager.signing import CertificateInfo
    import json

    trusted = []
    if cert_path:
        with open(cert_path, "r") as f:
            trusted.append(CertificateInfo.from_dict(json.load(f)))

    verifier = SignatureVerifier(trusted)
    ok, msg = verifier.verify(Path(package_path))
    print(msg)
    if not ok:
        raise SystemExit(1)


@app.command("resolve")
def resolve(
    project_dir: str = Argument(".", help="Project root directory"),
    lockfile: Optional[str] = Option(None, "--lock", "-l", help="Output lockfile path"),
):
    """Resolve dependencies for a project"""
    project_path = Path(project_dir).resolve()

    # 加载 manifest
    manifest_path = project_path / "qooskills.toml"
    if not manifest_path.exists():
        manifest_path = project_path / "manifest.json"
    if not manifest_path.exists():
        print("❌ No manifest found")
        raise SystemExit(1)

    builder = PackageBuilder(project_path)
    manifest = builder.load_manifest(manifest_path)

    resolver = DependencyResolver()
    try:
        graph = resolver.resolve(manifest.dependencies, manifest.python_dependencies)

        print("📊 Dependency Graph:")
        for name in graph.topological_order():
            node = graph.nodes[name]
            print(f"   {name} == {node.version} (via {node.source})")

        if lockfile:
            resolver.generate_lockfile(graph, Path(lockfile))

    except ConflictError as e:
        print(f"❌ {e}")
        raise SystemExit(1)


@app.command("generate-keypair")
def generate_keypair(
    output_dir: str = Option("./keys", "--output", "-o", help="Output directory"),
    algorithm: str = Option("ed25519", "--algorithm", "-a", help="Key algorithm"),
):
    """Generate a developer keypair for signing"""
    import json
    from qoodev.packager.signing import CertificateInfo

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    private_key, public_key = CodeSigner.generate_keypair(SigningAlgorithm(algorithm))

    import base64
    # 保存私钥
    priv_path = out / "developer.key"
    with open(priv_path, "wb") as f:
        f.write(private_key)
    os.chmod(priv_path, 0o600)  # 仅所有者可读写

    # 生成证书
    cert = CertificateInfo(
        developer_id=f"dev_{hashlib.sha256(public_key).hexdigest()[:16]}",
        developer_name="Developer",
        public_key_pem=base64.b64encode(public_key).decode("ascii"),
        algorithm=SigningAlgorithm(algorithm),
        issued_at=datetime.utcnow().isoformat(),
        expires_at=(datetime.utcnow() + timedelta(days=365)).isoformat(),
    )

    cert_path = out / "developer.cert"
    with open(cert_path, "w") as f:
        json.dump(cert.to_dict(), f, indent=2)

    print(f"✅ Keypair generated:")
    print(f"   Private key: {priv_path}")
    print(f"   Certificate: {cert_path}")
    print(f"   Developer ID: {cert.developer_id}")


# 注册到主 CLI
def register_packager_commands(main_app):
    main_app.add_typer(app, name="package", help="Package and distribute skills")
