Python Crawler（auto download from website）
=====

# Required

* OS：windows（maybe Linux and mac）<br>
* Python：v3.8+, not supported Python 2.X

# Suggest

* IDE and Project Encoding setting with UTF-8

# Features

* 多线程<br>
  multithreading<br>
* 支持使用代理设置<br>
  support proxy<br>
* 支持绑定键盘事件（快捷键），如暂停/启动程序运行<br>
  support bind keyboard events, e.g. pause or restart process<br>
* 支持本地端口监听，根据收到的请求内容暂停/启动程序运行<br>
  support local port listener, according to the received content to pause or restart process<br>
* 支持从本地浏览器中读取cookies并携带访问限制的网站<br>
  read cookies from your local browser<br>
* 页面访问支持多种参数：<br>
  support multiple parameter for visit web
    * 支持常用请求方法：GET、POST、HEAD、PUT、DELETE、OPTIONS、TRACE<br>
      common request method: GET, POST, HEAD, PUT, DELETE, OPTIONS, TRACE<br>
    * 可自定义添加request header<br>
      add customize request header<br>
    * 可自定义添加Cookies<br>
      add customize cookies<br>
    * 可设置链接超时、读取超时<br>
      set connection timeout and read timeout<br>
    * 可设置是否自动跳转（http code 301、302、303、307、308）<br>
      set whether auto redirect(http code 301, 302, 303, 307, 308) <br>

# Install

* 如果已安装Visual C++ 生成工具和swig（并将swig的安装路径加入系统变量中，否则会提示无法找到swig.exe），请运行install/install.bat<br>
  If you have installed Visual C++ Build Tools and swig for windows (and add swig's install path to your environment
  variables), you can run install/install.bat <br>

> 如何安装Visual C++ 生成工具
>> 访问[微软官方Visual Studio下载页面](https://visualstudio.microsoft.com/downloads/)<br>
选择"Visual Studio 2019 工具" - "Visual Studio 2019 生成工具"下载<br>
运行下载的exe引导文件、开始安装Visual Studio Installer<br>
Visual Studio Installer安装完毕后，勾选"桌面应用和移动应用"标签下的"使用C++的桌面开发"和"通用windows平台生成工具"并安装<br>

> 如何安装swig
>> 访问[swig官网下载页面](http://www.swig.org/download.html)<br>
选择swigwin-X.X.XX（版本号，如swigwin-4.0.2）下载，不要下载源码swig-X.X.XX（如swig-4.0.2）<br>
解压下载的压缩文件到任意目录，并将该目录添加到系统环境变量中（如 D:\swig-4.0.2）

* (不推荐) 如果未安装Visual C++ 生成工具和swig，请运行install/install.bat<br>
  (Don't suggest) If you haven't installed Visual C++ Build Tools and swig for windows, you can run
  install/install_whl.bat<br>

# Support website / App

* [Ameblo](https://ameblo.jp/) （有效性检测日期：2022/07/19）
* [半次元](https://bcy.net/) （有效性检测日期：2022/07/19）
* [哔哩哔哩](https://www.bilibili.com/) （有效性检测日期：2022/07/19）
* [哔哩哔哩漫画](https://manga.bilibili.com/) （有效性检测日期：2022/07/19）
* [Dailymotion](https://www.dailymotion.com/) （有效性检测日期：2022/07/19）
* [动漫之家漫画](https://www.dmzj.com/) （有效性检测日期：2022/07/19）
* [5sing](https://5sing.kugou.com/index.html) （有效性检测日期：2022/07/19）
* [Flickr](https://www.flickr.com/) （有效性检测日期：2022/07/19）
* [日向坂46公式Blog](https://www.hinatazaka46.com/s/official/diary/member) （有效性检测日期：2022/07/19）
* [Instagram](https://www.instagram.com/)
* [欅坂46公式Blog](https://www.keyakizaka46.com/s/k46o/diary/member) （有效性检测日期：2022/07/20）
* [Lofter](https://www.lofter.com/) （有效性检测日期：2022/07/20）
* [漫画柜漫画](https://www.manhuagui.com/) （有效性检测日期：2022/07/20）
* [美拍](https://www.meipai.com/) （有效性检测日期：2022/07/20）
* [755](https://7gogo.jp/) （有效性检测日期：2022/07/20）
* [乃木坂46公式Blog](https://www.nogizaka46.com/s/n46/diary/MEMBER/list) （有效性检测日期：2022/07/20）
* [TikTok](https://www.tiktok.com/)
* [听书宝](http://m.tingshubao.com/) （有效性检测日期：2022/07/20）
* [图虫](https://tuchong.com/) （有效性检测日期：2022/07/20）
* [Tumblr](https://www.tumblr.com/)
* [Twitter](https://twitter.com/)
* [微博](https://weibo.com/)
* [World Cosplay](https://worldcosplay.net/)
* [喜马拉雅FM](https://www.ximalaya.com/) （有效性检测日期：2022/07/20）
* [一直播](https://www.yizhibo.com/)
* [Youtube](https://www.youtube.com/)

# Code Structure

1. /common，公共类<br>

* /common/crawler.py 爬虫父类，多线程爬取父类，异常类<br>
* /common/browser.py 浏览器类，获取操作系统中安装的浏览器目录以及保存的cookies<br>
* /common/crypto.py 加密解密类，使用基于本计算机信息（MAC+计算机名）的私钥对隐私信息进行AES128加密（如输入的账号、密码）<br>
* /common/file.py 文件操作类，读、写文件，计算文件MD5值<br>
* /common/keyboard_event.py 键盘监听事件类，可以通过指定快捷键暂停/重启/立刻结束爬虫（默认在下一次网络请求时阻塞线程）<br>
* /common/log.py 日志记录类，线程安全，4个级别（error、step、trace、notice）的日志记录方法<br>
* /common/net.py 网络通信类（基于urllib3），网页访问、资源下载等<br>
* /common/output.py 控制台输出类，线程安全<br>
* /common/path.py 操作系统路径相关类，创建/删除目录，移动/复制文件或文件夹等操作<br>
* /common/port_listener_event.py 端口监听类，可以通过向指定端口发送请求暂停/重启/立刻结束爬虫（默认在下一次网络请求时阻塞线程）<br>
* /common/tool.py 其他一些公共方法类，如字符串截取，字符串和列表的转化等
* /common/log_config.json 日志类的配置文件
* /common/net_config.json 网络通信类的配置文件

2. /install，项目依赖的一些扩展包的安装文件（使用pip install）
3. /project，爬虫项目

# Known Issue

* **install/install_whl.bat** 中使用的PyHook（用于在windows中监听鼠标、键盘事件）在python3下有兼容性问题<br>
  如果前台激活了存在非ascii字符的窗口，会抛出异常（类似于 TypeError: KeyboardSwitch() missing 8 required positional arguments: 'msg', '
  vk_code', 'scan_code', 'ascii', 'flags', 'time', 'hwnd', and 'win_name'）、甚至导致进程退出<br>
  如遇到该问题，可安装Visual C++ 生成工具和swig后使用**install/install.bat**中的PyHook3替换；或者在config.ini中禁用键盘事件监听功能
* 一些较大文件会自动开启多线程下载，有小几率可能无法检测因网络原因导致的部分分段下载失败，可在/common/net_config.json中将ENABLE_MULTI_THREAD_DOWNLOAD设置为False
