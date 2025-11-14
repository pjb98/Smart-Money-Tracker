"""
Monitor Process Management Module
Handles starting, stopping, and checking status of monitoring processes
"""
import psutil
import subprocess
import os
from pathlib import Path
from typing import Dict, List, Optional
from loguru import logger


class MonitorManager:
    """Manages monitoring processes"""

    MONITORS = {
        'smart_money': {
            'name': 'Smart Money Monitor',
            'script': 'monitor_smart_money.py',
            'description': 'Tracks elite wallet activities'
        },
        'migration': {
            'name': 'Migration Monitor',
            'script': 'monitor_pumpportal.py',
            'description': 'Watches for token graduations'
        },
        'realtime': {
            'name': 'Realtime Monitor',
            'script': 'monitor_realtime.py',
            'description': 'Live token monitoring'
        }
    }

    def __init__(self):
        """Initialize monitor manager"""
        self.base_dir = Path(__file__).parent

    def get_monitor_status(self, monitor_id: str) -> Dict:
        """
        Check if a monitor is running

        Args:
            monitor_id: ID of monitor to check (e.g., 'smart_money')

        Returns:
            Dict with status info
        """
        if monitor_id not in self.MONITORS:
            return {
                'running': False,
                'error': 'Unknown monitor',
                'pid': None
            }

        monitor_info = self.MONITORS[monitor_id]
        script_name = monitor_info['script']

        # Find running processes
        running_pids = []
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                cmdline = proc.info.get('cmdline', [])
                if cmdline and any(script_name in arg for arg in cmdline):
                    running_pids.append(proc.info['pid'])
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        return {
            'running': len(running_pids) > 0,
            'pid': running_pids[0] if running_pids else None,
            'count': len(running_pids),
            'name': monitor_info['name'],
            'description': monitor_info['description']
        }

    def get_all_statuses(self) -> Dict[str, Dict]:
        """Get status of all monitors"""
        return {
            monitor_id: self.get_monitor_status(monitor_id)
            for monitor_id in self.MONITORS.keys()
        }

    def start_monitor(self, monitor_id: str) -> Dict:
        """
        Start a monitor process

        Args:
            monitor_id: ID of monitor to start

        Returns:
            Dict with result info
        """
        if monitor_id not in self.MONITORS:
            return {
                'success': False,
                'error': 'Unknown monitor'
            }

        # Check if already running
        status = self.get_monitor_status(monitor_id)
        if status['running']:
            return {
                'success': False,
                'error': f"Monitor already running (PID: {status['pid']})"
            }

        monitor_info = self.MONITORS[monitor_id]
        script_path = self.base_dir / monitor_info['script']

        if not script_path.exists():
            return {
                'success': False,
                'error': f"Script not found: {script_path}"
            }

        try:
            # Start process in background
            if os.name == 'nt':  # Windows
                # Use CREATE_NEW_CONSOLE to create new window
                subprocess.Popen(
                    ['python', str(script_path)],
                    creationflags=subprocess.CREATE_NEW_CONSOLE,
                    cwd=str(self.base_dir)
                )
            else:  # Unix/Linux
                subprocess.Popen(
                    ['python', str(script_path)],
                    cwd=str(self.base_dir),
                    start_new_session=True
                )

            logger.info(f"Started {monitor_info['name']}")
            return {
                'success': True,
                'message': f"{monitor_info['name']} started successfully"
            }

        except Exception as e:
            logger.error(f"Failed to start {monitor_info['name']}: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def stop_monitor(self, monitor_id: str) -> Dict:
        """
        Stop a monitor process

        Args:
            monitor_id: ID of monitor to stop

        Returns:
            Dict with result info
        """
        if monitor_id not in self.MONITORS:
            return {
                'success': False,
                'error': 'Unknown monitor'
            }

        monitor_info = self.MONITORS[monitor_id]
        script_name = monitor_info['script']

        # Find and kill all instances
        killed_count = 0
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                cmdline = proc.info.get('cmdline', [])
                if cmdline and any(script_name in arg for arg in cmdline):
                    proc.terminate()
                    killed_count += 1
                    logger.info(f"Terminated {monitor_info['name']} (PID: {proc.info['pid']})")
            except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
                logger.warning(f"Could not terminate process: {e}")
                continue

        if killed_count > 0:
            return {
                'success': True,
                'message': f"Stopped {killed_count} instance(s) of {monitor_info['name']}"
            }
        else:
            return {
                'success': False,
                'error': 'Monitor not running'
            }
