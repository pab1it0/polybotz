"""Integration tests for src/main.py."""

import pytest
import asyncio
import signal
from unittest.mock import AsyncMock, MagicMock, patch
import httpx

from src.main import (
    handle_shutdown,
    run_poll_cycle,
    main_async,
    main,
)
from src.models import MonitoredEvent, MonitoredMarket
from src.config import Configuration


class TestHandleShutdown:
    """Tests for handle_shutdown function."""

    def test_handle_shutdown_sets_flag(self):
        """Test that shutdown handler sets the global flag."""
        import src.main as main_module

        main_module.shutdown_requested = False

        handle_shutdown(signal.SIGINT, None)

        assert main_module.shutdown_requested is True

    def test_handle_shutdown_sigterm(self):
        """Test handling SIGTERM signal."""
        import src.main as main_module

        main_module.shutdown_requested = False

        handle_shutdown(signal.SIGTERM, None)

        assert main_module.shutdown_requested is True


class TestRunPollCycle:
    """Tests for run_poll_cycle function."""

    @pytest.mark.asyncio
    async def test_poll_cycle_no_spikes(self, valid_config, gamma_api_response):
        """Test poll cycle when no spikes are detected."""
        initial_event = MonitoredEvent(
            slug="test-slug",
            name="Test Event",
            markets=[
                MonitoredMarket(
                    id="cond-001",
                    question="Will outcome A happen?",
                    outcome="Yes",
                    current_price=0.65,
                    previous_price=0.64,  # Small change, no spike
                    is_closed=False,
                )
            ],
        )
        events = {"test-slug": initial_event}

        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = gamma_api_response
        mock_client.get.return_value = mock_response

        result = await run_poll_cycle(mock_client, events, valid_config)

        assert "test-slug" in result

    @pytest.mark.asyncio
    async def test_poll_cycle_with_spikes(self, valid_config, gamma_api_response):
        """Test poll cycle when spikes are detected."""
        initial_event = MonitoredEvent(
            slug="test-slug",
            name="Test Event",
            markets=[
                MonitoredMarket(
                    id="cond-001",
                    question="Will outcome A happen?",
                    outcome="Yes",
                    current_price=0.50,
                    previous_price=0.50,
                    is_closed=False,
                )
            ],
        )
        events = {"test-slug": initial_event}

        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = gamma_api_response
        mock_client.get.return_value = mock_response

        with patch("src.alerter.httpx.AsyncClient") as mock_alert_client:
            alert_mock = AsyncMock()
            alert_response = MagicMock()
            alert_response.status_code = 200
            alert_response.json.return_value = {"ok": True}
            alert_mock.post.return_value = alert_response
            mock_alert_client.return_value.__aenter__.return_value = alert_mock

            result = await run_poll_cycle(mock_client, events, valid_config)

            assert "test-slug" in result

    @pytest.mark.asyncio
    async def test_poll_cycle_logs_info(self, valid_config, gamma_api_response, caplog):
        """Test poll cycle logging."""
        events = {
            "slug1": MonitoredEvent(slug="slug1", name="Event 1", markets=[]),
            "slug2": MonitoredEvent(slug="slug2", name="Event 2", markets=[]),
        }

        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = gamma_api_response
        mock_client.get.return_value = mock_response

        with caplog.at_level("INFO"):
            await run_poll_cycle(mock_client, events, valid_config)

        assert "Starting poll cycle for 2 events" in caplog.text
        assert "Poll cycle completed" in caplog.text


class TestMainAsync:
    """Tests for main_async function."""

    @pytest.mark.asyncio
    async def test_main_config_not_found(self, tmp_path, monkeypatch):
        """Test main exits with error when config not found."""
        monkeypatch.chdir(tmp_path)

        exit_code = await main_async()

        assert exit_code == 1

    @pytest.mark.asyncio
    async def test_main_invalid_config(self, tmp_path, monkeypatch):
        """Test main exits with error for invalid config."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
slugs: []
poll_interval: 5
spike_threshold: 200
telegram:
  bot_token: ""
  chat_id: ""
""")
        monkeypatch.chdir(tmp_path)

        exit_code = await main_async()

        assert exit_code == 1

    @pytest.mark.asyncio
    async def test_main_no_valid_slugs(self, tmp_path, monkeypatch):
        """Test main exits when no valid slugs found."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
slugs:
  - "nonexistent-slug"
poll_interval: 10
spike_threshold: 5.0
telegram:
  bot_token: "token"
  chat_id: "chatid"
""")
        monkeypatch.chdir(tmp_path)

        with patch("src.poller.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 404
            mock_client.get.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            exit_code = await main_async()

            assert exit_code == 1

    @pytest.mark.asyncio
    async def test_main_successful_startup_then_shutdown(self, tmp_path, monkeypatch, gamma_api_response):
        """Test main starts successfully and shuts down gracefully."""
        import src.main as main_module

        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
slugs:
  - "test-slug"
poll_interval: 10
spike_threshold: 5.0
telegram:
  bot_token: "token"
  chat_id: "chatid"
""")
        monkeypatch.chdir(tmp_path)

        # Reset shutdown flag
        main_module.shutdown_requested = False

        with patch("src.poller.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = gamma_api_response
            mock_client.get.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            # Set shutdown flag after a short delay
            async def trigger_shutdown():
                await asyncio.sleep(0.1)
                main_module.shutdown_requested = True

            # Run both concurrently
            results = await asyncio.gather(
                main_async(),
                trigger_shutdown(),
                return_exceptions=True,
            )

            exit_code = results[0]
            assert exit_code == 0

    @pytest.mark.asyncio
    async def test_main_logs_startup(self, tmp_path, monkeypatch, gamma_api_response, caplog):
        """Test main logs startup messages."""
        import src.main as main_module

        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
slugs:
  - "test-slug"
poll_interval: 10
spike_threshold: 5.0
telegram:
  bot_token: "token"
  chat_id: "chatid"
""")
        monkeypatch.chdir(tmp_path)
        main_module.shutdown_requested = False

        with patch("src.poller.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = gamma_api_response
            mock_client.get.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            async def trigger_shutdown():
                await asyncio.sleep(0.1)
                main_module.shutdown_requested = True

            with caplog.at_level("INFO"):
                await asyncio.gather(
                    main_async(),
                    trigger_shutdown(),
                )

            assert "Polybotz starting" in caplog.text
            assert "Loaded configuration" in caplog.text


class TestMain:
    """Tests for main function."""

    def test_main_calls_asyncio_run(self):
        """Test that main calls asyncio.run."""
        with patch("src.main.asyncio.run") as mock_run:
            mock_run.return_value = 0

            with patch("sys.exit") as mock_exit:
                main()

                mock_run.assert_called_once()
                mock_exit.assert_called_once_with(0)

    def test_main_exits_with_correct_code(self):
        """Test that main exits with the return code from main_async."""
        with patch("src.main.asyncio.run") as mock_run:
            mock_run.return_value = 1

            with patch("sys.exit") as mock_exit:
                main()

                mock_exit.assert_called_once_with(1)


class TestSignalHandling:
    """Tests for signal handler registration."""

    @pytest.mark.asyncio
    async def test_signal_handlers_registered(self, tmp_path, monkeypatch):
        """Test that signal handlers are registered on startup."""
        import src.main as main_module

        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
slugs:
  - "test-slug"
poll_interval: 10
spike_threshold: 5.0
telegram:
  bot_token: "token"
  chat_id: "chatid"
""")
        monkeypatch.chdir(tmp_path)
        main_module.shutdown_requested = False

        with patch("signal.signal") as mock_signal:
            with patch("src.poller.httpx.AsyncClient") as mock_client_class:
                mock_client = AsyncMock()
                mock_response = MagicMock()
                mock_response.status_code = 404
                mock_client.get.return_value = mock_response
                mock_client_class.return_value.__aenter__.return_value = mock_client

                await main_async()

                # Check that signal handlers were registered
                calls = mock_signal.call_args_list
                signal_nums = [call[0][0] for call in calls]
                assert signal.SIGINT in signal_nums
                assert signal.SIGTERM in signal_nums


class TestPollCycleErrorHandling:
    """Tests for error handling in poll cycle."""

    @pytest.mark.asyncio
    async def test_poll_cycle_handles_exception(self, tmp_path, monkeypatch, gamma_api_response, caplog):
        """Test that poll loop continues after exception in cycle."""
        import src.main as main_module

        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
slugs:
  - "test-slug"
poll_interval: 10
spike_threshold: 5.0
telegram:
  bot_token: "token"
  chat_id: "chatid"
""")
        monkeypatch.chdir(tmp_path)
        main_module.shutdown_requested = False

        call_count = 0

        async def mock_poll_all(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("Test error")
            return {}

        with patch("src.poller.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = gamma_api_response
            mock_client.get.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            async def trigger_shutdown():
                await asyncio.sleep(0.2)
                main_module.shutdown_requested = True

            with caplog.at_level("INFO"):
                await asyncio.gather(
                    main_async(),
                    trigger_shutdown(),
                )

            # Should have continued running despite error
            assert "shutdown complete" in caplog.text.lower()
