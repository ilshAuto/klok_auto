import asyncio
import base64
import secrets
import sys
import time
import random
import hashlib
import json
from datetime import datetime, timezone
import uuid

import httpx

import cloudscraper
from loguru import logger
import aiohttp  # 添加到文件开头的导入部分
import aiofiles  # 添加到文件开头的导入部分

# 初始化日志记录
logger.remove()
logger.add(sys.stdout, format='<g>{time:YYYY-MM-DD HH:mm:ss:SSS}</g> | <c>{level}</c> | <level>{message}</level>')

def generate_nonce():
    # 生成 64 字节的随机数据
    random_bytes = secrets.token_bytes(48)

    # 转换为十六进制字符串
    nonce = random_bytes.hex()

    return nonce

async def generate_nonce_async():
    return await asyncio.to_thread(generate_nonce)



class ScraperReq:
    def __init__(self, proxy: dict, header: dict):
        self.scraper = cloudscraper.create_scraper(browser={
            'browser': 'chrome',
            'platform': 'windows',
            'mobile': False,
        })
        self.proxy: dict = proxy
        self.header: dict = header

    def post_req(self, url, req_json, req_param):
        # logger.info(self.header)
        # logger.info(req_json)
        return self.scraper.post(url=url, headers=self.header, json=req_json, proxies=self.proxy, params=req_param)

    async def post_async(self, url, req_param=None, req_json=None):
        return await asyncio.to_thread(self.post_req, url, req_json, req_param)

    def get_req(self, url, req_param):
        return self.scraper.get(url=url, headers=self.header, params=req_param, proxies=self.proxy)

    async def get_async(self, url, req_param=None, req_json=None):
        return await asyncio.to_thread(self.get_req, url, req_param)


class Klok:
    def __init__(self, mnemonic: str, proxy: str, JS_SERVER: str, acc: dict, headers: dict, index: int):
        proxy_dict = {
            'http': proxy,
            'https': proxy,
        }
        self.scraper = ScraperReq(proxy_dict, headers)
        self.mnemonic = mnemonic
        self.proxy = proxy
        self.JS_SERVER = f'http://{JS_SERVER}:3666'
        self.index = index
        self.wallet_address = None
        self.ques_list = acc['ques']
        logger.info(f'{self.index}, {self.proxy} 初始化完成, JS_SERVER: {self.JS_SERVER}')

    async def check_proxy(self):
        try:
            res = await self.scraper.get_async('http://ip-api.com/json')
            logger.success(f'{self.index}, {self.proxy} 代理检测成功')
        except Exception as e:
            logger.error(f'{self.index}, {self.proxy} 代理检测失败: {e}')
            return False
        return True

    async def get_wallet_address(self):
        for i in range(3):
            try:
                res = await httpx.AsyncClient(timeout=30).post(f'{self.JS_SERVER}/api/wallet_address',
                                                               json={'mnemonic': self.mnemonic})
                if res.json()['success']:
                    self.wallet_address = res.json()['data']['address']
                    logger.success(f'{self.index}, {self.proxy} {self.wallet_address} 获取钱包成功')
                    return True
                else:
                    logger.error(f'{self.index}, {self.proxy} 获取钱包失败')
                    continue
            except Exception as e:
                logger.error(f'{self.index}, {self.proxy} get_wallet_address error: {e}')
                await asyncio.sleep(3)
                continue
        return False

    async def get_sign_message(self, nonce: str):
        """构造签名消息"""
        # 确保时间戳格式完全匹配
        timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
        address = self.wallet_address

        # 构建纯文本消息，注意地址后面有三个换行符
        message = (
            f"klokapp.ai wants you to sign in with your Ethereum account:\n"
            f"{address}\n\n\n"  # 这里是三个换行符
            f"URI: https://klokapp.ai/\n"
            f"Version: 1\n"
            f"Chain ID: 1\n"
            f"Nonce: {nonce}\n"
            f"Issued At: {timestamp}"
        )

        # logger.info(f'{self.index}, {self.proxy} 构造签名消息: {message}')

        # 发送签名请求
        sign_payload = {
            'mnemonic': self.mnemonic,
            'proxy': self.proxy,
            'payload': message
        }

        try:
            sign_res = await httpx.AsyncClient().post(f'{self.JS_SERVER}/api/sign', json=sign_payload)
            # logger.info(f'{self.index}, {self.proxy} 签名响应内容: {sign_res.text}')

            if sign_res.json()['success']:
                signature = sign_res.json()['signature']
                logger.success(f'{self.index}, {self.proxy} 签名成功')
                return message, signature
            else:
                logger.error(f'{self.index}, {self.proxy} 签名失败: {sign_res.text}')
                return None, None
        except Exception as e:
            logger.error(f'{self.index}, {self.proxy} 签名异常: {e}')
            return None, None

    async def update_session_token(self, token: str):
        """更新请求头中的 session token"""
        self.scraper.header['x-session-token'] = token
        logger.success(f'{self.index}, {self.proxy}登陆成功 更新session token: {token}')

    async def get_me(self):
        """获取用户信息"""
        try:
            me_res = await self.scraper.get_async('https://api1-pp.klokapp.ai/v1/me')
            if me_res.status_code == 200:
                # logger.error(f'{self.index}, {self.proxy} 获取用户信息: {me_res.json()[""]}')
                return
            logger.error(f'{self.index}, {self.proxy} 获取用户信息失败: {me_res.status_code}')
            return None
        except Exception as e:
            logger.error(f'{self.index}, {self.proxy} 获取用户信息异常: {e}')
            return None

    async def get_points(self):
        """获取积分信息"""
        try:
            points_res = await self.scraper.get_async('https://api1-pp.klokapp.ai/v1/points')
            if points_res.status_code == 200:
                logger.success(f'{self.index}, {self.proxy} 积分: {points_res.json()["total_points"]}, 交互数量：{points_res.json()["points"]["inference"]}')
                return
            logger.error(f'{self.index}, {self.proxy} 获取积分信息失败: {points_res.status_code}')
            return None
        except Exception as e:
            logger.error(f'{self.index}, {self.proxy} 获取积分信息异常: {e}')
            return None

    async def get_rate_limit(self):
        """获取速率限制信息"""
        try:
            rate_res = await self.scraper.get_async('https://api1-pp.klokapp.ai/v1/rate-limit')
            if rate_res.status_code == 200:
                rate_json = rate_res.json()
                limit = int(rate_json["limit"])
                remaining = int(rate_json["remaining"])
                logger.success(f'{self.index}, {self.proxy} 总: {limit}，剩余：{remaining}')
                if remaining == 0:
                    return False, 0
                else:
                    return True, remaining
            logger.error(f'{self.index}, {self.proxy} 获取速率限制失败: {rate_res.status_code}')
            return None, 0
        except Exception as e:
            logger.error(f'{self.index}, {self.proxy} 获取速率限制异常: {e}')
            return None, 0

    async def chat(self, messages: list, chat_id: str,model: str = "llama-3.3-70b-instruct"):
        """发送聊天请求"""
        try:
            chat_data = {
                "id": chat_id,
                "title": "",
                "messages": messages,
                "sources": [],
                "model": model,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "language": "english"
            }

            # 设置超时
            timeout = aiohttp.ClientTimeout(total=None)  # 无限超时

            async with aiohttp.ClientSession() as session:
                async with session.post(
                        'https://api1-pp.klokapp.ai/v1/chat',
                        json=chat_data,
                        headers=self.scraper.header,
                        proxy=self.proxy,
                        ssl=False
                ) as response:
                    if response.status != 200:
                        logger.error(f'{self.index}, {self.proxy} 聊天请求失败: {response.status}')
                        return False

                    # 等待10秒
                    await asyncio.sleep(10)
                    return True

        except Exception as e:
            logger.error(f'{self.index}, {self.proxy} 发送聊天请求异常: {e}')
            return False

    async def login(self):
        logger.info(f'{self.index}, {self.proxy} 开始登录流程')

        if not await self.get_wallet_address():
            logger.error(f'{self.index}, {self.proxy} 获取钱包地址失败，登录终止')
            return False

        nonce = await generate_nonce_async()
        logger.info(f'{self.index}, {self.proxy} 生成nonce: {nonce}')

        message, signature = await self.get_sign_message(nonce)
        if not message or not signature:
            logger.error(f'{self.index}, {self.proxy} 获取签名失败，登录终止')
            return False

        # 构造登录请求数据
        login_data = {
            "signedMessage": signature,
            "message": message,
            "referral_code": None
        }

        try:
            # 发送登录请求
            login_res = await self.scraper.post_async(
                'https://api1-pp.klokapp.ai/v1/verify',
                req_json=login_data
            )
            # logger.info(f'{self.index}, {self.proxy} 登录响应内容: {login_res.text}')

            if login_res.status_code == 200:
                res_json = login_res.json()
                if res_json.get('session_token'):
                    token = res_json["session_token"]
                    await self.update_session_token(token)
                    
                    # 获取推荐码
                    await self.get_referral_stats()
                    
                    return True
                else:
                    logger.error(f'{self.index}, {self.proxy} {self.wallet_address} 登录失败: {res_json}')
                    return False
            else:
                logger.error(f'{self.index}, {self.proxy} {self.wallet_address} 登录失败: {login_res.status_code}')
                return False

        except Exception as e:
            logger.error(f'{self.index}, {self.proxy} {self.wallet_address} 登录异常: {e}')
            return False

    async def loop_task(self):
        while True:
            try:
                if not await self.check_proxy():
                    logger.error(f'{self.index}, {self.proxy} 代理不可用，等待重试')
                    await asyncio.sleep(3*3600)
                    continue
                login_flag = await self.login()
                if login_flag:
                    # 获取各种信息
                    me_info = await self.get_me()
                    points_info = await self.get_points()
                    rate_flag, remaining = await self.get_rate_limit()

                    # 根据 rate limit 判断是否可以聊天
                    if rate_flag:
                        chat_id = str(uuid.uuid4())
                        for i in range(remaining):
                            messages = [{"role": "user", "content": random.choice(self.ques_list)}]
                            chat_res = await self.chat(messages, chat_id)
                            if chat_res:
                                logger.info(f'{self.index}, {self.proxy} 第{i+1}次聊天成功')
                            await asyncio.sleep(5)  # 每次聊天之间稍微间隔一下
                            if i % 3 == 0:
                                await self.get_points()
                    await asyncio.sleep(6*3600)
            except Exception as e:
                logger.error(f'{self.index}, {self.proxy} 任务异常: {e}')
                await asyncio.sleep(3*3600)

    async def get_referral_stats(self):
        """获取推荐码信息"""
        try:
            referral_res = await self.scraper.get_async('https://api1-pp.klokapp.ai/v1/referral/stats')
            if referral_res.status_code == 200:
                referral_json = referral_res.json()
                referral_code = referral_json.get("referral_code")
                if referral_code:
                    logger.success(f'{self.index}, {self.proxy} 推荐码: {referral_code}')
                    # 使用 aiofiles 异步写入文件
                    async with aiofiles.open('referral_code.txt', 'a', encoding='utf-8') as f:
                        await f.write(f'{self.wallet_address}----{referral_code}\n')
                    return referral_code
                else:
                    logger.error(f'{self.index}, {self.proxy} 获取推荐码失败: 响应中没有推荐码')
                    return None
            logger.error(f'{self.index}, {self.proxy} 获取推荐码失败: {referral_res.status_code}')
            return None
        except Exception as e:
            logger.error(f'{self.index}, {self.proxy} 获取推荐码异常: {e}')
            return None


async def run(acc: dict, JS_SERVER: str):
    headers = {
        'accept-language': 'zh-CN,zh;q=0.6',
        'origin': 'https://klokapp.ai',
        'priority': 'u=1, i',
        'referer': 'https://klokapp.ai/',
    }

    klok = Klok(acc['mnemonic'], acc['proxy'], JS_SERVER, acc, headers, acc['index'])
    await klok.loop_task()


async def main(JS_SERVER: str):
    # acc_line = """
    # faith almost reward rug pipe swallow candy juice genuine win there knee----socks5://192.168.0.106:17010
    # """
    acc_lines = []
    with open('./main', 'r', encoding='utf-8') as file:
        for line in file.readlines():
            acc_lines.append(line)

    ques_list = []
    accs = []
    with open('../web3_questions.txt', 'r', encoding='utf-8') as file:
        for line in file.readlines():
            ques = line.strip()
            ques_list.append(ques)
    for index, acc_line in enumerate(acc_lines):
        parts = acc_line.strip().split('----')
        mnemonic = parts[0]
        proxy = parts[1]

        acc = {
            'mnemonic': mnemonic,
            'proxy': proxy,
            'ques': ques_list,
            'index': index
        }
        accs.append(acc)

    tasks = [run(acc, JS_SERVER) for acc in accs]
    await asyncio.gather(*tasks)


if __name__ == '__main__':
    logger.info('🚀 [ILSH] klok v1.0 | Airdrop Campaign Live')
    logger.info('🌐 ILSH Community: t.me/ilsh_auto')
    logger.info('🐦 X(Twitter): https://x.com/hashlmBrian')
    logger.info('☕ Pay me Coffe：USDT（TRC20）:TAiGnbo2isJYvPmNuJ4t5kAyvZPvAmBLch')

    JS_SERVER = '127.0.0.1'
    print('----' * 30)
    print('请验证, JS_SERVER（钱包验证服务）的host是否正确')
    print('pay attention to whether the host of the js service is correct')
    print('----' * 30)
    asyncio.run(main(JS_SERVER))