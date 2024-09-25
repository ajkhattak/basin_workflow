from __future__ import annotations

import typing

from ngen.cal import hookimpl
from hypy.nexus import Nexus
import pandas as pd
from pathlib import Path

#from download_nwm_streamflow import

if typing.TYPE_CHECKING:
    from datetime import datetime
    from ngen.cal.meta import JobMeta

class SaveOutput:
    def __init__(self) -> None:
        self.sim: pd.Series | None = None
        self.obs: pd.Series | None = None
        self.first_iteration: bool = True
        self.save_obs_nwm: bool = True

    @hookimpl(wrapper=True)
    def ngen_cal_model_observations(
        self,
        nexus: Nexus,
        start_time: datetime,
        end_time: datetime,
        simulation_interval: pd.Timedelta,
    ) -> typing.Generator[None, pd.Series, pd.Series]:
        # In short, all registered `ngen_cal_model_observations` hooks run
        # before `yield` and the results are sent as the result to `yield`
        # NOTE: DO NOT MODIFY `obs`
        obs = yield
        if self.first_iteration and obs is None:
           self.first_iteration = False
           return None
        assert isinstance(obs, pd.Series), f"expected pd.Series, got {type(obs)!r}"
        self.obs = obs
        return obs

    @hookimpl(wrapper=True)
    def ngen_cal_model_output(
        self, id: str | None
    ) -> typing.Generator[None, pd.Series, pd.Series]:
        # In short, all registered `ngen_cal_model_output` hooks run
        # before `yield` and the results are sent as the result to `yield`
        # NOTE: DO NOT MODIFY `sim`
        sim = yield
        if self.first_iteration and sim is None:
           self.first_iteration = False
           return None
        assert isinstance(sim, pd.Series), f"expected pd.Series, got {type(sim)!r}"
        self.sim = sim
        return sim

    @hookimpl
    def ngen_cal_model_iteration_finish(self, iteration: int, info: JobMeta) -> None:
        if self.sim is None:
            return None
        assert (
            self.sim is not None
        ), "make sure `ngen_cal_model_output` was called"
        assert self.obs is not None, "make sure `ngen_cal_model_observations` was called"

        # index: hourly datetime
        # columns: `obs_flow` and `sim_flow`; units m^3/s
        #df = pd.merge(self.sim, self.obs, left_index=True, right_index=True)

        if self.save_obs_nwm:
            #self.save_obs_nwm = False  # will revisit this later
            df = pd.merge(self.sim, self.obs, left_index=True, right_index=True)
        else:
            df = pd.DataFrame(self.sim)

        df.reset_index(names="time", inplace=True)
        #df.to_parquet(f"sim_obs_{iteration}.parquet")

        path = info.workdir
        #out_dir = path / f"output_{iteration}"
        out_dir = path / f"output_sim_obs"
        if (not out_dir.is_dir()):
            Path.mkdir(out_dir)
        df.to_csv(f"{out_dir}/sim_obs_{iteration}.csv")
