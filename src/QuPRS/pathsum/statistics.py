# src/QuPRS/pathsum/statistics.py

# 用一個字典來追蹤簡化次數
_reduction_counts = {
    'total': 0,
    'Elim': 0,
    'HH': 0,
    'omega': 0,
}
# 控制簡化功能是否啟用
_reduction_enabled = True

def get_reduction_counts():
    """取得所有簡化規則的計數副本。"""
    return _reduction_counts.copy()

def get_reduction_count(key: str):
    """取得特定簡化規則的計數。"""
    return _reduction_counts.get(key, 0)

def increment_reduction_count(key: str, value: int = 1):
    """增加特定簡化規則的計數。"""
    if key in _reduction_counts:
        _reduction_counts[key] += value

def get_reduction_hitrate():
    """計算簡化規則的命中率。"""
    total = _reduction_counts['total']
    if total == 0:
        return 1.0
    else:
        hit = _reduction_counts['Elim'] + _reduction_counts['HH'] + _reduction_counts['omega']
        return hit / total

def reset_reduction_counts():
    """重置所有簡化規則的計數為 0。"""
    for key in _reduction_counts:
        _reduction_counts[key] = 0

def set_reduction_switch(value: bool) -> None:
    """設定簡化功能的總開關。"""
    global _reduction_enabled
    _reduction_enabled = value

def is_reduction_enabled() -> bool:
    """檢查簡化功能是否已啟用。"""
    return _reduction_enabled