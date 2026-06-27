"""Load my_param.json and print all fields for manual inspection."""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from backend.data_load.my_param_loader import load_my_param

if __name__ == "__main__":
    file_path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "data1", "my_param.json")
    my_param = load_my_param(file_path)
    print("Loaded my_param.json:")
    print(my_param)
