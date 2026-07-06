"""bridge — compose the so101-lab hardware/execution cell by reference.

Lets the sim pipeline use so101-lab's real Placo kinematics (and, later, live pose +
motion) without forking it, with a graceful built-in fallback so gates run standalone.

    from bridge import solve_path, probe, status
"""

from .so101_bridge import probe, solve_path, status

__all__ = ["solve_path", "probe", "status"]
