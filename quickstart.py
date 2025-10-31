import ast
import sys
import os
import subprocess
import shutil
import urllib.request
import zipfile
import tempfile

def get_package_name(setup_path: str):
    with open(setup_path, "r", encoding="utf-8") as f:
        node = ast.parse(f.read(), filename=setup_path)

    for stmt in node.body:
        # Find the setup() call
        if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
            func = stmt.value.func
            if getattr(func, "id", "") == "setup":  # found setup()
                for kw in stmt.value.keywords:
                    if kw.arg == "name":
                        return ast.literal_eval(kw.value)
    return None

def create_virtual_environment():
    print("Creating virtual environment...")
    subprocess.run(["python", "-m", "venv", "venv"])
    subprocess.run([sys.executable, "-m", "venv", "venv"], check=True)
    print("\033[92mSUCCESS\033[0m: Virtual Environment created")

NO_GIT_FLAG = False
GIT_PATH = ""
def has_git():
    print("Checking for git...")
    global NO_GIT_FLAG
    try:    
        subprocess.run(["git", "--version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print("\033[92mSUCCESS\033[0m: Git has been found")
        return True
    except FileNotFoundError:
        print("\033[94mINFO\033[0m: Git not found")
        NO_GIT_FLAG = True
        return False
    


def install_temp_git():
    if not has_git():
        
        global GIT_PATH
        print("\n\nTemporarily Installing Git...")

        temp_dir = tempfile.mkdtemp()
        portable_git_exe = os.path.join(temp_dir, "PortableGit.exe")
        url = "https://github.com/git-for-windows/git/releases/download/v2.51.1.windows.1/PortableGit-2.51.1-64-bit.7z.exe"

        print("Downloading Portable Git...")
        urllib.request.urlretrieve(url, portable_git_exe)

        portable_git_temp_dir = os.path.join(temp_dir, "PortableGit")
        
        GIT_PATH = portable_git_temp_dir

        print(f"Installing Portable Git to {portable_git_temp_dir}\nPlease press OK... (This will be deleted after installation)")
        subprocess.run([
            portable_git_exe,
            f'/DIR={portable_git_temp_dir}',
            '/VERYSILENT',
            '/NORESTART'
        ], check=True)

        git_bin = os.path.join(portable_git_temp_dir, "cmd")
        os.environ["PATH"] = f"{git_bin};" + os.environ["PATH"]
        print("\033[92mSUCCESS\033[0m: Git temporarily installed")


def clean_temp_git(path):
    if path and os.path.exists(path):
        print(f"Cleaning up PortableGit from {path}")
        shutil.rmtree(path, ignore_errors=True)
        print("\033[92mSUCCESS\033[0m: Cleanup complete")



def install_requirements():
    print("\n\nInstalling requirements...")
    pip_path = os.path.join("venv", "Scripts", "pip.exe")    
    env = os.environ.copy()
    global GIT_PATH
    if GIT_PATH:
        subprocess.run(["where", "git"], env=env)
        git_cmd = os.path.join(GIT_PATH, "cmd")
        git_usr_bin = os.path.join(GIT_PATH, "usr", "bin")
        git_mingw_bin = os.path.join(GIT_PATH, "mingw64", "bin")
        env["PATH"] = f"{git_cmd};{git_usr_bin};{git_mingw_bin};" + env["PATH"]
    subprocess.run([pip_path, "install", "-r", "requirements.txt"], check=True, env=env)
    print("\033[92mSUCCESS\033[0m: Requirements have been installed")


def create_quickstart_bat(script_name):
    """
    Creates a Windows batch file that runs quickstart.py from its own directory.
    """
#     bat_contents = rf"""@echo off
# setlocal

# cd /d "%~dp0"

# title {script_name}

# call ".\venv\Scripts\activate.bat"

# python ".\main.py"
# """
    bat_contents = rf"""@echo off
setlocal

cd /d "%~dp0"

title {script_name}

start "" ".\venv\Scripts\pythonw.exe" ".\main.py"
"""
    path = f"start {script_name}.bat"
    with open(path, "w", encoding="utf-8") as f:
        f.write(bat_contents)
    print(f"\033[92mSUCCESS:\033[0m {path} created")


def main():

    script_name = get_package_name("setup.py")
    print(f"\033[91mNOTICE:\033[0m This script will install the necessary files for \033[94m{script_name}\033[0m. This will create a virtual environment to contain these files and dependants, without modifying your system.\n\n")

    success = False

    while True:
        _ = input("Continue? (y/n) ").lower()
        if _ == "y" or _ == "n":
            if _ == "y":
                break
            else:
                print("Exiting...")
                exit()

    try:
        create_virtual_environment()
        install_temp_git()
        install_requirements()
        success = True

    except Exception as e:
        print("\033[91mERROR:\033[0m", e)

    finally:
        global NO_GIT_FLAG
        global GIT_PATH
        if NO_GIT_FLAG:
            clean_temp_git(GIT_PATH)

    if success:
        try:
            create_quickstart_bat(script_name)
            input("\n\n\033[92mSUCCESS\033[0m: Virtual Environment and Requirements Installed. Press enter to exit...")
            exit()
        except Exception as e:
            print("\033[91mERROR:\033[0m", e)

    
    input(f"\n\n\033[91mFAILED:\033[0m: {script_name} failed to install. Press enter to exit...")


if __name__ == "__main__":
    main()