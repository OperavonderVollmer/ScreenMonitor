# ScreenMonitor

**HeadMade** dutifully sorts folders for you based on pre-written rules on a time based interval

# Features

- **Robust Rule System:** Allows you to create multiple rules of files that are applicable
- **Time Based Execution:** Performs file sorting either on a select time, or select intervals

 
## Installation

### Prerequisites

- Python 3.x
- Required dependencies (install using pip):
  ```sh
  pip install Pillow pystray git+https://github.com/OperavonderVollmer/OperaPowerRelay.git
  ```

### Manual Installation

1. Clone or download the repository.
2. Navigate to the directory containing `setup.py`:
   ```sh
   cd /path/to/HeadMade
   ```
3. Install the package in **editable mode**:
   ```sh
   pip install -e .
   ```

### Installing via pip
```sh
pip install git+https://github.com/OperavonderVollmer/HeadMade@main
```

## Usage
Run HeadMade.bat to open the script

### Configuring the Filesorter   
1. Provide the file path of the folder to be sorted.
2. Provide a set of criteria that the file must have for it to be eligable for sorting.
3. Provide a destination folder for the eligable files to be sent to
4. Repeat as required

### Configuring HeadMade
1. Select between Interval based or Schedule based configuration
2. Provide a time in HH:MM:SS military time format
3. HeadMade will either perform its every HH:MM:SS (interval) throughout a day or every HH:MM:SS once a day (schedule)
