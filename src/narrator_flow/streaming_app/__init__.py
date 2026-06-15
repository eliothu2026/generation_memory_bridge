"""流式运行时骨架（Layer 1）。

把"无界 ASR 输入 → 背压缓冲 → 单会话 worker → 并发三流水线 → 会话存储"
这条主干跑通。CrewAI 的 Crew（Layer 2）原样复用，只是不再用 CrewAI Flow
来编排，而是用一个 async 事件循环统一输入/并发/服务三个模型。

模块划分：
- session_store : 会话状态存储（当前为内存占位，接口可换 Redis/PG）
- coalescing_queue : 有界队列 + 合并策略（背压核心）
- analyzer : 单段分析（ingest + asyncio.gather 三条流水线）
- worker : 单会话消费循环
- producer : 模拟 ASR 流式输入
- run_stream : CLI 入口，把以上接成一条主干
"""
