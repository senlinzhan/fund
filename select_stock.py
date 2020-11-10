import requests
import pyhkconnect as hkc
import json
from bs4 import BeautifulSoup
import re
import tushare as ts
import csv
from datetime import date
import datetime
import os.path


class Stock:

    def __init__(self, Acode, name, hold_num, percent):
        self.Acode = Acode
        self.name = name
        self.hold_num = hold_num
        self.percent = percent


code_name = {}


def get_yesterday_price(Acode):
    yesterdayObj = date.today() - datetime.timedelta(days=1)
    yesterday = yesterdayObj.strftime("%Y%m%d")

    pro = ts.pro_api(
        '2771aab48229b73d209c27e7cbd333a4156eabe774b7c57f4e4c1d9d')
    if Acode in code_name:
        code = Acode + "." + code_name[Acode]["zone"]
        df = pro.daily(ts_code=code,
                       start_date=yesterday, end_date=yesterday)
        if "close" in df and len(df["close"]) > 0:
            return float(df["close"][0])

    return 0.0


def getname():
    pro = ts.pro_api(
        '2771aab48229b73d209c27e7cbd333a4156eabe774b7c57f4e4c1d9d')
    data = pro.stock_basic(exchange='', list_status='L',
                           fields='ts_code,symbol,name,area,industry,list_date')

    index = 0
    for code in data["ts_code"]:
        Acode = code.split(".")[0]
        zone = code.split(".")[1]
        name = data["name"][index]
        code_name[Acode] = {
            "name": name,
            "zone": zone
        }
        index = index + 1


def write_info_map(info_map):
    today = date.today().strftime("%Y-%m-%d")
    name = "info-" + today + ".csv"
    if not os.path.exists(name):
        with open(name, 'w', newline='') as csvfile:
            spamwriter = csv.writer(csvfile, delimiter=' ',
                                    quotechar='|', quoting=csv.QUOTE_MINIMAL)
            for Acode, stock in info_map.items():
                spamwriter.writerow(
                    [Acode, stock.name, stock.hold_num, stock.percent])


def load_info_map_yesterday():
    info_map = {}
    yesterdayObj = date.today() - datetime.timedelta(days=1)
    yesterday = yesterdayObj.strftime("%Y-%m-%d")
    name = "info-" + yesterday + ".csv"
    if os.path.exists(name):
        with open(name) as f:
            spamreader = csv.reader(f, delimiter=' ', quotechar='|')
            for row in spamreader:
                info_map[row[0]] = Stock(row[0], row[1], row[2], row[3])

    return info_map


def yesterday_buy_top50(info_map, yesterday_info_map):
    diff_map = {}
    for Acode, stock in info_map.items():
        if Acode in yesterday_info_map:
            yesterday_stock = yesterday_info_map[Acode]
            diff_hold_num = float(stock.hold_num) - \
                float(yesterday_stock.hold_num)
            diff_percent = float(stock.percent) - \
                float(yesterday_stock.percent)
            diff_map[Acode] = {
                "hold_num": diff_hold_num,
                "percent": diff_percent,
                "name": stock.name
            }
    sorted_diff_map = sorted(diff_map.items(), key=lambda item: item[
        1]["hold_num"], reverse=True)
    return sorted_diff_map[0:50]


def yesterday_buy_money_top50(info_map, yesterday_info_map):
    diff_map = {}
    for Acode, stock in info_map.items():
        if Acode in yesterday_info_map:
            yesterday_stock = yesterday_info_map[Acode]
            diff_hold_num = float(stock.hold_num) - \
                float(yesterday_stock.hold_num)

            # 外资持股大于 5% 并且当天买入超过 10000 股
            if stock.percent >= 5.0 and diff_hold_num >= 10000:
                price = get_yesterday_price(Acode)
                diff_money = round(diff_hold_num * price /
                                   10000.0 / 10000.0, 2)
                diff_map[Acode] = {
                    "hold_num": diff_hold_num,
                    "money": diff_money,
                    "name": stock.name,
                }

    sorted_diff_map = sorted(diff_map.items(), key=lambda item: item[
        1]["money"], reverse=True)
    return sorted_diff_map


if __name__ == "__main__":
    getname()

    dp = hkc.northbound_shareholding_sh()
    json_obj = json.loads(dp.to_json(orient='index'))

    info_map = {}

    for code, stock_info in json_obj.items():
        Acode = stock_info["name"].split()[-1][1:-1]
        if "#" in Acode:
            Acode = Acode.split('#')[1]

        china_name = "未知"
        if Acode in code_name:
            china_name = code_name[Acode]["name"]
        hold_num = stock_info["shareholding"].replace(",", "")
        percent = float(stock_info["shareholding_percent"][:-1])
        stock = Stock(Acode, china_name, hold_num, percent)
        info_map[Acode] = stock

    dp = hkc.northbound_shareholding_sz()
    json_obj = json.loads(dp.to_json(orient='index'))
    for code, stock_info in json_obj.items():
        Acode = stock_info["name"].split()[-1][1:-1]
        if "#" in Acode:
            Acode = Acode.split("#")[1]

        china_name = "未知"
        if Acode in code_name:
            china_name = code_name[Acode]["name"]
        hold_num = stock_info["shareholding"].replace(",", "")
        percent = float(stock_info["shareholding_percent"][:-1])
        stock = Stock(Acode, china_name, hold_num, percent)
        info_map[Acode] = stock

    write_info_map(info_map)

    sorted_map = sorted(info_map.items(), key=lambda item: item[
                        1].percent, reverse=True)

    print("外资持股TOP 50:")
    print("================================================================")
    for item in sorted_map[0:50]:
        stock = item[1]

        print("代码: {}, 名称: {:>4}, 外资持股数: {}, 外资持股比例: {}%".format(
            stock.Acode, stock.name, stock.hold_num, stock.percent))

    yesterday_info_map = load_info_map_yesterday()
    yes_buy_top50 = yesterday_buy_top50(info_map, yesterday_info_map)
    print("\n外资昨天买入股数TOP 50:")
    print("================================================================")
    for item in yes_buy_top50:
        Acode = item[0]
        stock_diff = item[1]
        print("代码: {}, 名称: {:>4}, 外资买入股数: {}, 外资持股变化: {}%".format(
            Acode, stock_diff["name"], stock_diff["hold_num"],
            round(stock_diff["percent"], 2)))

    print("================================================================")
    print("\n外资昨天买入资金TOP 50:")
    yes_buy_money_top50 = yesterday_buy_money_top50(
        info_map, yesterday_info_map)
    for item in yes_buy_money_top50:
        Acode = item[0]
        stock_diff = item[1]
        print("代码: {}, 名称: {:>4}, 外资买入股数: {}, 买入金额: {}亿".format(
            Acode, stock_diff["name"], stock_diff["hold_num"], stock_diff["money"]))
