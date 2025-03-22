#执行以下代码，浏览器启动并且访问了项目官网，说明可直接使用，跳过后面的步骤即可。
from DrissionPage import Chromium

tab = Chromium().latest_tab
tab.get('http://DrissionPage.cn')