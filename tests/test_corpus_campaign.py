# SPDX-License-Identifier: GPL-3.0-or-later
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

from . import corpus_campaign as campaign


class CampaignRunnerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.result = self.root / 'result.json'

    def job(self, code, **changes):
        job = dict(job_id='JOB-0001', case_id='CASE-0001', stage='health',
                   argv=[sys.executable, '-c', code], cwd=str(self.root),
                   result_path=str(self.result), timeout_seconds=5, input_hashes={})
        job.update(changes)
        return job

    def writer(self, verdict='PASS'):
        return "import json; from pathlib import Path; Path(%r).write_text(json.dumps({'verdict': %r, 'reason': 'NONE'}))" % (str(self.result), verdict)

    def test_child_failure_is_not_product_failure(self):
        row = campaign.run_job(self.job('raise SystemExit(7)'), self.root)
        self.assertEqual((row['verdict'], row['reason']), ('UNPROVEN', 'HARNESS_ERROR'))
        self.assertEqual(row['returncode'], 7)

    def test_timeout_is_recorded(self):
        row = campaign.run_job(self.job('import time; time.sleep(10)', timeout_seconds=.1), self.root)
        self.assertEqual(row['reason'], 'TIMEOUT')

    def test_zero_without_result_and_stale_result_are_rejected(self):
        for stale in (False, True):
            if stale:
                self.result.write_text('{"verdict":"PASS", "reason":"NONE"}')
            row = campaign.run_job(self.job('pass'), self.root)
            self.assertEqual(row['reason'], 'HARNESS_ERROR')
            self.assertNotEqual(row['verdict'], 'PASS')

    def test_input_mismatch_does_not_launch_child(self):
        source = self.root / 'source'
        source.write_text('changed')
        job = self.job(self.writer(), input_hashes={str(source): '0' * 64})
        row = campaign.run_job(job, self.root)
        self.assertEqual(row['reason'], 'INPUT_INVALID')
        self.assertFalse(self.result.exists())

    def test_malformed_result_does_not_stop_next_case(self):
        for data in ('[]', '{bad json', '{"verdict":"PASS"}'):
            code = "from pathlib import Path; Path(%r).write_text(%r)" % (str(self.result), data)
            manifest = dict(campaign_id='test', jobs=[self.job(code), self.job(self.writer(), job_id='JOB-0002')])
            rows = campaign.run_manifest(manifest, self.root, 'health')
            self.assertEqual(rows[0]['reason'], 'HARNESS_ERROR')
            self.assertEqual(rows[1]['verdict'], 'PASS')

    def test_missing_input_is_invalid(self):
        row = campaign.run_job(self.job(self.writer(), input_hashes={str(self.root / 'missing'): '0'*64}), self.root)
        self.assertEqual(row['reason'], 'INPUT_INVALID')

    def test_child_input_mutation_invalidates_pass(self):
        source = self.root / 'source'
        source.write_bytes(b'fixture')
        code = self.writer() + '; Path(%r).write_text("mutated")' % str(source)
        row = campaign.run_job(self.job(code, input_hashes={str(source): hashlib.sha256(b'fixture').hexdigest()}), self.root)
        self.assertEqual((row['verdict'], row['reason']), ('UNPROVEN', 'INPUT_INVALID'))

    def test_child_result_is_preserved_with_private_logs(self):
        source = self.root / 'source'
        source.write_bytes(b'fixture')
        job = self.job('print("private secret"); ' + self.writer('RED'),
                       input_hashes={str(source): hashlib.sha256(b'fixture').hexdigest()})
        row = campaign.run_job(job, self.root)
        self.assertEqual(row['verdict'], 'RED')
        self.assertTrue(Path(row['stdout_path']).is_file())
        self.assertEqual(row['output_hashes'][str(self.result)], campaign.sha256_file(self.result))

    def test_failure_continues_and_resume_skips_finished(self):
        jobs = [self.job('raise SystemExit(2)'), self.job(self.writer(), job_id='JOB-0002')]
        manifest = dict(campaign_id='private campaign', jobs=jobs)
        self.assertEqual(len(campaign.run_manifest(manifest, self.root, 'health')), 2)
        self.assertEqual(campaign.run_manifest(manifest, self.root, 'resume'), [])

    def test_resume_marks_abandoned_running_attempt_and_runs_again(self):
        job = self.job(self.writer())
        event = dict(job_id=job['job_id'], case_id=job['case_id'], attempt_id='old', execution_state='RUNNING')
        (self.root / 'progress.jsonl').write_text(json.dumps(event) + '\n')
        rows = campaign.run_manifest(dict(campaign_id='test', jobs=[job]), self.root, 'resume')
        self.assertEqual(rows[0]['verdict'], 'PASS')
        events = [json.loads(line) for line in (self.root / 'progress.jsonl').read_text().splitlines()]
        self.assertTrue(any(e['execution_state'] == 'INTERRUPTED' for e in events))

    def test_public_summary_is_allowlisted(self):
        job = self.job(self.writer(), package_identity='private identity', reason='private reason')
        campaign.run_job(job, self.root)
        summary = campaign.public_summary(self.root)
        text = json.dumps(summary)
        for secret in (str(self.root), 'private identity', 'private reason', 'argv', 'sha256'):
            self.assertNotIn(secret, text)
        self.assertEqual(summary['rows'][0]['case_id'], 'CASE-0001')

    def test_changed_configuration_is_not_resumed_as_old_pass(self):
        job = self.job(self.writer())
        manifest = dict(campaign_id='test', jobs=[job])
        campaign.run_manifest(manifest, self.root, 'health')
        job['production_commit'] = 'new revision'
        self.assertEqual(len(campaign.run_manifest(manifest, self.root, 'resume')), 1)

    def test_resume_rechecks_result_hash_and_current_inputs(self):
        source = self.root / 'source'
        source.write_bytes(b'fixture')
        job = self.job(self.writer(), input_hashes={str(source): hashlib.sha256(b'fixture').hexdigest()})
        manifest = dict(campaign_id='test', jobs=[job])
        campaign.run_manifest(manifest, self.root, 'health')
        self.result.unlink()
        self.assertEqual(len(campaign.run_manifest(manifest, self.root, 'resume')), 1)
        self.result.write_text('{"verdict":"RED","reason":"PRODUCT_BUG"}')
        self.assertEqual(len(campaign.run_manifest(manifest, self.root, 'resume')), 1)
        source.write_bytes(b'mutated')
        rows = campaign.run_manifest(manifest, self.root, 'resume')
        self.assertEqual(rows[0]['reason'], 'INPUT_INVALID')

    def test_explicit_red_result_survives_probe_nonzero(self):
        row = campaign.run_job(self.job(self.writer('RED') + '; raise SystemExit(1)'), self.root)
        self.assertEqual((row['verdict'], row['returncode']), ('RED', 1))

    def test_explicit_blocked_nonzero_preserves_dependency_reason_and_evidence(self):
        code = self.writer('BLOCKED').replace("'NONE'", "'DEPENDENCY_MISSING'") + '; raise SystemExit(1)'
        row = campaign.run_job(self.job(code), self.root)
        self.assertEqual((row['verdict'], row['reason'], row['returncode']), ('BLOCKED', 'DEPENDENCY_MISSING', 1))
        self.assertEqual(row['result']['reason'], 'DEPENDENCY_MISSING')
        self.assertEqual(row['output_hashes'][str(self.result)], campaign.sha256_file(self.result))

    def test_nonzero_pass_and_not_applicable_are_rejected(self):
        for verdict in ('PASS', 'NOT_APPLICABLE'):
            row = campaign.run_job(self.job(self.writer(verdict) + '; raise SystemExit(1)'), self.root)
            self.assertEqual((row['verdict'], row['reason']), ('UNPROVEN', 'HARNESS_ERROR'))

    def test_explicit_unsupported_and_unproven_survive_nonzero(self):
        for verdict in ('UNSUPPORTED', 'UNPROVEN'):
            row = campaign.run_job(self.job(self.writer(verdict) + '; raise SystemExit(1)'), self.root)
            self.assertEqual(row['verdict'], verdict)
            self.assertIn('result', row)


if __name__ == '__main__':
    unittest.main()
