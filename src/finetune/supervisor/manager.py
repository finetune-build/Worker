import subprocess
import time
import os
from pathlib import Path
from typing import Any, Dict, Optional

from finetune.config import Config
from finetune.exceptions import SupervisorError
from finetune.supervisor.config import ConfigGenerator


class SupervisorManager:
    """Manage supervisor daemon and processes."""
    
    def __init__(self, config: Config):
        self.config = config
        self.config_generator = ConfigGenerator(config)
        self.config_path = Path.cwd() / "config" / "supervisord.conf"
        self._server = None
    
    def generate_config(self, output_path: Optional[Path] = None) -> str:
        """Generate supervisor configuration file."""
        if output_path is None:
            output_path = self.config_path
        
        return self.config_generator.generate_config(output_path)
    
    def start(self, daemon: bool = True) -> None:
        """Start supervisor daemon and all processes."""
        # Create necessary directories
        self._create_directories()
        
        # Generate configuration if it doesn't exist
        if not self.config_path.exists():
            self.generate_config()
        
        # Start supervisord
        self._start_supervisord(daemon)
        
        # Wait for supervisor to be ready
        self._wait_for_supervisor()
        
        # Start all processes
        self._start_all_processes()
    
    def stop(self) -> None:
        """Stop all processes and supervisor daemon."""
        try:
            # Stop all processes first
            self._execute_supervisorctl("stop", "all")
            
            # Shutdown supervisor daemon
            self._execute_supervisorctl("shutdown")
            
        except SupervisorError as e:
            # If supervisor is not running, that's ok
            if "refused connection" not in str(e).lower():
                raise
    
    def restart_process(self, process_name: str) -> None:
        """Restart a specific process."""
        self._execute_supervisorctl("restart", process_name)
    
    def get_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all processes."""
        try:
            output = self._execute_supervisorctl("status")
            return self._parse_status_output(output)
        except SupervisorError:
            return {}
    
    def show_logs(self, process_name: Optional[str] = None, follow: bool = False) -> None:
        """Show process logs."""
        if process_name:
            # Show logs for specific process
            if follow:
                self._execute_supervisorctl("tail", "-f", process_name)
            else:
                output = self._execute_supervisorctl("tail", process_name)
                print(output)
        else:
            # Show logs for all processes
            processes = self.config.get_process_configs()
            for name in processes.keys():
                print(f"\n{'='*50}")
                print(f"Logs for {name}:")
                print('='*50)
                try:
                    output = self._execute_supervisorctl("tail", name)
                    print(output)
                except SupervisorError:
                    print(f"No logs available for {name}")
    
    def _start_supervisord(self, daemon: bool) -> None:
        """Start the supervisor daemon."""
        cmd = [
            "supervisord",
            "-c", str(self.config_path)
        ]
        
        if not daemon:
            cmd.append("-n")  # Don't daemonize
        
        try:
            # Suppress pkg_resources warnings by setting environment variable
            env = os.environ.copy()
            env['PYTHONWARNINGS'] = 'ignore::UserWarning:pkg_resources'
            
            if daemon:
                subprocess.run(
                    cmd,
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.PIPE,
                    text=True,
                    env=env  # Use modified environment
                )
            else:
                # For non-daemon mode, let it run in foreground
                subprocess.run(cmd, check=True, env=env)
                
        except subprocess.CalledProcessError as e:
            # Filter out pkg_resources warnings from error messages
            error_stderr = e.stderr
            if error_stderr and "pkg_resources is deprecated" in error_stderr:
                # Extract only the actual error, not the warning
                lines = error_stderr.split('\n')
                actual_error = [line for line in lines if 'pkg_resources' not in line and 'UserWarning' not in line]
                error_stderr = '\n'.join(actual_error).strip()
            
            # Check if supervisor is already running
            if "already listening" in error_stderr:
                return  # Already running, that's fine
            raise SupervisorError(f"Failed to start supervisord: {error_stderr}")
        except FileNotFoundError:
            raise SupervisorError(
                "supervisord not found. Please install supervisor: pip install supervisor"
            )
    
    def _wait_for_supervisor(self, timeout: int = 30) -> None:
        """Wait for supervisor to be ready."""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                self._execute_supervisorctl("status")
                return  # Supervisor is ready
            except SupervisorError:
                time.sleep(1)
        
        raise SupervisorError("Supervisor did not start within timeout period")
    
    def _start_all_processes(self) -> None:
        """Start all configured processes."""
        processes = self.config.get_process_configs()
        
        for process_name in processes.keys():
            try:
                self._execute_supervisorctl("start", process_name)
            except SupervisorError as e:
                # If process is already running, that's ok
                if "already started" not in str(e).lower():
                    raise
    
    def _execute_supervisorctl(self, *args: str) -> str:
        """Execute supervisorctl command with warning suppression."""
        cmd = [
            "supervisorctl",
            "-c", str(self.config_path)
        ] + list(args)
        
        try:
            # Suppress pkg_resources warnings by setting environment variable
            env = os.environ.copy()
            env['PYTHONWARNINGS'] = 'ignore::UserWarning:pkg_resources'
            
            result = subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                text=True,
                env=env  # Use modified environment
            )
            return result.stdout.strip()
            
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr.strip() or e.stdout.strip()
            
            # Filter out pkg_resources warnings from error messages
            if "pkg_resources is deprecated" in error_msg:
                # Extract only the actual error, not the warning
                lines = error_msg.split('\n')
                actual_error = [line for line in lines if 'pkg_resources' not in line and 'UserWarning' not in line]
                error_msg = '\n'.join(actual_error).strip()
                
                # If after filtering there's no actual error, don't raise an exception
                if not error_msg:
                    return ""  # Command succeeded, just had warnings
            
            # Only raise if there's an actual error message
            if error_msg:
                raise SupervisorError(f"supervisorctl command failed: {error_msg}")
            else:
                return ""  # No error, just warnings that were filtered out
                
        except FileNotFoundError:
            raise SupervisorError(
                "supervisorctl not found. Please install supervisor: pip install supervisor"
            )
    
    def _parse_status_output(self, output: str) -> Dict[str, Dict[str, Any]]:
        """Parse supervisorctl status output."""
        status = {}
        
        for line in output.split('\n'):
            if not line.strip():
                continue
            
            parts = line.split(None, 3)  # Split on whitespace, max 4 parts
            if len(parts) < 2:
                continue
            
            process_name = parts[0]
            state = parts[1]
            
            # Extract PID if available
            pid = None
            description = ""
            
            if len(parts) > 2:
                # Look for PID in the format "pid 12345"
                remaining = " ".join(parts[2:])
                if remaining.startswith("pid "):
                    pid_part = remaining.split(",")[0]  # Get part before comma
                    try:
                        pid = int(pid_part.split()[1])  # Extract number after "pid "
                    except (IndexError, ValueError):
                        pass
                description = remaining
            
            status[process_name] = {
                'statename': state,
                'pid': pid,
                'description': description
            }
        
        return status
    
    def _create_directories(self) -> None:
        """Create necessary directories for logs and runtime files."""
        # Create log directory
        log_dir = Path(self.config.log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # Create directory for supervisor socket file
        socket_file = Path(self.config.supervisor.socket_file)
        socket_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Create directory for supervisor log file
        supervisor_log = Path(self.config.supervisor.logfile)
        supervisor_log.parent.mkdir(parents=True, exist_ok=True)
        
        # Create directory for supervisor pid file
        pid_file = Path(self.config.supervisor.pidfile)
        pid_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Create directories for all process log files
        processes = self.config.get_process_configs()
        for process_config in processes.values():
            if process_config.stdout_logfile:
                stdout_log = Path(process_config.stdout_logfile)
                stdout_log.parent.mkdir(parents=True, exist_ok=True)
            
            if process_config.stderr_logfile:
                stderr_log = Path(process_config.stderr_logfile)
                stderr_log.parent.mkdir(parents=True, exist_ok=True)
