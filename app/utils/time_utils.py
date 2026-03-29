
def ms_to_srt_time(ms: int) -> str:
    """
    将毫秒转换为 SRT 时间格式: HH:MM:SS,mmm
    """
    hours = ms // 3600000
    minutes = (ms % 3600000) // 60000
    seconds = (ms % 60000) // 1000
    milliseconds = ms % 1000  # 直接取余数，得到 0-999 的毫秒数

    # 格式化为 HH:MM:SS,mmm (注意毫秒是3位)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"