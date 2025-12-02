import psutil
import os
import signal

class KillProcess:
    """Helper class to kill a process by its name."""

    @staticmethod
    def by_port(port: int) -> bool:
            """
            Kill any process using the specified port.
            Args:
                port: The port number to check and free up
            Returns:
                True if a process was killed, False otherwise
            """
            killed = False
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    connections = proc.net_connections(kind='inet')
                    for conn in connections:
                        if conn.laddr.port == port:
                            if os.name == 'nt':  # Windows
                                proc.kill()
                            else:  # Unix/Linux/Mac
                                os.kill(proc.pid, signal.SIGTERM)
                            killed = True
                            break
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pass
            return killed