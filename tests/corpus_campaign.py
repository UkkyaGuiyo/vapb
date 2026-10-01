# SPDX-License-Identifier: GPL-3.0-or-later
"""Thin private campaign scheduler for existing CLI probes.

Child result JSON must contain explicit verdict and reason fields. Process
success alone is never product evidence. All probe output stays in run_dir.
"""
import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import time
import uuid

VERDICTS = {'PASS', 'RED', 'UNSUPPORTED', 'UNPROVEN', 'BLOCKED', 'NOT_APPLICABLE'}
REASONS = {'NONE', 'PRODUCT_BUG', 'UNSUPPORTED_STRUCTURE', 'UNSUPPORTED_NUMERIC_CONTEXT',
           'DEPENDENCY_MISSING', 'DEPENDENCY_AMBIGUOUS', 'IDENTITY_UNPROVEN',
           'HARNESS_UNSUPPORTED', 'HARNESS_ERROR', 'INPUT_INVALID', 'ENVIRONMENT_FAILURE', 'TIMEOUT'}
MODES = ('inventory', 'health', 'representative', 'expand', 'retry', 'validate-final', 'summarize', 'resume')


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def fingerprint(job):
    return hashlib.sha256(json.dumps(job, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def _inputs_match(inputs):
    try:
        return all(sha256_file(path) == expected for path, expected in inputs.items())
    except OSError:
        return False


def _read_rows(path):
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding='utf-8').splitlines():
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue  # An interrupted append is not completion evidence.
        if isinstance(row, dict):
            rows.append(row)
    return rows


def _append(path, row):
    # Preserve an incomplete last append without joining the next event to it.
    needs_newline = path.exists() and path.stat().st_size > 0
    if needs_newline:
        with path.open('rb') as stream:
            stream.seek(-1, 2)
            needs_newline = stream.read(1) != b'\n'
    with path.open('a', encoding='utf-8') as stream:
        if needs_newline:
            stream.write('\n')
        stream.write(json.dumps(row, sort_keys=True) + '\n')
        stream.flush()
        os.fsync(stream.fileno())


def _stop_child(process):
    if os.name == 'nt':
        subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        if process.poll() is None:
            process.kill()
    else:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    process.wait()


def run_job(job, run_dir):
    """Run one manifest job and append its private execution/evidence record."""
    root = Path(run_dir).resolve()
    root.mkdir(parents=True, exist_ok=True)
    attempt = uuid.uuid4().hex
    evidence = root / 'attempts' / attempt
    evidence.mkdir(parents=True)
    started = time.time()
    row = dict(job)
    row.update(attempt_id=attempt, config_fingerprint=fingerprint(job),
               execution_state='RUNNING', started_at=started,
               stdout_path=str(evidence / 'stdout.log'), stderr_path=str(evidence / 'stderr.log'),
               returncode=None, verdict='UNPROVEN', reason='HARNESS_ERROR', output_hashes={})
    progress = root / 'progress.jsonl'
    _append(progress, row)
    process = None
    interrupted = False
    try:
        result_path = Path(job['result_path']).resolve()
        if not result_path.is_relative_to(root):
            raise ValueError('Result must be inside private run directory')
        timeout = float(job.get('timeout_seconds', 600))
        if timeout <= 0:
            raise ValueError('Timeout must be positive')
        inputs = job.get('input_hashes', {})
        if not _inputs_match(inputs):
            row['reason'] = 'INPUT_INVALID'
        else:
            if result_path.exists():
                result_path.rename(evidence / 'prior_result.json')
            result_path.parent.mkdir(parents=True, exist_ok=True)
            with open(row['stdout_path'], 'wb') as stdout, open(row['stderr_path'], 'wb') as stderr:
                process = subprocess.Popen(job['argv'], cwd=job.get('cwd'), stdout=stdout, stderr=stderr,
                                           start_new_session=os.name != 'nt')
                try:
                    row['returncode'] = process.wait(timeout=timeout)
                except subprocess.TimeoutExpired:
                    _stop_child(process)
                    row['returncode'] = process.returncode
                    row['reason'] = 'TIMEOUT'
            if row['reason'] != 'TIMEOUT':
                if result_path.is_file():
                    if not result_path.resolve().is_relative_to(root):
                        raise ValueError('Child result escaped private run directory')
                    result = json.loads(result_path.read_text(encoding='utf-8'))
                    if (isinstance(result, dict) and result.get('verdict') in VERDICTS
                            and result.get('reason') in REASONS
                            and (row['returncode'] == 0 or result['verdict'] in
                                 {'RED', 'BLOCKED', 'UNPROVEN', 'UNSUPPORTED'})):
                        row.update(verdict=result['verdict'], reason=result['reason'], result=result)
                        row['output_hashes'][str(result_path)] = sha256_file(result_path)
                        (evidence / 'result.json').write_text(json.dumps(result, sort_keys=True), encoding='utf-8')
            if not _inputs_match(inputs):
                row.update(verdict='UNPROVEN', reason='INPUT_INVALID')
    except KeyboardInterrupt:
        if process is not None and process.poll() is None:
            _stop_child(process)
        interrupted = True
    except (OSError, ValueError, KeyError, TypeError) as exc:
        row['error_type'] = type(exc).__name__
        if isinstance(exc, FileNotFoundError) and process is None:
            row['reason'] = 'ENVIRONMENT_FAILURE'
    finally:
        row.update(execution_state='INTERRUPTED' if interrupted else 'FINISHED',
                   ended_at=time.time(), duration_seconds=time.time() - started)
        _append(progress, row)
        _append(root / 'case_results.jsonl', row)
    if interrupted:
        raise KeyboardInterrupt
    return row


def run_manifest(manifest, run_dir, mode='resume'):
    """Schedule stage jobs, retry non-PASS jobs, or resume unfinished identities."""
    if mode not in MODES:
        raise ValueError('Unknown campaign mode')
    root = Path(run_dir).resolve()
    root.mkdir(parents=True, exist_ok=True)
    if mode == 'summarize':
        return public_summary(root)
    progress = root / 'progress.jsonl'
    latest_attempt = {}
    for row in _read_rows(progress):
        latest_attempt[row.get('attempt_id')] = row
    if mode == 'resume':
        for row in latest_attempt.values():
            if row.get('execution_state') == 'RUNNING':
                _append(progress, dict(row, execution_state='INTERRUPTED', ended_at=time.time()))
    latest = {}
    for row in _read_rows(root / 'case_results.jsonl'):
        latest[row.get('job_id')] = row
    results = []
    for spec in manifest['jobs']:
        job = dict(spec, campaign_id=manifest['campaign_id'])
        previous = latest.get(job['job_id'])
        if (mode == 'resume' and previous and previous.get('execution_state') == 'FINISHED'
                and previous.get('config_fingerprint') == fingerprint(job)
                and _inputs_match(job.get('input_hashes', {}))
                and _inputs_match(previous.get('output_hashes', {}))):
            continue
        if mode == 'retry' and (not previous or previous.get('verdict') == 'PASS'):
            continue
        if mode not in ('resume', 'retry') and job.get('stage') != mode:
            continue
        results.append(run_job(job, root))
    return results


def public_summary(run_dir):
    """Only fixed enums and anonymous identifiers can leave the private run."""
    latest = {}
    for row in _read_rows(Path(run_dir) / 'case_results.jsonl'):
        latest[row.get('job_id')] = row
    safe = []
    for row in latest.values():
        safe.append(dict(case_id=row['case_id'] if re.fullmatch(r'CASE-\d{4,}', str(row.get('case_id'))) else 'REDACTED',
                         job_id=row['job_id'] if re.fullmatch(r'JOB-\d{4,}', str(row.get('job_id'))) else 'REDACTED',
                         execution_state=row.get('execution_state') if row.get('execution_state') in {'PENDING', 'RUNNING', 'FINISHED', 'INTERRUPTED'} else 'INTERRUPTED',
                         verdict=row.get('verdict') if row.get('verdict') in VERDICTS else 'UNPROVEN',
                         reason=row.get('reason') if row.get('reason') in REASONS else 'HARNESS_ERROR'))
    return dict(rows=safe, counts=dict(Counter(row['verdict'] for row in safe)))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=MODES)
    parser.add_argument('--run-dir', required=True)
    parser.add_argument('--manifest')
    args = parser.parse_args()
    if args.mode != 'summarize':
        if not args.manifest:
            parser.error('--manifest is required for execution')
        manifest = json.loads(Path(args.manifest).read_text(encoding='utf-8'))
        run_manifest(manifest, args.run_dir, args.mode)
    print(json.dumps(public_summary(args.run_dir), sort_keys=True))


if __name__ == '__main__':
    main()
