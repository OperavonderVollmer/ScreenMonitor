from setuptools import setup, find_packages

setup(
    name="ScreenMonitor",
    version="1.0",
    packages=find_packages(),
    package_data={
        'ScreenMonitor': ['assets/*'],  # Specify the folder/files to include
    },
    include_package_data=True,
    install_requires=[
        "OperaPowerRelay @ git+https://github.com/OperavonderVollmer/OperaPowerRelay.git",
        "PluginTemplate @ git+https://github.com/OperavonderVollmer/PluginTemplate.git",
        "pywin32",
        "psutil",
        "pillow",
        "pystray",
        "winotify"
    ],
    python_requires=">=3.7",
    author="Opera von der Vollmer",
    description="An application usage monitor",
    url="https://github.com/OperavonderVollmer/ScreenMonitor", 
    license="MIT",
)
