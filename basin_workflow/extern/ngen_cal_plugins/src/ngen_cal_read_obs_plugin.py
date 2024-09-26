from __future__ import annotations

import typing

from ngen.cal import hookimpl
from hypy.nexus import Nexus
import pandas as pd
from pathlib import Path
import numpy as np

if typing.TYPE_CHECKING:
    from datetime import datetime
    from ngen.cal.meta import JobMeta
    from ngen.cal.model import ModelExec


class Proxy:
    def __init__(self, obj):
        self._proxy_obj = obj

    def set_proxy(self, obj):
        self._proxy_obj = obj

    def __getattribute__(self, name: str):
        if name not in ("_proxy_obj", "set_proxy"):
            return getattr(super().__getattribute__("_proxy_obj"), name)
        return super().__getattribute__(name)

    def __repr__(self):
        return repr(super().__getattribute__("_proxy_obj"))

    def __hash__(self):
        return hash(super().__getattribute__("_proxy_obj"))


class ReadObservedData:
    def __init__(self):
        self.proxy = Proxy(pd.Series())
        self.ft3_to_m3 = 0.0283168
        self.units     = None
        self.window    = 1

    @hookimpl
    def ngen_cal_model_configure(self, config: ModelExec) -> None:

        # read file
        #df = pd.read_parquet(config.plugin_settings["ngen_cal_read_obs_data"]["obs_data_path"])
        df = pd.read_csv(config.plugin_settings["ngen_cal_read_obs_data"]["obs_data_path"], usecols=['value_time', 'value'])
        self.units  = config.plugin_settings["ngen_cal_read_obs_data"]["units"]
        self.window = int(config.plugin_settings["ngen_cal_read_obs_data"]["window"])

        df["value_time"] = pd.to_datetime(df['value_time'])
        if (self.units == "ft3/sec" or self.units == "ft3/s"):
            df["value"] = self.ft3_to_m3 * df["value"]
            
        #config.plugin_settings["ngen_cal_read_observed_data"]["observation_file"]

        nexus = self.obs_kwargs["nexus"]
        start = self.obs_kwargs["start_time"]
        end = self.obs_kwargs["end_time"]
        simulation_interval = self.obs_kwargs["simulation_interval"]

        divide_id = nexus.id
        # subset into `pd.Series` that is indexed by `datetime` with a name
        df.set_index("value_time", inplace=True)
        df = df.loc[start:end]

        # get total hours to ensure the length of observed data is consistent with the leght of simulated data
        total_hours = (end - start).total_seconds()/3600.
        length = int(total_hours/self.window)

        assert (length > 0)

        #ds = df["value"].resample(simulation_interval).nearest()
        ds = df["value"][:length]
        ds.rename("obs_flow", inplace=True)

        self.proxy.set_proxy(ds)

    @hookimpl
    def ngen_cal_model_observations(
        self,
        nexus: Nexus,
        start_time: datetime,
        end_time: datetime,
        simulation_interval: pd.Timedelta,
    ) -> pd.Series:

        self.obs_kwargs = {
            "nexus": nexus,
            "start_time": start_time,
            "end_time": end_time,
            "simulation_interval": simulation_interval,
        }
        return self.proxy

    @hookimpl(wrapper=True)
    def ngen_cal_model_output(
        self, id: str | None
    ) -> typing.Generator[None, pd.Series, pd.Series]:

        sim = yield

        if sim is None:
            return None

        index = self.proxy._proxy_obj.index
        sim_local = sim.copy()

        mean_values = np.reshape(sim_local.values,(-1,self.window)).mean(axis=1)

        assert (len(mean_values) == len(index))
        ds_sim = pd.Series(mean_values, index=index)
        ds_sim.rename("sim_flow", inplace=True)

        assert isinstance(sim_local, pd.Series), f"expected pd.Series, got {type(sim_local)!r}"

        return ds_sim
