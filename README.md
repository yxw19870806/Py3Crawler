Python Crawler（auto download from website）
=====
# Required
* OS：windows（maybe Linux and mac）<br>
* Python：v3.6+, not supported Python 2.X

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
If you have installed Visual C++ Build Tools and swig for windows (and add swig's install path to your environment variables), you can run install/install.bat <br>
> 如何安装Visual C++ 生成工具
>> 访问[微软官方Visual Studio下载页面](https://visualstudio.microsoft.com/zh-hans/downloads/)<br>
选择"Visual Studio 2017 生成工具"那列的下载<br>
运行下载的exe引导文件、开始安装Visual Studio Installer<br>
Visual Studio Installer安装完毕后，在工作负载标签下选择 'Visual C++生成工具'（点击后右侧默认会有'测试工具核心功能 - 生成工具'+一个对应操作系统的最新版本SDK包）并安装<br>

> 如何安装swig
>> 访问[swig官网下载页面](http://www.swig.org/download.html)<br>
选择swigwin-X.X.XX（版本号，如swigwin-3.0.12）下载，不要下载源码swig-X.X.XX（如swig-3.0.12）<br>
解压下载的压缩文件到任意目录，并将该目录添加到系统环境变量中（如 D:\swig-3.0.12）

* 如果未安装Visual C++ 生成工具和swig，请运行install/install.bat <br>
If you haven't installed Visual C++ Build Tools and swig for windows, you can run install/install_whl.bat <br>


# Support website / App
* [Instagram](https://www.instagram.com/)
* [Twitter](https://twitter.com/)
* [Google+](https://plus.google.com/)
* [Tumblr](https://www.tumblr.com/)
* [Flickr](https://www.flickr.com/)
* [Dailymotion](http://www.dailymotion.com/)
* [Youtube](https://www.youtube.com/)
* [半次元](https://bcy.net/)
* [World Cosplay](http://worldcosplay.net/)
* [5sing](http://5sing.kugou.com/index.html)
* [唱吧](http://changba.com/)
* [全名K歌](http://kg.qq.com/)
* [喜马拉雅FM](http://www.ximalaya.com/)
* [美拍](http://www.meipai.com/)
* [秒拍](https://www.miaopai.com/)
* [小咖秀](https://www.xiaokaxiu.com/)
* [Lofter](http://www.lofter.com/)
* [图虫](https://tuchong.com/)
* [微博](https://weibo.com/)
* [一直播](https://www.yizhibo.com/)
* [755](https://7gogo.jp/)
* [Ameblo](https://ameblo.jp/)
* [ニコニコ动画](http://www.nicovideo.jp/)
