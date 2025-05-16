from pydantic import HttpUrl

from sqlalchemy.types import TypeDecorator, String


class HttpUrlType(TypeDecorator):
    impl = String
    cache_ok = True
    python_type = HttpUrl

    def process_bind_param(self, value: HttpUrl | None, dialect) -> str:
        if value is None:
            return value
        try:
            if value is not None:
                value = str(value)
            return value
        except Exception:
            return value

    def process_result_value(self, value: HttpUrl | None, dialect) -> str:
        try:
            if value is not None:
                value = str(value)
        except Exception:
            pass
        return value
