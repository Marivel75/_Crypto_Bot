"""ETL Job Scheduler — decouples schedule configuration from business logic (A5 — Architecture task)."""

from __future__ import annotations

import logging
from collections.abc import Callable

from apscheduler.schedulers.asyncio import AsyncIOScheduler  # type: ignore[import-untyped]
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class JobSchedule(BaseModel):
    """Configuration for a single scheduled ETL job."""

    job_id: str = Field(..., description="Unique job identifier (e.g., 'collect_ohlcv_priority')")
    func: Callable = Field(..., description="Coroutine function to execute")
    trigger: str = Field(default="interval", description="APScheduler trigger type (e.g., 'interval', 'cron')")
    max_instances: int = Field(default=1, description="Maximum concurrent instances of this job")
    coalesce: bool = Field(default=True, description="Skip missed runs if scheduler was stopped")

    # APScheduler parameters (flexible via kwargs)
    minutes: int | None = Field(default=None, description="Run every N minutes (for interval trigger)")
    hours: int | None = Field(default=None, description="Run every N hours")
    seconds: int | None = Field(default=None, description="Run every N seconds")
    cron_expression: str | None = Field(default=None, description="Cron expression (for cron trigger)")

    class Config:
        """Pydantic v2 config."""

        arbitrary_types_allowed = True  # Allow Callable type

    def to_scheduler_kwargs(self) -> dict:
        """Convert to APScheduler add_job kwargs."""
        kwargs = {
            "trigger": self.trigger,
            "id": self.job_id,
            "max_instances": self.max_instances,
            "coalesce": self.coalesce,
        }

        # Add trigger-specific parameters
        if self.trigger == "interval":
            if self.minutes is not None:
                kwargs["minutes"] = self.minutes
            if self.hours is not None:
                kwargs["hours"] = self.hours
            if self.seconds is not None:
                kwargs["seconds"] = self.seconds
        elif self.trigger == "cron":
            if self.cron_expression:
                # Parse cron expression and pass to APScheduler
                kwargs["expression"] = self.cron_expression

        return kwargs


class ETLScheduleConfig(BaseModel):
    """Configuration for all ETL jobs (extracted from hardcoded schedule in main.py)."""

    # Job schedule definitions (replaces hardcoded add_job calls)
    jobs: list[JobSchedule] = Field(default_factory=list)

    @classmethod
    def default(cls) -> ETLScheduleConfig:
        """Return the default production schedule."""
        # This replaces the hardcoded scheduler.add_job() calls in main.py
        # Jobs are now defined declaratively and can be overridden via env vars
        return cls(
            jobs=[
                JobSchedule(
                    job_id="collect_ohlcv_priority",
                    func=None,  # Will be injected by build_scheduler()
                    minutes=1,
                ),
                JobSchedule(
                    job_id="collect_ohlcv_all",
                    func=None,
                    minutes=5,
                ),
                JobSchedule(
                    job_id="collect_market_data",
                    func=None,
                    minutes=5,
                ),
                JobSchedule(
                    job_id="collect_news",
                    func=None,
                    minutes=15,
                ),
                JobSchedule(
                    job_id="collect_fear_greed",
                    func=None,
                    minutes=60,
                ),
                JobSchedule(
                    job_id="compute_indicators",
                    func=None,
                    minutes=5,
                ),
                JobSchedule(
                    job_id="reconciliation",
                    func=None,
                    minutes=60,
                ),
                JobSchedule(
                    job_id="evaluate_signal_outcomes",
                    func=None,
                    minutes=60,
                ),
                JobSchedule(
                    job_id="export_datasets",
                    func=None,
                    trigger="cron",
                    cron_expression="0 3 * * *",  # Daily at 03:00 timezone.utc
                ),
            ]
        )


def build_scheduler_from_config(
    config: ETLScheduleConfig,
    job_functions: dict[str, Callable],
    timezone: str = "timezone.utc",
) -> AsyncIOScheduler:
    """Build APScheduler from declarative configuration.

    Args:
        config: Schedule configuration.
        job_functions: Mapping of job_id → async function.
        timezone: Timezone for scheduler (default: timezone.utc).

    Returns:
        Initialized AsyncIOScheduler with all jobs registered.

    Raises:
        ValueError: If a job_id in config has no corresponding function.
    """
    scheduler = AsyncIOScheduler(timezone=timezone)

    for job_config in config.jobs:
        # Resolve the function by job ID
        if job_config.job_id not in job_functions:
            raise ValueError(f"Job function not found for '{job_config.job_id}'")

        func = job_functions[job_config.job_id]

        # Convert config to APScheduler kwargs
        kwargs = job_config.to_scheduler_kwargs()

        # Register the job
        scheduler.add_job(func, **kwargs)
        logger.info(f"Registered job: {job_config.job_id} (trigger: {job_config.trigger})")

    return scheduler


# Backward-compatible factory function (matches old build_scheduler signature)
def build_scheduler_default(
    job_functions: dict[str, Callable],
    timezone: str = "timezone.utc",
) -> AsyncIOScheduler:
    """Build scheduler with default production schedule.

    Args:
        job_functions: Mapping of job_id → async function.
        timezone: Timezone (default: timezone.utc).

    Returns:
        Initialized AsyncIOScheduler.
    """
    config = ETLScheduleConfig.default()
    return build_scheduler_from_config(config, job_functions, timezone)
