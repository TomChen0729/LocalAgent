import requests
import pandas as pd

class StockScraper:
    def __init__(self, stock_code):
        self.stock_code = stock_code
        self.base_url = "https://example.com/stock_data"  # 這需要替換為實際的台股數據源

    def fetch_data(self):
        params = {
            "code": self.stock_code,
            "date": "2023-10-10"  # 這需要參數化為動態日期
        }
        response = requests.get(self.base_url, params=params)
        return pd.DataFrame(response.json())

    def save_data(self, filename):
        self.data.to_csv(f"{filename}.csv", index=False)