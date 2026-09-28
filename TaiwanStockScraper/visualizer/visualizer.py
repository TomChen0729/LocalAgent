import matplotlib.pyplot as plt
import pandas as pd

def visualize_stock_data(data):
    plt.figure(figsize=(10, 6))
    plt.plot(data['date'], data['price'], marker='o', linestyle='-', color='b')
    plt.title('Taiwan Stock Price Visualization')
    plt.xlabel('Date')
    plt.ylabel('Price')
    plt.grid(True)
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.show()