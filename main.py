import requests
import re
import json
import datetime
import holidays

BUY_RECORD = [
    {
        "code": "005242",
        "buyRecordList": {
            "2020-09-09": 2500,  # 买入金额
            "2020-09-24": 2500,
        }, 
        #"sellRecordList": {
        #    "2020-10-21": 1000,  # 卖出份数
        #}
    },
    {
        "code": "001510",
        "buyRecordList": {
            "2020-09-24": 2500,
        },
    },
    {
        "code": "006101",
        "buyRecordList": {
            "2020-09-24": 2500,
        },
    },
    {
        "code": "005276",
        "buyRecordList": {
            "2020-09-24": 2500,
        },
    }
]

ONE_DAY = datetime.timedelta(days=1)
HOLIDAYS_US = holidays.US()

def nextBusinessDay(date):
    dtime = datetime.datetime.strptime(date, '%Y-%m-%d')
    nextDay = dtime + ONE_DAY
    while nextDay.weekday() in holidays.WEEKEND or nextDay in HOLIDAYS_US:
        nextDay += ONE_DAY
    return nextDay.date()

def fundHoldingDays(buyDate):
    confirmDate = nextBusinessDay(buyDate)
    today = datetime.date.today()
    holdingDays = (today - confirmDate).days + 1
    return holdingDays

class FundHistoryValue:
    def __init__(self, code, name):
        self.code = code
        self.name = name
        self.historyValueMap = {}

    def append(self, date, value):
        self.historyValueMap[date] = value        

    def getValueByDate(self, date):
        if date in self.historyValueMap:
            return self.historyValueMap[date]

        return None

    def getMaxValue(self):
        return max(self.historyValueMap.values())

    def getMinValue(self):
        return min(self.historyValueMap.values())

    def __str__(self):
        strValue = "代码: {0}, 名称: {1}, 净值列表:[\n".format(self.code, self.name)

        for date, value in self.historyValueMap.items():
            strValue += "\t日期: {0}, 净值: {1}\n".format(date, value)
        strValue += "]\n"

        return strValue


class FundEstimatedValue:
    def __init__(self, code, name, value, increasePercentage, realValue):
        self.code = code
        self.name = name
        self.value = float(value)
        self.increasePercentage = float(increasePercentage)
        self.realValue = float(realValue)

    def __str__(self):
        return "代码: {0}, 名称: {1}, 净值估算: {2}, 估算涨幅: {3}%, 单位净值: {4}".format(self.code, self.name, self.value, self.increasePercentage, self.realValue)


def getFundEstimatedValue(code):
    req = "http://fundgz.1234567.com.cn/js/{}.js?rt=1463558676006".format(code)
    resp = requests.get(req)

    pattern = r'^jsonpgz\((.*)\)'
    search = re.findall(pattern, resp.text)

    for i in search:
        data = json.loads(i)
        value = FundEstimatedValue(code, data['name'], data['gsz'], data['gszzl'], data["dwjz"])
        return value


def getFundHistoryValue(code, name):
    historyValue = FundHistoryValue(code, name)
    url = 'http://api.fund.eastmoney.com/f10/lsjz'
    
    pageIndex = 1
    # 参数化访问链接，以dict方式存储
    params = {
        'callback': 'jQuery18307633215694564663_1548321266367',
        'fundCode': code,
        'pageIndex': pageIndex,
        'pageSize': 50,
    }
    # 存储cookie内容
    cookie = 'EMFUND1=null; EMFUND2=null; EMFUND3=null; EMFUND4=null; EMFUND5=null; EMFUND6=null; EMFUND7=null; EMFUND8=null; EMFUND0=null; EMFUND9=01-24 17:11:50@#$%u957F%u4FE1%u5229%u5E7F%u6DF7%u5408A@%23%24519961; st_pvi=27838598767214; st_si=11887649835514'
    # 装饰头文件
    headers = {
        'Cookie': cookie,
        'Host': 'api.fund.eastmoney.com',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/71.0.3578.98 Safari/537.36',
        'Referer': 'http://fundf10.eastmoney.com/jjjz_%s.html' % code,
    }
    r = requests.get(url=url, headers=headers, params=params)  # 发送请求

    text = re.findall('\((.*?)\)', r.text)[0]  # 提取dict
    LSJZList = json.loads(text)['Data']['LSJZList']  # 获取历史净值数据
    TotalCount = json.loads(text)['TotalCount']  # 转化为dict

    for i in LSJZList:
        historyValue.append(i["FSRQ"], float(i["DWJZ"]))

    return historyValue


def custom_strategy(declinePencent, increasePencent, estimatedValue, currentMoney):
    if declinePencent >= 5 and estimatedValue.increasePercentage <= -1:
        needAddMoney = round(currentMoney * declinePencent * 2 / 100.0, 0)
        print("投资建议: 从高点回撤过大: {}%, 可以考虑加仓: {}元".format(declinePencent, needAddMoney))
    elif increasePencent >= 8 and estimatedValue.increasePercentage >= 1:
        needSellMoney = round(currentMoney * increasePencent * 2 / 100.0, 0)
        print("投资建议: 从低点涨幅过大{}%，可考虑卖出".format(increasePencent), needSellMoney)
    else:
        print("投资建议: 观望, 投资需要耐心")

def main():
    print("==================严格遵守投资纪律=================\n")
    for record in BUY_RECORD:
        print("---------------------------------------------------------------------")
        code = record["code"]
        estimatedValue = getFundEstimatedValue(code)
        print(estimatedValue)
        print("\n")

        historyValue = getFundHistoryValue(code, estimatedValue.name)

        print("{}, 购买记录:".format(estimatedValue.name))
        canSellFundNums = 0.0
        totalFundNum = 0.0
        for buyDate, buyMoney in record["buyRecordList"].items():
            holdingDays = fundHoldingDays(buyDate)
            hisValue = historyValue.getValueByDate(buyDate)
            fundNum = round(buyMoney / hisValue, 2)
            totalFundNum += fundNum
            print("买入, 日期: {}, 购买金额: {}, 确认份数: {}, 持有天数: {}, 确认净值: {}".format(buyDate, buyMoney, fundNum, holdingDays, hisValue))
            
            if holdingDays >= 30:
                canSellFundNums += fundNum

        if "sellRecordList" in record:
            for sellDate, sellfundNum in record["sellRecordList"].items():
                hisValue = historyValue.getValueByDate(sellDate)
                totalFundNum -= sellfundNum
                canSellFundNums = round(canSellFundNums - sellfundNum, 2)
            
                if hisValue is not None:
                    sellMoney = sellfundNum * hisValue
                    print("卖出, 日期: {}, 卖出金额: {}, 卖出份数: {}, 卖出净值: {}".format(sellDate, sellMoney, sellfundNum, hisValue))

        print("\n满 30 天可卖份数: {}".format(canSellFundNums))
        currentMoney = round(totalFundNum * estimatedValue.realValue, 2)
        estimateMoney = round(totalFundNum * estimatedValue.value, 2)
        diff = round(estimateMoney - currentMoney, 2)

        declinePencent = round(100.0 * (historyValue.getMaxValue() - estimatedValue.value) / historyValue.getMaxValue(), 2)
        increasePencent = round(100.0 * (estimatedValue.value - historyValue.getMinValue()) / historyValue.getMinValue(), 2)
        print("从最高点以来回撤: {}%, 从最低点以来涨幅: {}%".format(declinePencent, increasePencent))
        print("当前金额: {}, 今日估算盈亏: {}元".format(currentMoney, diff))
        custom_strategy(declinePencent, increasePencent, estimatedValue, currentMoney)

        print("---------------------------------------------------------------------\n")

main()
