"""Pydantic schemas for email templates."""

from datetime import datetime
from pydantic import UUID4, Field

from marvin.schemas._marvin import _MarvinModel


class EmailTemplateCreate(_MarvinModel):
    """Schema for creating a new email template."""

    template_type: str = Field(..., description="Type of email (invitation, password_reset, notification, test)")
    group_id: UUID4 | None = Field(None, description="Workspace ID - null for system-wide templates")
    name: str = Field(..., description="Human-readable template name")
    description: str | None = Field(None, description="Description of when this template is used")
    subject: str = Field(..., description="Email subject line - supports Jinja2 variables")
    header_text: str | None = Field(None, description="Header text (structured mode with default.html)")
    message_top: str | None = Field(None, description="Top message (structured mode with default.html)")
    message_bottom: str | None = Field(None, description="Bottom message (structured mode with default.html)")
    button_text: str | None = Field(None, description="Button text (structured mode with default.html)")
    custom_html: str | None = Field(None, description="Full custom HTML - if set, overrides structured fields")
    available_variables: dict | None = Field(None, description="Documentation of available variables")
    enabled: bool = Field(True, description="Whether this template is active")


class EmailTemplateUpdate(_MarvinModel):
    """Schema for updating an email template."""

    name: str | None = None
    description: str | None = None
    subject: str | None = None
    header_text: str | None = None
    message_top: str | None = None
    message_bottom: str | None = None
    button_text: str | None = None
    custom_html: str | None = None
    available_variables: dict | None = None
    enabled: bool | None = None


class EmailTemplateRead(_MarvinModel):
    """Schema for reading an email template."""

    id: UUID4
    template_type: str
    group_id: UUID4 | None
    name: str
    description: str | None
    subject: str
    header_text: str | None
    message_top: str | None
    message_bottom: str | None
    button_text: str | None
    custom_html: str | None
    available_variables: dict | None
    enabled: bool
    created_at: datetime
    update_at: datetime

    model_config = {"from_attributes": True}


class EmailTemplateSummary(_MarvinModel):
    """Summary schema for listing email templates."""

    id: UUID4
    template_type: str
    name: str
    description: str | None
    enabled: bool
    group_id: UUID4 | None = None  # None = system template, set = workspace customization

    model_config = {"from_attributes": True}
