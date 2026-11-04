"""Synthetic, offline QOO-13 admission policy tests. No Mac or CodSpeed invoked."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).with_name('qoo13_p1_admission.py')
spec = importlib.util.spec_from_file_location('qoo13_p1_admission', SCRIPT)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def sample(i, idle=70.0, backup=0.0, process=2.0, thermal=False, swapins=100):
    return dict(monotonic_elapsed_s=100.0 + 5*i, cpu_idle_pct=idle,
                backupd_cpu_pct=backup,
                top_processes=[dict(command_name='python', cpu_pct=process)],
                thermal_signal_available=thermal,
                vm_stat=dict(page_size_bytes=16384, swapins_pages=swapins+i,
                             swapouts_pages=10))


def report(samples):
    return dict(kind=m.SOURCE_KIND, script_version=4, samples=samples,
                sample_window=dict(status='MONITOR_ONLY_NOT_PERFORMANCE_CERTIFICATION',
                                   sample_count=len(samples)))


class TestAdmission(unittest.TestCase):
    def test_real_pilot_pattern_abstains_with_backupd_absent(self):
        idle = [61.89, 40.36, 45.2, 48.85, 55, 56, 60]
        samples = [sample(i, idle=x, swapins=100) for i, x in enumerate(idle)]
        r = m.assess(report(samples))
        self.assertEqual(r['verdict'], 'ABSTAIN')
        self.assertIn('CPU_IDLE_BELOW_50_PCT', r['stop_reasons'])
        self.assertEqual(r['cpu_idle_below_50_count'], 3)
        self.assertIn('THERMAL_TELEMETRY_UNAVAILABLE_OR_INCOMPLETE', r['observations'])
        self.assertFalse(r['authorizes_benchmark'])

    def test_backupd_and_other_heavy_process_abstain(self):
        samples = [sample(i) for i in range(7)]
        samples[1]['backupd_cpu_pct'] = 104.9
        samples[2]['top_processes'][0]['cpu_pct'] = 156.1
        r = m.assess(report(samples))
        self.assertEqual(r['verdict'], 'ABSTAIN')
        self.assertIn('BACKUPD_OVER_100_PCT', r['stop_reasons'])
        self.assertIn('OTHER_SINGLE_PROCESS_OVER_100_PCT', r['stop_reasons'])

    def test_short_window_incomplete(self):
        r = m.assess(report([sample(i) for i in range(4)]))
        self.assertEqual(r['verdict'], 'INCOMPLETE')
        self.assertIn('TOO_FEW_SAMPLES', r['evidence_gaps'])
        self.assertIn('OBSERVATION_WINDOW_TOO_SHORT', r['evidence_gaps'])

    def test_missing_idle_incomplete_not_quiet(self):
        samples = [sample(i) for i in range(7)]
        samples[4]['cpu_idle_pct'] = None
        r = m.assess(report(samples))
        self.assertEqual(r['verdict'], 'INCOMPLETE')
        self.assertIn('CPU_IDLE_MISSING_OR_INVALID', r['evidence_gaps'])

    def test_reset_swap_is_incomplete(self):
        samples = [sample(i) for i in range(7)]
        samples[-1]['vm_stat']['swapins_pages'] = 2
        r = m.assess(report(samples))
        self.assertEqual(r['verdict'], 'INCOMPLETE')
        self.assertIn('SWAPINS_PAGES_MISSING_OR_RESET', r['evidence_gaps'])

    def test_quiet_candidate_never_authorizes_measurement(self):
        r = m.assess(report([sample(i, thermal=True) for i in range(7)]))
        self.assertEqual(r['verdict'], 'QUIET_CANDIDATE_ONLY_NOT_CERTIFIED')
        self.assertFalse(r['authorizes_benchmark'])
        self.assertFalse(r['thermal_certified'])
        self.assertEqual(r['performance'], 'PERFORMANCE_UNQUALIFIED')

    def test_incorrect_source_and_boolean_measurement_fail_closed(self):
        self.assertEqual(m.assess({'kind': 'other'})['verdict'], 'INCOMPLETE')
        samples = [sample(i) for i in range(7)]
        samples[0]['cpu_idle_pct'] = True
        self.assertIn('CPU_IDLE_MISSING_OR_INVALID', m.assess(report(samples))['evidence_gaps'])

    def test_nan_inf_and_huge_numbers_never_produce_quiet_candidate(self):
        for corrupt in [float('nan'), float('inf'), -float('inf'), 10**400]:
            with self.subTest(corrupt=str(corrupt)[:25]):
                samples = [sample(i) for i in range(7)]
                samples[1]['backupd_cpu_pct'] = corrupt
                r = m.assess(report(samples))
                self.assertEqual(r['verdict'], 'INCOMPLETE')
                self.assertIn('BACKUPD_CPU_MISSING_OR_INVALID', r['evidence_gaps'])
                self.assertFalse(r['authorizes_benchmark'])
        samples = [sample(i) for i in range(7)]
        samples[1]['monotonic_elapsed_s'] = float('nan')
        r = m.assess(report(samples))
        self.assertEqual(r['verdict'], 'INCOMPLETE')
        self.assertIn('INVALID_MONOTONIC_TIMESTAMPS', r['evidence_gaps'])

    def test_invalid_or_empty_process_list_incomplete(self):
        samples = [sample(i) for i in range(7)]
        samples[1]['top_processes'] = []
        samples[2]['top_processes'][0]['cpu_pct'] = float('nan')
        samples[3]['command_status'] = {'ps': 'failed'}
        r = m.assess(report(samples))
        self.assertEqual(r['verdict'], 'INCOMPLETE')
        self.assertIn('TOP_PROCESSES_UNAVAILABLE', r['evidence_gaps'])
        self.assertIn('TOP_PROCESS_CPU_MISSING_OR_INVALID', r['evidence_gaps'])
        self.assertIn('PS_COMMAND_NOT_OK', r['evidence_gaps'])

    def test_missing_or_inconsistent_monitor_summary_incomplete(self):
        samples = [sample(i) for i in range(7)]
        data = report(samples)
        del data['sample_window']
        self.assertIn('MONITOR_SUMMARY_MISSING_OR_NOT_OBSERVED',
                      m.assess(data)['evidence_gaps'])
        data = report(samples)
        data['sample_window']['sample_count'] = 6
        self.assertIn('MONITOR_SAMPLE_COUNT_MISMATCH',
                      m.assess(data)['evidence_gaps'])

    def test_inconsistent_swap_page_size_incomplete(self):
        samples = [sample(i) for i in range(7)]
        samples[-1]['vm_stat']['page_size_bytes'] = 4096
        r = m.assess(report(samples))
        self.assertEqual(r['verdict'], 'INCOMPLETE')
        self.assertIn('SWAP_PAGE_SIZE_MISMATCH', r['evidence_gaps'])

    def test_missing_initial_page_size_incomplete(self):
        samples = [sample(i) for i in range(7)]
        samples[0]['vm_stat']['page_size_bytes'] = None
        r = m.assess(report(samples))
        self.assertEqual(r['verdict'], 'INCOMPLETE')
        self.assertIn('SWAP_PAGE_SIZE_MISSING', r['evidence_gaps'])

    def test_output_inside_source_directory_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            source = folder / 'p1-monitor.json'
            source.write_text(json.dumps(report([sample(i) for i in range(7)])))
            output = folder / 'nested' / 'assessment.json'
            x = subprocess.run([sys.executable, str(SCRIPT), '--input', str(source),
                                '--output', str(output)], capture_output=True, text=True)
            self.assertNotEqual(x.returncode, 0)
            self.assertIn('outside the source evidence directory', x.stderr)
            self.assertFalse(output.exists())

    def test_cli_does_not_overwrite_input_or_output(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            evidence = folder/'source_evidence'
            evidence.mkdir()
            source = evidence/'monitor.json'
            output = folder/'admission.json'
            source.write_text(json.dumps(report([sample(i) for i in range(7)])))
            args = [sys.executable, str(SCRIPT), '--input', str(source), '--output', str(output)]
            proc = subprocess.run(args, capture_output=True, text=True, check=True)
            self.assertIn('NO_BENCHMARK', proc.stdout)
            content = json.loads(output.read_text())
            self.assertEqual(content['verdict'], 'QUIET_CANDIDATE_ONLY_NOT_CERTIFIED')
            self.assertEqual(len(content['input_sha256']), 64)
            duplicate = subprocess.run(args, capture_output=True, text=True)
            self.assertNotEqual(duplicate.returncode, 0)
            same = subprocess.run([sys.executable, str(SCRIPT), '--input', str(source),
                                   '--output', str(source)], capture_output=True, text=True)
            self.assertNotEqual(same.returncode, 0)


if __name__ == '__main__':
    unittest.main(verbosity=2)
