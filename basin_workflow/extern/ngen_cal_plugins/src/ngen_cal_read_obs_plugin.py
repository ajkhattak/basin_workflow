from __future__ import annotations

import typing

from ngen.cal import hookimpl
from hypy.nexus import Nexus
import pandas as pd
from pathlib import Path

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

    @hookimpl
    def ngen_cal_model_configure(self, config: ModelExec) -> None:
        print("model_configure")
        # read file
        #df = pd.read_parquet(config.plugin_settings["ngen_cal_read_obs_data"]["obs_data_path"])
        df = pd.read_csv(config.plugin_settings["ngen_cal_read_obs_data"]["obs_data_path"], usecols=['value_time', 'value'])
        units = config.plugin_settings["ngen_cal_read_obs_data"]["units"]

        df["value_time"] = pd.to_datetime(df['value_time'])
        if (units == "ft3/sec" or units == "ft3/s"):
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

        #ds = df["value"].resample(simulation_interval).nearest()
        ds = df["value"]
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
        print("model_observations")
        self.obs_kwargs = {
            "nexus": nexus,
            "start_time": start_time,
            "end_time": end_time,
            "simulation_interval": simulation_interval,
        }
        return self.proxy

"""
class ReadObservedDataX:
    
    def __init__(self) -> None:
        self.sim: pd.Series | None = None
        self.obs: pd.Series | None = None
        self.obs_data_path  : str  = None
        self.first_iteration: bool = True
        self.config = None
    
    @hookimpl
    def ngen_cal_model_configure(self, config: ModelExec) -> None:
        print ("called_model_cofigure")
        self.obs_data_path = Path(config.plugin_settings["ngen_cal_read_obs_data"]["obs_data_path"])
        self.config = config
        #quit()

    @hookimpl(wrapper=True)
    def ngen_cal_model_observations(
        self,
        nexus: Nexus,
        start_time: datetime,
        end_time: datetime,
        simulation_interval: pd.Timedelta,
    ) -> pd.Series: #-> typing.Generator[None, pd.Series, pd.Series]:
        # In short, all registered `ngen_cal_model_observations` hooks run
        # before `yield` and the results are sent as the result to `yield`
        # NOTE: DO NOT MODIFY `obs`

        obs = yield
        print ("called_model_observation")
        print ("obs_data_path: ", self.obs_data_path)
        #print (obs)
        #print (obs.values)
        #obs[:] = 0.0
        
        #quit()
        if self.config is None:
            #return pd.Series()
            return obs
        elif obs is None:
            print ("let do this")
            quit()
        
    @hookimpl(wrapper=True)
    def ngen_cal_model_output(
        self, id: str | None
    ) -> typing.Generator[None, pd.Series, pd.Series]:
        # In short, all registered `ngen_cal_model_output` hooks run
        # before `yield` and the results are sent as the result to `yield`
        # NOTE: DO NOT MODIFY `sim`
        sim = yield
        #sim_dv = np.reshape(sim,24).mean(1)
        print ("called_model_output")
        if sim is None:
           self.first_iteration = False
           return None
        assert isinstance(sim, pd.Series), f"expected pd.Series, got {type(sim)!r}"
        self.sim = sim
        return sim
"""
