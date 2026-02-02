from setuptools import setup
from setuptools.command.build_py import build_py
import subprocess
import os


class BuildFrontend(build_py):
    def run(self):
        frontend_dir = os.path.join(os.path.dirname(__file__), "frontend")

        if not os.path.exists(frontend_dir):
            super().run()
            return

        if os.environ.get("SKIP_FRONTEND_BUILD") == "1":
            print("Skipping frontend build (SKIP_FRONTEND_BUILD=1)")
            super().run()
            return

        try:
            subprocess.check_call(["node", "--version"])
            subprocess.check_call(["npm", "--version"])
        except Exception:
            raise RuntimeError(
                "Node.js is required to build the frontend. "
                "Please install Node.js >= 18 or set SKIP_FRONTEND_BUILD=1."
            )

        subprocess.check_call(["npm", "install"], cwd=frontend_dir)
        subprocess.check_call(["npm", "run", "build"], cwd=frontend_dir)

        super().run()


setup(
    cmdclass={"build_py": BuildFrontend},
)
