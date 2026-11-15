"""Comprueba la conservación de fallos y la detección de regresiones de cobertura."""

import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(filename))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


validation = load('validation', 'validate-system.py')
coverage = load('coverage_summary', 'summarize-coverage.py')
BASELINE = '| src/CCNFT.sol | 100.00% (122/122) | 100.00% (116/116) | 97.53% (79/81) | 100.00% (25/25) |'


class ValidationToolsTest(unittest.TestCase):
    def test_coverage_accepts_baseline_and_improvements(self):
        coverage.check_baseline(BASELINE)
        coverage.check_baseline(BASELINE.replace('(79/81)', '(81/81)'))

    def test_coverage_rejects_regressions_and_changed_branch_total(self):
        for old, new in [('122/122', '121/122'), ('116/116', '115/116'),
                         ('25/25', '24/25'), ('79/81', '78/81'), ('79/81', '80/82')]:
            with self.subTest(new=new), self.assertRaises(ValueError):
                coverage.check_baseline(BASELINE.replace(old, new))

    def test_coverage_rejects_missing_malformed_or_duplicate_rows(self):
        for report in ['', '| src/CCNFT.sol | 100% |', BASELINE + '\n' + BASELINE]:
            with self.subTest(report=report), self.assertRaises(ValueError):
                coverage.check_baseline(report)

    def test_failed_command_preserves_both_streams_and_allows_next_check(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            failed = validation.run_check(output, 'failure', [sys.executable, '-c',
                'import sys; print("diagnostic"); print("error", file=sys.stderr); sys.exit(7)'])
            passed = validation.run_check(output, 'next', [sys.executable, '-c', 'print("next check")'])
            self.assertEqual(failed['exit_code'], 7)
            self.assertEqual(failed['status'], 'failed')
            self.assertIn('diagnostic', (output / failed['log']).read_text())
            self.assertIn('error', (output / failed['log']).read_text())
            self.assertEqual(passed['exit_code'], 0)

    def test_missing_binary_is_a_recorded_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            result = validation.run_check(Path(directory), 'missing', [str(Path(directory) / 'absent')])
            self.assertEqual(result['exit_code'], 127)
            self.assertIn('FileNotFoundError', (Path(directory) / result['log']).read_text())

    def test_existing_evidence_directory_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            sentinel = Path(directory) / 'result.json'
            sentinel.write_text('historical evidence')
            result = subprocess.run([sys.executable, str(Path(validation.__file__)), '--output-dir', directory],
                                    capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(sentinel.read_text(), 'historical evidence')


if __name__ == '__main__':
    unittest.main()
