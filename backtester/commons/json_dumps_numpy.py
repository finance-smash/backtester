from typing import Any
import json
from json import JSONEncoder
import numpy as np

class NumpyArrayEncoder(JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if obj == np.inf or obj == -np.inf or np.isnan(obj):
            return str(obj)
        return JSONEncoder.default(self, obj)


def json_dumps_numpy(with_numpy_objct: Any, indent: int = 4) -> str:
    json_results = json.dumps(with_numpy_objct, indent=indent, cls=NumpyArrayEncoder)
    return json_results