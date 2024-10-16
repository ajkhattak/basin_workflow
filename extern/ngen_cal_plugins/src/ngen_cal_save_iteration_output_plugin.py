from __future__ import annotations

import itertools

from ngen.cal import hookimpl
from ngen.cal.meta import JobMeta
from ngen.cal.model import ModelExec
from pathlib import Path

# NOTE: global variable that is set in `NgenSaveOutput.ngen_cal_model_iteration_finish`
_workdir: Path | None = None


def save_output(sim_dir: Path, output_suffix: str):
    runoff_pattern = "cat-*.csv"
    lateral_pattern = "nex-*.csv"
    terminal_pattern = "tnx-*.csv"
    coastal_pattern = "cnx-*.csv"
    routing_output_stream = "troute_output_*"
    routing_csv_output = "flowveldepth_*.csv"
    ngen_json = "realization*.json"

    out_dir = sim_dir / f"output_{output_suffix}"
    Path.mkdir(out_dir, exist_ok=True)

    globs = [
        sim_dir.glob(runoff_pattern),
        sim_dir.glob(lateral_pattern),
        sim_dir.glob(terminal_pattern),
        sim_dir.glob(coastal_pattern),
        sim_dir.glob(routing_output_stream),
        sim_dir.glob(routing_csv_output),
        sim_dir.glob(ngen_json),
    ]
    for f in itertools.chain(*globs):
        f.rename(out_dir / f.name)



class SaveCalibration:

    @hookimpl
    def ngen_cal_model_configure(self, config: ModelExec) -> None:
        path = config.workdir
        global _workdir
        # HACK: fix this in future
        _workdir = path

    @hookimpl
    def ngen_cal_model_iteration_finish(self, iteration: int, info: JobMeta) -> None:
        """
        After each iteration, copy the old outputs for possible future
        evaluation and inspection.
        """
        path = info.workdir

        save_output(path, str(iteration))

class SaveValidation:
    def __init__(self) -> None:
        self.sim: pd.Series | None = None
        self.obs: pd.Series | None = None
        self.first_iteration: bool = True
        #self.save_obs_nwm: bool = True

    @hookimpl
    def ngen_cal_finish(exception: Exception | None) -> None:
        if exception is None:
            print("not saving validation output")
            return
        global _workdir
        assert _workdir is not None, "invariant"

        save_output(_workdir, "validation")

"""
class SaveIterationRealizationPlugin:
    save_dir = Path("/some/dir/ngen_cal_output")

    @hookimpl
    def ngen_cal_model_iteration_finish(self, iteration: int, info: JobMeta):
        workdir: Path = info.workdir
        realization = workdir / "realization.json"
        output = self.save_dir / f"realization_{iteration}.json"
        shutil.copy(realization, output)
"""

