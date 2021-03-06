# coding=UTF-8
'''
######注意：首行必须定义编码
######获取网站数据主类(CSDN测试)
Created on 2020年4月2日

@author: dapao
'''
import os
import sys
import re
from bs4 import BeautifulSoup
import requests
import xlrd
import xlwt
import json
from xlutils.copy import copy
import datetime
# 用于解决爬取的数据格式化
import io
from future.backports.misc import count
from telnetlib import theNULL
from _datetime import date
import time
"""
※重要：共通方法的导入
"""
from com.free.utils.MailUtils import sendmail
from com.free.constant import CommonConstants
# Pojo导入
from com.free.pojo.FundDataPojo import FundDataPojo
from com.free.utils.PropertiesUtils import PropertiesUtils
config=PropertiesUtils()
from com.free.utils.LogUtils import getDebugObj, getErrorObj, MyLogger
mydebug = getDebugObj()
myerror = getErrorObj()
"""
REDME
详细解释：
本工具读取“天天基金网”（http://fund.eastmoney.com/）的指数型基金数据，通过自定义算法计算出符合预期的基金。
自定义算法：
1，
"""
"""
ULRd的描述部分
"""
# 基金的行业分布（JSON）
url_1 = r"http://api.fund.eastmoney.com/f10/HYPZ/?fundCode=519760&year=&callback=jQuery183004054548993098228_1610464364467&_=1610464364557"
#基金概况，(Page)
url_2=r"http://fundf10.eastmoney.com/jbgk_519760.html"
# 网页内容文件形式(路径)
file_path = config.get("net_data_save_path")
# 网页内容Excel形式(路径)
excel_path = config.get("net_excel_save_path")
# 当前时间(格式YYYYMMDDHHMiSS)
currentTime_YMDHMS = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
# 当前时间(格式YYYYMMDDHHMiSS)
currentTime = datetime.datetime.now()
# 网页内容文件形式(文件名)
fileNamePrefix = r"/site_data_json_"
# 网页内容文件形式(文件后缀)
fileNameSuffix = ".txt"
sys.stdout = io.TextIOWrapper(sys.stdout.buffer,CommonConstants.ENCODING_GB2312)
sys.setrecursionlimit(1000000)
# 获取多少条数控(控制变量)
selectNetDataCount = 10
# 获取网站的对象
def getUrlContent(url,headerFlg):
    
    # 建立代理
    proxy = {
        'http': 'http://106.75.25.3:80'
    }
    # 设置请求头 (※只有基金排行网站访问时使用)
    if headerFlg == "fundRankList" : 
        headers = {
            #'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.75 Safari/537.36',
            'Host': 'fund.eastmoney.com',
            'Connection': 'keep-alive',
            'Pragma': 'no-cache',
            'Cache-Control': 'no-cache',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.75 Safari/537.36',
            'Accept': '*/*',
            'Referer': 'http://fund.eastmoney.com/data/fundranking.html',
            'Accept-Encoding': 'gzip, deflate',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Cookie': 'st_si=88549087168632; st_asi=delete; ASP.NET_SessionId=iwwbre0e4dr1yi1ptd442kg3; st_pvi=78812708860534; st_sp=2020-04-05%2020%3A21%3A36; st_inirUrl=https%3A%2F%2Fwww.baidu.com%2Flink; st_sn=7; st_psi=2020123021012913-0-2920876662'
        }
        webPage = requests.get(url, headers=headers)
    else:
        webPage = requests.get(url)
#     webPage = requests.get(url, headers=headers, proxies=proxy, timeout=1)
    mydebug.logger.debug("当前访问网址：%s" %url)
    mydebug.logger.debug("访问后的状态码%d" %webPage.status_code)
    #指定网站编码
#     webPage.encoding = 'gb2312'
    jsonData = webPage.text
    return jsonData,webPage.status_code

# 判断网页是否存在
def adjustExist(url):
        # 文件路径
        fileName = file_path + fileNamePrefix + currentTime_YMDHMS + fileNameSuffix
#         fileName = file_path + fileNamePrefix + "20200405221230" + fileNameSuffix
        # 定义文件对象
        openFile = ""
        # 如果文件存在就去读取
        if(os.path.exists(fileName)) :
            mydebug.logger.debug("文件存在,开始读取: %s" % fileName)
            openFile = open(fileName, "r", encoding='utf-8')
            jsonDatas = openFile.read();
        # 否则创建文件
        else :
            mydebug.logger.debug("没有文件,开始将读取网站写入文件: %s" % fileName)
            openFile = open(fileName, "w", encoding='utf-8')
            # 获取网站的所有内容
            jsonDatas,responseCode = getUrlContent(url,"fundRankList")
            # 通过Url取得的数据放入Txt文本中（备份用）
            openFile.write(jsonDatas);
        # 关闭文件
        openFile.close()
        mydebug.logger.debug("处理的文件路径：" + fileName)
        #Excel的Title
        execelTitle = ["基金代码","基金简称","休盘日"," 单位净值 ","累计净值","日增长率","增长率(近周)","增长率(近1月)","增长率(近3月)","增长率(近6月)","增长率(近1年)","增长率(近2年)","增长率(近3年)","增长率(今年)","增长率(成立以来)","成立日期","手续费"]
        # 取得的Json数据分割
        rowDatas = jsonDatas.split('","')
        # 保存所有的基金数据(Pojo的List)
        pojoList = []
        for row_str in rowDatas:
            # 每行数据分割成列
            col_str = row_str.split(',')
            pojo = FundDataPojo()
            pojo.set_fund_cd(col_str[0]) # 基金代码
            pojo.set_fund_title(col_str[1]) # 基金简称
            pojo.set_fund_time(col_str[3]) # 日期
            pojo.set_NVA(col_str[4]) # 单位净值
            pojo.set_LJJZ(col_str[5]) # 累计净值
            pojo.set_growth_day(col_str[6]) # 日增长率
            pojo.set_growth_week(col_str[7]) # 日增长率近1周
            pojo.set_growth_month(col_str[8]) # 日增长率近1月
            pojo.set_growth_three_month(col_str[9]) # 日增长率近3月
            pojo.set_growth_six_month(col_str[10]) # 日增长率近6月
            pojo.set_growth_year(col_str[11]) # 日增长率近1年
            pojo.set_growth_two_year(col_str[12]) # 日增长率近2年
            pojo.set_growth_three_year(col_str[13]) # 日增长率近3年
            pojo.set_growth_current_year(col_str[14]) # 日增长率(当年)
            pojo.set_growth_all(col_str[15]) # 日增长率成立以来
            pojo.set_establishment_date(col_str[16]) # 成立日期
            pojo.set_service_charge(col_str[20]) # 手续费
            pojo.set_row_data_bak(row_str) # 备份当前基金数据
            pojoList.append(pojo)
        return (execelTitle,pojoList)

def writeExcel(execelTitle,execelList):
    try :
        mydebug.logger.debug("开始生成Excel")
        # 创建sheet
        workbook = xlwt.Workbook(encoding='utf-8');
        add_sheet = workbook.add_sheet("基金数据")
        # 打印Title
        for i in range(len(execelTitle)):
            add_sheet.write(0,i,label = execelTitle[i]);
        # 打印内容
        i = 0
        for row in execelList :
            global col_basic_nm
            col_basic_nm = 0
            #基金代码
            add_sheet.write(i+1,getNextColNum(),label = row.get_fund_cd());
            #基金简称
            add_sheet.write(i+1,getNextColNum(),label = row.get_fund_title());
            # 日期
            add_sheet.write(i+1,getNextColNum(),label = row.get_fund_time());
            #单位净值
            add_sheet.write(i+1,getNextColNum(),label = row.get_NVA());
            #累计净值
            add_sheet.write(i+1,getNextColNum(),label = row.get_LJJZ());
            #日增长率
            add_sheet.write(i+1,getNextColNum(),label = row.get_growth_day());
            #增长率(周)
            add_sheet.write(i+1,getNextColNum(),label = row.get_growth_week());
            #增长率(1月)
            add_sheet.write(i+1,getNextColNum(),label = row.get_growth_month());
            #增长率(3月)
            add_sheet.write(i+1,getNextColNum(),label = row.get_growth_three_month());
            #增长率(6月)
            add_sheet.write(i+1,getNextColNum(),label = row.get_growth_six_month());
            #增长率(1年)
            add_sheet.write(i+1,getNextColNum(),label = row.get_growth_year());
            #增长率(2年)
            add_sheet.write(i+1,getNextColNum(),label = row.get_growth_two_year());
            #增长率(3年)
            add_sheet.write(i+1,getNextColNum(),label = row.get_growth_three_year());
            #增长率(今年)
            add_sheet.write(i+1,getNextColNum(),label = row.get_growth_current_year());
            #日增长率成立以来
            add_sheet.write(i+1,getNextColNum(),label = row.get_growth_all());
            #成立日期
            add_sheet.write(i+1,getNextColNum(),label = row.get_establishment_date());
            #手续费
            add_sheet.write(i+1,getNextColNum(),label = row.get_service_charge());
            #备份当前基金数据
            add_sheet.write(i+1,getNextColNum(),label = row.get_row_data_bak());
            #是否可购买
            #add_sheet.write(i+1,getNextColNum(),label = row.get_LJJZ());
            i = i + 1
        excelPathAndNm = excel_path + fileNamePrefix + currentTime_YMDHMS +".xls"
        workbook.save(excelPathAndNm)
        mydebug.logger.debug("Excel生成成功，写入基金件数：%d" ,len(execelList))
        mydebug.logger.debug("Excel生成路径：%s" ,excelPathAndNm)
        return excelPathAndNm
    except Exception as e :
        myerror.logger.error("Excel生成失败 % s" % e)

col_basic_nm = 0
# Excel生成帮助
def getNextColNum():
    global col_basic_nm
    col_basic_nm = col_basic_nm + 1
    return col_basic_nm - 1

# 监视基金的处理
def doMonitorFund():
    # Common:监视基金的URL
    monitor_fund_url = config.get("monitor_fund_url")
    # Common:监视基金的List
    monitor_fund_cds = config.get("monitor_fund_cd")
    monitor_fund_cd_split = monitor_fund_cds.split(",")
    timeInt = str(int(time.time()))
    # Common：监视基金的List
    monitor_fund_cd_list = []
    # Common：监视出问题基金的List
    monitor_fund_cd_error_list = []
    # 监视的基金代码的遍历
    for monitor_fund_cd in monitor_fund_cd_split:
        # 访问的URL的关键内容替换(例如基金代码，访问URL日期等)
        monitor_fund_url_used = monitor_fund_url
        monitor_fund_url_used = monitor_fund_url_used.replace("#funcd#", monitor_fund_cd);
        monitor_fund_url_used = monitor_fund_url_used.replace("#currentTime#",  timeInt);
        # 对URL去访问并获取返回内容
        fund_site_response_content,responseCode = getUrlContent(monitor_fund_url_used,"monitorFund");
        # 访问失败的监视基金
        if responseCode != 200 :
            myerror.logger.error("当前监视基金【%s】在天天基金网站中不存在！！！",monitor_fund_cd)
            monitor_fund_cd_error_list.append(monitor_fund_cd)
            continue
        fund_site_response_content = fund_site_response_content.replace("jsonpgz(", "");
        fund_site_response_content = fund_site_response_content.replace(");", "");
        # 讲返回的内容转化为词典
        fund_site_response_dict = eval(fund_site_response_content)
        monitor_fund_cd_list.append(fund_site_response_dict)
    # 按照估算涨幅【gszzl】进行排序，reverse：true：降序，false：升序
    monitor_fund_cd_list.sort(key=orderByKey, reverse=False)
    # mail内容编写
    mail_monitor_fund_str="【监视基金的当日("+monitor_fund_cd_list[0]["gztime"].split()[0]+")涨幅概况】\n"
    mail_monitor_fund_str = mail_monitor_fund_str + ("代码 当日涨幅 名称 时间  \n")
    for monitor_fund_data in monitor_fund_cd_list:
        mail_monitor_fund_str = mail_monitor_fund_str + (monitor_fund_data["fundcode"] + " ")
        mail_monitor_fund_str = mail_monitor_fund_str + (monitor_fund_data["gszzl"] + " ")
        mail_monitor_fund_str = mail_monitor_fund_str + (monitor_fund_data["name"] + " ")
        mail_monitor_fund_str = mail_monitor_fund_str + (monitor_fund_data["gztime"].split()[1] + " \n")
    # 监视失败的URL放入邮寄本文中
    if len(monitor_fund_cd_error_list) > 0 :
        mail_monitor_fund_str = mail_monitor_fund_str + ("※该基金【代码：%s】在天天基金网站监视中出现问题，请联系管理员【mymask139@163.com】进行处理。"  % ','.join(monitor_fund_cd_error_list))
    mydebug.logger.debug("当前监视基金内容已转换为邮件，即将开始发送邮件。 邮件内容 ： \n %s" % mail_monitor_fund_str)
    return mail_monitor_fund_str

def orderByKey(elem):
    return elem["gszzl"]
    
if __name__ == '__main__':
    #URL1:开放基金排行：近2年涨幅排名（前100） and 今年    涨幅排名（前100）and 不分页 and 降序
    # 1，获取基金排行网站List
    url_arrs = [config.get("net_data_url")]
    for url in url_arrs:
        (execelTitle,execelList) = adjustExist(url)
        excelPath = writeExcel(execelTitle,execelList)
    # 2，监视基金内容
    mail_monitor_fund_str = doMonitorFund()
    sendmail("基金数据监视结果",mail_monitor_fund_str,excelPath)