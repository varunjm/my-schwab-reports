#!/usr/bin/env python3
"""
Simple test runner script for Schwab Reports project.

This script provides easy commands to run different types of tests
and code quality checks.
"""

import argparse
import subprocess
import sys
from pathlib import Path


def run_command(command: list[str], description: str) -> bool:
    """Run a command and return success status."""
    print(f"\n🔄 {description}...")
    print(f"Command: {' '.join(command)}")

    try:
        result = subprocess.run(command, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully")
        if result.stdout:
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed")
        if e.stdout:
            print("STDOUT:", e.stdout)
        if e.stderr:
            print("STDERR:", e.stderr)
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Run tests and code quality checks for Schwab Reports"
    )
    parser.add_argument(
        "--test-type",
        choices=["unit", "integration", "all", "coverage"],
        default="all",
        help="Type of tests to run",
    )
    parser.add_argument(
        "--quality",
        action="store_true",
        help="Run code quality checks (format, lint, type check)",
    )
    parser.add_argument(
        "--install-deps",
        action="store_true",
        help="Install development dependencies first",
    )

    args = parser.parse_args()

    # Change to project directory
    project_dir = Path(__file__).parent
    print(f"📁 Working directory: {project_dir}")

    success = True

    # Install dependencies if requested
    if args.install_deps:
        success &= run_command(
            ["pip", "install", "-r", "requirements-dev.txt"],
            "Installing development dependencies",
        )

    # Run tests based on type
    if args.test_type == "unit":
        success &= run_command(
            [
                "python",
                "-m",
                "pytest",
                "tests/test_config.py",
                "tests/test_data_processing.py",
                "-v",
            ],
            "Running unit tests",
        )
    elif args.test_type == "integration":
        success &= run_command(
            ["python", "-m", "pytest", "tests/test_integration.py", "-v"],
            "Running integration tests",
        )
    elif args.test_type == "coverage":
        success &= run_command(
            [
                "python",
                "-m",
                "pytest",
                "--cov=schwab_reports",
                "--cov-report=html",
                "--cov-report=term",
            ],
            "Running tests with coverage",
        )
    else:  # all
        success &= run_command(["python", "-m", "pytest", "-v"], "Running all tests")

    # Run code quality checks if requested
    if args.quality:
        print("\n🔧 Running code quality checks...")

        # Format check
        success &= run_command(
            ["python", "-m", "black", "--check", "schwab_reports.py"],
            "Checking code formatting with Black",
        )

        # Import sorting check
        success &= run_command(
            ["python", "-m", "isort", "--check-only", "schwab_reports.py"],
            "Checking import sorting with isort",
        )

        # Linting
        success &= run_command(
            ["python", "-m", "ruff", "check", "schwab_reports.py"],
            "Linting code with Ruff",
        )

        # Type checking
        success &= run_command(
            ["python", "-m", "mypy", "schwab_reports.py", "--ignore-missing-imports"],
            "Type checking with mypy",
        )

    # Summary
    if success:
        print("\n🎉 All checks passed successfully!")
        return 0
    else:
        print("\n💥 Some checks failed. Please review the output above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
