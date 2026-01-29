"""
Redis 分布式锁实现
防止并发兑换时出现一码多用
"""
import time
from contextlib import contextmanager
from app import redis_client


class RedisLock:
    """Redis 分布式锁"""
    
    def __init__(self, key, timeout=10, retry_interval=0.1, retry_times=30):
        self.key = f"lock:{key}"
        self.timeout = timeout
        self.retry_interval = retry_interval
        self.retry_times = retry_times
        self.locked = False
    
    def acquire(self):
        """获取锁"""
        if redis_client is None:
            # Redis 不可用时直接返回成功（降级处理）
            self.locked = True
            return True
        
        for _ in range(self.retry_times):
            # 使用 SET NX EX 原子操作
            if redis_client.set(self.key, "1", nx=True, ex=self.timeout):
                self.locked = True
                return True
            time.sleep(self.retry_interval)
        
        return False
    
    def release(self):
        """释放锁"""
        if redis_client is None:
            self.locked = False
            return
        
        if self.locked:
            redis_client.delete(self.key)
            self.locked = False
    
    def __enter__(self):
        if not self.acquire():
            raise Exception("获取锁失败，请稍后重试")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()
        return False


@contextmanager
def redeem_lock(code):
    """兑换码锁的便捷上下文管理器"""
    lock = RedisLock(f"redeem:{code}")
    try:
        if not lock.acquire():
            raise Exception("系统繁忙，请稍后重试")
        yield lock
    finally:
        lock.release()
