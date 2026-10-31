"""发送给大模型前的本地脱敏：号码、证件、银行卡替换为占位符，本地再还原。

原则：原始值只存在于本机数据库和最终回复的本地还原中，不进入模型上下文。
"""

from __future__ import annotations

import re

PLACEHOLDER_RE = re.compile(r"\[(PHONE|ID|BANK)_(\d+)\]")

# 身份证：18 位（末位可为 X）
ID_RE = re.compile(r"(?<!\d)\d{17}[\dXx](?!\d)")
# 手机号：11 位，避免误伤更长的数字串
PHONE_RE = re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)")
# 座机：010-12345678 / 0571-1234567
LANDLINE_RE = re.compile(r"(?<!\d)0\d{2,3}-\d{7,8}(?!\d)")
# 银行卡：16–19 位，放在最后，避免抢占身份证/手机号
BANK_RE = re.compile(r"(?<!\d)\d{16,19}(?!\d)")


class Desensitizer:
    """一次会话内保持占位符一致，便于模型引用并在本地还原。"""

    def __init__(self) -> None:
        self._values: dict[str, str] = {}
        self._reverse: dict[str, str] = {}

    def _placeholder(self, kind: str, value: str) -> str:
        if value in self._reverse:
            return self._reverse[value]
        index = 1 + sum(1 for key in self._values if key.startswith(f"[{kind}_"))
        placeholder = f"[{kind}_{index}]"
        self._values[placeholder] = value
        self._reverse[value] = placeholder
        return placeholder

    def mask(self, text: str | None) -> str:
        if not text:
            return ""
        masked = ID_RE.sub(lambda m: self._placeholder("ID", m.group(0)), text)
        masked = LANDLINE_RE.sub(lambda m: self._placeholder("PHONE", m.group(0)), masked)
        masked = PHONE_RE.sub(lambda m: self._placeholder("PHONE", m.group(0)), masked)
        masked = BANK_RE.sub(lambda m: self._placeholder("BANK", m.group(0)), masked)
        return masked

    def unmask(self, text: str | None) -> str:
        if not text:
            return ""

        def restore(match: re.Match[str]) -> str:
            return self._values.get(match.group(0), match.group(0))

        return PLACEHOLDER_RE.sub(restore, text)
