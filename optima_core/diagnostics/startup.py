"""启动自检模块"""

import asyncio
import logging
import time
from typing import Any, Callable, Coroutine, Dict, List, Optional, Tuple, Union

from optima_core.config import BuildInfo, get_settings

logger = logging.getLogger(__name__)

# 检查函数类型
CheckFunc = Union[Callable[[], bool], Callable[[], Coroutine[Any, Any, bool]]]


class StartupChecker:
    """启动时自检器"""

    def __init__(
        self,
        service_name: str,
        fail_on_error: bool = False,
        timeout: float = 10.0,
    ):
        """
        Args:
            service_name: 服务名称
            fail_on_error: 检查失败时是否抛出异常
            timeout: 每个检查的超时时间（秒）
        """
        self.service_name = service_name
        self.fail_on_error = fail_on_error
        self.timeout = timeout
        self.checks: List[Tuple[str, CheckFunc, bool]] = []  # (name, func, required)

    def add_check(
        self,
        name: str,
        check_func: CheckFunc,
        required: bool = True,
    ) -> "StartupChecker":
        """添加检查项

        Args:
            name: 检查名称
            check_func: 检查函数
            required: 是否必需（False 则失败时只警告）

        Returns:
            self（支持链式调用）
        """
        self.checks.append((name, check_func, required))
        return self

    async def run_all_checks(self) -> Dict[str, Any]:
        """运行所有检查"""
        build_info = BuildInfo()
        settings = get_settings()

        # 打印启动信息
        self._print_header(build_info, settings)

        results: Dict[str, Any] = {}
        all_required_passed = True

        for name, check_func, required in self.checks:
            result = await self._run_single_check(name, check_func, required)
            results[name] = result

            if result["status"] != "pass" and required:
                all_required_passed = False

        # 打印总结
        self._print_summary(all_required_passed)

        if not all_required_passed and self.fail_on_error:
            raise RuntimeError(
                f"[{self.service_name}] Startup health checks failed. "
                "Set fail_on_error=False to continue anyway."
            )

        return results

    async def _run_single_check(
        self, name: str, check_func: CheckFunc, required: bool
    ) -> Dict[str, Any]:
        """运行单个检查"""
        start = time.time()

        try:
            if asyncio.iscoroutinefunction(check_func):
                result = await asyncio.wait_for(check_func(), timeout=self.timeout)
            else:
                result = check_func()

            latency_ms = round((time.time() - start) * 1000, 1)

            if result:
                self._print_check_result("PASS", name, latency_ms)
                return {"status": "pass", "latency_ms": latency_ms}
            else:
                status = "FAIL" if required else "WARN"
                self._print_check_result(status, name, latency_ms)
                return {"status": "fail", "latency_ms": latency_ms}

        except asyncio.TimeoutError:
            self._print_check_result("TIMEOUT", name, error=f">{self.timeout}s")
            return {"status": "timeout", "error": f"Timed out after {self.timeout}s"}

        except Exception as e:
            status = "FAIL" if required else "WARN"
            self._print_check_result(status, name, error=str(e))
            return {"status": "error", "error": str(e)}

    def _print_header(self, build_info: BuildInfo, settings: Any) -> None:
        """打印启动头信息"""
        print("=" * 50)
        print(f"[{self.service_name}] Starting service...")
        print(f"  Version: {build_info.version}")
        print(f"  Git Commit: {build_info.short_commit}")
        print(f"  Environment: {settings.environment}")
        print("=" * 50)
        print("Running startup health checks...")

    def _print_check_result(
        self,
        status: str,
        name: str,
        latency_ms: Optional[float] = None,
        error: Optional[str] = None,
    ) -> None:
        """打印检查结果"""
        if status == "PASS":
            suffix = f"({latency_ms}ms)" if latency_ms else ""
            print(f"  [PASS] {name} {suffix}")
        elif status == "WARN":
            suffix = f"- {error}" if error else ""
            print(f"  [WARN] {name} {suffix}")
        elif status == "TIMEOUT":
            print(f"  [TIMEOUT] {name} - {error}")
        else:
            suffix = f"- {error}" if error else ""
            print(f"  [FAIL] {name} {suffix}")

    def _print_summary(self, success: bool) -> None:
        """打印总结"""
        print("=" * 50)
        if success:
            print("All checks passed. Service ready.")
        else:
            if self.fail_on_error:
                print("Some checks failed. Service will not start.")
            else:
                print("Some checks failed. Service starting anyway.")
        print("=" * 50)


async def run_startup_checks(
    service_name: str,
    checks: Dict[str, CheckFunc],
    fail_on_error: Optional[bool] = None,
    optional_checks: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """运行启动检查的便捷函数

    Args:
        service_name: 服务名称
        checks: 检查函数字典
        fail_on_error: 失败时是否抛出异常（默认：生产环境 True）
        optional_checks: 可选检查列表（这些检查失败只警告不阻止启动）

    Returns:
        检查结果字典

    Example:
        ```python
        @app.on_event("startup")
        async def startup():
            await run_startup_checks(
                service_name="user-auth",
                checks={
                    "database": check_database,
                    "redis": check_redis,
                },
                optional_checks=["redis"],
            )
        ```
    """
    settings = get_settings()

    if fail_on_error is None:
        fail_on_error = settings.environment == "production"

    checker = StartupChecker(
        service_name=service_name,
        fail_on_error=fail_on_error,
    )

    optional_set = set(optional_checks or [])

    for name, check_func in checks.items():
        required = name not in optional_set
        checker.add_check(name, check_func, required=required)

    return await checker.run_all_checks()
