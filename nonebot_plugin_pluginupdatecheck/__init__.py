import asyncio

import numpy as np
import toml
from nonebot import get_driver, on_command
from nonebot.matcher import Matcher
from nonebot.adapters.onebot.v11 import Bot, MessageEvent, Message
from nonebot.params import CommandArg, ArgPlainText
from nonebot.permission import SUPERUSER

from .config import Config
from .tool import send_forward_msg

global_config = get_driver().config
config = Config.parse_obj(global_config)

check_upgrade = on_command("ck_up", aliases={'检测插件更新', '检查插件更新'})
update_plg = on_command("up_plg", aliases={'更新插件'})
origin_look = on_command("lk_org", aliases={'查看源'})
install_plg = on_command("ins_plg", aliases={'安装插件'})
add_env = on_command("add_env", aliases={'添加env'})


async def get_sum(plugin,sem):
    async with sem:
        plugin[0]=plugin[0].replace("_","-")

        p = await asyncio.subprocess.create_subprocess_shell(f"pip show {plugin[0]}",
                                                             stdout=asyncio.subprocess.PIPE,
                                                             stderr=asyncio.subprocess.PIPE)
        stdout, stderr = await p.communicate()
        stdout = stdout.decode('gb2312')

        summary_line = next(line for line in stdout.split('\n') if line.startswith('Summary:'))
        summary = summary_line.split(':')[-1].strip()


        return [plugin[0],f"{plugin[0]}\n版本更新：{plugin[1]}->{plugin[2]}\n介绍:{summary}"]

@check_upgrade.handle()
async def check_upgrade(
        bot: Bot,
        event: MessageEvent,
        matcher: Matcher
):
    if not await SUPERUSER(bot, event):
        return
    p = await asyncio.subprocess.create_subprocess_shell("pip list -o -i https://pypi.org/simple",
                                                         stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    stdout, stderr = await p.communicate()
    stdout = stdout.decode('gb2312')
    stderr = stderr.decode('gb2312')
    # 第一行是名称,第二行是分割线
    stdout = stdout.split("\r\n")
    up_list = [i.split() for i in stdout[2:-1]]  # 库信息的排布:'numpy  旧版本 新版本 xx' 按空格分割拿到包名就好
    toml_file = toml.load("pyproject.toml").get("tool").get("nonebot").get("plugins")
    task_list=[]
    sem = asyncio.Semaphore(5)
    for i in up_list:
        i[0]=i[0].replace("-","_")
        if i[0] in toml_file:
            task = asyncio.create_task(get_sum(i, sem))
            task_list.append(task)
    update_list = await asyncio.gather(*task_list)
    update_list = [x for x in update_list if x != '']
    update_list = list(np.ravel(update_list))


    await send_forward_msg(bot, event, "更新小助手", str(bot.self_id), update_list)


# async def compare_plugin(plugin,sem):
#     async with sem:
#         p = await asyncio.subprocess.create_subprocess_shell(f"pip show {plugin}",
#                                                              stdout=asyncio.subprocess.PIPE,
#                                                              stderr=asyncio.subprocess.PIPE)
#         stdout, stderr = await p.communicate()
#         stdout = stdout.decode('gb2312')
#
#         # 解析输出并获取版本和摘要信息
#         version_line = next(line for line in stdout.split('\n') if line.startswith('Version:'))
#         version = version_line.split(':')[-1].strip()
#
#         summary_line = next(line for line in stdout.split('\n') if line.startswith('Summary:'))
#         summary = summary_line.split(':')[-1].strip()
#
#         # 获取pypi.org/pypi/{plugin}/json上的信息
#         data = await main(plugin)
#         far_version = data["info"]["version"]
#         print(far_version)
#
#         if version != far_version:
#             return [plugin, f"{plugin}\n版本更新：{version}->{far_version}\n介绍:{summary}"]
#         else:
#             return ""
#
#
# @check_upgrade.handle()
# async def check_upgrade(
#         bot: Bot,
#         event: MessageEvent,
#         matcher: Matcher
# ):
#     if not await SUPERUSER(bot, event):
#         return
#     # 读取toml中的nonebot2插件
#     toml_file = toml.load("pyproject.toml").get("tool").get("nonebot").get("plugins")
#     task_list = []
#     sem = asyncio.Semaphore(5)
#     # 并发执行pip show获取插件本地信息
#     for plugin in toml_file:
#         task = asyncio.create_task(compare_plugin(plugin, sem))
#         task_list.append(task)
#     update_list = await asyncio.gather(*task_list)
#     update_list = [x for x in update_list if x != '']
#     update_list = list(np.ravel(update_list))
#     await send_forward_msg(bot, event, "更新小助手", str(bot.self_id), update_list)


@origin_look.handle()
async def help():
    await origin_look.finish("0:清华源（默认） https://pypi.tuna.tsinghua.edu.cn/simple/\n"
                             "1:官方源 https://pypi.org/simple\n"
                             "2:豆瓣源 https://pypi.douban.com/simple/\n"
                             "3:中国科学技术大学源 https://pypi.mirrors.ustc.edu.cn/simple/\n"
                             "4:阿里源 https://mirrors.aliyun.com/pypi/simple/\n"
                             "5:腾讯源 https://mirrors.cloud.tencent.com/pypi/simple")


@update_plg.handle()
async def handle_function(
        bot: Bot,
        event: MessageEvent,
        matcher: Matcher,
        args: Message = CommandArg()):
    if not await SUPERUSER(bot, event):
        return
    if args.extract_plain_text():
        matcher.set_arg("up_plugin", args)


@update_plg.got("up_plugin", prompt="请输入插件名，空格后输入编号可换源，使用“查看源”命令查看，默认使用清华源")
async def update(
        bot: Bot,
        event: MessageEvent,
        matcher: Matcher,
        up_plugin: str = ArgPlainText()
):
    if not await SUPERUSER(bot, event):
        return
    up_plugin = up_plugin.split(" ")
    # 当模式为0时默认使用清华源
    if len(up_plugin) == 2:
        update_plugin = up_plugin[0]
        mode = int(up_plugin[1])
    else:
        update_plugin = up_plugin[0]
        mode = 0
    origin_list = ["https://pypi.tuna.tsinghua.edu.cn/simple/",
                   "https://pypi.org/simple",
                   "https://pypi.douban.com/simple/",
                   "https://pypi.mirrors.ustc.edu.cn/simple/",
                   "https://mirrors.aliyun.com/pypi/simple/",
                   "https://mirrors.cloud.tencent.com/pypi/simple"]
    origin = origin_list[mode]
    await update_plg.send(f'开始安装库:{update_plugin}')
    p = await asyncio.subprocess.create_subprocess_shell(f"pip install {update_plugin} -i {origin} --upgrade",
                                                         stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    stdout, stderr = await p.communicate()
    try:
        stdout = stdout.decode('gb2312')
        stderr = stderr.decode('gb2312')
        if "Successfully installed" in stdout:
            tips_info = stdout.split(" ")[-1].replace("\r\n", "")
            await update_plg.finish(f"安装成功:{tips_info}")
            return
        if "Requirement already satisfied" in stdout:
            if "Read timed out." in stderr:
                result = stdout.split("\r\n") + stderr.split("\r\n")
                await update_plg.send("更新超时")
                await send_forward_msg(bot, event, "更新小助手", str(bot.self_id), result)
                return
            result = stdout.split("\r\n") + stderr.split("\r\n")
            await update_plg.send("插件未更新，可能是当前库还未从官方同步该插件")
            await send_forward_msg(bot, event, "更新小助手", str(bot.self_id), result)
            return
        if "Ignoring invalid distribution" in stderr:
            result = stdout.split("\r\n") + stderr.split("\r\n")
            await update_plg.send("请输入正确的插件名")
            await send_forward_msg(bot, event, "更新小助手", str(bot.self_id), result)
            return
    except Exception:
        result = str(stdout or stderr)


@install_plg.handle()
async def handle_function(
        bot: Bot,
        event: MessageEvent,
        matcher: Matcher,
        args: Message = CommandArg()):
    if not await SUPERUSER(bot, event):
        return
    if args.extract_plain_text():
        matcher.set_arg("ins_plugin", args)


@install_plg.got("ins_plugin", prompt="请输入插件名，空格后输入编号可换源，使用“查看源”命令查看，默认使用清华源")
async def update(
        bot: Bot,
        event: MessageEvent,
        matcher: Matcher,
        ins_plugin: str = ArgPlainText()
):
    if not await SUPERUSER(bot, event):
        return
    ins_plugin = ins_plugin.split(" ")
    # 当模式为0时默认使用清华源
    if len(ins_plugin) == 2:
        update_plugin = ins_plugin[0]
        mode = int(ins_plugin[1])
    else:
        update_plugin = ins_plugin[0]
        mode = 0
    origin_list = ["https://pypi.tuna.tsinghua.edu.cn/simple/",
                   "https://pypi.org/simple",
                   "https://pypi.douban.com/simple/",
                   "https://pypi.mirrors.ustc.edu.cn/simple/",
                   "https://mirrors.aliyun.com/pypi/simple/",
                   "https://mirrors.cloud.tencent.com/pypi/simple"]
    origin = origin_list[mode]
    await install_plg.send(f'开始安装库:{update_plugin}')
    p = await asyncio.subprocess.create_subprocess_shell(f"nb plugin install {update_plugin} -i {origin}",
                                                         stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    stdout, stderr = await p.communicate()
    try:
        stdout = stdout.decode('gb2312')
        stderr = stderr.decode('gb2312')
        if "Successfully installed" in stdout:
            tips_info = stdout.split(" ")[-1].replace("\r\n", "")
            await install_plg.finish(f"安装成功:{tips_info}")
            return
        if "Requirement already satisfied" in stdout:
            if "Read timed out." in stderr:
                result = stdout.split("\r\n") + stderr.split("\r\n")
                await install_plg.send("更新超时")
                await send_forward_msg(bot, event, "更新小助手", str(bot.self_id), result)
                return
            result = stdout.split("\r\n") + stderr.split("\r\n")
            await install_plg.send("插件已存在")
            await send_forward_msg(bot, event, "更新小助手", str(bot.self_id), result)
            return
        if "Ignoring invalid distribution" in stderr:
            result = stdout.split("\r\n") + stderr.split("\r\n")
            await install_plg.send("请输入正确的插件名")
            await send_forward_msg(bot, event, "更新小助手", str(bot.self_id), result)
            return
    except Exception:
        result = str(stdout or stderr)


@add_env.handle()
async def handle_function(
        bot: Bot,
        event: MessageEvent,
        matcher: Matcher,
        args: Message = CommandArg()):
    if not await SUPERUSER(bot, event):
        return
    if args.extract_plain_text():
        matcher.set_arg("env", args)


@add_env.got("env", prompt="请输入你要添加的env变量")
async def update(
        bot: Bot,
        event: MessageEvent,
        matcher: Matcher,
        env: str = ArgPlainText()):
    if not await SUPERUSER(bot, event):
        return
    with open('.env', 'a') as file:
        file.write(f"\n{env}\n")
        await add_env.finish(f"添加成功")
