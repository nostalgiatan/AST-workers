"""Install ast-go CLI tool.

This module provides the `ast-workers-mcp install-go` command to compile
and install the Go AST manipulation CLI from source.

Requirements:
    - Go 1.18+ (for generic support)
"""

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

# Minimum Go version required (1.18 for generics)
MIN_GO_VERSION = (1, 18)


def get_package_dir() -> Path:
    """Get the directory where this package is installed."""
    return Path(__file__).parent


def get_go_source_dir() -> Path:
    """Get the directory containing ast-go source code."""
    package_dir = get_package_dir()
    return package_dir.parent / "core" / "go"


def parse_go_version(version_output: str) -> tuple[int, int] | None:
    """Parse Go version from 'go version' output.

    Examples:
        go version go1.21.0 linux/amd64 -> (1, 21)
        go version go1.18.10 darwin/arm64 -> (1, 18)
    """
    match = re.search(r"go(\d+)\.(\d+)", version_output)
    if match:
        return (int(match.group(1)), int(match.group(2)))
    return None


def check_go_toolchain() -> tuple[bool, str, tuple[int, int] | None]:
    """Check if Go toolchain is available and meets minimum version.

    Returns:
        (success, message, version_tuple)
    """
    # Check if go command exists
    go_cmd = shutil.which("go")

    if not go_cmd:
        return (
            False,
            "Go toolchain not found.\n"
            "\n"
            "Please install Go 1.18+ from:\n"
            "  https://go.dev/dl/\n"
            "\n"
            "Or use your system package manager:\n"
            "  Ubuntu/Debian: sudo apt install golang-go\n"
            "  macOS: brew install go\n"
            "  Windows: winget install GoLang.Go",
            None,
        )

    # Check Go version
    result = subprocess.run(
        ["go", "version"],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        return (
            False,
            f"Go is installed but 'go version' failed:\n{result.stderr}",
            None,
        )

    version = parse_go_version(result.stdout)

    if not version:
        return (
            False,
            f"Could not parse Go version from: {result.stdout.strip()}",
            None,
        )

    # Check minimum version
    if version < MIN_GO_VERSION:
        return (
            False,
            f"Go {version[0]}.{version[1]} is installed, but Go {MIN_GO_VERSION[0]}.{MIN_GO_VERSION[1]}+ is required.\n"
            f"Please upgrade Go from https://go.dev/dl/",
            version,
        )

    return (True, "", version)


def get_installed_version() -> Path | None:
    """Check if ast-go is already installed.

    Returns:
        Path to installed binary, or None if not installed.
    """
    binary_path = Path.home() / ".local" / "bin" / "ast-go"

    if binary_path.exists() and os.access(binary_path, os.X_OK):
        return binary_path

    # Also check if it's in PATH
    in_path = shutil.which("ast-go")
    if in_path:
        return Path(in_path)

    return None


def install_go() -> int:
    """Install ast-go CLI tool by compiling from source.

    Returns:
        0 on success, non-zero on failure.
    """
    print("Checking Go toolchain...")

    # Check Go toolchain
    ok, msg, go_version = check_go_toolchain()

    if not ok:
        print(f"\nError: {msg}", file=sys.stderr)
        return 1

    # go_version is guaranteed to be non-None when ok is True
    if go_version:
        print(f"  Found Go {go_version[0]}.{go_version[1]}")

    # Check source directory
    go_src_dir = get_go_source_dir()

    if not go_src_dir.exists():
        print(f"\nError: ast-go source not found at {go_src_dir}", file=sys.stderr)
        print("Make sure you installed ast-workers-mcp from source.", file=sys.stderr)
        return 1

    # Check existing installation
    existing = get_installed_version()
    if existing:
        print(f"\nast-go is already installed at: {existing}")
        print("Reinstalling...")

    # Prepare install directory
    install_dir = Path.home() / ".local" / "bin"
    install_dir.mkdir(parents=True, exist_ok=True)

    binary_path = install_dir / "ast-go"

    print("\nCompiling ast-go...")
    print(f"  Source: {go_src_dir}")
    print(f"  Output: {binary_path}")

    # Get version from pyproject.toml or use default
    cli_version = "0.1.7"

    # Compile with optimizations and version
    result = subprocess.run(
        ["go", "build",
         f"-ldflags=-s -w -X cmd.Version={cli_version}",
         "-o", str(binary_path), "."],
        cwd=str(go_src_dir),
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        print("\nError: Failed to compile ast-go:", file=sys.stderr)
        print(result.stderr, file=sys.stderr)
        return 1

    # Make executable
    binary_path.chmod(0o755)

    # Verify installation
    verify_result = subprocess.run(
        [str(binary_path), "version"],
        capture_output=True,
        text=True,
    )

    if verify_result.returncode != 0:
        print("\nWarning: Installation succeeded but verification failed", file=sys.stderr)
    else:
        print(f"  Verified: {verify_result.stdout.strip()}")

    print(f"""
Installation complete!

  Binary: {binary_path}

Make sure ~/.local/bin is in your PATH:
    export PATH="$HOME/.local/bin:$PATH"

Test with:
    ast-go help
    ast-go list-functions -m yourfile.go
""")

    return 0


def uninstall_go() -> int:
    """Uninstall ast-go CLI tool.

    Returns:
        0 on success, non-zero on failure.
    """
    binary_path = Path.home() / ".local" / "bin" / "ast-go"

    removed = False

    if binary_path.exists():
        binary_path.unlink()
        print(f"Removed: {binary_path}")
        removed = True

    # Check if installed elsewhere
    in_path = shutil.which("ast-go")
    if in_path and in_path != str(binary_path):
        print(f"\nNote: ast-go also found at: {in_path}")
        print("This may need to be removed manually.")

    if removed:
        print("\nast-go uninstalled.")
    else:
        print("ast-go is not installed at ~/.local/bin/ast-go")

    return 0


def check_command() -> int:
    """Check installation status and requirements."""
    print("Checking ast-go installation status...\n")

    # Check Go toolchain
    ok, msg, go_version = check_go_toolchain()

    print("Go toolchain:")
    if ok and go_version:
        print(f"  [OK] Go {go_version[0]}.{go_version[1]}")
    else:
        print(f"  [MISSING] {msg.split(chr(10))[0]}")
        if "1.18+" in msg:
            print(f"         Requires Go {MIN_GO_VERSION[0]}.{MIN_GO_VERSION[1]}+")

    # Check installation
    print("\nast-go installation:")
    installed = get_installed_version()
    if installed:
        print(f"  [OK] {installed}")
        # Check version
        result = subprocess.run(
            [str(installed), "version"],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            print(f"       {result.stdout.strip()}")
    else:
        print("  [NOT INSTALLED]")
        if ok:
            print("\n  Run 'ast-workers-mcp install-go install' to install")

    return 0


def main():
    """CLI entry point."""
    if len(sys.argv) < 2:
        command = "install"
    else:
        command = sys.argv[1]

    if command == "install":
        return install_go()
    elif command == "uninstall":
        return uninstall_go()
    elif command == "check":
        return check_command()
    elif command in ["-h", "--help", "help"]:
        print("ast-workers-mcp install-go - Install ast-go CLI tool")
        print()
        print("Usage: ast-workers-mcp install-go [command]")
        print()
        print("Commands:")
        print("  install    Install ast-go CLI (default, requires Go toolchain)")
        print("  uninstall  Remove ast-go CLI")
        print("  check      Check installation status and requirements")
        print()
        print("Requirements:")
        print(f"  Go {MIN_GO_VERSION[0]}.{MIN_GO_VERSION[1]}+ (for generic type support)")
        return 0
    else:
        print(f"Unknown command: {command}", file=sys.stderr)
        print("Run 'ast-workers-mcp install-go --help' for usage.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
