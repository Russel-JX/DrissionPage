#获取洲际官网数据
from DrissionPage import Chromium, ChromiumOptions

# 创建页面对象
tab = Chromium().latest_tab
print("======start======")

# 访问某一页的网页
tab.get(f'https://www.ihg.com.cn/hotels/cn/zh/find-hotels/hotel-search?qDest=%E5%8C%97%E4%BA%AC%E4%BA%9A%E8%BF%90%E6%9D%91&qPt=CASH&qCiD=23&qCoD=24&qCiMy=032025&qCoMy=032025&qAdlt=1&qChld=0&qRms=1&qIta=99618455&qRtP=6CBARC&qAAR=6CBARC&qAkamaiCC=CN&srb_u=1&qExpndSrch=false&qSrt=sAV&qBrs=6c.hi.ex.sb.ul.ic.cp.cw.in.vn.cv.rs.ki.kd.ma.sp.va.re.vx.nd.sx.we.lx.rn.sn.nu&qWch=0&qSmP=0&qRad=100&qRdU=km&setPMCookies=false&qpMbw=0&qErm=false&qpMn=1&qLoSe=false')
print("======visit======")
# 获取所有data-slnm-ihg属性值是brandHotelNameSID的元素列表
prices = tab.eles('@data-slnm-ihg=brandHotelNameSID')
print("======count======",len(prices))

# 爬取3页
for i in range(1, 4):
    # 遍历所有price的<div>元素
    for price in prices:
        # 打印价格信息
        print(price.text)
    #TODO 下面下滑的没成功，每次都是在第一页
    tab.scroll.to_bottom()
    