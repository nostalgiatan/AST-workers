"""Install ast-ts CLI tool.

This module provides the `ast-workers-mcp install-ts` command to install
the bundled TypeScript AST manipulation CLI.
"""

import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path


def get_package_dir() -> Path:
    """Get the directory where this package is installed."""
    return Path(__file__).parent


def get_install_dir() -> Path:
    """Get the installation directory for ast-ts."""
    # Install to user's local bin or a dedicated directory
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", "~"))
        return base / "ast-workers" / "ast-ts"
    else:
        # Use ~/.local/share/ast-workers/ast-ts on Unix
        base = Path.home() / ".local" / "share"
        return base / "ast-workers" / "ast-ts"


def check_node_npm() -> tuple[bool, str]:
    """Check if Node.js and npm are available."""
    node = shutil.which("node")
    npm = shutil.which("npm")
    
    if not node:
        return False, "Node.js not found. Please install Node.js first."
    if not npm:
        return False, "npm not found. Please install npm first."
    
    return True, ""


def install_ts() -> int:
    """Install ast-ts CLI tool.
    
    Returns:
        0 on success, non-zero on failure.
    """
    # Check Node.js and npm
    ok, msg = check_node_npm()
    if not ok:
        print(f"Error: {msg}", file=sys.stderr)
        return 1
    
    # Get paths
    package_dir = get_package_dir()
    tarball = package_dir / "ast-ts-dist.tar.gz"
    
    if not tarball.exists():
        print(f"Error: ast-ts dist not found at {tarball}", file=sys.stderr)
        return 1
    
    install_dir = get_install_dir()
    
    print(f"Installing ast-ts to {install_dir}...")
    
    # Create install directory
    install_dir.mkdir(parents=True, exist_ok=True)
    
    # Extract tarball
    with tempfile.TemporaryDirectory() as tmpdir:
        # Extract to temp directory first
        with tarfile.open(tarball, "r:gz") as tar:
            tar.extractall(tmpdir, filter='data')
        
        # Move dist to install directory
        dist_src = Path(tmpdir) / "dist"
        if install_dir.exists():
            shutil.rmtree(install_dir)
        shutil.move(str(dist_src), str(install_dir))
    
    # Create package.json for the installed ast-ts
    package_json = install_dir.parent / "package.json"
    package_json.parent.mkdir(parents=True, exist_ok=True)
    package_json.write_text('''{
  "name": "ast-workers-ts-installed",
  "version": "0.1.0",
  "type": "module",
  "bin": {
    "ast-ts": "ast-ts/cli.js"
  },
  "dependencies": {
    "commander": "^14.0.3",
    "ts-morph": "^27.0.2"
  }
}
''')
    
    # Install dependencies
    print("Installing dependencies...")
    result = subprocess.run(
        ["npm", "install", "--production"],
        cwd=str(install_dir.parent),
        capture_output=True,
        text=True,
    )
    
    if result.returncode != 0:
        print(f"Warning: npm install had issues: {result.stderr}", file=sys.stderr)
    
    # Create symlink or add to PATH instructions
    cli_js = install_dir / "cli.js"
    bin_dir = Path.home() / ".local" / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    
    # Create a wrapper script
    wrapper = bin_dir / "ast-ts"
    wrapper.write_text(f'''#!/bin/bash
exec node "{cli_js}" "$@"
''')
    wrapper.chmod(0o755)
    
    print(f"""
✓ ast-ts installed successfully!

Location: {install_dir}
CLI: {wrapper}

Make sure ~/.local/bin is in your PATH:
    export PATH="$HOME/.local/bin:$PATH"

You can add this to your ~/.bashrc or ~/.zshrc.

Test with:
    ast-ts --help
""")
    
    return 0


def uninstall_ts() -> int:
    """Uninstall ast-ts CLI tool.
    
    Returns:
        0 on success, non-zero on failure.
    """
    install_dir = get_install_dir()
    bin_wrapper = Path.home() / ".local" / "bin" / "ast-ts"
    package_json = install_dir.parent / "package.json"
    node_modules = install_dir.parent / "node_modules"
    
    removed = []
    
    if install_dir.exists():
        shutil.rmtree(install_dir)
        removed.append(str(install_dir))
    
    if bin_wrapper.exists():
        bin_wrapper.unlink()
        removed.append(str(bin_wrapper))
    
    if package_json.exists():
        package_json.unlink()
        removed.append(str(package_json))
    
    if node_modules.exists():
        shutil.rmtree(node_modules)
        removed.append(str(node_modules))
    
    if removed:
        print("Removed:")
        for path in removed:
            print(f"  - {path}")
        print("\n✓ ast-ts uninstalled.")
    else:
        print("ast-ts is not installed.")
    
    return 0


def main():
    """CLI entry point."""
    if len(sys.argv) < 2:
        print("Usage: ast-workers-mcp install-ts [install|uninstall]")
        print("\nCommands:")
        print("  install    Install ast-ts CLI (default)")
        print("  uninstall  Remove ast-ts CLI")
        return 1
    
    command = sys.argv[1]
    
    if command == "install":
        return install_ts()
    elif command == "uninstall":
        return uninstall_ts()
    else:
        print(f"Unknown command: {command}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
