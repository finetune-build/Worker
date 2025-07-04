"""finetune-sdk CLI package."""

from .__main__ import app, console, ConfigOption, VerboseOption

from .health import register_health
from .initialize import register_initialize
from .kill import register_kill
from .logs import register_logs
from .restart import register_restart
from .start import register_start
from .status import register_status
from .stop import register_stop
from .version import register_version

register_health(app)
register_initialize(app)
register_kill(app)
register_logs(app)
register_restart(app)
register_start(app)
register_status(app)
register_stop(app)
register_version(app)

if __name__ == "__main__":
    app()
