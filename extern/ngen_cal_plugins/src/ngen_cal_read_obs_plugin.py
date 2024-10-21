from __future__ import annotations

import typing

from ngen.cal import hookimpl
from hypy.nexus import Nexus
import pandas as pd
import numpy as np

if typing.TYPE_CHECKING:
    from datetime import datetime
    from ngen.cal.model import ModelExec

ds_sim_test = pd.Series
ds_obs_test = pd.Series
_workdir: Path | None = None

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
        self.obs_data_path = None
        self.units = None
        self.window = 1

    @hookimpl
    def ngen_cal_model_configure(self, config: ModelExec) -> None:
        path = config.workdir
        global _workdir
        # HACK: fix this in future
        _workdir = path
        
        self.obs_data_path = config.plugin_settings["ngen_cal_read_obs_data"][
            "obs_data_path"
        ]
        self.units = config.plugin_settings["ngen_cal_read_obs_data"]["units"]
        self.window = int(config.plugin_settings["ngen_cal_read_obs_data"]["window"])

        start = self.obs_kwargs["start_time"]
        end = self.obs_kwargs["end_time"]

        ds = self._read_observations(self, self.obs_data_path, start, end, self.window)
        self.proxy.set_proxy(ds)

    @staticmethod
    def _read_observations(self,
        filename: str, start_time: datetime, end_time: datetime, window: int
    ) -> pd.Series:
        # read file
        print ("filename: ", filename)
        df = pd.read_csv(filename, usecols=["value_date", "value"])

        df["value_date"] = pd.to_datetime(df["value_date"])
        if self.units == "ft3/sec" or self.units == "ft3/s":
            df["value"] = self.ft3_to_m3 * df["value"]

        # subset into `pd.Series` that is indexed by `datetime` with a name
        df.set_index("value_date", inplace=True)
        df = df.loc[start_time:end_time]

        # get total hours to ensure the length of observed data is consistent with the leght of simulated data
        total_hours = (end_time - start_time).total_seconds() / 3600.0
        length = int(total_hours / window)

        assert length > 0

        ds = df["value"][:length]
        ds.rename("obs_flow", inplace=True)

        global ds_obs_test
        ds_obs_test = ds
        
        return ds

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

        # `ngen_cal_model_observations` must have already called, so call again and set proxy
        if not self.proxy.empty:
            assert self.obs_data_path is not None, "invariant"
            ds = self._read_observations(self,
                self.obs_data_path, start_time, end_time, self.window
            )
            self.proxy.set_proxy(ds)

        

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
        
        mean_values = np.reshape(sim_local.values, (-1, self.window)).mean(axis=1)

        #assert len(mean_values) == len(index)
        if (len(mean_values) == len(index) ):
            ds_sim = pd.Series(mean_values, index=index)
        else:
            index = pd.date_range(start=sim_local.index[0], end=sim_local.index[-1], freq=f'{self.window}h')
            if self.window == 24:
                index = pd.date_range(start=sim_local.index[0].normalize(), end=sim_local.index[-1], freq='d')
                index = index[:len(mean_values)]

            ds_sim = pd.Series(mean_values, index=index)

        ds_sim.rename("sim_flow", inplace=True)

        assert isinstance(
            sim_local, pd.Series
        ), f"expected pd.Series, got {type(sim_local)!r}"

        global ds_sim_test
        ds_sim_test = ds_sim

        return ds_sim


    @hookimpl
    def ngen_cal_finish(exception: Exception | None) -> None:
        
        if exception is None:
            print("validation: not saving obs/sim output")
            return
        global _workdir
        
        assert _workdir is not None, "invariant"

        if (len(ds_sim_test.index) == len(ds_obs_test.index)):
            df = pd.merge(ds_sim_test, ds_obs_test, left_index=True, right_index=True)
        else:
            df = pd.DataFrame(ds_sim_test)

        df.reset_index(names="time", inplace=True)

        path = _workdir
        out_dir = path / f"output_sim_obs"
        if (not out_dir.is_dir()):
            Path.mkdir(out_dir)
        df.to_csv(f"{out_dir}/sim_obs_validation.csv")
"""
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

    def set_proxy_full(self, obj):
        self._proxy_obj_full = obj
        
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
        self.data

    @hookimpl
    def ngen_cal_model_configure(self, config: ModelExec) -> None:

        # read file
        #df = pd.read_parquet(config.plugin_settings["ngen_cal_read_obs_data"]["obs_data_path"])
        df = pd.read_csv(config.plugin_settings["ngen_cal_read_obs_data"]["obs_data_path"], usecols=['value_date', 'value'])
        self.units  = config.plugin_settings["ngen_cal_read_obs_data"]["units"]
        self.window = int(config.plugin_settings["ngen_cal_read_obs_data"]["window"])

        df["value_date"] = pd.to_datetime(df['value_date'])
        if (self.units == "ft3/sec" or self.units == "ft3/s"):
            df["value"] = self.ft3_to_m3 * df["value"]
            
        #config.plugin_settings["ngen_cal_read_observed_data"]["observation_file"]

        nexus = self.obs_kwargs["nexus"]
        start = self.obs_kwargs["start_time"]
        end = self.obs_kwargs["end_time"]
        simulation_interval = self.obs_kwargs["simulation_interval"]

        divide_id = nexus.id
        # subset into `pd.Series` that is indexed by `datetime` with a name
        df.set_index("value_date", inplace=True)
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
        print ("AA ", mean_values, index)

        start = self.obs_kwargs["start_time"]
        end = self.obs_kwargs["end_time"]
        print ("start = ", start)
        print ("end = ", end)
        assert (len(mean_values) == len(index))
        ds_sim = pd.Series(mean_values, index=index)
        ds_sim.rename("sim_flow", inplace=True)

        assert isinstance(sim_local, pd.Series), f"expected pd.Series, got {type(sim_local)!r}"

        return ds_sim
"""
