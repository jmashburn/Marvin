"""Database model for email templates."""

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from marvin.db.models._model_base import BaseMixins, SqlAlchemyBase


class EmailTemplateModel(SqlAlchemyBase, BaseMixins):
    """Email templates stored in the database.

    Supports both system-wide templates (group_id=None) and workspace-specific
    templates (group_id set). Templates are HTML with Jinja2 variable support.

    Template types:
    - invitation: Workspace invitation emails
    - password_reset: Password reset emails
    - notification: General notification emails
    - test: Test emails for SMTP verification
    """

    __tablename__ = "email_templates"

    # Template identifier and scope
    template_type: Mapped[str] = mapped_column(
        sa.String,
        nullable=False,
        index=True,
        doc="Type of email template (invitation, password_reset, notification, test)",
    )
    group_id: Mapped[str | None] = mapped_column(
        sa.String,
        sa.ForeignKey("groups.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        doc="Group/workspace ID - null for system-wide templates",
    )

    # Template metadata
    name: Mapped[str] = mapped_column(
        sa.String,
        nullable=False,
        doc="Human-readable name for the template",
    )
    description: Mapped[str | None] = mapped_column(
        sa.String,
        nullable=True,
        doc="Description of when this template is used",
    )

    # Email content - supports two modes:
    # 1. Structured mode: Use subject + content fields, rendered with default.html template
    # 2. Custom HTML mode: Use custom_html with full HTML template (overrides structured fields)
    subject: Mapped[str] = mapped_column(
        sa.String,
        nullable=False,
        doc="Email subject line - supports Jinja2 variables like {{ user_name }}",
    )
    header_text: Mapped[str | None] = mapped_column(
        sa.String,
        nullable=True,
        doc="Header text for structured template (used with default.html)",
    )
    message_top: Mapped[str | None] = mapped_column(
        sa.Text,
        nullable=True,
        doc="Top message for structured template (used with default.html)",
    )
    message_bottom: Mapped[str | None] = mapped_column(
        sa.Text,
        nullable=True,
        doc="Bottom message for structured template (used with default.html)",
    )
    button_text: Mapped[str | None] = mapped_column(
        sa.String,
        nullable=True,
        doc="Button text for structured template (used with default.html)",
    )
    custom_html: Mapped[str | None] = mapped_column(
        sa.Text,
        nullable=True,
        doc="Full custom HTML template - if set, overrides structured fields. Supports Jinja2 variables.",
    )

    # Template variables documentation
    available_variables: Mapped[dict | None] = mapped_column(
        sa.JSON,
        nullable=True,
        doc="JSON object documenting available variables for this template type",
    )

    # Status
    enabled: Mapped[bool] = mapped_column(
        sa.Boolean,
        nullable=False,
        default=True,
        doc="Whether this template is active",
    )

    # Unique constraint: one template per type per workspace
    __table_args__ = (
        sa.UniqueConstraint(
            "template_type",
            "group_id",
            name="uq_email_template_type_group",
        ),
    )
