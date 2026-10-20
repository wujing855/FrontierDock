# FrontierDock — 前沿工作站

**Build your own research frontier.**

An open-source, self-hosted research intelligence platform.

把期刊目录、论文摘要、阅读清单和资料统计放在同一个本地工作区。你可以请自己的 Agent 帮你配置、维护和修改这个工作站。从研究领域到页面细节，都可以按自己的习惯调整。

![仅含虚构资料的本地演示](docs/images/demo-home.png)

## 先打开看看

需要 Python 3.11 或更新版本，以及常用浏览器。基础功能无需安装 Python 第三方包，也不需要 API 密钥。

让 Agent 进入解压后的项目目录，执行下面两步。

```sh
python3 -m frontierdock init --workspace workspace --demo
python3 -m frontierdock serve --workspace workspace
```

浏览器打开 **http://127.0.0.1:8876**。页面里出现的两本期刊和论文都是虚构示例，不能用作学术引用。关闭服务时，在启动它的终端按 Control+C。

试用后，要配置自己的资料，另建空白工作区。

```sh
python3 -m frontierdock init --workspace my-research
```

工作区包含数据库、期刊配置、个人阅读和维护记录。它不会继承任何开发者的期刊清单、机器路径、登录状态或 API 密钥。

## 让 Agent 帮你配置

可以把这句话直接发给你常用的 Agent。

> 请读取这个项目中的 skills/frontierdock-setup/SKILL.md，陪我配置自己的前沿工作站。先问我想关注的领域和使用习惯，给出可以跳过、以后修改的选项，再帮我验证能正常运行。遇到小问题请先帮我诊断和修复，别让我一开始就去提交反馈。

这个 Skill 随项目提供。能读取本地文件和运行命令的 Agent 可以直接按它操作；它不会自动安装到所有聊天窗口。只提供网页问答的 Agent 无法直接操作你的电脑，需要你执行它给出的步骤。

你可以决定关注哪些学科、期刊和年份，是否让 Agent 搜索，是否配置 DeepSeek，是否使用翻译 API，以及什么时候检查更新。不会强制安装某个云服务，也不会要求把别人的期刊表照搬过来。你可以随时让 Agent 修改这些选择，也可以继续改页面和流程。

## 日常能用什么

| 页面 | 可以做的事 |
|---|---|
| 研究工作台 | 看各刊近期收录，加入待读 |
| 期刊浏览 | 展开期刊资料，进入已收录卷期和当期题录 |
| 论文检索 | 按题名、DOI、作者、期刊和日期筛选 |
| 我的阅读 | 保存未读、待读、已读状态；移除后可以还原 |
| 数据与方法 | 查看领域分布、年份覆盖和逐年关键词 |
| 摘要阅读 | 看原摘要、可选译文、来源链接和提取关键词；切换阅读主题 |

有摘要不等于已经人工精读。没有摘要时，维护队列会要求 Agent 核对出版社或官方论文页，确认 DOI、题名和 Abstract。搜索引擎生成的网页摘要不会替代论文原摘要。卷期不明的连续出版论文会单列，不会为了填齐目录而编造期号。

## 检查更新与补齐字段

```sh
python3 -m frontierdock plan --workspace my-research
python3 -m frontierdock update --workspace my-research
python3 -m frontierdock maintain --workspace my-research
python3 -m frontierdock doctor --workspace my-research
```

`plan` 显示到期刊物。`update` 按每刊间隔检查，并限制每轮处理量。默认 Agent 模式会写入 `requests/agent_tasks.json`，需要 Agent 实际读取并执行。选择结构化检索后，可由 Crossref 按核实过的 ISSN 获取一段最新记录；它不保证补全整年。

`maintain` 会根据原摘要生成待翻译和关键词任务；配置了模型 API 后，可以在每轮调用上限内处理。缺原摘要的记录仍需核对来源。定时器只负责发起运行，不能保证外部网站能访问，也不能替代 Agent 完成它尚未执行的队列。

需要无人值守时，让 Agent 按你的系统、时区、时间和预算设置外部调度。项目不会自行安装开机启动项。电脑休眠或关机时，本地任务无法保证执行。

## 配置密钥

只在选择相应服务后运行。交互式终端输入不会显示密钥。

```sh
python3 -m frontierdock key set deepseek
python3 -m frontierdock key set llm
python3 -m frontierdock key set mineru
```

密钥保存在用户配置目录的 `frontierdock/secrets/`，不在项目和工作区内；也可以使用环境变量。不要把密钥发在聊天、截图或 GitHub 问题中。保存成功只表示本地文件写入成功，联网调用和免费额度需要另行验证。

详见 [配置与字段约定](docs/DATA_CONTRACT.md)、[服务接入状态](docs/INTEGRATIONS.md) 和 [排错方法](docs/TROUBLESHOOTING.zh-CN.md)。

## 交流

用着卡住，先让你的 Agent 跑一遍 `doctor` 和 `plan`，多数问题能当场解决。想聊改造思路、AI 工具和科研用法，欢迎来群里。

**AI Open Space** 是面向本科生、研究生和 AI 爱好者的开放社群，关注大模型与智能体、ChatGPT / Claude / Gemini 这类工具的实际用法、文献阅读与学术写作，也聊跨学科的想法。进群后把昵称改成「专业+昵称」，例如 `生物医学|小明`，方便找到同行。群里不发广告，引用别人的资料时照旧守学术规范。

群二维码有效期到 2026 年 10 月 27 日。过期就扫下面的个人微信，我拉你进群。

<img src="docs/images/community-group.png" width="240" alt="AI Open Space 群二维码">
<img src="docs/images/community-wechat.jpg" width="240" alt="维护者微信">

## 开源与数据

项目采用 MIT 许可证。你自己导入的论文、摘要和 PDF 仍受原有权利约束，不能因为软件开源就一并公开。工作区、凭据、日志和个人阅读均应留在本地。发布前请执行项目提供的检查与打包程序。
