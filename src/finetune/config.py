from pathlib import Path
from typing import Dict, Optional

from pydantic import BaseModel, Field


class RedisConfig(BaseModel):
    """Redis configuration."""
    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: Optional[str] = None


class ProcessConfig(BaseModel):
    """Individual process configuration."""
    command: str
    directory: Optional[str] = None
    autostart: bool = True
    autorestart: bool = True
    user: Optional[str] = None
    environment: Dict[str, str] = Field(default_factory=dict)
    stdout_logfile: Optional[str] = None
    stderr_logfile: Optional[str] = None


class SupervisorConfig(BaseModel):
    """Supervisor daemon configuration."""
    socket_file: str = "/tmp/finetune/supervisor.sock"
    logfile: str = "/tmp/finetune/supervisord.log"
    pidfile: str = "/tmp/finetune/supervisord.pid"
    logfile_maxbytes: str = "50MB"
    logfile_backups: int = 10
    loglevel: str = "info"


class Config(BaseModel):
    """Main application configuration."""
    redis: RedisConfig = Field(default_factory=RedisConfig)  # Re-enabled Redis
    supervisor: SupervisorConfig = Field(default_factory=SupervisorConfig)
    processes: Dict[str, ProcessConfig] = Field(default_factory=dict)
    app_name: str = "finetune"
    log_dir: str = "/tmp/finetune"
    
    def __post_init__(self):
        """Ensure directories exist after configuration is created."""
        self.create_directories()
    
    def create_directories(self):
        """Create all necessary directories."""
        # Create base log directory
        log_dir = Path(self.log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # Create supervisor-related directories
        supervisor_log_dir = Path(self.supervisor.logfile).parent
        supervisor_log_dir.mkdir(parents=True, exist_ok=True)
        
        supervisor_socket_dir = Path(self.supervisor.socket_file).parent
        supervisor_socket_dir.mkdir(parents=True, exist_ok=True)
        
        supervisor_pid_dir = Path(self.supervisor.pidfile).parent
        supervisor_pid_dir.mkdir(parents=True, exist_ok=True)
        
        # Create process-specific log directories
        for process_config in self.get_process_configs().values():
            if process_config.stdout_logfile:
                stdout_dir = Path(process_config.stdout_logfile).parent
                stdout_dir.mkdir(parents=True, exist_ok=True)
            
            if process_config.stderr_logfile:
                stderr_dir = Path(process_config.stderr_logfile).parent
                stderr_dir.mkdir(parents=True, exist_ok=True)
    
    @classmethod
    def load(cls, config_path: Optional[Path] = None) -> "Config":
        """Load configuration from file."""
        if config_path and config_path.exists():
            # In a real implementation, you'd load from YAML/TOML/JSON
            # For now, return default config
            pass
        
        # Create instance and ensure directories exist
        instance = cls()
        instance.create_directories()
        return instance
    
    def get_process_configs(self) -> Dict[str, ProcessConfig]:
        """Get default process configurations."""
        if not self.processes:
            # Default processes
            python_path = f"python -m {self.app_name}.processes"
            
            self.processes = {
                "events": ProcessConfig(
                    command=f"{python_path}.events",
                    stdout_logfile=f"{self.log_dir}/events.out.log",
                    stderr_logfile=f"{self.log_dir}/events.err.log",
                ),
                "client": ProcessConfig(
                    command=f"{python_path}.client",
                    stdout_logfile=f"{self.log_dir}/client.out.log",
                    stderr_logfile=f"{self.log_dir}/client.err.log",
                ),
                "server": ProcessConfig(
                    command=f"{python_path}.server",
                    stdout_logfile=f"{self.log_dir}/server.out.log",
                    stderr_logfile=f"{self.log_dir}/server.err.log",
                ),
            }
        
        return self.processes