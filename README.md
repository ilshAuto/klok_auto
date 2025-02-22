# ILSH KLOK 交互脚本

## 注意事项

⚠️ 重要安全提示：

1. 代理配置需使用可靠的服务商
2. 钱包信息请妥善保管
3. 建议在隔离环境运行脚本

## 社区支持

💬 空投信息、脚本频道：[Telegram频道](https://t.me/ilsh_auto)
🐦 最新更新：[X官方账号](https://x.com/hashlmBrian)
🚀 AI交互自动化工具

## 功能特点
- 账号注册、邀请
- 自动聊天

## 效果展示

![img.png](/imgs%2Fimg.png)



![img_1.png](/imgs%2Fimg_1.png)



## 安装说明

！！先启动钱包服务（js部分）、再启动Python
* 出现问题请先使用deepseek、chatgpt询问

### js部分
WALLET_SERVER: https://github.com/ilshAuto/wallet_server/releases/tag/wallet_server
用于生成钱包签名，使用webstorm或者命令行启动

### python部分

用于klok交互

#### 生成邀请码账户
*  reg文件下，账户填入main文件，文件格式：助记词----socks5代理

1. 安装依赖包：
   pip install -r requirements.txt
2. 进入reg文件夹，填写main。
    * main，运行klok_main_reg后会生成邀请码。运行klok_auto时会使用这些邀请码。


#### 聊天运行
1. 将所有账号添加到acc文件 格式同main一致。
2. 填写完毕后执行：python klok_auto.py


## 支持开发

☕ 如果您觉得这个工具有帮助，可以通过发送 USDT 来支持开发:

- 网络: TRC20
- 地址: `TAiGnbo2isJYvPmNuJ4t5kAyvZPvAmBLch`

click start plz.