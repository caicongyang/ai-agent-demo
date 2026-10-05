"""Python 装饰器（Decorator）演示

装饰器本质就一句话：
    @deco
    def f(): ...
等价于
    f = deco(f)

所以装饰器只是"接收函数、返回新函数"的高阶函数，底层依赖闭包
（被捕获的 func / 配置参数），可配合 closure_demo.py 一起看。

直接运行：
    python decorator_demo.py
"""

import asyncio
import functools
import inspect
import time


class DecoratorDemo:
    """把装饰器的各种形态、顺序规则和实用场景收在一个类里。

    每个 demo_* 方法独立可运行，run_all() 会按顺序全部跑一遍。
    """

    # ==================================================================
    # 1. 最简装饰器 + 为什么需要 functools.wraps
    # ==================================================================
    @staticmethod
    def shout_bad(func):
        """没有 wraps：元信息（__name__ / __doc__ / 签名）全丢了。"""

        def wrapper(*args, **kwargs):
            return str(func(*args, **kwargs)).upper()

        return wrapper

    @staticmethod
    def shout(func):
        """加上 wraps：把原函数的元信息复制到 wrapper 上。"""

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return str(func(*args, **kwargs)).upper()

        return wrapper

    def demo_basic(self) -> None:
        print("\n[1] 最简装饰器 & functools.wraps")

        def greet(name: str) -> str:
            """打个招呼。"""
            return f"hello {name}"

        bad = DecoratorDemo.shout_bad(greet)
        good = DecoratorDemo.shout(greet)

        print("  调用结果:", good("kiro"))
        print(f"  无 wraps -> __name__={bad.__name__!r}, __doc__={bad.__doc__!r}")
        print(f"  有 wraps -> __name__={good.__name__!r}, __doc__={good.__doc__!r}")
        print("  有 wraps 的签名:", inspect.signature(good))
        print("  原函数可通过 __wrapped__ 取回:", good.__wrapped__ is greet)

    # ==================================================================
    # 2. 带参数的装饰器：多一层函数
    # ==================================================================
    @staticmethod
    def repeat(times: int):
        """@repeat(3) -> repeat(3) 返回真正的装饰器，共三层。"""

        def decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                return [func(*args, **kwargs) for _ in range(times)]

            return wrapper

        return decorator

    def demo_with_args(self) -> None:
        print("\n[2] 带参数的装饰器（三层结构）")

        @DecoratorDemo.repeat(times=3)
        def roll() -> str:
            return "dice"

        print("  @repeat(3) 的结果:", roll())
        print("  层次：repeat(配置) -> decorator(函数) -> wrapper(实参)")

    # ==================================================================
    # 3. 同时支持 @deco 和 @deco(...) 的通用写法
    # ==================================================================
    @staticmethod
    def logged(func=None, *, prefix: str = "LOG"):
        """裸用 @logged 或带参 @logged(prefix='API') 都可以。

        技巧：第一个位置参数为 None 时，说明是带参调用，返回偏函数即可。
        """
        if func is None:
            return functools.partial(DecoratorDemo.logged, prefix=prefix)

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            print(f"    [{prefix}] -> {func.__name__}{args}")
            result = func(*args, **kwargs)
            print(f"    [{prefix}] <- {result}")
            return result

        return wrapper

    def demo_optional_args(self) -> None:
        print("\n[3] 兼容两种用法：@deco 与 @deco(...)")

        @DecoratorDemo.logged
        def add(a: int, b: int) -> int:
            return a + b

        @DecoratorDemo.logged(prefix="API")
        def mul(a: int, b: int) -> int:
            return a * b

        add(1, 2)
        mul(3, 4)

    # ==================================================================
    # 4. 多个装饰器叠加：顺序怎么算
    # ==================================================================
    def demo_stacking(self) -> None:
        print("\n[4] 装饰器叠加顺序")

        def tag(name: str):
            def decorator(func):
                @functools.wraps(func)
                def wrapper(*args, **kwargs):
                    print(f"    进入 {name}")
                    result = func(*args, **kwargs)
                    print(f"    离开 {name}")
                    return result

                return wrapper

            return decorator

        @tag("outer")   # 最后装饰 -> 最先执行
        @tag("inner")   # 最先装饰 -> 最靠近原函数
        def work() -> str:
            print("    执行原函数")
            return "done"

        work()
        print("  规则：自下而上装饰（inner 先包），自上而下执行（outer 先跑）")
        print("  等价于 work = tag('outer')(tag('inner')(work))")

    # ==================================================================
    # 5. 类实现的装饰器：用 __call__
    # ==================================================================
    class CountCalls:
        """装饰器也可以是类：实例化时拿到 func，__call__ 时执行。

        好处是状态放在实例属性上，可读可改，比闭包更好观察。
        """

        def __init__(self, func) -> None:
            functools.update_wrapper(self, func)  # 等价于 wraps 的类版本
            self.func = func
            self.calls = 0

        def __call__(self, *args, **kwargs):
            self.calls += 1
            return self.func(*args, **kwargs)

        def reset(self) -> None:
            self.calls = 0

    def demo_class_based(self) -> None:
        print("\n[5] 用类实现装饰器（__call__）")

        @DecoratorDemo.CountCalls
        def ping() -> str:
            return "pong"

        for _ in range(3):
            ping()
        print(f"  {ping.__name__} 被调用 {ping.calls} 次（状态挂在实例上）")
        ping.reset()
        print("  reset 后:", ping.calls)

    # ==================================================================
    # 6. 装饰类而不是函数
    # ==================================================================
    @staticmethod
    def singleton(cls):
        """装饰器的参数也可以是类：这里把类改造成单例。"""
        instances: dict = {}

        @functools.wraps(cls)
        def get_instance(*args, **kwargs):
            if cls not in instances:
                instances[cls] = cls(*args, **kwargs)
            return instances[cls]

        return get_instance

    @staticmethod
    def add_repr(cls):
        """另一种玩法：往类上注入方法后原样返回类。"""

        def __repr__(self) -> str:  # noqa: N807
            fields = ", ".join(f"{k}={v!r}" for k, v in vars(self).items())
            return f"{cls.__name__}({fields})"

        cls.__repr__ = __repr__
        return cls

    def demo_decorating_class(self) -> None:
        print("\n[6] 装饰类：单例 & 注入方法")

        @DecoratorDemo.singleton
        class Config:
            def __init__(self, env: str = "dev") -> None:
                self.env = env

        a = Config("prod")
        b = Config("test")  # 参数被忽略，拿到的是同一个实例
        print(f"  a is b -> {a is b}，env={a.env}")

        @DecoratorDemo.add_repr
        class Point:
            def __init__(self, x: int, y: int) -> None:
                self.x, self.y = x, y

        print("  注入 __repr__ 后:", Point(1, 2))

    # ==================================================================
    # 7. 实用装饰器：计时 / 重试 / 缓存
    # ==================================================================
    @staticmethod
    def timeit(func):
        """统计耗时，典型的横切关注点（cross-cutting concern）。"""

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start = time.perf_counter()
            try:
                return func(*args, **kwargs)
            finally:
                cost = (time.perf_counter() - start) * 1000
                print(f"    {func.__name__} 耗时 {cost:.2f} ms")

        return wrapper

    @staticmethod
    def retry(times: int = 3, exceptions: tuple = (Exception,), delay: float = 0.0):
        """失败重试，注意只捕获指定异常，不要无脑 except Exception。"""

        def decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                for attempt in range(1, times + 1):
                    try:
                        return func(*args, **kwargs)
                    except exceptions as exc:
                        print(f"    第 {attempt}/{times} 次失败: {exc}")
                        if attempt == times:
                            raise
                        if delay:
                            time.sleep(delay)

            return wrapper

        return decorator

    def demo_practical(self) -> None:
        print("\n[7] 实用装饰器：计时 / 重试 / 缓存")

        @functools.lru_cache(maxsize=None)
        def _fib(n: int) -> int:
            return n if n < 2 else _fib(n - 1) + _fib(n - 2)

        @DecoratorDemo.timeit
        def fib(n: int) -> int:
            return _fib(n)

        print("  fib(30) =", fib(30))
        print("  lru_cache 统计:", _fib.cache_info())
        print("  坑：把 timeit 直接套在递归函数上，每层递归都会打印一次")

        state = {"n": 0}

        @DecoratorDemo.retry(times=3, exceptions=(ConnectionError,))
        def fetch() -> str:
            state["n"] += 1
            if state["n"] < 3:
                raise ConnectionError("网络抖动")
            return "payload"

        print("  retry 结果:", fetch())

    # ==================================================================
    # 8. 参数校验：借 inspect 拿到形参名
    # ==================================================================
    @staticmethod
    def validate_types(func):
        """按类型注解做运行时校验，演示如何读取被装饰函数的签名。"""
        sig = inspect.signature(func)
        hints = {
            name: param.annotation
            for name, param in sig.parameters.items()
            if param.annotation is not inspect.Parameter.empty
        }

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            bound = sig.bind(*args, **kwargs)
            bound.apply_defaults()
            for name, value in bound.arguments.items():
                expected = hints.get(name)
                if isinstance(expected, type) and not isinstance(value, expected):
                    raise TypeError(
                        f"{func.__name__}() 参数 {name} 需要 {expected.__name__}，"
                        f"实际是 {type(value).__name__}"
                    )
            return func(*args, **kwargs)

        return wrapper

    def demo_validation(self) -> None:
        print("\n[8] 用签名信息做参数校验")

        @DecoratorDemo.validate_types
        def divide(a: int, b: int = 1) -> float:
            return a / b

        print("  divide(10, 2) =", divide(10, 2))
        try:
            divide(10, "2")
        except TypeError as exc:
            print("  捕获到:", exc)

    # ==================================================================
    # 9. 注册表模式：装饰器当"登记入口"
    # ==================================================================
    def demo_registry(self) -> None:
        print("\n[9] 注册表模式（框架里最常见的用法）")
        registry: dict[str, callable] = {}

        def tool(name: str):
            """像 FastAPI 的 @app.get / LangChain 的 @tool 那样登记函数。"""

            def decorator(func):
                registry[name] = func
                return func  # 原样返回，不改变调用行为

            return decorator

        @tool("search")
        def search(q: str) -> str:
            return f"searching {q}"

        @tool("calc")
        def calc(expr: str) -> str:
            return f"calc {expr}"

        print("  已注册:", list(registry))
        print("  按名字调度:", registry["search"]("python decorator"))

    # ==================================================================
    # 10. 异步函数的装饰器
    # ==================================================================
    @staticmethod
    def async_timeit(func):
        """协程要用 async wrapper + await，不能直接套同步装饰器。"""

        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            start = time.perf_counter()
            try:
                return await func(*args, **kwargs)
            finally:
                cost = (time.perf_counter() - start) * 1000
                print(f"    async {func.__name__} 耗时 {cost:.2f} ms")

        return wrapper

    def demo_async(self) -> None:
        print("\n[10] 装饰异步函数")

        @DecoratorDemo.async_timeit
        async def fetch_all() -> list[str]:
            async def one(i: int) -> str:
                await asyncio.sleep(0.05)
                return f"r{i}"

            return await asyncio.gather(*(one(i) for i in range(3)))

        print("  结果:", asyncio.run(fetch_all()))
        print("  注意：同步装饰器套在协程上只会拿到未 await 的 coroutine 对象")

    # ==================================================================
    def run_all(self) -> None:
        print("=" * 64)
        print("Python 装饰器演示")
        print("=" * 64)
        for name in (
            "demo_basic",
            "demo_with_args",
            "demo_optional_args",
            "demo_stacking",
            "demo_class_based",
            "demo_decorating_class",
            "demo_practical",
            "demo_validation",
            "demo_registry",
            "demo_async",
        ):
            getattr(self, name)()
        print("\n" + "=" * 64)
        print("小结：@deco 就是 f = deco(f)；一律加 functools.wraps 保留元信息；")
        print("带参装饰器多一层；叠加时自下而上包、自上而下跑；协程要用 async wrapper。")
        print("=" * 64)


if __name__ == "__main__":
    DecoratorDemo().run_all()
