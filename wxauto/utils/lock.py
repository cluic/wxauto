import threading
import multiprocessing
import asyncio
import functools

class LockManager:
    """全局锁管理器"""
    process_lock = multiprocessing.Lock()
    thread_lock = threading.RLock()
    async_lock = asyncio.Lock()

def uilock(func):
    """
    装饰器，确保 UI 自动化方法在多进程、多线程、异步环境下安全执行
    """
    @functools.wraps(func)
    def lock_wrapper(*args, **kwargs):
            with LockManager.thread_lock:
                return func(*args, **kwargs)
    return lock_wrapper