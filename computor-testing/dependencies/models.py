"""
Computor Testing Framework - Dependency Models

Pydantic models for parsing and validating dependencies.yaml files.
These models define the structure for package dependencies across
Python, R, Octave, Julia, and system packages.
"""

from enum import Enum
from typing import List, Optional, Union
from pydantic import BaseModel, Field


class PythonManager(str, Enum):
    """Python package managers"""
    pip = "pip"
    conda = "conda"
    poetry = "poetry"


class PythonPackage(BaseModel):
    """Python package definition"""
    name: str = Field(min_length=1)
    version: Optional[str] = Field(default=None, description="Version constraint (e.g., '>=1.0', '~=2.0')")
    extras: Optional[List[str]] = Field(default=None, description="Package extras (e.g., ['dev', 'test'])")
    git: Optional[str] = Field(default=None, description="Git repository URL")
    branch: Optional[str] = Field(default=None, description="Git branch")
    path: Optional[str] = Field(default=None, description="Local path for development")

    def to_pip_string(self) -> str:
        """Convert to pip install string"""
        if self.git:
            result = f"git+{self.git}"
            if self.branch:
                result += f"@{self.branch}"
            return result
        if self.path:
            return self.path

        result = self.name
        if self.extras:
            result += f"[{','.join(self.extras)}]"
        if self.version:
            result += self.version
        return result


class PythonDependencies(BaseModel):
    """Python dependencies section"""
    version: Optional[str] = Field(default=">=3.10", description="Python version requirement")
    manager: PythonManager = Field(default=PythonManager.pip)
    packages: List[Union[str, PythonPackage]] = Field(default=[])

    def get_packages(self) -> List[PythonPackage]:
        """Normalize packages to PythonPackage objects"""
        result = []
        for pkg in self.packages:
            if isinstance(pkg, str):
                result.append(PythonPackage(name=pkg))
            else:
                result.append(pkg)
        return result

    def to_pip_list(self) -> List[str]:
        """Convert to list of pip install strings"""
        return [pkg.to_pip_string() for pkg in self.get_packages()]

    def to_requirements_txt(self) -> str:
        """Generate requirements.txt content"""
        lines = [f"# Python {self.version}", ""]
        lines.extend(self.to_pip_list())
        return "\n".join(lines)


class RPackage(BaseModel):
    """R package definition"""
    name: str = Field(min_length=1)
    version: Optional[str] = Field(default=None, description="Version constraint")
    github: Optional[str] = Field(default=None, description="GitHub repository (user/repo)")
    bioconductor: Optional[bool] = Field(default=False, description="Install from Bioconductor")

    def to_install_command(self, lib_path: Optional[str] = None) -> str:
        """Generate R install command"""
        lib_arg = f", lib='{lib_path}'" if lib_path else ""

        if self.github:
            return f"devtools::install_github('{self.github}'{lib_arg})"
        if self.bioconductor:
            return f"BiocManager::install('{self.name}'{lib_arg})"

        return f"install.packages('{self.name}'{lib_arg})"


class RDependencies(BaseModel):
    """R dependencies section"""
    version: Optional[str] = Field(default=">=4.0", description="R version requirement")
    cran_mirror: str = Field(default="https://cloud.r-project.org/")
    lib_path: Optional[str] = Field(default=None, description="User library path")
    packages: List[Union[str, RPackage]] = Field(default=[])

    def get_packages(self) -> List[RPackage]:
        """Normalize packages to RPackage objects"""
        result = []
        for pkg in self.packages:
            if isinstance(pkg, str):
                result.append(RPackage(name=pkg))
            else:
                result.append(pkg)
        return result

    def to_install_script(self) -> str:
        """Generate R installation script"""
        lines = [
            f"# R {self.version}",
            f"options(repos = c(CRAN = '{self.cran_mirror}'))",
            "",
        ]

        if self.lib_path:
            lines.append(f"dir.create('{self.lib_path}', recursive = TRUE, showWarnings = FALSE)")
            lines.append("")

        # Group CRAN packages for batch install
        cran_packages = []
        special_packages = []

        for pkg in self.get_packages():
            if pkg.github or pkg.bioconductor:
                special_packages.append(pkg)
            else:
                cran_packages.append(pkg.name)

        if cran_packages:
            pkg_list = ", ".join(f"'{p}'" for p in cran_packages)
            lib_arg = f", lib = '{self.lib_path}'" if self.lib_path else ""
            lines.append(f"install.packages(c({pkg_list}){lib_arg})")
            lines.append("")

        for pkg in special_packages:
            lines.append(pkg.to_install_command(self.lib_path))

        return "\n".join(lines)


class OctavePackage(BaseModel):
    """Octave package definition"""
    name: str = Field(min_length=1)
    version: Optional[str] = Field(default=None)
    url: Optional[str] = Field(default=None, description="Direct download URL")

    def to_install_command(self, forge: bool = True) -> str:
        """Generate Octave install command"""
        if self.url:
            return f"pkg install '{self.url}'"
        if forge:
            if self.version:
                return f"pkg install -forge {self.name}@{self.version}"
            return f"pkg install -forge {self.name}"
        return f"pkg install {self.name}"


class OctaveDependencies(BaseModel):
    """Octave dependencies section"""
    version: Optional[str] = Field(default=">=6.0", description="Octave version requirement")
    forge: bool = Field(default=True, description="Install from Octave Forge")
    packages: List[Union[str, OctavePackage]] = Field(default=[])

    def get_packages(self) -> List[OctavePackage]:
        """Normalize packages to OctavePackage objects"""
        result = []
        for pkg in self.packages:
            if isinstance(pkg, str):
                result.append(OctavePackage(name=pkg))
            else:
                result.append(pkg)
        return result

    def to_install_script(self) -> str:
        """Generate Octave installation script"""
        lines = [f"# Octave {self.version}", ""]
        for pkg in self.get_packages():
            lines.append(pkg.to_install_command(self.forge))
        return "\n".join(lines)


class JuliaPackage(BaseModel):
    """Julia package definition"""
    name: str = Field(min_length=1)
    version: Optional[str] = Field(default=None, description="Version constraint")
    uuid: Optional[str] = Field(default=None, description="Package UUID")
    url: Optional[str] = Field(default=None, description="Git repository URL")

    def to_install_command(self) -> str:
        """Generate Julia Pkg install command"""
        if self.url:
            return f'Pkg.add(url="{self.url}")'
        if self.version:
            return f'Pkg.add(Pkg.PackageSpec(name="{self.name}", version="{self.version}"))'
        return f'Pkg.add("{self.name}")'


class JuliaDependencies(BaseModel):
    """Julia dependencies section"""
    version: Optional[str] = Field(default=">=1.6", description="Julia version requirement")
    packages: List[Union[str, JuliaPackage]] = Field(default=[])

    def get_packages(self) -> List[JuliaPackage]:
        """Normalize packages to JuliaPackage objects"""
        result = []
        for pkg in self.packages:
            if isinstance(pkg, str):
                result.append(JuliaPackage(name=pkg))
            else:
                result.append(pkg)
        return result

    def to_install_script(self) -> str:
        """Generate Julia installation script"""
        lines = [f"# Julia {self.version}", "import Pkg", ""]
        for pkg in self.get_packages():
            lines.append(pkg.to_install_command())
        return "\n".join(lines)


class SystemDependencies(BaseModel):
    """System-level dependencies"""
    apt: List[str] = Field(default=[], description="Debian/Ubuntu packages")
    yum: List[str] = Field(default=[], description="RHEL/CentOS packages")
    brew: List[str] = Field(default=[], description="macOS Homebrew packages")

    def to_apt_command(self) -> str:
        """Generate apt-get install command"""
        if not self.apt:
            return ""
        packages = " \\\n    ".join(self.apt)
        return f"apt-get update && apt-get install -y \\\n    {packages}"

    def to_yum_command(self) -> str:
        """Generate yum install command"""
        if not self.yum:
            return ""
        packages = " ".join(self.yum)
        return f"yum install -y {packages}"

    def to_brew_command(self) -> str:
        """Generate brew install command"""
        if not self.brew:
            return ""
        packages = " ".join(self.brew)
        return f"brew install {packages}"


class Dependencies(BaseModel):
    """
    Root model for dependencies.yaml

    Example:
        python:
          version: ">=3.10"
          packages:
            - numpy
            - matplotlib>=3.5

        r:
          packages:
            - jsonlite
            - ggplot2

        octave:
          packages:
            - signal
            - statistics

        julia:
          packages:
            - JSON
            - DataFrames

        system:
          apt:
            - libcurl4-openssl-dev
    """
    python: Optional[PythonDependencies] = Field(default=None)
    r: Optional[RDependencies] = Field(default=None)
    octave: Optional[OctaveDependencies] = Field(default=None)
    julia: Optional[JuliaDependencies] = Field(default=None)
    system: Optional[SystemDependencies] = Field(default=None)

    @classmethod
    def from_yaml(cls, path: str) -> "Dependencies":
        """Load dependencies from YAML file"""
        import yaml
        with open(path, "r") as f:
            data = yaml.safe_load(f)
        return cls(**data) if data else cls()

    def to_yaml(self) -> str:
        """Export dependencies to YAML string"""
        import yaml
        data = self.model_dump(exclude_none=True, exclude_defaults=True)
        return yaml.dump(data, default_flow_style=False, sort_keys=False)

    def merge(self, other: "Dependencies") -> "Dependencies":
        """Merge another Dependencies object into this one"""
        # Helper to merge package lists
        def merge_packages(a, b):
            if a is None:
                return b
            if b is None:
                return a
            # Use dict to deduplicate by name
            seen = {}
            for pkg in (a or []) + (b or []):
                name = pkg if isinstance(pkg, str) else pkg.name if hasattr(pkg, 'name') else pkg.get('name', pkg)
                seen[name] = pkg
            return list(seen.values())

        result = Dependencies()

        # Merge Python
        if self.python or other.python:
            result.python = PythonDependencies(
                version=other.python.version if other.python else (self.python.version if self.python else None),
                manager=other.python.manager if other.python else (self.python.manager if self.python else PythonManager.pip),
                packages=merge_packages(
                    self.python.packages if self.python else [],
                    other.python.packages if other.python else []
                )
            )

        # Merge R
        if self.r or other.r:
            result.r = RDependencies(
                version=other.r.version if other.r else (self.r.version if self.r else None),
                cran_mirror=other.r.cran_mirror if other.r else (self.r.cran_mirror if self.r else "https://cloud.r-project.org/"),
                lib_path=other.r.lib_path if other.r else (self.r.lib_path if self.r else None),
                packages=merge_packages(
                    self.r.packages if self.r else [],
                    other.r.packages if other.r else []
                )
            )

        # Merge Octave
        if self.octave or other.octave:
            result.octave = OctaveDependencies(
                version=other.octave.version if other.octave else (self.octave.version if self.octave else None),
                forge=other.octave.forge if other.octave else (self.octave.forge if self.octave else True),
                packages=merge_packages(
                    self.octave.packages if self.octave else [],
                    other.octave.packages if other.octave else []
                )
            )

        # Merge Julia
        if self.julia or other.julia:
            result.julia = JuliaDependencies(
                version=other.julia.version if other.julia else (self.julia.version if self.julia else None),
                packages=merge_packages(
                    self.julia.packages if self.julia else [],
                    other.julia.packages if other.julia else []
                )
            )

        # Merge System
        if self.system or other.system:
            result.system = SystemDependencies(
                apt=list(set((self.system.apt if self.system else []) + (other.system.apt if other.system else []))),
                yum=list(set((self.system.yum if self.system else []) + (other.system.yum if other.system else []))),
                brew=list(set((self.system.brew if self.system else []) + (other.system.brew if other.system else [])))
            )

        return result


if __name__ == "__main__":
    # Test the models
    deps = Dependencies(
        python=PythonDependencies(
            version=">=3.10",
            packages=["numpy", PythonPackage(name="matplotlib", version=">=3.5")]
        ),
        r=RDependencies(
            packages=["jsonlite", "ggplot2"]
        ),
        julia=JuliaDependencies(
            packages=["JSON", "DataFrames"]
        ),
        system=SystemDependencies(
            apt=["libcurl4-openssl-dev"]
        )
    )

    print("=== YAML Output ===")
    print(deps.to_yaml())

    print("\n=== Python requirements.txt ===")
    print(deps.python.to_requirements_txt())

    print("\n=== R install script ===")
    print(deps.r.to_install_script())

    print("\n=== Julia install script ===")
    print(deps.julia.to_install_script())

    print("\n=== System apt command ===")
    print(deps.system.to_apt_command())
