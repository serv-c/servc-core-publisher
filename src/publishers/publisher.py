from typing import Any, Callable, Dict, Tuple

from servc.svc.config import Config

ENGINE_FUNC = Callable[[Config, str, Any, Any], Tuple[str, Dict[str, Any]]]
