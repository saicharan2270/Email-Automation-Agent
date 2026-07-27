#!/usr/bin/env python
import time
from typing import List
from uuid import uuid4

from crewai.flow import Flow, listen, start
from pydantic import BaseModel, Field

from email_auto_responder_flow.types import Email
from email_auto_responder_flow.utils.emails import check_email, format_emails

from .crews.email_filter_crew.email_filter_crew import EmailFilterCrew


class AutoResponderState(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    emails: List[Email] = []
    checked_emails_ids: set[str] = set()


class EmailAutoResponderFlow(Flow[AutoResponderState]):
    initial_state = AutoResponderState

    @start("wait_next_run")
    def fetch_new_emails(self):
        print("Kickoff the Email Filter Crew")
        new_emails, updated_checked_email_ids = check_email(
            checked_emails_ids=self.state.checked_emails_ids
        )
        print(f"Found {len(new_emails)} new emails")
        for email in new_emails:
            print(f"Email: {email}")

        self.state.emails = new_emails
        self.state.checked_emails_ids = updated_checked_email_ids

    @listen(fetch_new_emails)
    def generate_draft_responses(self):
        print("Current email queue: ", len(self.state.emails))
        if len(self.state.emails) > 0:
            print("Writing New emails")
            emails = format_emails(self.state.emails)

            EmailFilterCrew().crew().kickoff(inputs={"emails": emails})

            self.state.emails = []

        print("Waiting for 5 seconds")
        time.sleep(5)


def kickoff():
    """
    Run the flow.
    """
    email_auto_response_flow = EmailAutoResponderFlow()
    email_auto_response_flow.kickoff()


def plot_flow():
    """
    Plot the flow.
    """
    email_auto_response_flow = EmailAutoResponderFlow()
    email_auto_response_flow.plot()


if __name__ == "__main__":
    kickoff()
