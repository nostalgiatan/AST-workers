"""Install ast-go CLI tool.

This module provides the `ast-workers-mcp install-go` command to compile
and install the Go AST manipulation CLI from source.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path


def get_package_dir() -> Path:
    """Get the directory where this package is installed."""
    return Path(__file__).parent


def get_go_source_dir() -> Path:
    """Get the directory containing ast-go source code."""
    # ast-go source is in core/go relative to the package
    package_dir = get_package_dir()
    # Go up from ast_mcp to project root, then into core/go
    return package_dir.parent / "core" / "go"


def check_go() -> tuple[bool, str]:
    """Check if Go toolchain is available."""
    go = shutil.which("go")
    
    if not go:
        return False, "Go not found. Please install Go from https://go.dev/dl/"
    
    # Check Go version
    result = subprocess.run(
        ["go", "version"],
        capture_output=True,
        text=True,
    )
    
    if result.returncode != 0:
        return False, "Go is installed but 'go version' failed."
    
    return True, ""


def install_go() -> int:
    """Install ast-go CLI tool by compiling from source.
    
    Returns:
        0 on success, non-zero on failure.
    """
    # Check Go toolchain
    ok, msg = check_go()
    if not ok:
        print(f"Error: {msg}", file=sys.stderr)
        return 1
    
    # Get paths
    go_src_dir = get_go_source_dir()
    
    if not go_src_dir.exists():
        print(f"Error: ast-go source not found at {go_src_dir}", file=sys.stderr)
        print("Make sure you installed ast-workers-mcp from source.", file=sys.stderr)
        return 1
    
    install_dir = Path.home() / ".local" / "bin"
    install_dir.mkdir(parents=True, exist_ok=True)
    
    binary_path = install_dir / "ast-go"
    
    print(f"Compiling ast-go from {go_src_dir}...")
    print(f"Installing to {binary_path}...")
    
    # Compile
    result = subprocess.run(
        ["go", "build", "-o", str(binary_path), "."],
        cwd=str(go_src_dir),
        capture_output=True,
        text=True,
    )
    
    if result.returncode != 0:
        print(f"Error: Failed to compile ast-go:", file=sys.stderr)
        print(result.stderr, file=sys.stderr)
        return 1
    
    # Make executable
    binary_path.chmod(0o755)
    
    print(f"""
✓ ast-go installed successfully!

CLI: {binary_path}

Make sure ~/.local/bin is in your PATH:
    export PATH="$HOME/.local/bin:$PATH"

You can add this to your ~/.bashrc or ~/.zshrc.

Test with:
    ast-go help
""")
    
    return 0


def uninstall_go() -> int:
    """Uninstall ast-go CLI tool.
    
    Returns:
        0 on success, non-zero on failure.
    """
    binary_path = Path.home() / ".local" / "bin" / "ast-go"
    
    if binary_path.exists():
        binary_path.unlink()
        print(f"Removed: {binary_path}")
        print("\n✓ ast-go uninstalled.")
    else:
        print("ast-go is not installed.")
    
    return 0


def main():
    """CLI entry point."""
    if len(sys.argv) < 2:
        print("Usage: ast-workers-mcp install-go [install|uninstall]")
        print("\nCommands:")
        print("  install    Install ast-go CLI (default, requires Go toolchain)")
        print("  uninstall  Remove ast-go CLI")
        return 1
    
    command = sys.argv[1]
    
    if command == "install":
        return install_go()
    elif command == "uninstall":
        return uninstall_go()
    else:
        print(f"Unknown command: {command}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())