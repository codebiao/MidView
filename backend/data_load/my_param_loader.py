"""Load my_param.json, return MyParam struct."""

import dataclasses
import json

from backend.models.my_param import MyParam, MidlevelSysParam, EdsParam, XyCalParam


def load_my_param(file_path: str) -> MyParam | None:
    """Load my_param.json from *file_path*, return MyParam."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            raw = json.load(f)
    except FileNotFoundError:
        return None

    raw["midlevel_sys_param"] = MidlevelSysParam(**raw.get("midlevel_sys_param", {}))
    raw["eds_param"] = EdsParam(**raw.get("eds_param", {}))
    raw["xy_cal_param"] = XyCalParam(**raw.get("xy_cal_param", {}))
    top_fields = {f.name for f in dataclasses.fields(MyParam)}
    return MyParam(**{k: v for k, v in raw.items() if k in top_fields})