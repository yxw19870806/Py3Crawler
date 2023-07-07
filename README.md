Python3 Crawler
=====

### Required

* OS：windows（maybe Linux and mac）<br>
* Python：v3.11+, not supported Python 2.X

### Suggest

* IDE and Project Encoding setting with UTF-8

### Features

* 多线程<br>
  multithreading<br>
* 支持使用代理设置<br>
  support proxy<br>
* 支持绑定键盘事件（快捷键），如暂停/启动程序运行<br>
  support bind keyboard events, e.g. pause or restart process<br>
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

### Install
* 安装Visual C++ 生成工具 <br>
> 访问[微软官方Visual Studio下载页面](https://visualstudio.microsoft.com/downloads/)<br>
选择"用于 Visual Studio 的工具" - "Visual Studio 2022 生成工具"下载<br>
运行下载的exe引导文件、开始安装Visual Studio Installer<br>
Visual Studio Installer安装完毕后，勾选"桌面应用和移动应用"标签下的"使用C++的桌面开发"和"通用windows平台生成工具"并安装<br>

* 安装swig，并将swig的安装路径加入系统变量中，否则会提示无法找到swig.exe
> 访问[swig官网下载页面](http://www.swig.org/download.html)<br>
选择swigwin-X.X.XX（版本号，如swigwin-4.1.1）下载，不要下载源码swig-X.X.XX（如swig-4.1.1）<br>
解压下载的压缩文件到任意目录（如 D:\swig-4.1.1），并将该目录添加到系统环境变量中

* 运行 [/install/install.bat](install/install.bat)<br>

### Support website / App

* [Ameblo](https://ameblo.jp/) （最后更新日期：2022/11/02）
* [半次元](https://bcy.net/) （最后更新日期：2022/11/02）
* [哔哩哔哩](https://www.bilibili.com/) （最后更新日期：2023/07/07）
* [哔哩哔哩漫画](https://manga.bilibili.com/) （最后更新日期：2022/11/02）
* [Dailymotion](https://www.dailymotion.com/) （最后更新日期：2022/11/02）
* [动漫之家漫画](https://www.dmzj.com/) （最后更新日期：2022/11/02）
* [5sing](https://5sing.kugou.com/index.html) （最后更新日期：2022/11/02）
* [Flickr](https://www.flickr.com/) （最后更新日期：2022/11/02）
* [日向坂46公式Blog](https://www.hinatazaka46.com/s/official/diary/member) （最后更新日期：2022/11/02）
* [Instagram](https://www.instagram.com/) （最后更新日期：2022/07/25）
* [欅坂46公式Blog](https://www.keyakizaka46.com/s/k46o/diary/member) （最后更新日期：2022/11/02）
* [Lofter](https://www.lofter.com/) （最后更新日期：2022/11/02）
* [漫画柜漫画](https://www.manhuagui.com/) （最后更新日期：2023/07/07）
* [美拍](https://www.meipai.com/) （最后更新日期：2022/11/02）
* [755](https://7gogo.jp/) （最后更新日期：2022/07/20）
* [乃木坂46公式Blog](https://www.nogizaka46.com/s/n46/diary/MEMBER/list) （最后更新日期：2022/11/02）
* [起点](https://www.qidian.com/) （最后更新日期：2023/05/10）
* [TikTok](https://www.tiktok.com/)
* [听书宝](http://m.tingshubao.com/) （最后更新日期：2022/11/02）
* [图虫](https://tuchong.com/) （最后更新日期：2022/11/02）
* [Tumblr](https://www.tumblr.com/) （最后更新日期：2022/11/02）
* [Twitter](https://twitter.com/) （最后更新日期：2022/07/20）
* [微博](https://weibo.com/) （最后更新日期：2022/07/25）
* [World Cosplay](https://worldcosplay.net/) （最后更新日期：2022/07/25）
* [喜马拉雅FM](https://www.ximalaya.com/) （最后更新日期：2022/07/20）
* [一直播](https://www.yizhibo.com/) （最后更新日期：2022/07/20）
* [Youtube](https://www.youtube.com/) （最后更新日期：2022/12/15）

### Code Structure  

1. [/common](common)，公共类<br>
   * [/common/crawler.py](common/crawler.py) 爬虫父类，多线程爬取父类，异常类<br>
   * [/common/browser.py](common/browser.py) 浏览器，获取操作系统中安装的浏览器目录以及保存的cookies；模拟浏览器渲染效果<br>
   * [/common/color_format.py](common/color_format.py) 格式化输出内容<br>
   * [/common/console.py](common/console.py) 控制台输出，线程安全<br>
   * [/common/const.py](common/const.py) 常量<br>
   * [/common/crypto.py](common/crypto.py) 加密解密类，使用基于本计算机信息（MAC+计算机名）的私钥对隐私信息进行AES128加密（如输入的账号、密码）<br>
   * [/common/file.py](common/file.py) 用来处理文件读、写的常用方法，计算文件MD5值<br>
   * [/common/keyboard_event.py](common/keyboard_event.py) 键盘监听事件，可以通过指定快捷键暂停/重启/立刻结束爬虫（默认在下一次网络请求时阻塞线程）<br>
   * [/common/logger.py](common/logger.py) 日志，封装自logging<br>
   * [/common/net.py](common/net.py) 网络通信（基于urllib3），网页访问、资源下载等<br>
   * [/common/net_config.py](common/net_config.py) 网络通信配置类<br>
   * [/common/path.py](common/path.py) 用来处理操作系统路径相关的常用方法，创建/删除目录，移动/复制文件或文件夹等操作<br>
   * [/common/port_listener_event.py](common/port_listener_event.py) 端口监听类，可以通过向指定端口发送请求暂停/重启/立刻结束爬虫（默认在下一次网络请求时阻塞线程）<br>
   * [/common/tool.py](common/tool.py) 其他一些常用方法，如字符串截取，字符串和列表的转化等
   * [/common/url.py](common/url.py) 用来处理URL的常用方法，如获取文件名，解析query参数等
   * [/common/log_config.json](common/log_config.json) 日志类的配置文件
   * [/common/net_config.json](common/net_config.json) 网络通信类的配置文件
2. [/install](install)，项目依赖的一些扩展包的安装文件（使用pip install）
3. [/project](project)，爬虫项目
