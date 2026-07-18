from pathlib import Path

PARENT = Path(__file__).parent.parent
PROJECT_DIR = Path(__file__).parent.parent.parent.parent
MARVIN_DIR = PARENT.parent.parent / "marvin"


class Directories:
    out_dir = PARENT / "generated"


class CodeTemplates:
    interface = PARENT / "templates" / "interface.js"
    pytest_routes = PARENT / "templates" / "test_routes.py.j2"


class ModuleTemplates:
    base = PARENT / "templates" / "module"
    db_model = base / "db_model.py.j2"
    schema = base / "schema.py.j2"
    repo = base / "repo.py.j2"
    controller = base / "controller.py.j2"


class MarvinPaths:
    db_models_platform = MARVIN_DIR / "db" / "models" / "platform"
    schemas_platform = MARVIN_DIR / "schemas" / "platform"
    repos_platform = MARVIN_DIR / "repos" / "platform"
    repo_factory = MARVIN_DIR / "repos" / "repository_factory.py"
    routes_platform = MARVIN_DIR / "routes" / "platform"


class CodeDest:
    interface = PARENT / "generated" / "interface.js"
    pytest_routes = PARENT / "generated" / "test_routes.py"
    use_locales = PROJECT_DIR / "frontend" / "composables" / "use-locales" / "available-locales.ts"


class CodeKeys:
    """Hard coded comment IDs that are used to generate code"""

    nuxt_local_messages = "MESSAGE_LOCALES"
    nuxt_local_dates = "DATE_LOCALES"

    platform_model_imports = "PLATFORM_MODEL_IMPORTS"
    platform_model_all = "PLATFORM_MODEL_ALL"
    platform_schema_imports = "PLATFORM_SCHEMA_IMPORTS"
    platform_schema_all = "PLATFORM_SCHEMA_ALL"
    platform_repo_imports = "PLATFORM_REPO_IMPORTS"
    platform_repo_all = "PLATFORM_REPO_ALL"
    factory_repo_imports = "FACTORY_REPO_IMPORTS"
    factory_repo_properties = "FACTORY_REPO_PROPERTIES"
    platform_route_imports = "PLATFORM_ROUTE_IMPORTS"
    platform_route_includes = "PLATFORM_ROUTE_INCLUDES"
