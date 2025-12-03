"""启动自检测试"""

import pytest

from optima_core.diagnostics import StartupChecker, run_startup_checks


class TestStartupChecker:
    """StartupChecker 测试"""

    @pytest.mark.asyncio
    async def test_all_pass(self, capsys: pytest.CaptureFixture[str]) -> None:
        """测试所有检查通过"""
        checker = StartupChecker("test-service")
        checker.add_check("check1", lambda: True)
        checker.add_check("check2", lambda: True)

        result = await checker.run_all_checks()

        assert result["check1"]["status"] == "pass"
        assert result["check2"]["status"] == "pass"

        # 验证输出
        captured = capsys.readouterr()
        assert "[PASS] check1" in captured.out
        assert "[PASS] check2" in captured.out
        assert "All checks passed" in captured.out

    @pytest.mark.asyncio
    async def test_required_fail_no_error(self, capsys: pytest.CaptureFixture[str]) -> None:
        """测试必需检查失败但不抛异常"""
        checker = StartupChecker("test-service", fail_on_error=False)
        checker.add_check("failing", lambda: False, required=True)

        result = await checker.run_all_checks()

        assert result["failing"]["status"] == "fail"

        captured = capsys.readouterr()
        assert "[FAIL] failing" in captured.out
        assert "starting anyway" in captured.out

    @pytest.mark.asyncio
    async def test_required_fail_raises(self) -> None:
        """测试必需检查失败抛异常"""
        checker = StartupChecker("test-service", fail_on_error=True)
        checker.add_check("failing", lambda: False, required=True)

        with pytest.raises(RuntimeError, match="health checks failed"):
            await checker.run_all_checks()

    @pytest.mark.asyncio
    async def test_optional_fail_warns(self, capsys: pytest.CaptureFixture[str]) -> None:
        """测试可选检查失败只警告"""
        checker = StartupChecker("test-service", fail_on_error=True)
        checker.add_check("optional", lambda: False, required=False)

        result = await checker.run_all_checks()

        assert result["optional"]["status"] == "fail"

        captured = capsys.readouterr()
        assert "[WARN] optional" in captured.out
        assert "All checks passed" in captured.out  # 可选失败不影响总体

    @pytest.mark.asyncio
    async def test_async_check(self, capsys: pytest.CaptureFixture[str]) -> None:
        """测试异步检查"""
        checker = StartupChecker("test-service")

        async def async_check() -> bool:
            return True

        checker.add_check("async", async_check)

        result = await checker.run_all_checks()

        assert result["async"]["status"] == "pass"

    @pytest.mark.asyncio
    async def test_check_exception(self, capsys: pytest.CaptureFixture[str]) -> None:
        """测试检查抛出异常"""
        checker = StartupChecker("test-service", fail_on_error=False)

        def failing() -> bool:
            raise ValueError("Test error")

        checker.add_check("failing", failing, required=True)

        result = await checker.run_all_checks()

        assert result["failing"]["status"] == "error"
        assert "Test error" in result["failing"]["error"]

    @pytest.mark.asyncio
    async def test_chain_add_check(self) -> None:
        """测试链式调用 add_check"""
        checker = StartupChecker("test-service")

        result = checker.add_check("a", lambda: True).add_check("b", lambda: True)

        assert result is checker
        assert len(checker.checks) == 2


class TestRunStartupChecks:
    """run_startup_checks 便捷函数测试"""

    @pytest.mark.asyncio
    async def test_basic_usage(self, capsys: pytest.CaptureFixture[str]) -> None:
        """测试基本用法"""
        result = await run_startup_checks(
            service_name="test-service",
            checks={
                "check1": lambda: True,
                "check2": lambda: True,
            },
            fail_on_error=False,
        )

        assert result["check1"]["status"] == "pass"
        assert result["check2"]["status"] == "pass"

    @pytest.mark.asyncio
    async def test_optional_checks(self, capsys: pytest.CaptureFixture[str]) -> None:
        """测试可选检查"""
        result = await run_startup_checks(
            service_name="test-service",
            checks={
                "required": lambda: True,
                "optional": lambda: False,
            },
            optional_checks=["optional"],
            fail_on_error=True,
        )

        # 不应抛异常，因为失败的是可选检查
        assert result["required"]["status"] == "pass"
        assert result["optional"]["status"] == "fail"
