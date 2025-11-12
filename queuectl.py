#!/usr/bin/env python3
import click
import json
import time
from db import init_db, save_job, list_jobs, get_config, set_config, get_job, update_job_state

@click.group()
def cli():
    """QueueCTL - Background Job Queue System"""
    init_db()


@cli.command()
@click.option("--file", "file_path", type=click.Path(), help="Path to a JSON file containing the job")
@click.argument("job_json", required=False)
def enqueue(file_path, job_json):
    """Add a new job to the queue. Provide JSON string or use --file <path>."""
    try:
        if file_path:
            with open(file_path, "r", encoding="utf-8") as f:
                job = json.load(f)
        else:
            if not job_json:
                raise click.UsageError("Either provide job JSON or use --file <path>")
            job = json.loads(job_json)

        if "id" not in job or "command" not in job:
            raise ValueError("Job must include 'id' and 'command'")

        if "max_retries" not in job:
            job["max_retries"] = int(get_config("default_max_retries") or 3)

        save_job(job)
        click.echo(f"Job '{job['id']}' enqueued.")
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
        line = f"{r['id']} | {r['state']} | attempts={r['attempts']} | cmd={r['command']}"
        click.echo(line)
        if verbose:
            click.echo(f"  stdout: {r['last_stdout']}")
            click.echo(f"  stderr: {r['last_stderr']}")


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
        click.echo(f"{r['id']} | {r['state']} | attempts={r['attempts']} | cmd={r['command']}")


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
