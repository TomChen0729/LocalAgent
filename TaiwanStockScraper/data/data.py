# 數據處理
import pandas as pd

def save_data(data, filename):
    data.to_csv(f"{filename}.csv", index=False)

def load_data(filename):
    return pd.read_csv(f"{filename}.csv")