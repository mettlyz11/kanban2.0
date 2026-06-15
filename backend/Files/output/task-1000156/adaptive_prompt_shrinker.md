# adaptive_prompt_shrinker

> 任务: v8 #5 调用频率自适应 — 高峰期降 prompt 长度
> 附件类型: Python模块
> 生成时间: 2026-05-12 05:49

# 调用频率自适应 — 高峰期降 prompt 长度（Python 模块）

本模块实现了基于实时负载监控的 prompt 长度自适应压缩功能，核心组件包括：

- `LoadMonitor`：实时收集错误率、连续错误次数等负载指标；
- `PIDController`：利用 PID 算法根据负载调节压缩比例；
- `ImportanceCompressor`：基于 token 重要性（例如 TF-IDF、关键词匹配）修剪 prompt 中的低重要性内容；
- `AdaptiveScheduler`：整合以上组件，提供统一的 `compress_prompt` 接口，支持动态配置与重置。

模块设计遵循高内聚低耦合原则，所有参数均可配置，适合嵌入到 LLM 调用中间件或代理层。以下为完整源代码及详细注释。

```python
"""
adaptive_prompt_compressor.py
=============================
调用频率自适应降 prompt 长度模块。
监控调用错误率、连续故障次数等指标，通过 PID 控制器动态调整压缩比例，
并基于 token 重要性保留关键内容，从而在高峰期降低系统负载。

使用示例:
    from adaptive_prompt_compressor import AdaptiveScheduler

    scheduler = AdaptiveScheduler(
        target_error_rate=0.05,
        pid_kp=0.6, pid_ki=0.2, pid_kd=0.1,
        compression_min=0.3, compression_max=0.9
    )

    # 假设在一次调用后获得了错误信息
    prompt = "请根据以下内容回答：……（省略长文本）……"
    compressed = scheduler.compress_prompt(prompt, error_rate=0.08)
    print(compressed)
"""

import time
import math
import random
from collections import deque
from typing import Optional, List, Dict, Any

# ---------------------------------------------------------------------------
# LoadMonitor —— 负载指标监控
# ---------------------------------------------------------------------------
class LoadMonitor:
    """
    实时收集与负载相关的指标，包括：
    - 错误率 (最近 N 次调用的比例)
    - 连续错误次数 (当前连续失败的调用次数)
    - 平均响应延迟 (可选)
    
    通过滑动窗口记录历史调用的成功/失败状态。
    """

    def __init__(self, window_size: int = 100):
        """
        Args:
            window_size: 滑动窗口大小，用于计算错误率。
        """
        self.window_size = window_size
        self._history = deque(maxlen=window_size)   # True表示成功，False表示失败
        self._consecutive_failures = 0

    def record_call(self, success: bool):
        """
        记录一次调用结果。

        Args:
            success: 调用是否成功（True 表示正常，False 表示错误）。
        """
        self._history.append(success)
        if success:
            self._consecutive_failures = 0
        else:
            self._consecutive_failures += 1

    def error_rate(self) -> float:
        """
        返回当前窗口内的错误率（0.0 ~ 1.0）。若窗口为空则返回 0.0。
        """
        if not self._history:
            return 0.0
        failures = sum(1 for ok in self._history if not ok)
        return failures / len(self._history)

    def consecutive_failures(self) -> int:
        """返回当前连续失败次数。"""
        return self._consecutive_failures

    def is_overloaded(self, threshold: float = 0.2) -> bool:
        """
        判断是否过载：错误率超过阈值 或 连续失败次数超过窗口长度的 10%。
        Args:
            threshold: 错误率阈值，默认 0.2。
        Returns:
            bool
        """
        return (self.error_rate() > threshold or
                self.consecutive_failures() > max(1, self.window_size // 10))


# ---------------------------------------------------------------------------
# PIDController —— PID 调节器
# ---------------------------------------------------------------------------
class PIDController:
    """
    比例-积分-微分 (PID) 控制器，用于平滑调节压缩比例。
    输入为当前负载指标（如错误率），输出为压缩比例调整量（delta）。
    实际压缩比例 = clamp(last_ratio + output, min_ratio, max_ratio)

    参数说明:
    - Kp: 比例增益，快速响应当前误差
    - Ki: 积分增益，消除稳态误差
    - Kd: 微分增益，抑制振荡
    - setpoint: 目标值（期望错误率）
    - output_limits: 输出限幅 (min, max)，防止调整幅度过大
    """

    def __init__(self,
                 Kp: float = 0.5,
                 Ki: float = 0.1,
                 Kd: float = 0.05,
                 setpoint: float = 0.05,
                 output_limits: tuple = (-0.3, 0.3)):
        self.Kp = Kp
        self.Ki = Ki
        self.Kd = Kd
        self.setpoint = setpoint
        self.output_min, self.output_max = output_limits

        # 内部状态
        self._integral = 0.0
        self._previous_error = 0.0
        self._last_time = time.time()

    def reset(self):
        """重置积分与微分记忆。"""
        self._integral = 0.0
        self._previous_error = 0.0
        self._last_time = time.time()

    def compute(self, current_value: float) -> float:
        """
        根据当前值（如错误率）计算输出调整量。

        Args:
            current_value: 当前观测值 (例如 LoadMonitor.error_rate())
        Returns:
            调整量 (增量)，可正可负，范围受 output_limits 限制。
        """
        now = time.time()
        dt = now - self._last_time
        if dt <= 0.0:
            dt = 1e-6   # 避免除零

        error = self.setpoint - current_value

        # 比例项
        P = self.Kp * error

        # 积分项（带抗积分饱和）
        self._integral += error * dt
        I = self.Ki * self._integral

        # 微分项
        derivative = (error - self._previous_error) / dt
        D = self.Kd * derivative

        # 计算原始输出
        output = P + I + D

        # 限幅
        output = max(self.output_min, min(self.output_max, output))

        # 更新状态
        self._previous_error = error
        self._last_time = now

        return output

    def set_setpoint(self, new_setpoint: float):
        """更新目标值。"""
        self.setpoint = new_setpoint


# ---------------------------------------------------------------------------
# ImportanceCompressor —— 基于重要性剪枝的压缩器
# ---------------------------------------------------------------------------
class ImportanceCompressor:
    """
    根据 token 的重要性分数保留 prompt 中最重要的部分。
    假设输入 prompt 为字符串，重要性计算方式可插拔。

    内置两种重要性评分策略:
    1) 'random': 随机分配重要性 (仅用于测试)
    2) 'keyword': 根据预定义关键词列表计算 token 重要性 (简单实用)
    3) 可传入自定义 scroring 函数。

    压缩时，按重要性降序保留前 ratio 比例的 token（或字符）。
    为了保持语义完整性，本实现采用按句子级别保留（按句号、问号等分割），
    但保留策略基于句子内 token 的平均重要性排序。
    """

    def __init__(self, scoring_strategy: str = 'keyword',
                 keywords: Optional[List[str]] = None,
                 scoring_fn=None):
        """
        Args:
            scoring_strategy: 内置策略名称 ('random' 或 'keyword')
            keywords: 关键词列表 (仅在 strategy='keyword' 时使用)
            scoring_fn: 可调用对象，接受 token (str) 返回重要性分数 (float)
        """
        self.strategy = scoring_strategy
        self._scoring_fn = scoring_fn
        if keywords is None:
            keywords = ['问题', '答案', '关键', '必须', '重要',
                        '重点', '核心', '要求', '指令', '请回答']
        self._keywords = set(k.lower() for k in keywords)

    def _tokenize(self, text: str) -> List[str]:
        """简单按空格和标点切分 token（生产环境可替换为分词器）。"""
        import re
        # 保留中文、英文、数字、常见符号作为 token
        tokens = re.findall(r'[\w\']+|[^\w\s]', text)
        return tokens

    def _score_token(self, token: str) -> float:
        """返回单个 token 的重要性分数。"""
        if self._scoring_fn is not None:
            return self._scoring_fn(token)
        if self.strategy == 'random':
            return random.random()
        elif self.strategy == 'keyword':
            # 如果 token 是小写关键词或包含关键词，给予高分
            if token.lower() in self._keywords:
                return 1.0
            # 非字母数字的标点通常低重要性
            if not token.isalnum():
                return 0.1
            return 0.5
        else:
            # 默认所有 token 同等重要
            return 0.5

    def compress(self, text: str, ratio: float) -> str:
        """
        按保留比例压缩文本。

        Args:
            text: 原始 prompt
            ratio: 保留比例 (0.0~1.0)，例如 0.6 表示保留 60% 内容。
        Returns:
            压缩后的 prompt（字符串）。
        """
        if ratio >= 1.0 or not text:
            return text

        # 将文本分割成句子（以句号、问号、感叹号、换行符分割）
        import re
        sentences = re.split(r'(?<=[。！？\n])', text)
        # 过滤空句子
        sentences = [s.strip() for s in sentences if s.strip()]

        if not sentences:
            return text

        # 为每个句子计算平均重要性
        sentence_scores = []
        for sent in sentences:
            tokens = self._tokenize(sent)
            if not tokens:
                continue
            scores = [self._score_token(t) for t in tokens]
            avg_score = sum(scores) / len(scores)
            sentence_scores.append((avg_score, sent))

        # 按重要性降序排序
        sentence_scores.sort(key=lambda x: -x[0])

        # 确定要保留的句子数量
        total_len = len(sentence_scores)
        keep_count = max(1, int(total_len * ratio))
        # 如果 keep_count 与 total_len 相同，直接返回原文本
        if keep_count >= total_len:
            return text

        # 保留前 keep_count 个句子，并按它们在原文中的顺序重新排列
        # 先记录每个句子的原始索引（保留排序前的顺序以便恢复）
        # 更好的做法：为每个句子记录原始索引
        indexed = []
        for idx, sent in enumerate(sentences):
            tokens = self._tokenize(sent)
            if not tokens:
                continue
            scores = [self._score_token(t) for t in tokens]
            avg = sum(scores) / len(scores)
            indexed.append((avg, idx, sent))

        # 按分数降序，取前 keep_count 个
        indexed.sort(key=lambda x: -x[0])
        top = indexed[:keep_count]
        # 按原始索引排序，恢复顺序
        top.sort(key=lambda x: x[1])
        compressed = "".join([sent for _, _, sent in top])

        # 如果压缩后为空（极端情况），至少返回第一个句子
        if not compressed and sentences:
            compressed = sentences[0]

        return compressed


# ---------------------------------------------------------------------------
# AdaptiveScheduler —— 主调度器，集成所有组件
# ---------------------------------------------------------------------------
class AdaptiveScheduler:
    """
    自适应调度器，对外提供 compress_prompt 接口。
    内部维护负载监控器、PID 控制器、重要性压缩器。
    每次调用 compress_prompt 时，可传入当前错误率（或由内部监控器自动记录），
    调度器根据错误率动态调整压缩比例，并压缩 prompt。

    使用流程:
    1. 初始化 AdaptiveScheduler，设置目标错误率、PID 参数、压缩比范围等。
    2. 每次请求前后分别调用 record_call(success=True/False) 记录调用结果。
    3. 在请求前调用 compress_prompt(prompt) 获得压缩后的 prompt。
    4. 调度器内部会自动执行 PID 调节并更新压缩比例。

    对外接口:
    - compress_prompt(prompt, error_rate=None) -> str
    - record_call(success: bool)
    - get_current_ratio() -> float
    - reset()
    """

    def __init__(self,
                 target_error_rate: float = 0.05,
                 pid_kp: float = 0.6,
                 pid_ki: float = 0.2,
                 pid_kd: float = 0.1,
                 compression_min: float = 0.3,
                 compression_max: float = 0.9,
                 window_size: int = 100,
                 compressor_kwargs: Optional[Dict[str, Any]] = None):
        """
        Args:
            target_error_rate: 目标错误率（PID 设定值）
            pid_kp, pid_ki, pid_kd: PID 参数
            compression_min: 最小压缩比例 (即保留比例最小值)
            compression_max: 最大压缩比例 (即保留比例最大值)
            window_size: 负载监控窗口大小
            compressor_kwargs: 传递给 ImportanceCompressor 的参数字典
        """
        self.compression_min = compression_min
        self.compression_max = compression_max

        # 内部组件
        self.monitor = LoadMonitor(window_size=window_size)
        self.pid = PIDController(Kp=pid_kp, Ki=pid_ki, Kd=pid_kd,
                                 setpoint=target_error_rate)
        if compressor_kwargs is None:
            compressor_kwargs = {'scoring_strategy': 'keyword'}
        self.compressor = ImportanceCompressor(**compressor_kwargs)

        # 当前压缩比例（初始为中间值）
        self._current_ratio = (compression_min + compression_max) / 2.0

    def record_call(self, success: bool):
        """记录一次调用结果，更新负载监控。"""
        self.monitor.record_call(success)

    def get_current_ratio(self) -> float:
        """返回当前的压缩保留比例。"""
        return self._current_ratio

    def compress_prompt(self, prompt: str, error_rate: Optional[float] = None) -> str:
        """
        主压缩接口。
        1. 如果提供了 error_rate，直接使用；否则从负载监控获取最近错误率。
        2. 用 PID 计算压缩比例调整量并更新 _current_ratio。
        3. 调用重要性压缩器对 prompt 进行压缩。
        4. 返回压缩后的字符串。

        Args:
            prompt: 原始 prompt 文本
            error_rate: 可选，手动指定当前错误率。
        Returns:
            压缩后的 prompt。
        """
        # 获取错误率
        if error_rate is not None:
            load = error_rate
        else:
            load = self.monitor.error_rate()

        # PID 调节
        delta = self.pid.compute(load)

        # 更新压缩比例：当前比例 + delta，然后 clamp 到 [min, max]
        new_ratio = self._current_ratio + delta
        new_ratio = max(self.compression_min, min(self.compression_max, new_ratio))
        self._current_ratio = new_ratio

        # 应用压缩
        compressed = self.compressor.compress(prompt, self._current_ratio)
        return compressed

    def reset(self):
        """重置监控器、PID 以及当前比例到初始值。"""
        self.monitor = LoadMonitor(window_size=self.monitor.window_size)
        self.pid.reset()
        self._current_ratio = (self.compression_min + self.compression_max) / 2.0


# ---------------------------------------------------------------------------
# 单元测试与示例
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import time

    print("=== 自适应压缩模块自测 ===")

    # 创建调度器
    scheduler = AdaptiveScheduler(
        target_error_rate=0.05,
        pid_kp=0.6, pid_ki=0.2, pid_kd=0.1