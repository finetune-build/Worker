import os
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, Template

from finetune.config import Config

class ConfigGenerator:
    """Generate supervisor configuration files."""
    
    def __init__(self, config: Config):
        self.config = config
        self.template_dir = Path(__file__).parent.parent / "templates"
        self.template_dir.mkdir(exist_ok=True)
        
        # Create Jinja2 environment
        self.env = Environment(
            loader=FileSystemLoader(str(self.template_dir)),
            trim_blocks=True,
            lstrip_blocks=True
        )
    
    def generate_config(self, output_path: Path) -> str:
        """Generate supervisor configuration file.
        
        Args:
            output_path: Path where to write the configuration
            
        Returns:
            Generated configuration content
        """
        template_content = self._get_supervisor_template()
        template = Template(template_content)
        
        # Prepare template variables
        variables = {
            'supervisor': self.config.supervisor,
            'processes': self.config.get_process_configs(),
            'user': os.getenv('USER', 'root'),
            'cwd': Path.cwd(),
            'app_name': self.config.app_name,
        }
        
        # Render configuration
        config_content = template.render(**variables)
        
        # Write to file
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(config_content)
        
        return config_content
    
    def _get_supervisor_template(self) -> str:
        """Get supervisor configuration template."""
        return """
[unix_http_server]
file={{ supervisor.socket_file }}

[supervisord]
logfile={{ supervisor.logfile }}
logfile_maxbytes={{ supervisor.logfile_maxbytes }}
logfile_backups={{ supervisor.logfile_backups }}
loglevel={{ supervisor.loglevel }}
pidfile={{ supervisor.pidfile }}
nodaemon=false
minfds=1024
minprocs=200

[rpcinterface:supervisor]
supervisor.rpcinterface_factory = supervisor.rpcinterface:make_main_rpcinterface

[supervisorctl]
serverurl=unix://{{ supervisor.socket_file }}

{% for name, process in processes.items() %}
[program:{{ name }}]
command={{ process.command }}
{% if process.directory %}
directory={{ process.directory }}
{% else %}
directory={{ cwd }}
{% endif %}
autostart={{ 'true' if process.autostart else 'false' }}
autorestart={{ 'true' if process.autorestart else 'false' }}
{% if process.stdout_logfile %}
stdout_logfile={{ process.stdout_logfile }}
{% endif %}
{% if process.stderr_logfile %}
stderr_logfile={{ process.stderr_logfile }}
{% endif %}
{% if process.user %}
user={{ process.user }}
{% else %}
user={{ user }}
{% endif %}
environment=PYTHONPATH="{{ cwd }}"{% if process.environment %},{% for key, value in process.environment.items() %}{{ key }}="{{ value }}"{% if not loop.last %},{% endif %}{% endfor %}{% endif %}
redirect_stderr=false
stdout_logfile_maxbytes=10MB
stdout_logfile_backups=10
stderr_logfile_maxbytes=10MB
stderr_logfile_backups=10

{% endfor %}

[group:{{ app_name }}]
programs={% for name in processes.keys() %}{{ name }}{% if not loop.last %},{% endif %}{% endfor %}
priority=999
""".strip()