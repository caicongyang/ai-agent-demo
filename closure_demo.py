"""Python 闭包（Closure）演示

闭包 = 嵌套函数 + 引用外层作用域变量 + 外层函数返回内层函数。
内层函数会把被引用的外层局部变量"打包"带走（存在 cell 对象里），
即使外层函数已经执行结束，这些变量依然存活。

直接运行：
    python closure_demo.py
"""

import functools
import time


class ClosureDemo:
    """把常见的闭包用法与坑点收在一个类里，便于逐个演示。

    每个 demo_* 方法独立可运行，run_all() 会按顺序全部跑一遍。
    """

    # ------------------------------------------------------------------
    # 1. 最小闭包：计数器
    # ------------------------------------------------------------------
    @staticmethod
    def make_counter(start: int = 0):
        """返回一个计数器函数，count 被闭包捕获，调用间保持状态。"""
        count = start

        def counter() -> int:
            # nonlocal 声明 count 是外层函数的局部变量，而不是新建局部变量
            nonlocal count
            count += 1
            return count

        return counter

    def demo_counter(self) -> None:
        print("\n[1] 最小闭包：计数器")
        c1 = ClosureDemo.make_counter()
        c2 = ClosureDemo.make_counter(100)
        print("  c1:", [c1() for _ in range(3)])   # [1, 2, 3]
        print("  c2:", [c2() for _ in range(3)])   # [101, 102, 103]
        print("  两个闭包状态互不干扰，各自持有独立的 count")

    # ------------------------------------------------------------------
    # 2. 函数工厂：同一份逻辑，生成不同配置的函数
    # ------------------------------------------------------------------
    @staticmethod
    def make_power(exponent: int):
        """exponent 在定义时被捕获，生成专用的幂函数。"""

        def power(base: float) -> float:
            return base ** exponent

        power.__name__ = f"power_{exponent}"
        return power

    def demo_function_factory(self) -> None:
        print("\n[2] 函数工厂：参数化生成函数")
        square = ClosureDemo.make_power(2)
        cube = ClosureDemo.make_power(3)
        print(f"  {square.__name__}(5) =", square(5))
        print(f"  {cube.__name__}(5) =", cube(5))

    # ------------------------------------------------------------------
    # 3. 闭包的"私有状态"：比类更轻量的状态封装
    # ------------------------------------------------------------------
    @staticmethod
    def make_accumulator():
        """返回 (add, total) 两个函数，共享同一份被捕获的 items 列表。"""
        items: list[float] = []

        def add(value: float) -> float:
            items.append(value)
            return sum(items)

        def total() -> float:
            return sum(items)

        return add, total

    def demo_shared_state(self) -> None:
        print("\n[3] 多个闭包共享同一份状态")
        add, total = ClosureDemo.make_accumulator()
        for v in (10, 20, 5):
            print(f"  add({v}) ->", add(v))
        print("  total() ->", total(), "（add 和 total 捕获的是同一个 items）")

    # ------------------------------------------------------------------
    # 4. 经典坑：循环中的延迟绑定（late binding）
    # ------------------------------------------------------------------
    def demo_late_binding(self) -> None:
        print("\n[4] 经典坑：循环里的延迟绑定")

        # 错误写法：闭包捕获的是变量 i 本身，不是当次循环的值
        wrong = [lambda: i for i in range(3)]
        print("  错误写法:", [f() for f in wrong], "-> 全是 2，因为循环结束后 i == 2")

        # 修复 1：用默认参数在定义时求值
        fixed_default = [lambda i=i: i for i in range(3)]
        print("  默认参数修复:", [f() for f in fixed_default])

        # 修复 2：多包一层函数，让每次循环拿到独立的作用域
        def bind(value):
            return lambda: value

        fixed_factory = [bind(i) for i in range(3)]
        print("  工厂函数修复:", [f() for f in fixed_factory])

    # ------------------------------------------------------------------
    # 5. 闭包最常见的落地形态：装饰器
    # ------------------------------------------------------------------
    @staticmethod
    def retry(times: int = 3, delay: float = 0.0):
        """带参数的装饰器 = 三层闭包：times/delay -> func -> wrapper。"""

        def decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                last_exc = None
                for attempt in range(1, times + 1):
                    try:
                        return func(*args, **kwargs)
                    except Exception as exc:  # 演示用，实际应收窄异常类型
                        last_exc = exc
                        print(f"    第 {attempt} 次调用失败: {exc}")
                        if delay and attempt < times:
                            time.sleep(delay)
                raise last_exc

            return wrapper

        return decorator

    def demo_decorator(self) -> None:
        print("\n[5] 装饰器：闭包最常见的落地形态")
        calls = {"n": 0}

        @ClosureDemo.retry(times=3)
        def flaky() -> str:
            calls["n"] += 1
            if calls["n"] < 3:
                raise ValueError("服务暂时不可用")
            return "成功"

        print("  结果:", flaky(), f"（共调用 {calls['n']} 次）")

    # ------------------------------------------------------------------
    # 6. 用闭包做缓存（手写一个简化版 lru_cache）
    # ------------------------------------------------------------------
    @staticmethod
    def memoize(func):
        """cache 字典被闭包持有，随函数生命周期存活。"""
        cache: dict = {}

        @functools.wraps(func)
        def wrapper(*args):
            if args in cache:
                return cache[args]
            result = func(*args)
            cache[args] = result
            return result

        wrapper.cache = cache  # 暴露出来便于观察
        return wrapper

    def demo_memoize(self) -> None:
        print("\n[6] 闭包做缓存：手写 memoize")

        @ClosureDemo.memoize
        def fib(n: int) -> int:
            return n if n < 2 else fib(n - 1) + fib(n - 2)

        t0 = time.perf_counter()
        value = fib(30)
        cost = (time.perf_counter() - t0) * 1000
        print(f"  fib(30) = {value}，耗时 {cost:.2f} ms，缓存条目 {len(fib.cache)}")

    # ------------------------------------------------------------------
    # 7. 看见闭包：__closure__ 与 cell_contents
    # ------------------------------------------------------------------
    def demo_introspect(self) -> None:
        print("\n[7] 看见闭包：__closure__ / cell_contents")
        counter = ClosureDemo.make_counter(7)
        counter()
        print("  自由变量名:", counter.__code__.co_freevars)
        print("  cell 内容:", [cell.cell_contents for cell in counter.__closure__])

        def plain():
            return 1

        print("  普通函数的 __closure__:", plain.__closure__, "（没有捕获外层变量就是 None）")

    # ------------------------------------------------------------------
    # 8. 闭包 vs 类：同一个需求的两种写法
    # ------------------------------------------------------------------
    def demo_closure_vs_class(self) -> None:
        print("\n[8] 闭包 vs 类：状态封装的两种选择")

        def make_rate_limiter(limit: int):
            used = 0

            def allow() -> bool:
                nonlocal used
                if used >= limit:
                    return False
                used += 1
                return True

            return allow

        class RateLimiter:
            def __init__(self, limit: int) -> None:
                self.limit = limit
                self.used = 0

            def allow(self) -> bool:
                if self.used >= self.limit:
                    return False
                self.used += 1
                return True

        allow_fn = make_rate_limiter(2)
        allow_obj = RateLimiter(2)
        print("  闭包版:", [allow_fn() for _ in range(3)])
        print("  类版本:", [allow_obj.allow() for _ in range(3)])
        print("  行为一致：状态少、只有一个行为时闭包更轻；需要多方法/可检查状态时用类")

    # ------------------------------------------------------------------
    def run_all(self) -> None:
        print("=" * 60)
        print("Python 闭包演示")
        print("=" * 60)
        for name in (
            "demo_counter",
            "demo_function_factory",
            "demo_shared_state",
            "demo_late_binding",
            "demo_decorator",
            "demo_memoize",
            "demo_introspect",
            "demo_closure_vs_class",
        ):
            getattr(self, name)()
        print("\n" + "=" * 60)
        print("小结：闭包 = 函数 + 被捕获的外层变量；修改要用 nonlocal；")
        print("循环中捕获变量注意延迟绑定；装饰器/缓存/函数工厂都是它的典型应用。")
        print("=" * 60)


if __name__ == "__main__":
    ClosureDemo().run_all()
