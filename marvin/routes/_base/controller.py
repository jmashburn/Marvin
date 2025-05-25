"""
This module provides utilities for creating Class-Based Views (CBVs) in FastAPI,
largely adapted from the `fastapi-utils` project by dmontagu. It allows developers
to structure their route handlers within classes, leveraging Python's object-oriented
features, while still integrating with FastAPI's dependency injection and routing
mechanisms.

The core component is the `controller` decorator, which registers a class with a
FastAPI router, making its methods available as route handlers. The module also
includes helper functions for inspecting and modifying class signatures to ensure
compatibility with FastAPI's DI system.

Original `fastapi-utils` project: https://github.com/dmontagu/fastapi-utils
Original Pydantic V1 typing utilities: https://github.com/pydantic/pydantic (V1 branch)

Note: This code is subject to the MIT license of the original `fastapi-utils` project.
"""

import inspect
from collections.abc import Callable
from typing import Any, ClassVar, ForwardRef, TypeVar, cast, get_origin, get_type_hints

from fastapi import APIRouter, Depends
from fastapi.routing import APIRoute
from starlette.routing import Route, WebSocketRoute # Used for route instance checks

# Type variable for generic decorators
T = TypeVar("T")

# Internal keys used to store metadata on CBV classes
CBV_CLASS_KEY = "__cbv_class__"  # Marks a class as a CBV
INCLUDE_INIT_PARAMS_KEY = "__include_init_params__" # Controls if __init__ params are included in DI
RETURN_TYPES_FUNC_KEY = "__return_types_func__" # Stores a function that provides return type hints


def controller(router: APIRouter, *urls: str) -> Callable[[type[T]], type[T]]:
    """
    A decorator to register a class as a controller (Class-Based View) with a FastAPI router.

    Methods of the decorated class that are already decorated as FastAPI route handlers
    (e.g., using `@router.get`, `@router.post`) will be adapted to work within
    the CBV pattern. The first argument of these methods (conventionally `self`)
    will be injected with an instance of the controller class, created using
    FastAPI's dependency injection.

    This allows for organizing related endpoints within a class, sharing dependencies,
    and using object-oriented principles.

    Args:
        router (APIRouter): The FastAPI router instance to which the controller's
                            routes will be added.
        *urls (str): One or more URL prefixes for the routes defined in this controller.
                     These are applied in addition to any prefix on the main `router`.
                     If multiple URLs are provided, routes might be duplicated under
                     each prefix, or specific methods might map to specific URLs if
                     the `_allocate_routes_by_method_name` logic handles it.
                     (Note: The original `fastapi-utils` behavior with multiple `*urls`
                     might lead to routes being registered under each specified URL prefix.
                     If specific method-to-URL mapping is needed, it's often handled by
                     decorating methods directly with full paths.)

    Returns:
        Callable[[type[T]], type[T]]: A decorator function that takes the class
                                      to be converted into a CBV.
    """

    def decorator(cls: type[T]) -> type[T]:
        """
        Inner decorator function that processes the class.
        It calls `_cbv` to perform the actual registration and modification.
        """
        # Mark the class as a CBV and process its routes
        return _cbv(router, cls, *urls)

    return decorator


def _cbv(router: APIRouter, cls: type[T], *urls: str, instance: Any | None = None) -> type[T]:
    """
    Core logic for converting a class to a Class-Based View (CBV).

    This function initializes the CBV class (modifying its `__init__` and `__signature__`)
    and registers its methods as endpoints on the provided router.

    Args:
        router (APIRouter): The FastAPI router.
        cls (type[T]): The class to convert to a CBV.
        *urls (str): URL prefixes for the controller's routes.
        instance (Any | None, optional): An existing instance to use. If provided,
            the class's DI behavior might change. Defaults to None.

    Returns:
        type[T]: The modified class, now acting as a CBV.
    """
    _init_cbv(cls, instance)  # Prepare the class for dependency injection
    _register_endpoints(router, cls, *urls)  # Find and register endpoint methods
    return cls


# The following two functions (_check_classvar, _is_classvar) are utility functions
# copied from Pydantic V1 source code. They are used to identify ClassVar annotations
# so that they are not treated as injectable dependencies for the CBV class.

def _check_classvar(v: type[Any] | None) -> bool:
    """
    Checks if a type annotation is `typing.ClassVar` (Pydantic V1 internal utility).
    """
    if v is None:
        return False
    # Direct check for ClassVar or its origin in generic ClassVars (e.g., ClassVar[int])
    return v.__class__ == ClassVar.__class__ and getattr(v, "_name", None) == "ClassVar"


def _is_classvar(ann_type: type[Any]) -> bool:
    """
    Determines if a type annotation is `typing.ClassVar` or a `ForwardRef` to it (Pydantic V1 internal utility).
    """
    # Check if the type itself or its origin (for generics like ClassVar[int]) is ClassVar
    if _check_classvar(ann_type) or _check_classvar(get_origin(ann_type)):
        return True

    # Handle ForwardRef annotations like "ClassVar[...]"
    if isinstance(ann_type, ForwardRef) and ann_type.__forward_arg__.startswith("ClassVar["):
        return True

    return False


def _init_cbv(cls: type[Any], instance: Any | None = None) -> None:
    """
    Initializes a class for CBV usage (called by `_cbv`).

    This function idempotently modifies the class:
    - Updates `__init__` to inject dependencies defined as class attributes
      (excluding ClassVars and attributes starting with '_').
    - Sets a new `__signature__` for `__init__` to guide FastAPI's DI.
    - Private attributes (starting with '_') are initialized to None unless
      already set by the original `__init__`.

    Args:
        cls (type[Any]): The class to initialize.
        instance (Any | None): If an instance is provided, the DI behavior for
                               `__init__` might be altered based on `INCLUDE_INIT_PARAMS_KEY`.
    """
    if getattr(cls, CBV_CLASS_KEY, False):  # Check if already initialized
        return

    original_init: Callable[..., Any] = cls.__init__
    original_signature = inspect.signature(original_init)
    # Parameters of the original __init__ (excluding 'self')
    original_init_params = list(original_signature.parameters.values())[1:]
    
    # Parameters to keep for the new __init__ signature (excluding *args, **kwargs from original)
    new_init_signature_params = [
        p for p in original_init_params 
        if p.kind not in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD)
    ]

    private_attributes_to_none: list[str] = [] # Store names of private attributes to set to None

    # Identify class-level dependencies to inject
    class_dependency_names: list[str] = []
    type_hints = get_type_hints(cls) # Get all type hints for the class

    for name, hint in type_hints.items():
        if _is_classvar(hint):  # Skip ClassVar attributes
            continue

        if name.startswith("_"): # Handle private attributes
            private_attributes_to_none.append(name)
            continue

        # This attribute is a dependency to be injected
        class_dependency_names.append(name)
        # Create a parameter for this dependency for the new __init__ signature
        # It's keyword-only, and its default is taken from the class attribute if present
        param_kwargs = {"default": getattr(cls, name, inspect.Parameter.empty)} # Use inspect.Parameter.empty for no default
        new_init_signature_params.append(
            inspect.Parameter(name=name, kind=inspect.Parameter.KEYWORD_ONLY, annotation=hint, **param_kwargs)
        )
    
    # Create the new signature for __init__
    # If no instance is provided OR if the class explicitly wants init params included for DI
    if not instance or hasattr(cls, INCLUDE_INIT_PARAMS_KEY):
        final_signature = original_signature.replace(parameters=new_init_signature_params)
    else: # If an instance is provided and init params are not explicitly included
        final_signature = inspect.Signature(()) # Empty signature, DI won't call __init__ with class vars

    # Define the new __init__ method
    def new_init(self: Any, *args: Any, **kwargs: Any) -> None:
        # Inject class-level dependencies first
        for dep_name in class_dependency_names:
            if dep_name in kwargs: # Dependency provided via FastAPI's DI
                setattr(self, dep_name, kwargs.pop(dep_name))
            # If not in kwargs, it might have a default value from class or be an error (FastAPI handles missing DI)

        # If an instance is provided and we are not including init params,
        # effectively make `self` become that `instance`.
        if instance and not hasattr(cls, INCLUDE_INIT_PARAMS_KEY):
            # This is a more complex scenario, potentially for singleton-like behavior or pre-configured instances.
            # It replaces the newly created `self`'s state with that of the provided `instance`.
            self.__class__ = instance.__class__ #
            self.__dict__ = instance.__dict__
        else:
            # Call the original __init__ with its original args and remaining kwargs
            original_init(self, *args, **kwargs)

    # Replace original __init__ and __signature__
    cls.__signature__ = final_signature
    cls.__init__ = new_init
    setattr(cls, CBV_CLASS_KEY, True) # Mark as initialized

    # Ensure private attributes (like _repos, _logger in BaseController) are set to None initially
    # if not handled by the original __init__ or class definition.
    for name in private_attributes_to_none:
        if not hasattr(cls, name): # Or if getattr(cls, name, None) is Ellipsis from param_kwargs setup
             setattr(cls, name, None)


def _register_endpoints(router: APIRouter, cls: type[Any], *urls: str) -> None:
    """
    Registers methods of the CBV class as route endpoints on the router.

    It iterates through methods of `cls`. If a method is already part of a route
    defined on `router` (e.g., decorated with `@router.get`), its signature is
    updated for CBV dependency injection, and it's re-added to a temporary
    `cbv_router`. This `cbv_router` is then included in the original `router`.

    The `*urls` parameter seems to be intended for prefixing or specific URL allocation,
    handled by `_allocate_routes_by_method_name`.

    Args:
        router (APIRouter): The main FastAPI router.
        cls (type[Any]): The CBV class.
        *urls (str): URL prefixes.
    """
    cbv_specific_router = APIRouter() # Temporary router for CBV methods
    function_members = inspect.getmembers(cls, inspect.isfunction)

    # This function seems to handle cases where routes are defined by method names (e.g. def get(): ...).
    # It allocates routes on the main `router` based on method names for each specified URL.
    for url_prefix in urls:
        _allocate_routes_by_method_name(router, url_prefix, function_members)

    # Check for duplicate route definitions (path + method) on the main router
    # This can happen if multiple URLs in *urls lead to the same effective route definition.
    # Or if _allocate_routes_by_method_name adds routes that conflict.
    router_path_methods = []
    for r in router.routes:
        if isinstance(r, APIRoute):
            router_path_methods.append((r.path, frozenset(r.methods or {}))) # Use frozenset for hashability
    if len(set(router_path_methods)) != len(router_path_methods):
        # This exception message might be too generic. A more detailed one could list duplicates.
        raise Exception("An identical route (path and method) has been defined more than once on the router.")

    # Map existing route endpoints on the main router to their index and route object
    # This is to re-register them correctly for the CBV pattern.
    # Only considers FastAPI's Route or WebSocketRoute instances.
    numbered_routes_by_endpoint_fn = {
        route.endpoint: (i, route) 
        for i, route in enumerate(router.routes) 
        if isinstance(route, (Route, WebSocketRoute))
    }

    # Store routes that belong to the CBV to re-add them later, ordered by original definition
    routes_to_re_add_ordered: list[tuple[int, Route | WebSocketRoute]] = []
    
    # Remove original prefix length to get relative path for CBV router
    # This seems to assume that routes on the main router might already include its prefix.
    main_router_prefix_len = len(router.prefix)

    for _, func_member in function_members: # Iterate through all functions in the class
        # Check if this function was registered as an endpoint on the main router
        indexed_route_info = numbered_routes_by_endpoint_fn.get(func_member)

        if indexed_route_info is None:
            continue # This function is not a registered endpoint, skip it.

        original_index, route_object = indexed_route_info
        
        # Adjust route path: remove main router's prefix if it was part of the path.
        # This prepares the route for inclusion in the `cbv_specific_router` which will
        # then be included into the main router with the prefix.
        if route_object.path.startswith(router.prefix):
            route_object.path = route_object.path[main_router_prefix_len:]
            
        routes_to_re_add_ordered.append((original_index, route_object))
        router.routes.remove(route_object) # Temporarily remove from main router

        # Update the function signature for CBV dependency injection
        _update_cbv_route_endpoint_signature(cls, route_object)
    
    # Sort routes by their original index to maintain order
    routes_to_re_add_ordered.sort(key=lambda item: item[0])

    # Add the processed routes to our temporary CBV-specific router
    cbv_specific_router.routes = [route for _, route in routes_to_re_add_ordered]

    # Hacky part: Include the CBV router back into the main router.
    # The main router's prefix is temporarily cleared and then re-applied
    # when including the `cbv_specific_router`. This is done to ensure that
    # the paths within `cbv_specific_router` (which are now relative) are correctly
    # prefixed by the main router's original prefix.
    # This implies the main `router` object passed to `controller()` might be
    # mutated in a way that could be surprising if it's used for other things later.
    original_main_router_prefix = router.prefix
    router.prefix = "" # Temporarily clear prefix
    router.include_router(cbv_specific_router, prefix=original_main_router_prefix) # Re-apply prefix here


def _allocate_routes_by_method_name(
    router: APIRouter, url: str, function_members: list[tuple[str, Any]]
) -> None:
    """
    Automatically creates routes for methods in a CBV based on their names (e.g., `get`, `post`).

    If a method name matches a standard HTTP verb (e.g., 'get', 'post', 'put', 'delete'),
    and it's not already explicitly routed for the given `url`, this function
    will attempt to register it as an API route on the `router`.

    This supports a convention-over-configuration approach where method names
    imply their HTTP method.

    Args:
        router (APIRouter): The router to add routes to.
        url (str): The URL path for these routes.
        function_members (list[tuple[str, Any]]): A list of (name, function_object)
                                                 pairs from the CBV class.
    """
    # sourcery skip: merge-nested-ifs (original skip comment from source)
    
    # Get endpoints and paths of routes already registered on the router
    # to avoid duplicating route registrations for the same (function, url) pair.
    existing_routes_info: list[tuple[Any, str]] = []
    for r in router.routes:
        if isinstance(r, APIRoute): # Only consider APIRoutes
            existing_routes_info.append((r.endpoint, r.path))

    for method_name, func_obj in function_members:
        # Check if method_name corresponds to a router method (like 'get', 'post')
        # and is a public method (not starting/ending with dunder).
        if hasattr(router, method_name) and \
           not method_name.startswith("__") and \
           not method_name.endswith("__"):
            
            # Check if this specific function for this URL isn't already registered
            if (func_obj, url) not in existing_routes_info:
                # Default FastAPI route parameters
                response_model = None
                responses = None
                kwargs_for_route = {} # Additional kwargs for router.api_route
                status_code = 200 # Default HTTP 200 OK

                # Check if the function has stored return type metadata (set by another decorator perhaps)
                # This allows fine-tuning response_model, status_code, etc., on a per-method basis.
                if return_types_provider_func := getattr(func_obj, RETURN_TYPES_FUNC_KEY, None):
                    # Call the stored function to get route-specific parameters
                    response_model, status_code, responses, kwargs_for_route = return_types_provider_func()

                # Dynamically get the router's HTTP method (e.g., router.get, router.post)
                # This part was originally router.api_route with methods=[name.capitalize()].
                # Using getattr(router, method_name) is more direct if method_name is 'get', 'post', etc.
                # However, api_route is more general. The original capitalized method might be a convention.
                # Sticking to `api_route` with capitalized method for closer adherence if that was intended.
                http_method_registrar = router.api_route 
                
                # Register the function as an API route for the given URL and HTTP method
                # The HTTP method is derived from the function's name (e.g., 'get' -> 'GET')
                route_decorator = http_method_registrar(
                    url,
                    methods=[method_name.upper()], # HTTP method (e.g., GET, POST)
                    response_model=response_model,
                    status_code=status_code,
                    responses=responses,
                    **kwargs_for_route,
                )
                route_decorator(func_obj) # Apply the route decorator to the function


def _update_cbv_route_endpoint_signature(cls: type[Any], route: Route | WebSocketRoute) -> None:
    """
    Updates the signature of a CBV method endpoint for FastAPI dependency injection.

    It takes the original endpoint function, inspects its signature, and modifies
    the first parameter (conventionally `self`) to include `Depends(cls)`. This
    tells FastAPI to inject an instance of the CBV class (`cls`) as the first
    argument when handling a request for this route. Other parameters are made
    keyword-only to align with FastAPI's expectations for DI after `Depends`.

    Args:
        cls (type[Any]): The CBV class whose instance will be injected.
        route (Route | WebSocketRoute): The Starlette/FastAPI route object whose
                                        endpoint signature needs updating.
    """
    original_endpoint_func = route.endpoint
    original_signature = inspect.signature(original_endpoint_func)
    original_parameters: list[inspect.Parameter] = list(original_signature.parameters.values())

    if not original_parameters: # Should not happen for a method
        return

    # The first parameter is assumed to be 'self' (or equivalent)
    self_param = original_parameters[0]
    # Modify 'self' to be injected with an instance of the CBV class
    injected_self_param = self_param.replace(default=Depends(cls))

    # Subsequent parameters are made keyword-only, a common pattern with FastAPI DI
    # when the first arg is a `Depends`.
    remaining_params = [
        param.replace(kind=inspect.Parameter.KEYWORD_ONLY) for param in original_parameters[1:]
    ]
    
    updated_parameters = [injected_self_param] + remaining_params
    updated_signature = original_signature.replace(parameters=updated_parameters)
    
    # Directly assign the new signature to the endpoint function
    # This is a somewhat advanced Python feature, modifying a function's perceived signature.
    route.endpoint.__signature__ = updated_signature
