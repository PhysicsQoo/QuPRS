#!/usr/bin/env python3
"""Offline synthetic-fixture tests; never run CodSpeed or macOS host commands."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).with_name('qoo13_mac_diagnostics.py')
spec = importlib.util.spec_from_file_location('qoo13_mac_diagnostics', SCRIPT)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class DiagnosticTests(unittest.TestCase):
    def test_vm_stat_page_parsing(self):
        r = m.parse_vm_stat('Mach Virtual Memory Statistics: (page size of 16384 bytes)\n'
                            'Swapins: 1,234.\nSwapouts: 2,567.\nPages free: 123.\n')
        self.assertEqual(r['page_size_bytes'], 16384)
        self.assertEqual(r['swapins_pages'], 1234)
        self.assertEqual(r['swapouts_pages'], 2567)

    def test_process_cpu_and_idle(self):
        p = m.parse_processes('42 104.9 /usr/libexec/backupd\n11 12.5 /bin/python\n')
        self.assertEqual(p[0]['command_name'], 'backupd')
        self.assertEqual(p[0]['cpu_pct'], 104.9)
        self.assertEqual(m.extract_cpu_idle('CPU usage: 7.6% user, 12.5% sys, 79.9% idle'), 79.9)

    def test_bounded_warning_scan_head_and_tail(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            log = root / 'huge.log'
            with log.open('w') as out:
                out.write('Warning: Failed writing environment metadata token=topsecret\n')
                out.write('safe\n' * 450_000)
                out.write('Warning: Cannot write metadata authorization: bearer-secret\n')
            report = m.scan_evidence(root)
            self.assertTrue(report['partial_scan'])
            warnings = report['warnings']
            self.assertGreaterEqual(len(warnings), 2)
            self.assertTrue(all('metadata' in x['redacted_excerpt'] for x in warnings))
            self.assertNotIn('topsecret', json.dumps(warnings))
            self.assertIsNone(warnings[-1]['line'])
            self.assertTrue(all(x['kind'] == 'metadata_or_environment' for x in warnings))

    def test_scan_no_symlink_and_json_keys(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root/'summary.json').write_text('{"event": "local", "run": 5}')
            (root/'outside.log').symlink_to(root/'summary.json')
            r = m.scan_evidence(root)
            self.assertEqual(r['json_top_level_keys']['summary.json'], ['event', 'run'])
            self.assertEqual(r['files_scanned'], 1)

    def test_swap_window_and_contention(self):
        a = {'monotonic_elapsed_s': 100, 'backupd_cpu_pct': 0,
             'load_average_1_5_15': [2, 3, 4],
             'thermal_signal_available': False,
             'vm_stat': {'page_size_bytes': 16384, 'swapins_pages': 100, 'swapouts_pages': 200}}
        b = {'monotonic_elapsed_s': 120, 'backupd_cpu_pct': 104.9,
             'load_average_1_5_15': [4, 3, 4],
             'thermal_signal_available': False,
             'vm_stat': {'page_size_bytes': 16384, 'swapins_pages': 356, 'swapouts_pages': 200}}
        result = m.summarize_window([a, b])
        self.assertEqual(result['swapins_delta_mib'], 4.0)
        self.assertEqual(result['swapins_rate_mib_s'], 0.2)
        self.assertEqual(result['contention_preflight'], 'ABSTAIN_BACKUPD_OVER_100_PCT')
        self.assertTrue(result['thermal_unavailable'])

    def test_scan_only_outputs_and_no_host_commands(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            evidence = root / 'evidence'
            evidence.mkdir()
            (evidence/'test.log').write_text('Warning: failed to save environment metadata\n')
            report = root/'report.json'
            completed = subprocess.run(
                [sys.executable, str(SCRIPT), '--scan-only', '--evidence', str(evidence),
                 '--output', str(report)], capture_output=True, text=True, check=True)
            self.assertIn('NO_BENCHMARK', completed.stdout)
            payload = json.loads(report.read_text())
            self.assertEqual(payload['sample_window']['status'], 'NOT_SAMPLED')
            self.assertEqual(len(payload['samples']), 0)
            self.assertEqual(len(payload['evidence_scan']['warnings']), 1)
            duplicate = subprocess.run([sys.executable, str(SCRIPT), '--scan-only',
                                        '--evidence', str(evidence), '--output', str(report)],
                                       capture_output=True, text=True)
            self.assertNotEqual(duplicate.returncode, 0)
            self.assertIn('refusing to overwrite', duplicate.stderr)
            inside = subprocess.run([sys.executable, str(SCRIPT), '--scan-only',
                                     '--evidence', str(evidence),
                                     '--output', str(evidence/'invalid.json')],
                                    capture_output=True, text=True)
            self.assertNotEqual(inside.returncode, 0)
            self.assertIn('outside the preserved evidence directory', inside.stderr)

    def test_thermal_note_is_not_thermal_data(self):
        note = ('Note: No thermal warning level has been recorded\n'
                'Note: No performance warning level has been recorded\n'
                'Note: No CPU power status has been recorded\n')
        self.assertEqual(m.parse_thermal_metrics(note)['status'],
                         'NO_NUMERIC_THERMAL_OR_POWER_LIMIT_DATA')
        self.assertEqual(m.parse_thermal_metrics(note)['metrics'], {})
        d = m.parse_thermal_metrics('CPU_Speed_Limit = 80\nCPU_Scheduler_Limit = 95\n')
        self.assertEqual(d['metrics']['CPU_Speed_Limit'], 80.0)
        self.assertIn('NOT_THERMAL_CERTIFICATION', d['status'])
        self.assertEqual(m.parse_thermal_metrics(note, 'failed')['status'], 'COMMAND_UNAVAILABLE')

    def test_low_idle_abstains_even_if_backupd_absent(self):
        samples = [
            {'backupd_cpu_pct': 0, 'load_average_1_5_15': [1, 2, 3],
             'thermal_signal_available': False, 'cpu_idle_pct': idle,
             'monotonic_elapsed_s': 100 + 5 * k,
             'vm_stat': {'page_size_bytes': 16384, 'swapins_pages': k, 'swapouts_pages': 0}}
            for k, idle in enumerate([61.89, 40.36, 45.20, 48.85, 55.0, 56.0, 60.0])
        ]
        r = m.summarize_window(samples)
        self.assertEqual(r['cpu_idle_below_50_pct_count'], 3)
        self.assertEqual(r['min_cpu_idle_pct'], 40.36)
        self.assertEqual(r['contention_preflight'], 'ABSTAIN_CPU_IDLE_BELOW_50_PCT')
        self.assertTrue(r['thermal_unavailable'])

    def test_profile_folder_inspection_is_read_only(self):
        self.assertEqual(m.inspect_profile_folder(None)['status'], 'NOT_PROVIDED')
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'environment-123.json').write_text('{"python": {"version": "3.12"}}')
            (root / 'environment.json').write_text('not-json')
            result = m.inspect_profile_folder(root)
            self.assertEqual(result['root_cause'], 'UNVERIFIED')
            by_name = {x['name']: x for x in result['environment_files']}
            self.assertEqual(by_name['environment.json']['status'], 'UNREADABLE_OR_BAD_JSON')
            self.assertEqual(by_name['environment-123.json']['top_level_keys'], ['python'])
            self.assertEqual(m.inspect_profile_folder(root / 'absent')['status'],
                             'NOT_A_PRESERVED_DIRECTORY')
            (root/'link').symlink_to(root)
            self.assertEqual(m.inspect_profile_folder(root/'link')['status'], 'SYMLINK_REFUSED')

    def test_environment_warning_classification(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root/'mac.log').write_text('[ERROR] instrument-hooks: failed to write environment.json\n'
                                        'RuntimeWarning: Failed to write environment data\n')
            r = m.scan_evidence(root)
            self.assertEqual(r['codspeed_environment_write'],
                             'ERROR_OBSERVED_CAUSE_UNDETERMINED')
            self.assertEqual(len(r['warnings']), 2)


    def test_precision_contract_not_claimed(self):
        with tempfile.TemporaryDirectory() as folder:
            result = subprocess.run([sys.executable, str(SCRIPT), '--scan-only',
                                     '--evidence', folder], capture_output=True, text=True,
                                    check=True)
            data = json.loads(result.stdout)
            self.assertEqual(data['interpretation']['local_gpmc_arithmetic_precision'], 'PRECISION_UNVERIFIED')
            self.assertEqual(data['interpretation']['performance'], 'PERFORMANCE_UNQUALIFIED')


if __name__ == '__main__':
    unittest.main(verbosity=2)
