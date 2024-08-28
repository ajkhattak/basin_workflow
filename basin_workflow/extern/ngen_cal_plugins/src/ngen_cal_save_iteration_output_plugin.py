from ngen.cal import hookimpl
from ngen.cal.meta import JobMeta
from pathlib import Path

class NgenSaveOutput:
    runoff_pattern = "cat-*.csv"
    lateral_pattern = "nex-*.csv"
    terminal_pattern = "tnx-*.csv"
    coastal_pattern = "cnx-*.csv"
    routing_output_stream = "troute_output_*"
    routing_csv_output = "flowveldepth_*.csv"
    ngen_json         = "realization*.json"
    
    @hookimpl
    def ngen_cal_model_iteration_finish(self, iteration: int, info: JobMeta) -> None:
        """
        After each iteration, copy the old outputs for possible future
        evaluation and inspection.
        """
        path = info.workdir
        out_dir = path / f"output_{iteration}"
        if (not out_dir.is_dir()):
            Path.mkdir(out_dir)
        
        globs = [
            path.glob(self.runoff_pattern),
            path.glob(self.lateral_pattern),
            path.glob(self.terminal_pattern),
            path.glob(self.coastal_pattern),
            path.glob(self.routing_output_stream),
            path.glob(self.routing_csv_output),
            path.glob(self.ngen_json),
        ]
        for g in globs:
            for f in g:
                f.rename(out_dir / f.name)

#from __future__ import annotations

#import shutil
#import typing

#from ngen.cal import hookimpl

#if typing.TYPE_CHECKING:
#    from pathlib import Path
#    from ngen.cal.meta import JobMeta


class SaveIterationRealizationPlugin:
    save_dir = Path("/some/dir/ngen_cal_output")
    @hookimpl
    def ngen_cal_model_iteration_finish(self, iteration: int, info: JobMeta):
        workdir: Path = info.workdir
        realization = workdir / "realization.json"
        output = self.save_dir / f"realization_{iteration}.json"
        shutil.copy(realization, output)


