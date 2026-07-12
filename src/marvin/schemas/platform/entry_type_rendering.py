"""Entry type rendering and capabilities definition models."""

from marvin.schemas._marvin import _MarvinModel


class RenderingDefinition(_MarvinModel):
    """Describes how entries of this type should be rendered on the frontend."""

    renderer: str | None = None
    package: str | None = None
    version: str | None = None
    config: dict | None = None


class CapabilitiesDefinition(_MarvinModel):
    """Describes behavioral capabilities for entries of this type."""

    publishable: bool = True
    submittable: bool = False
    routable: bool = True
