# Courtesy of Austin Raney
# Sept. 26, 2024

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from ngen.cal import hookimpl

if TYPE_CHECKING:
    from ngen.cal.model import ModelExec


class NgenCalSymlinkDir:
    """
    Create a symbolic link to ngen-cal's created workdir
    (e.g. `202409260448_ngen_ocpz40bk_worker`)

    Configuration:
    Add symlink path under `ngen_cal_symlink_dir.dir` key in the
    `model.plugin_settings` of an `ngen.cal` config file.

    Example:
    ```yaml
    model:
      plugin_settings:
        ngen_cal_symlink_dir:
          path: './ngen_cal_output'
    ```
    """

    @hookimpl(tryfirst=True)
    def ngen_cal_model_configure(self, config: ModelExec) -> None:
        if (
            "ngen_cal_symlink_dir" not in config.plugin_settings
        ) and "path" not in config.plugin_settings["ngen_cal_symlink_dir"]:
            raise RuntimeError(
                "NgenCalSymlinkDir no configuration provided. Add `ngen_cal_symlink_dir.path` to `model.plugin_settings` or `ngen.cal` config file"
            )
        symdir = Path(config.plugin_settings["ngen_cal_symlink_dir"]["path"])
        if symdir.is_symlink():
            import warnings

            warnings.warn(
                f"NgenCalSymlinkDir symlink exists to {symdir.readlink()!s}; relinking {symdir!s} to {config.workdir!s}",
                RuntimeWarning,
            )
        elif symdir.exists():
            raise RuntimeError(
                f"NgenCalSymlinkDir path exists and is not symlink {symdir!s}"
            )
        symdir.symlink_to(config.workdir, target_is_directory=True)
