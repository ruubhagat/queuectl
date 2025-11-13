#!/usr/bin/env python3
import click
import json
import time
import os
from datetime import datetime, timezone
from db import init_db, save_job, list_jobs, get_config, set_config, get_job, update_job_state, stats_summary

init_db()  # ensure DB exists when the module is imported


def parse_iso_to_epoch(s: str) -> int:
    """
    Parse ISO 8601 string to epoch seconds (UTC). Accepts '2025-11-10T12:00:00Z' or '2025-11-10 12:00:00'
    """
    if not s:
        return 0
    try:
        # Try parsing with timezone Z
        if s.endswith("Z"):
            dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        else:
            dt = datetime.fromisoformat(s)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
        return int(dt.timestamp())
    except Exception:
        # fallback: try common formats
        try:
            dt = datetime.strptime(s, "%Y-%m-%dT%H:%M:%S")
            dt = dt.replace(tzinfo=timezone.utc)
            return int(dt.timestamp())
        except Exception:
            raise click.BadParameter("Invalid run_at datetime. Use ISO format, e.g. 2025-11-12T15:30:00Z")


@click.group()
def cli():
    """QueueCTL - Background Job Queue System"""
    pass


@cli.command()
@click.option("--file", "file_path", type=click.Path(), help="Path to a JSON file containing the job")
@click.option("--priority", type=int, default=0, help="Job priority (higher processed first)")
@click.option("--timeout", type=int, default=None, help="Job timeout in seconds (optional)")
@click.option("--run-at", "run_at", type=str, default=None, help="Schedule job at ISO time (UTC), e.g. 2025-11-12T15:30:00Z")
@click.argument("job_json", required=False)
def enqueue(file_path, priority, timeout, run_at, job_json):
    """
    Add a new job to the queue. Provide JSON string or use --file <path>.
    Extra CLI options can set priority, timeout, and scheduled run time.
    """
    try:
        if file_path:
            with open(file_path, "r", encoding="utf-8") as f:
                job = json.load(f)
        else:
            if not job_json:
                raise click.UsageError("Either provide job JSON or use --file <path>")
            job = json.loads(job_json)
        if "id" not in job or "command" not in job:
            raise click.BadParameter("Job must include 'id' and 'command'")

        # CLI flags override JSON fields if provided
        if priority is not None:
            job["priority"] = priority
        if timeout is not None:
            job["timeout"] = timeout
        if run_at:
            job["next_run_at"] = parse_iso_to_epoch(run_at)
        else:
            # if job JSON has run_at (string), convert it
            if "run_at" in job and job.get("run_at"):
                job["next_run_at"] = parse_iso_to_epoch(job["run_at"])

        # default max_retries
        if "max_retries" not in job:
            job["max_retries"] = int(get_config("default_max_retries") or 3)

        # set priority default
        if "priority" not in job:
            job["priority"] = 0

        save_job(job)
        click.echo(f"Job '{job['id']}' enqueued. priority={job.get('priority')} run_at={job.get('next_run_at',0)} timeout={job.get('timeout')}")
    except Exception as e:
        click.echo(f"Error: {e}")


@cli.command(name="list")
@click.option("--state", help="Filter jobs by state (pending, processing, completed, failed, dead)")
@click.option("--verbose", is_flag=True, help="Show stdout/stderr for jobs")
def list_jobs_cmd(state, verbose):
    """List jobs by state (or all)"""
    rows = list_jobs(state)
    if not rows:
        click.echo("No jobs found.")
        return
    for r in rows:
        line = f"{r['id']} | {r['state']} | attempts={r['attempts']} | priority={r['priority']} | cmd={r['command']}"
        click.echo(line)
        if verbose:
            click.echo(f"  stdout: {r['last_stdout']}")
            click.echo(f"  stderr: {r['last_stderr']}")
            click.echo(f"  next_run_at: {r['next_run_at']}")


@cli.command()
def status():
    """Show summary of job states and basic metrics"""
    summary = stats_summary()
    click.echo("=== Queue Summary ===")
    for state, count in summary.items():
        if state == "total":
            click.echo(f"Total jobs: {count}")
        else:
            click.echo(f"{state}: {count}")
    # simple extra metrics
    # avg attempts
    rows = list_jobs()
    if rows:
        avg_attempts = sum([r["attempts"] for r in rows]) / len(rows)
    else:
        avg_attempts = 0
    click.echo(f"Avg attempts per job: {avg_attempts:.2f}")


@cli.group()
def config():
    """Manage configuration values"""
    pass


@config.command("get")
@click.argument("key")
def get_config_cmd(key):
    val = get_config(key)
    click.echo(f"{key} = {val}" if val is not None else "Not set.")


@config.command("set")
@click.argument("key")
@click.argument("value")
def set_config_cmd(key, value):
    set_config(key, value)
    click.echo(f"Config '{key}' set to {value}")


from worker import start_workers

@cli.group()
def worker():
    """Manage worker processes"""
    pass


@worker.command("start")
@click.option("--count", default=1, help="Number of worker processes to start")
@click.option("--foreground", is_flag=True, help="Run single worker in foreground (no multiprocessing) - useful for debugging")
def worker_start(count, foreground):
    click.echo(f"Starting {count} worker(s){' (foreground)' if foreground else ''}...")
    start_workers(count if not foreground else 1, foreground=foreground)


@cli.group()
def dlq():
    """Dead Letter Queue commands"""
    pass


@dlq.command("list")
def dlq_list():
    rows = list_jobs("dead")
    if not rows:
        click.echo("No dead jobs.")
        return
    for r in rows:
        click.echo(f"{r['id']} | {r['state']} | attempts={r['attempts']} | priority={r['priority']} | cmd={r['command']}")


@dlq.command("retry")
@click.argument("job_id")
def dlq_retry(job_id):
    j = get_job(job_id)
    if not j:
        click.echo("Job not found.")
        return
    if j["state"] != "dead":
        click.echo("Job is not in DLQ.")
        return
    update_job_state(job_id, state="pending", attempts=0, next_run_at=0, last_error=None, last_stdout=None, last_stderr=None)
    click.echo(f"Requeued {job_id} from DLQ.")


if __name__ == "__main__":
    cli()
