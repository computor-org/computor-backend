"""Temporal workflows for the support-ticket mail bridge (issues#520).

Both workflows run on the ``support`` queue. Their activities are
queue-bound (``QUEUE_ACTIVITIES``), so only the support worker, the one
container holding the mailbox credentials and attached to the mail host's
support network, can execute them.

* ``support_mail_import``: import new mail from the team mailbox. A Temporal
  schedule (``ensure_import_schedule``) starts it every
  ``SUPPORT_MAIL_POLL_SECONDS``; overlapping runs are skipped.
* ``support_send_reply``: deliver one queued reply. The activity is never
  retried, so a reply cannot be sent twice; failures are recorded on the
  message and can be re-queued by a person.
"""
import logging
from datetime import timedelta
from typing import Any, Dict

from temporalio import activity, workflow
from temporalio.common import RetryPolicy

from .registry import register_task
from .temporal_base import BaseWorkflow, WorkflowResult

logger = logging.getLogger(__name__)

SUPPORT_QUEUE = "support"
IMPORT_SCHEDULE_ID = "support-mail-import"


@activity.defn(name="support_import_mailbox")
def support_import_mailbox() -> Dict[str, int]:
    from computor_backend.support.operations import run_mail_import
    return run_mail_import()


@activity.defn(name="support_deliver_reply")
def support_deliver_reply(message_id: str) -> Dict[str, str]:
    from computor_backend.support.operations import deliver_reply
    return deliver_reply(message_id)


@activity.defn(name="support_send_welcome")
def support_send_welcome(user_id: str, language: str = "en") -> Dict[str, str]:
    from computor_backend.support.welcome import send_welcome
    return send_welcome(user_id, language=language)


@register_task
@workflow.defn(name="support_mail_import", sandboxed=False)
class SupportMailImportWorkflow(BaseWorkflow):
    @classmethod
    def get_name(cls) -> str:
        return "support_mail_import"

    @classmethod
    def get_task_queue(cls) -> str:
        return SUPPORT_QUEUE

    @classmethod
    def get_execution_timeout(cls) -> timedelta:
        return timedelta(minutes=20)

    @classmethod
    def get_retry_policy(cls) -> RetryPolicy:
        return RetryPolicy(maximum_attempts=1)

    @workflow.run
    async def run(self, parameters: Dict[str, Any]) -> WorkflowResult:
        counts = await workflow.execute_activity(
            support_import_mailbox,
            start_to_close_timeout=timedelta(minutes=15),
            retry_policy=RetryPolicy(maximum_attempts=2, initial_interval=timedelta(seconds=30)),
        )
        return WorkflowResult(status="completed", result=counts)


@register_task
@workflow.defn(name="support_send_reply", sandboxed=False)
class SupportSendReplyWorkflow(BaseWorkflow):
    @classmethod
    def get_name(cls) -> str:
        return "support_send_reply"

    @classmethod
    def get_task_queue(cls) -> str:
        return SUPPORT_QUEUE

    @classmethod
    def get_execution_timeout(cls) -> timedelta:
        return timedelta(hours=2)

    @classmethod
    def get_retry_policy(cls) -> RetryPolicy:
        return RetryPolicy(maximum_attempts=1)

    @workflow.run
    async def run(self, parameters: Dict[str, Any]) -> WorkflowResult:
        missing = self.require_params(parameters, "message_id")
        if missing:
            return missing
        result = await workflow.execute_activity(
            support_deliver_reply,
            parameters["message_id"],
            # Queued until the support worker picks it up; once running it is
            # one SMTP transaction plus the Sent copy.
            schedule_to_start_timeout=timedelta(hours=1),
            start_to_close_timeout=timedelta(minutes=5),
            retry_policy=RetryPolicy(maximum_attempts=1),
        )
        return WorkflowResult(status="completed", result=result)


@register_task
@workflow.defn(name="support_welcome_mail", sandboxed=False)
class SupportWelcomeMailWorkflow(BaseWorkflow):
    """Welcome mail after a completed registration (issues#185). The workflow
    ID is per user and duplicates are rejected, and the activity is never
    retried, so a user gets the mail at most once."""

    @classmethod
    def get_name(cls) -> str:
        return "support_welcome_mail"

    @classmethod
    def get_task_queue(cls) -> str:
        return SUPPORT_QUEUE

    @classmethod
    def get_execution_timeout(cls) -> timedelta:
        return timedelta(hours=2)

    @classmethod
    def get_retry_policy(cls) -> RetryPolicy:
        return RetryPolicy(maximum_attempts=1)

    @workflow.run
    async def run(self, parameters: Dict[str, Any]) -> WorkflowResult:
        missing = self.require_params(parameters, "user_id")
        if missing:
            return missing
        result = await workflow.execute_activity(
            support_send_welcome,
            args=[parameters["user_id"], parameters.get("language", "en")],
            schedule_to_start_timeout=timedelta(hours=1),
            start_to_close_timeout=timedelta(minutes=5),
            retry_policy=RetryPolicy(maximum_attempts=1),
        )
        return WorkflowResult(status="completed", result=result)


async def ensure_import_schedule(client, poll_seconds: int) -> None:
    """Create (or update the interval of) the periodic import schedule."""
    from temporalio.client import (
        Schedule,
        ScheduleActionStartWorkflow,
        ScheduleAlreadyRunningError,
        ScheduleIntervalSpec,
        ScheduleOverlapPolicy,
        SchedulePolicy,
        ScheduleSpec,
        ScheduleUpdate,
    )

    schedule = Schedule(
        action=ScheduleActionStartWorkflow(
            "support_mail_import",
            {},
            id="support-mail-import-scheduled",
            task_queue=SUPPORT_QUEUE,
            execution_timeout=SupportMailImportWorkflow.get_execution_timeout(),
        ),
        spec=ScheduleSpec(intervals=[ScheduleIntervalSpec(every=timedelta(seconds=poll_seconds))]),
        policy=SchedulePolicy(overlap=ScheduleOverlapPolicy.SKIP),
    )
    try:
        await client.create_schedule(IMPORT_SCHEDULE_ID, schedule)
        logger.info("support: created schedule %s every %ss", IMPORT_SCHEDULE_ID, poll_seconds)
    except ScheduleAlreadyRunningError:
        handle = client.get_schedule_handle(IMPORT_SCHEDULE_ID)

        def _update(_input):
            return ScheduleUpdate(schedule=schedule)

        await handle.update(_update)
        logger.info("support: updated schedule %s every %ss", IMPORT_SCHEDULE_ID, poll_seconds)


# Shared activities: none. Mail activities exist only on the support queue's
# worker; any other worker asked to run them fails with an unknown activity.
ACTIVITIES: list = []
QUEUE_ACTIVITIES = {
    SUPPORT_QUEUE: [support_import_mailbox, support_deliver_reply, support_send_welcome],
}
