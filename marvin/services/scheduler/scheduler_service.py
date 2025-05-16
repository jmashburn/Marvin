import asyncio
from datetime import datetime, timedelta, timezone
from pathlib import Path

from marvin.core import root_logger
from marvin.core.config import get_app_settings
from marvin.services.scheduler.runner import repeat_every

from .scheduler_registry import SchedulerRegistry

logger = root_logger.get_logger("scheduler")

CWD = Path(__file__).parent

MINUTES_DAY = 1440
MINUTES_5 = 5
MINUTES_HOUR = 60


class SchedulerService:
    @staticmethod
    async def start():
        await run_minutely()
        await run_hourly()

        # Wait to trigger our daily run until our given "daily time", so having asyncio handle it.
        asyncio.create_task(schedule_daily())


async def schedule_daily():
    now = datetime.now(timezone.utc)
    daily_schedule_time = get_app_settings().DAILY_SCHEDULE_TIME_UTC
    logger.info(f"Current time is {now} and DAILY_SCHEDULE_TIME (in UTC) is {daily_schedule_time}")

    next_schedule = now.replace(
        hour=daily_schedule_time.hour, minute=daily_schedule_time.minute, second=0, microsecond=0
    )
    delta = next_schedule - now
    if delta < timedelta(0):
        next_schedule = next_schedule + timedelta(days=1)
        delta = next_schedule - now

    hours_until, seconds_reminder = divmod(delta.total_seconds(), 3600)
    minutes_until, seconds_reminder = divmod(seconds_reminder, 60)
    seconds_until = round(seconds_reminder)
    logger.info("Time left: %02d:%02d:%02d", hours_until, minutes_until, seconds_until)

    target_time = next_schedule.replace(microsecond=0, second=0)
    logger.info("Daily tasks scheduled for %s", str(target_time))

    wait_seconds = delta.total_seconds()
    await asyncio.sleep(wait_seconds)
    await run_daily()


def _scheduled_task_wrapper(callable):
    try:
        callable()
    except Exception as e:
        logger.error("Error in scheduled task func='%s': exception='%s'", callable.__name__, e)


@repeat_every(minutes=MINUTES_DAY, wait_first=False, logger=logger)
def run_daily():
    now = datetime.now(timezone.utc)
    logger.info(f"Running daily callbacks at {now} and again at {now + timedelta(minutes=1440)}")
    for func in SchedulerRegistry._daily:
        _scheduled_task_wrapper(func)


@repeat_every(minutes=MINUTES_HOUR, wait_first=True, logger=logger)
def run_hourly():
    now = datetime.now(timezone.utc)
    logger.info(f"Running hourly callbacks at {now} and again at {now + timedelta(minutes=MINUTES_HOUR)}")
    for func in SchedulerRegistry._hourly:
        _scheduled_task_wrapper(func)


@repeat_every(minutes=MINUTES_5, wait_first=True, logger=logger)
def run_minutely():
    now = datetime.now(timezone.utc)
    logger.info(f"Running minutely callbacks at {now} and again at {now + timedelta(minutes=MINUTES_5)}")
    for func in SchedulerRegistry._minutely:
        _scheduled_task_wrapper(func)
