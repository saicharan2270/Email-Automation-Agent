from typing import Type

from crewai.tools import BaseTool
from langchain_community.agent_toolkits import GmailToolkit
from langchain_community.tools.gmail.get_thread import GmailGetThread
from pydantic import BaseModel, Field
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


class GetThreadInput(BaseModel):
    thread_id: str = Field(..., description="The Gmail thread ID to read.")


class CreateDraftInput(BaseModel):
    to: str = Field(..., description="Recipient email address to reply to.")
    subject: str = Field(..., description="Email subject line, typically starting with 'Re:'.")
    message: str = Field(..., description="The full body text of the draft reply.")
    thread_id: str = Field(None, description="The Gmail thread ID to reply to. If provided, the draft will be in the same thread.")


class GmailGetThreadTool(BaseTool):
    name: str = "Get Gmail Thread"
    description: str = (
        "Read a full Gmail conversation thread by its thread ID. "
        "Use this to understand the email context before drafting a reply."
    )
    args_schema: Type[BaseModel] = GetThreadInput

    def _run(self, thread_id: str) -> str:
        gmail = GmailToolkit()
        thread_tool = GmailGetThread(api_resource=gmail.api_resource)
        result = thread_tool._run(thread_id=thread_id)
        return str(result)


def _get_last_message_headers(service, thread_id: str) -> dict:
    """Fetch headers of the most recent message in a thread.

    Gmail only threads a new draft under an existing conversation if, in
    addition to `threadId`, the `In-Reply-To`/`References` headers point at
    the prior message's `Message-ID` and the `Subject` matches (ignoring the
    "Re:" prefix). This pulls what's needed to satisfy that.
    """
    thread = service.users().threads().get(
        userId="me",
        id=thread_id,
        format="metadata",
        metadataHeaders=["Message-ID", "References", "Subject"],
    ).execute()
    last_message = thread["messages"][-1]
    return {h["name"]: h["value"] for h in last_message["payload"]["headers"]}


class CreateDraftTool(BaseTool):
    name: str = "Create Draft"
    description: str = (
        "Create a Gmail draft reply. Provide the recipient email, subject, message body, and optionally the thread_id to reply in the same thread."
    )
    args_schema: Type[BaseModel] = CreateDraftInput

    def _run(self, to: str, subject: str, message: str, thread_id: str = None) -> str:
        print(f"CreateDraftTool called with: to={to}, subject={subject}, thread_id={thread_id}")

        gmail = GmailToolkit()
        service = gmail.api_resource

        thread_id = thread_id.strip() if thread_id else None
        subject = subject.strip()

        # Create the email message
        email_message = MIMEMultipart()
        email_message['to'] = to.strip()

        if thread_id:
            try:
                headers = _get_last_message_headers(service, thread_id)
                original_message_id = headers.get("Message-ID")
                original_subject = headers.get("Subject")
                original_references = headers.get("References", "")

                if original_message_id:
                    email_message['In-Reply-To'] = original_message_id
                    email_message['References'] = (
                        f"{original_references} {original_message_id}".strip()
                    )

                if original_subject:
                    subject = (
                        original_subject
                        if original_subject.strip().lower().startswith("re:")
                        else f"Re: {original_subject}"
                    )
            except Exception as e:
                print(f"Could not fetch original headers for threading: {e}")

        email_message['subject'] = subject
        email_message.attach(MIMEText(message.strip(), 'plain'))

        # Encode the message
        raw_message = base64.urlsafe_b64encode(email_message.as_bytes()).decode()

        # threadId must live inside `message`, not at the top level of the
        # draft body -- Gmail's Draft resource has no top-level threadId
        # field, so putting it there is silently ignored.
        draft_body = {
            'message': {
                'raw': raw_message
            }
        }

        if thread_id:
            draft_body['message']['threadId'] = thread_id
            print(f"Using thread_id: {thread_id}")

        print(f"Creating draft with thread_id: {thread_id}")
        try:
            draft = service.users().drafts().create(
                userId='me',
                body=draft_body
            ).execute()
            print(f"Draft created successfully: {draft}")
            return f"Draft created with ID: {draft['id']}"
        except Exception as e:
            print(f"Error creating draft: {e}")
            return f"Error creating draft: {str(e)}"
