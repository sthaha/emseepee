#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 emseepee Contributors
# SPDX-License-Identifier: MIT
"""
Gmail Service for MCP Server

Provides Gmail API integration for the get-unread-emails tool.
"""

import os
import logging
import time
import base64
import webbrowser
from typing import Any, List, Dict, Optional
from email.message import EmailMessage

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)


class GmailService:
    def __init__(
        self,
        creds_file_path: str,
        token_path: str,
        scopes: List[str] = None,
    ):
        if scopes is None:
            scopes = ["https://www.googleapis.com/auth/gmail.modify"]

        logger.info(f"Initializing GmailService with creds file: {creds_file_path}")
        self.creds_file_path = creds_file_path
        self.token_path = token_path
        self.scopes = scopes
        self.token = self._get_token()
        logger.info("Token retrieved successfully")
        self.service = self._get_service()
        logger.info("Gmail service initialized")
        self.user_email = self._get_user_email()
        logger.info(f"User email retrieved: {self.user_email}")

        # Caching for unread emails to reduce API calls
        self._unread_cache = None
        self._cache_timestamp = None
        self._cache_ttl = 60  # Cache for 60 seconds

    def _get_token(self) -> Credentials:
        """Get or refresh Google API token"""
        token = None

        if os.path.exists(self.token_path):
            logger.info("Loading token from file")
            token = Credentials.from_authorized_user_file(self.token_path, self.scopes)

        if not token or not token.valid:
            if token and token.expired and token.refresh_token:
                logger.info("Refreshing token")
                token.refresh(Request())
            else:
                logger.info("Fetching new token")
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.creds_file_path, self.scopes
                )
                token = flow.run_local_server(port=0)

            with open(self.token_path, "w") as token_file:
                token_file.write(token.to_json())
                logger.info(f"Token saved to {self.token_path}")

        return token

    def _get_service(self) -> Any:
        """Initialize Gmail API service"""
        try:
            service = build("gmail", "v1", credentials=self.token)
            return service
        except HttpError as error:
            logger.error(f"An error occurred building Gmail service: {error}")
            raise ValueError(f"An error occurred: {error}")

    def _get_user_email(self) -> str:
        """Get user email address"""
        profile = self.service.users().getProfile(userId="me").execute()
        user_email = profile.get("emailAddress", "")
        return user_email

    async def get_unread_emails(
        self, max_emails: int = 5
    ) -> List[Dict[str, str]] | str:
        """
        Retrieves unread messages from mailbox with details.
        Uses in-memory caching to reduce API calls.

        Args:
            max_emails: Maximum number of emails to fetch (default: 5)

        Returns:
            list of email objects with subject, sender, date, snippet, id, and labels
        """
        # Check cache first
        current_time = time.time()
        if (
            self._unread_cache is not None
            and self._cache_timestamp is not None
            and current_time - self._cache_timestamp < self._cache_ttl
        ):
            logger.info("Returning cached unread emails")
            return self._unread_cache[:max_emails]

        try:
            logger.info(f"Fetching up to {max_emails} unread emails from Gmail API")
            user_id = "me"
            query = "in:inbox is:unread"

            response = (
                self.service.users()
                .messages()
                .list(userId=user_id, q=query, maxResults=max_emails)
                .execute()
            )
            message_ids = []
            if "messages" in response:
                message_ids.extend(response["messages"])

            # Fetch details for each message
            detailed_emails = []
            for message in message_ids:
                try:
                    msg = (
                        self.service.users()
                        .messages()
                        .get(userId=user_id, id=message["id"], format="metadata")
                        .execute()
                    )

                    # Extract headers
                    headers = {
                        h["name"]: h["value"]
                        for h in msg.get("payload", {}).get("headers", [])
                    }

                    # Extract label information
                    label_ids = msg.get("labelIds", [])
                    labels = []

                    # Get label details for each label ID
                    for label_id in label_ids:
                        try:
                            # For system labels, we can provide known names
                            if label_id in [
                                "INBOX",
                                "UNREAD",
                                "IMPORTANT",
                                "STARRED",
                                "SENT",
                                "DRAFT",
                                "TRASH",
                                "SPAM",
                                "CATEGORY_PERSONAL",
                                "CATEGORY_SOCIAL",
                                "CATEGORY_PROMOTIONS",
                                "CATEGORY_UPDATES",
                                "CATEGORY_FORUMS",
                            ]:
                                labels.append(
                                    {
                                        "id": label_id,
                                        "name": label_id.replace(
                                            "CATEGORY_", ""
                                        ).title(),
                                    }
                                )
                            else:
                                # For custom labels, fetch the label details
                                try:
                                    label_response = (
                                        self.service.users()
                                        .labels()
                                        .get(userId=user_id, id=label_id)
                                        .execute()
                                    )
                                    labels.append(
                                        {
                                            "id": label_id,
                                            "name": label_response.get(
                                                "name", label_id
                                            ),
                                        }
                                    )
                                except Exception as label_error:
                                    # If we can't get label details, just include the ID
                                    logger.warning(
                                        f"Could not get label details for {label_id}: {label_error}"
                                    )
                                    labels.append({"id": label_id, "name": label_id})
                        except Exception as e:
                            logger.warning(f"Error processing label {label_id}: {e}")
                            continue

                    detailed_emails.append(
                        {
                            "id": message["id"],
                            "subject": headers.get("Subject", "No subject"),
                            "sender": headers.get("From", "Unknown sender"),
                            "date": headers.get("Date", ""),
                            "snippet": msg.get("snippet", ""),
                            "labels": labels,
                        }
                    )
                except Exception as e:
                    # If we can't get details for one email, skip it
                    logger.warning(
                        f"Failed to get details for email {message.get('id', 'unknown')}: {e}"
                    )
                    continue

            # Cache the results
            self._unread_cache = detailed_emails
            self._cache_timestamp = current_time
            logger.info(f"Cached {len(detailed_emails)} unread emails")

            return detailed_emails

        except HttpError as error:
            return f"An HttpError occurred: {str(error)}"

    async def send_email(self, recipient_id: str, subject: str, message: str) -> str:
        """Send an email to the specified recipient."""
        try:
            msg = EmailMessage()
            msg["Subject"] = subject
            msg["From"] = self.user_email
            msg["To"] = recipient_id
            msg.set_content(message)

            # Encode message
            raw_message = base64.urlsafe_b64encode(msg.as_bytes()).decode("ascii")
            send_message = {"raw": raw_message}

            result = (
                self.service.users()
                .messages()
                .send(userId="me", body=send_message)
                .execute()
            )

            logger.info(f"Email sent successfully. Message ID: {result['id']}")
            return (
                f"Email sent successfully to {recipient_id}. Message ID: {result['id']}"
            )
        except HttpError as error:
            logger.error(f"Failed to send email: {error}")
            return f"Failed to send email: {str(error)}"

    async def read_email(self, email_id: str) -> Dict[str, Any] | str:
        """Read the full content of an email by ID."""
        try:
            # Get the email message
            msg = (
                self.service.users()
                .messages()
                .get(userId="me", id=email_id, format="full")
                .execute()
            )

            # Extract headers
            headers = {
                h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])
            }

            # Extract body
            body_text = ""
            if "parts" in msg["payload"]:
                for part in msg["payload"]["parts"]:
                    if part["mimeType"] == "text/plain":
                        if "data" in part["body"]:
                            body_text = base64.urlsafe_b64decode(
                                part["body"]["data"]
                            ).decode("utf-8")
                        break
            elif msg["payload"]["mimeType"] == "text/plain":
                if "data" in msg["payload"]["body"]:
                    body_text = base64.urlsafe_b64decode(
                        msg["payload"]["body"]["data"]
                    ).decode("utf-8")

            return {
                "id": email_id,
                "subject": headers.get("Subject", "No subject"),
                "sender": headers.get("From", "Unknown sender"),
                "recipient": headers.get("To", "Unknown recipient"),
                "date": headers.get("Date", ""),
                "body": body_text,
                "snippet": msg.get("snippet", ""),
            }
        except HttpError as error:
            logger.error(f"Failed to read email {email_id}: {error}")
            return f"Failed to read email: {str(error)}"

    async def trash_email(self, email_id: str) -> str:
        """Move an email to trash."""
        try:
            self.service.users().messages().trash(userId="me", id=email_id).execute()
            logger.info(f"Email {email_id} moved to trash")
            return "Email moved to trash successfully."
        except HttpError as error:
            logger.error(f"Failed to trash email {email_id}: {error}")
            return f"Failed to trash email: {str(error)}"

    async def mark_email_as_read(self, email_id: str) -> str:
        """Mark an email as read."""
        try:
            self.service.users().messages().modify(
                userId="me", id=email_id, body={"removeLabelIds": ["UNREAD"]}
            ).execute()
            logger.info(f"Email {email_id} marked as read")
            return "Email marked as read successfully."
        except HttpError as error:
            logger.error(f"Failed to mark email as read {email_id}: {error}")
            return f"Failed to mark email as read: {str(error)}"

    async def open_email(self, email_id: str) -> str:
        """Open an email in the default web browser."""
        try:
            url = f"https://mail.google.com/mail/u/0/#inbox/{email_id}"
            webbrowser.open(url)
            logger.info(f"Opened email {email_id} in browser")
            return "Email opened in browser successfully."
        except Exception as error:
            logger.error(f"Failed to open email {email_id}: {error}")
            return f"Failed to open email in browser: {str(error)}"

    async def archive_email(self, email_id: str) -> str:
        """Archive an email (remove from inbox)."""
        try:
            self.service.users().messages().modify(
                userId="me", id=email_id, body={"removeLabelIds": ["INBOX"]}
            ).execute()
            logger.info(f"Email {email_id} archived")
            return "Email archived successfully."
        except HttpError as error:
            logger.error(f"Failed to archive email {email_id}: {error}")
            return f"Failed to archive email: {str(error)}"

    async def restore_to_inbox(self, email_id: str) -> str:
        """Restore an archived email back to inbox."""
        try:
            self.service.users().messages().modify(
                userId="me", id=email_id, body={"addLabelIds": ["INBOX"]}
            ).execute()
            logger.info(f"Email {email_id} restored to inbox")
            return "Email restored to inbox successfully."
        except HttpError as error:
            logger.error(f"Failed to restore email {email_id}: {error}")
            return f"Failed to restore email to inbox: {str(error)}"

    # Draft Management Methods

    async def create_draft(
        self, recipient_id: str, subject: str, message: str
    ) -> Dict[str, Any]:
        """Create a new email draft."""
        try:
            msg = EmailMessage()
            msg["Subject"] = subject
            msg["From"] = self.user_email
            msg["To"] = recipient_id
            msg.set_content(message)

            # Encode message
            raw_message = base64.urlsafe_b64encode(msg.as_bytes()).decode("ascii")
            draft_message = {"message": {"raw": raw_message}}

            result = (
                self.service.users()
                .drafts()
                .create(userId="me", body=draft_message)
                .execute()
            )

            logger.info(f"Draft created successfully. Draft ID: {result['id']}")
            return {
                "id": result["id"],
                "message_id": result["message"]["id"],
                "subject": subject,
                "recipient": recipient_id,
                "status": "draft_created",
            }
        except HttpError as error:
            logger.error(f"Failed to create draft: {error}")
            return {"error": f"Failed to create draft: {str(error)}"}

    async def list_drafts(self) -> List[Dict[str, Any]] | str:
        """List all draft emails."""
        try:
            result = self.service.users().drafts().list(userId="me").execute()
            drafts = result.get("drafts", [])

            detailed_drafts = []
            for draft in drafts:
                try:
                    draft_detail = (
                        self.service.users()
                        .drafts()
                        .get(userId="me", id=draft["id"])
                        .execute()
                    )

                    msg = draft_detail["message"]
                    headers = {
                        h["name"]: h["value"]
                        for h in msg.get("payload", {}).get("headers", [])
                    }

                    detailed_drafts.append(
                        {
                            "id": draft["id"],
                            "message_id": msg["id"],
                            "subject": headers.get("Subject", "No subject"),
                            "recipient": headers.get("To", "No recipient"),
                            "snippet": msg.get("snippet", ""),
                        }
                    )
                except Exception as e:
                    logger.warning(
                        f"Failed to get details for draft {draft.get('id', 'unknown')}: {e}"
                    )
                    continue

            logger.info(f"Retrieved {len(detailed_drafts)} drafts")
            return detailed_drafts
        except HttpError as error:
            logger.error(f"Failed to list drafts: {error}")
            return f"Failed to list drafts: {str(error)}"

    # Label Management Methods

    async def list_labels(self) -> List[Dict[str, Any]] | str:
        """List all Gmail labels."""
        try:
            result = self.service.users().labels().list(userId="me").execute()
            labels = result.get("labels", [])

            formatted_labels = []
            for label in labels:
                formatted_labels.append(
                    {
                        "id": label["id"],
                        "name": label["name"],
                        "type": label.get("type", "user"),
                        "messages_total": label.get("messagesTotal", 0),
                        "messages_unread": label.get("messagesUnread", 0),
                    }
                )

            logger.info(f"Retrieved {len(formatted_labels)} labels")
            return formatted_labels
        except HttpError as error:
            logger.error(f"Failed to list labels: {error}")
            return f"Failed to list labels: {str(error)}"

    async def create_label(self, name: str) -> Dict[str, Any] | str:
        """Create a new Gmail label."""
        try:
            label_object = {
                "name": name,
                "labelListVisibility": "labelShow",
                "messageListVisibility": "show",
            }

            result = (
                self.service.users()
                .labels()
                .create(userId="me", body=label_object)
                .execute()
            )

            logger.info(f"Label '{name}' created with ID: {result['id']}")
            return {
                "id": result["id"],
                "name": result["name"],
                "status": "label_created",
            }
        except HttpError as error:
            logger.error(f"Failed to create label '{name}': {error}")
            return f"Failed to create label: {str(error)}"

    async def apply_label(self, email_id: str, label_id: str) -> str:
        """Apply a label to an email."""
        try:
            self.service.users().messages().modify(
                userId="me", id=email_id, body={"addLabelIds": [label_id]}
            ).execute()
            logger.info(f"Label {label_id} applied to email {email_id}")
            return "Label applied successfully."
        except HttpError as error:
            logger.error(
                f"Failed to apply label {label_id} to email {email_id}: {error}"
            )
            return f"Failed to apply label: {str(error)}"

    async def remove_label(self, email_id: str, label_id: str) -> str:
        """Remove a label from an email."""
        try:
            self.service.users().messages().modify(
                userId="me", id=email_id, body={"removeLabelIds": [label_id]}
            ).execute()
            logger.info(f"Label {label_id} removed from email {email_id}")
            return "Label removed successfully."
        except HttpError as error:
            logger.error(
                f"Failed to remove label {label_id} from email {email_id}: {error}"
            )
            return f"Failed to remove label: {str(error)}"

    async def rename_label(self, label_id: str, new_name: str) -> Dict[str, Any] | str:
        """Rename an existing label."""
        try:
            # Get current label
            current_label = (
                self.service.users().labels().get(userId="me", id=label_id).execute()
            )

            # Update with new name
            current_label["name"] = new_name

            result = (
                self.service.users()
                .labels()
                .update(userId="me", id=label_id, body=current_label)
                .execute()
            )

            logger.info(f"Label {label_id} renamed to '{new_name}'")
            return {
                "id": result["id"],
                "name": result["name"],
                "status": "label_renamed",
            }
        except HttpError as error:
            logger.error(f"Failed to rename label {label_id}: {error}")
            return f"Failed to rename label: {str(error)}"

    async def delete_label(self, label_id: str) -> str:
        """Delete a Gmail label."""
        try:
            self.service.users().labels().delete(userId="me", id=label_id).execute()
            logger.info(f"Label {label_id} deleted")
            return "Label deleted successfully."
        except HttpError as error:
            logger.error(f"Failed to delete label {label_id}: {error}")
            return f"Failed to delete label: {str(error)}"

    async def search_by_label(self, label_id: str) -> List[Dict[str, Any]] | str:
        """Search for emails with a specific label."""
        try:
            # Get label name for query
            label = (
                self.service.users().labels().get(userId="me", id=label_id).execute()
            )
            label_name = label["name"]

            # Search using label
            query = f"label:{label_name}"
            result = (
                self.service.users()
                .messages()
                .list(userId="me", q=query, maxResults=50)
                .execute()
            )

            messages = result.get("messages", [])
            detailed_emails = []

            for message in messages:
                try:
                    msg = (
                        self.service.users()
                        .messages()
                        .get(userId="me", id=message["id"], format="metadata")
                        .execute()
                    )

                    headers = {
                        h["name"]: h["value"]
                        for h in msg.get("payload", {}).get("headers", [])
                    }

                    detailed_emails.append(
                        {
                            "id": message["id"],
                            "subject": headers.get("Subject", "No subject"),
                            "sender": headers.get("From", "Unknown sender"),
                            "date": headers.get("Date", ""),
                            "snippet": msg.get("snippet", ""),
                        }
                    )
                except Exception as e:
                    logger.warning(
                        f"Failed to get details for email {message.get('id', 'unknown')}: {e}"
                    )
                    continue

            logger.info(f"Found {len(detailed_emails)} emails with label {label_name}")
            return detailed_emails
        except HttpError as error:
            logger.error(f"Failed to search by label {label_id}: {error}")
            return f"Failed to search by label: {str(error)}"

    # Filter Management Methods

    async def list_filters(self) -> List[Dict[str, Any]] | str:
        """List all Gmail filters."""
        try:
            result = (
                self.service.users().settings().filters().list(userId="me").execute()
            )
            filters = result.get("filter", [])

            formatted_filters = []
            for filter_obj in filters:
                formatted_filters.append(
                    {
                        "id": filter_obj["id"],
                        "criteria": filter_obj.get("criteria", {}),
                        "action": filter_obj.get("action", {}),
                    }
                )

            logger.info(f"Retrieved {len(formatted_filters)} filters")
            return formatted_filters
        except HttpError as error:
            logger.error(f"Failed to list filters: {error}")
            return f"Failed to list filters: {str(error)}"

    async def get_filter(self, filter_id: str) -> Dict[str, Any] | str:
        """Get details of a specific Gmail filter."""
        try:
            result = (
                self.service.users()
                .settings()
                .filters()
                .get(userId="me", id=filter_id)
                .execute()
            )

            return {
                "id": result["id"],
                "criteria": result.get("criteria", {}),
                "action": result.get("action", {}),
            }
        except HttpError as error:
            logger.error(f"Failed to get filter {filter_id}: {error}")
            return f"Failed to get filter: {str(error)}"

    async def create_filter(
        self,
        from_email: Optional[str] = None,
        to_email: Optional[str] = None,
        subject: Optional[str] = None,
        query: Optional[str] = None,
        exclude_chats: Optional[bool] = None,
        has_attachment: Optional[bool] = None,
        size: Optional[int] = None,
        size_comparison: Optional[str] = None,
        add_label_ids: Optional[List[str]] = None,
        remove_label_ids: Optional[List[str]] = None,
        forward: Optional[str] = None,
        never_spam: Optional[bool] = None,
    ) -> Dict[str, Any] | str:
        """Create a new Gmail filter with specified criteria and actions."""
        try:
            # Build criteria
            criteria = {}
            if from_email:
                criteria["from"] = from_email
            if to_email:
                criteria["to"] = to_email
            if subject:
                criteria["subject"] = subject
            if query:
                criteria["query"] = query
            if exclude_chats is not None:
                criteria["excludeChats"] = exclude_chats
            if has_attachment is not None:
                criteria["hasAttachment"] = has_attachment
            if size is not None:
                criteria["size"] = size
            if size_comparison:
                criteria["sizeComparison"] = size_comparison

            # Build action
            action = {}
            if add_label_ids:
                action["addLabelIds"] = add_label_ids
            if remove_label_ids:
                action["removeLabelIds"] = remove_label_ids
            if forward:
                action["forward"] = forward
            if never_spam is not None:
                action["neverSpam"] = never_spam

            filter_object = {"criteria": criteria, "action": action}

            result = (
                self.service.users()
                .settings()
                .filters()
                .create(userId="me", body=filter_object)
                .execute()
            )

            logger.info(f"Filter created with ID: {result['id']}")
            return {
                "id": result["id"],
                "criteria": result.get("criteria", {}),
                "action": result.get("action", {}),
                "status": "filter_created",
            }
        except HttpError as error:
            logger.error(f"Failed to create filter: {error}")
            return f"Failed to create filter: {str(error)}"

    async def delete_filter(self, filter_id: str) -> str:
        """Delete a Gmail filter."""
        try:
            self.service.users().settings().filters().delete(
                userId="me", id=filter_id
            ).execute()
            logger.info(f"Filter {filter_id} deleted")
            return "Filter deleted successfully."
        except HttpError as error:
            logger.error(f"Failed to delete filter {filter_id}: {error}")
            return f"Failed to delete filter: {str(error)}"

    # Search Methods

    async def search_emails(
        self, query: str, max_results: int = 50
    ) -> List[Dict[str, Any]] | str:
        """Search emails using Gmail's search syntax."""
        try:
            result = (
                self.service.users()
                .messages()
                .list(userId="me", q=query, maxResults=max_results)
                .execute()
            )

            messages = result.get("messages", [])
            detailed_emails = []

            for message in messages:
                try:
                    msg = (
                        self.service.users()
                        .messages()
                        .get(userId="me", id=message["id"], format="metadata")
                        .execute()
                    )

                    headers = {
                        h["name"]: h["value"]
                        for h in msg.get("payload", {}).get("headers", [])
                    }

                    detailed_emails.append(
                        {
                            "id": message["id"],
                            "subject": headers.get("Subject", "No subject"),
                            "sender": headers.get("From", "Unknown sender"),
                            "recipient": headers.get("To", "Unknown recipient"),
                            "date": headers.get("Date", ""),
                            "snippet": msg.get("snippet", ""),
                        }
                    )
                except Exception as e:
                    logger.warning(
                        f"Failed to get details for email {message.get('id', 'unknown')}: {e}"
                    )
                    continue

            logger.info(f"Search found {len(detailed_emails)} emails")
            return detailed_emails
        except HttpError as error:
            logger.error(f"Failed to search emails with query '{query}': {error}")
            return f"Failed to search emails: {str(error)}"

    # Folder/Organization Methods

    async def create_folder(self, name: str) -> Dict[str, Any] | str:
        """Create a new folder (implemented as nested label)."""
        # In Gmail, folders are implemented as nested labels
        return await self.create_label(name)

    async def move_to_folder(self, email_id: str, folder_id: str) -> str:
        """Move an email to a folder."""
        try:
            # Remove from inbox and add folder label
            self.service.users().messages().modify(
                userId="me",
                id=email_id,
                body={"addLabelIds": [folder_id], "removeLabelIds": ["INBOX"]},
            ).execute()
            logger.info(f"Email {email_id} moved to folder {folder_id}")
            return "Email moved to folder successfully."
        except HttpError as error:
            logger.error(
                f"Failed to move email {email_id} to folder {folder_id}: {error}"
            )
            return f"Failed to move email to folder: {str(error)}"

    async def list_folders(self) -> List[Dict[str, Any]] | str:
        """List all folders (nested labels)."""
        # In Gmail, folders are user-created labels
        try:
            result = self.service.users().labels().list(userId="me").execute()
            labels = result.get("labels", [])

            # Filter for user-created labels (folders)
            folders = []
            for label in labels:
                if label.get("type") == "user":
                    folders.append(
                        {
                            "id": label["id"],
                            "name": label["name"],
                            "messages_total": label.get("messagesTotal", 0),
                            "messages_unread": label.get("messagesUnread", 0),
                        }
                    )

            logger.info(f"Retrieved {len(folders)} folders")
            return folders
        except HttpError as error:
            logger.error(f"Failed to list folders: {error}")
            return f"Failed to list folders: {str(error)}"

    # Batch Operations

    async def batch_archive(self, query: str, max_emails: int = 100) -> Dict[str, Any]:
        """Archive multiple emails matching a search query."""
        try:
            # First, search for emails matching the query
            result = (
                self.service.users()
                .messages()
                .list(userId="me", q=query, maxResults=max_emails)
                .execute()
            )

            messages = result.get("messages", [])
            archived_count = 0
            errors = []

            for message in messages:
                try:
                    self.service.users().messages().modify(
                        userId="me",
                        id=message["id"],
                        body={"removeLabelIds": ["INBOX"]},
                    ).execute()
                    archived_count += 1
                except HttpError as e:
                    errors.append(f"Failed to archive {message['id']}: {str(e)}")
                    logger.warning(f"Failed to archive email {message['id']}: {e}")

            logger.info(f"Batch archived {archived_count} emails")
            return {
                "archived_count": archived_count,
                "total_found": len(messages),
                "errors": errors,
                "status": "completed",
            }
        except HttpError as error:
            logger.error(f"Failed to batch archive with query '{query}': {error}")
            return {
                "error": f"Failed to batch archive: {str(error)}",
                "archived_count": 0,
                "status": "failed",
            }

    async def list_archived(self, max_results: int = 50) -> List[Dict[str, Any]] | str:
        """List archived emails."""
        try:
            # Search for emails that are not in inbox (archived)
            query = "-in:inbox"
            result = (
                self.service.users()
                .messages()
                .list(userId="me", q=query, maxResults=max_results)
                .execute()
            )

            messages = result.get("messages", [])
            detailed_emails = []

            for message in messages:
                try:
                    msg = (
                        self.service.users()
                        .messages()
                        .get(userId="me", id=message["id"], format="metadata")
                        .execute()
                    )

                    headers = {
                        h["name"]: h["value"]
                        for h in msg.get("payload", {}).get("headers", [])
                    }

                    detailed_emails.append(
                        {
                            "id": message["id"],
                            "subject": headers.get("Subject", "No subject"),
                            "sender": headers.get("From", "Unknown sender"),
                            "date": headers.get("Date", ""),
                            "snippet": msg.get("snippet", ""),
                        }
                    )
                except Exception as e:
                    logger.warning(
                        f"Failed to get details for archived email {message.get('id', 'unknown')}: {e}"
                    )
                    continue

            logger.info(f"Retrieved {len(detailed_emails)} archived emails")
            return detailed_emails
        except HttpError as error:
            logger.error(f"Failed to list archived emails: {error}")
            return f"Failed to list archived emails: {str(error)}"
