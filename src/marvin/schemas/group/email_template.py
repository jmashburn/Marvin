"""Pydantic schemas for email templates."""

from datetime import datetime

from pydantic import UUID4, Field

from marvin.schemas._marvin import _MarvinModel


class EmailTemplateCreate(_MarvinModel):
    """Schema for creating a new email template."""

    template_type: str = Field(..., description="Type of email (invitation, password_reset, welcome, custom, test)")
    group_id: UUID4 | None = Field(None, description="Workspace ID - null for system-wide templates")
    name: str = Field(..., description="Human-readable template name")
    description: str | None = Field(None, description="Description of when this template is used")
    subject: str = Field(..., description="Email subject line - supports Jinja2 variables")
    body_markdown: str | None = Field(None, description="Markdown body rendered via default.html template")
    custom_html: str | None = Field(None, description="Full custom HTML - if set, overrides body_markdown")
    available_variables: dict | None = Field(None, description="Documentation of available variables")
    enabled: bool = Field(True, description="Whether this template is active")


class EmailTemplateUpdate(_MarvinModel):
    """Schema for updating an email template."""

    name: str | None = None
    description: str | None = None
    subject: str | None = None
    body_markdown: str | None = None
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
    body_markdown: str | None
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
