# debug_hook.py
"""
Debug module for more efficient
and compact traceback prints

Author: Elcoyote Solitaire
"""
import sys
import traceback
import os
import linecache


def find_project_frame(exc_tb, project_root, python_install_path, venv_path):
    """
    Finds the last line of error from the traceback

    Makes sure the lines are from your project's files
    ignoring libraries and virtual environment (venv)

    Returns:
        inner_frame as str for the last line of error
    """
    tb_frames = []
    tb_frame = exc_tb
    while tb_frame:
        tb_frames.append(tb_frame)
        tb_frame = tb_frame.tb_next

    inner_frame = tb_frames[-1]
    frame = inner_frame.tb_frame
    filename = os.path.abspath(frame.f_code.co_filename)

    if filename.startswith(project_root):
        return inner_frame
    else:
        for tb_frame in reversed(tb_frames):
            frame = tb_frame.tb_frame
            filename = os.path.abspath(frame.f_code.co_filename)
            if filename.startswith(project_root):
                return tb_frame
        return inner_frame

def custom_excepthook(exc_type, exc_value, exc_tb):
    """
    Custom exception hook for a better, more concise display of the traceback

    Errors covered:
        AttributeError
        IndexError
        ValueError
        KeyError
        FileNotFoundError
    """
    traceback.print_exception(exc_type, exc_value, exc_tb)
    print("\n===== Custom Exception Handler =====\n")
    print(f"{exc_type.__name__}: {exc_value}")

    python_install_path = os.path.abspath(sys.base_prefix)
    venv_path = os.path.abspath(sys.prefix)

    project_root = os.path.abspath(os.getcwd())  # or the actual path to your project

    tb_frame = find_project_frame(exc_tb, project_root, python_install_path, venv_path)
    frame = tb_frame.tb_frame
    filename = os.path.abspath(frame.f_code.co_filename)
    lineno = tb_frame.tb_lineno
    function = frame.f_code.co_name

    try:
        with open(filename, "r", encoding="utf-8") as f:
            lines = f.readlines()
            code_line = lines[lineno - 1].strip()
    except Exception as e:
        code_line = f"Could not read code line: {e}"

    print(f"Full path: {filename}")
    print(f"File: {os.path.basename(filename)}")
    print(f"Function: {function}")
    print(f"Line number: {lineno}")
    print(f"Line of code: {code_line}")

    if exc_type is AttributeError:
        try:
            error_msg = str(exc_value)
            print(f"Error message: {error_msg}")

            if "object '" in error_msg and "' has no attribute" in error_msg:
                start = error_msg.find("object '") + len("object '")
                end = error_msg.find("'", start)
                obj_name = error_msg[start:end]
                print(f"Extracted object name: {obj_name}")

                obj = eval(obj_name)

                attrs = [attr for attr in dir(obj) if not (attr.startswith('__') and attr.endswith('__'))]
                print(f"Attributes of {obj_name}:\n{attrs}")
            else:
                print("Could not parse object name from error message.")
        except Exception as err_attr:
            print(f"Could not display attributes due to: {err_attr}")

    elif exc_type is IndexError:
        try:
            tb_frame = exc_tb.tb_frame
            local_vars = tb_frame.f_locals
            for var_name, var_value in local_vars.items():
                tup_index = 0
                if isinstance(var_value, (list, tuple)):
                    for ind_val in var_value:
                        print(f"Index {tup_index}: {ind_val}")
                        tup_index += 1
        except Exception as err_list:
            print(f"Could not display list/tuple contents: {err_list}")

    elif exc_type is ValueError:
        tb_frame = exc_tb.tb_frame
        local_vars = tb_frame.f_locals

        if "unpack" in str(exc_value):
            try:
                line = linecache.getline(tb_frame.f_code.co_filename, exc_tb.tb_lineno).strip()
            except Exception as err_line:
                print(f"Could not get problematic line: {err_line}")

            found = False
            for var_name, var_value in local_vars.items():
                if isinstance(var_value, (list, tuple)):
                    print(f"Variable '{var_name}' (list/tuple) contents: {var_value}")
                    found = True
            if not found:
                print("No list/tuple variable found in locals at this frame.")

        elif "unconverted data remains" in str(exc_value):
            print("Datetime parsing ValueError detected.")
            for var_name, var_value in local_vars.items():
                if isinstance(var_value, str) and not var_name.startswith("__"):
                    print(f"Involved string variable '{var_name}': '{var_value}'")

    elif exc_type is KeyError:
        tb_frame = exc_tb.tb_frame
        local_vars = tb_frame.f_locals
        print(f"KeyError for key: {exc_value}")
        for var_name, var_value in local_vars.items():
            if isinstance(var_value, dict) and not var_name.startswith("__"):
                print(f"Dictionary '{var_name}' available keys: {list(var_value.keys())}")

    elif exc_type is FileNotFoundError:
        file_path = getattr(exc_value, "filename", "Unknown")
        _, ext = os.path.splitext(file_path)

        cwd = os.getcwd()
        all_files = os.listdir(cwd)

        same_ext_files = [f for f in all_files if f.lower().endswith(ext.lower())]

        print(f"FileNotFoundError: {exc_value}")
        print(f"Current working directory: {cwd}")
        if same_ext_files:
            print(f"Files with extension '{ext}':")
            for file in same_ext_files:
                print(f"  - {file}")
        else:
            print("🔎 No files found with the same extension.")

    print("\n===== End of Custom Exception Handler =====\n")


sys.excepthook = custom_excepthook
