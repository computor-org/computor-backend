#!/usr/bin/env python3
"""
Integration Test Runner

Runs all permission tests in sequence and generates a comprehensive report.
"""

import asyncio
import sys
import subprocess
from pathlib import Path
from datetime import datetime
import json


class IntegrationTestRunner:
    """Orchestrates running all integration tests"""

    def __init__(self):
        self.scripts_dir = Path(__file__).parent
        self.data_dir = self.scripts_dir.parent / "data"
        self.test_scripts = [
            ("Student Permissions", "test_student_permissions.py"),
            ("Tutor Permissions", "test_tutor_permissions.py"),
            ("Lecturer Permissions", "test_lecturer_permissions.py"),
        ]
        self.results = []

    def run_test_script(self, name: str, script_path: Path) -> dict:
        """
        Run a single test script and capture results

        Returns:
            Dict with test results
        """
        print(f"\n{'='*80}")
        print(f"Running: {name}")
        print(f"{'='*80}\n")

        start_time = datetime.now()

        try:
            # Run the script
            result = subprocess.run(
                [sys.executable, str(script_path)],
                cwd=self.scripts_dir,
                capture_output=True,
                text=True,
                timeout=120
            )

            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            # Print output
            print(result.stdout)
            if result.stderr:
                print("STDERR:", result.stderr)

            # Try to load the JSON results
            results_file = self.data_dir / f"{script_path.stem}_results.json"
            test_results = None
            if results_file.exists():
                with open(results_file, 'r') as f:
                    test_results = json.load(f)

            return {
                "name": name,
                "script": script_path.name,
                "exit_code": result.returncode,
                "passed": result.returncode == 0,
                "duration": duration,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "test_results": test_results
            }

        except subprocess.TimeoutExpired:
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            print(f"❌ Test script timed out after {duration}s")
            return {
                "name": name,
                "script": script_path.name,
                "exit_code": -1,
                "passed": False,
                "duration": duration,
                "error": "Timeout"
            }

        except Exception as e:
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            print(f"❌ Error running test: {e}")
            return {
                "name": name,
                "script": script_path.name,
                "exit_code": -1,
                "passed": False,
                "duration": duration,
                "error": str(e)
            }

    def run_all_tests(self):
        """Run all test scripts"""
        print("\n" + "="*80)
        print("INTEGRATION TEST SUITE")
        print("="*80)
        print(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Scripts Directory: {self.scripts_dir}")
        print(f"Data Directory: {self.data_dir}")
        print("="*80)

        # Run each test script
        for name, script_file in self.test_scripts:
            script_path = self.scripts_dir / script_file

            if not script_path.exists():
                print(f"\n❌ Script not found: {script_path}")
                self.results.append({
                    "name": name,
                    "script": script_file,
                    "passed": False,
                    "error": "Script not found"
                })
                continue

            result = self.run_test_script(name, script_path)
            self.results.append(result)

    def print_summary(self):
        """Print a comprehensive summary of all test results"""
        print("\n" + "="*80)
        print("INTEGRATION TEST SUMMARY")
        print("="*80)

        total_scripts = len(self.results)
        passed_scripts = sum(1 for r in self.results if r.get("passed", False))
        failed_scripts = total_scripts - passed_scripts

        # Calculate total test cases
        total_tests = 0
        passed_tests = 0
        failed_tests = 0

        for result in self.results:
            if result.get("test_results"):
                total_tests += result["test_results"].get("total", 0)
                passed_tests += result["test_results"].get("passed", 0)
                failed_tests += result["test_results"].get("failed", 0)

        print(f"\nTest Scripts:")
        print(f"  Total: {total_scripts}")
        print(f"  Passed: {passed_scripts}")
        print(f"  Failed: {failed_scripts}")

        print(f"\nTest Cases:")
        print(f"  Total: {total_tests}")
        print(f"  Passed: {passed_tests} ({100*passed_tests/total_tests if total_tests > 0 else 0:.1f}%)")
        print(f"  Failed: {failed_tests} ({100*failed_tests/total_tests if total_tests > 0 else 0:.1f}%)")

        print(f"\nDetailed Results:")
        for result in self.results:
            status = "✓ PASS" if result.get("passed") else "✗ FAIL"
            duration = result.get("duration", 0)
            print(f"  {status} - {result['name']} ({duration:.1f}s)")

            if result.get("test_results"):
                tr = result["test_results"]
                print(f"         {tr['passed']}/{tr['total']} tests passed")

            if not result.get("passed") and result.get("error"):
                print(f"         Error: {result['error']}")

        print("\n" + "="*80)

        if failed_scripts == 0 and failed_tests == 0:
            print("✓ ALL TESTS PASSED!")
        else:
            print("✗ SOME TESTS FAILED")

        print("="*80 + "\n")

    def save_summary(self):
        """Save a JSON summary of all test results"""
        summary_file = self.data_dir / "test_summary.json"

        summary = {
            "run_time": datetime.now().isoformat(),
            "total_scripts": len(self.results),
            "passed_scripts": sum(1 for r in self.results if r.get("passed", False)),
            "failed_scripts": sum(1 for r in self.results if not r.get("passed", False)),
            "results": self.results
        }

        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)

        print(f"Summary saved to: {summary_file}\n")

    def run(self):
        """Main entry point"""
        self.run_all_tests()
        self.print_summary()
        self.save_summary()

        # Return exit code based on results
        failed = sum(1 for r in self.results if not r.get("passed", False))
        return 0 if failed == 0 else 1


def main():
    """Entry point"""
    runner = IntegrationTestRunner()
    exit_code = runner.run()
    return exit_code


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
