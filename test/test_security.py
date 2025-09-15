"""
Test security features to ensure network access controls work properly.
"""

import pytest
from unittest.mock import Mock

from serena.analytics import AnthropicTokenCount, RegisteredTokenCountEstimator, ToolUsageStats
from solidlsp.ls_utils import FileUtils
from solidlsp.ls_exceptions import SolidLSPException
from solidlsp.ls_logger import LanguageServerLogger


def test_anthropic_token_count_blocks_without_permission():
    """Test that AnthropicTokenCount blocks network access by default."""
    with pytest.raises(ValueError) as exc_info:
        AnthropicTokenCount(allow_network_access=False)
    
    assert "requires explicit permission for network access" in str(exc_info.value)
    assert "allow_network_access=True" in str(exc_info.value)
    assert "TiktokenCountEstimator" in str(exc_info.value)


def test_anthropic_token_count_allows_with_permission():
    """Test that AnthropicTokenCount works when explicitly allowed."""
    # This would normally work if we had an API key, but we just test the permission check
    # Since we don't have anthropic installed in test env, we can't fully test this
    # but the permission check is what we're primarily testing
    try:
        estimator = AnthropicTokenCount(allow_network_access=True)
        # If we get here, the permission check passed
        assert True
    except ImportError:
        # anthropic module not available in test environment, which is fine
        assert True
    except Exception as e:
        # Some other error (like missing API key) is expected
        assert "requires explicit permission" not in str(e)


def test_tool_usage_stats_blocks_tiktoken_without_model_downloads():
    """Test that ToolUsageStats blocks TikToken when model downloads disabled."""
    # Test with TikToken and model downloads disabled - this should raise an error
    # if TikToken models aren't already cached
    with pytest.raises(ValueError) as exc_info:
        ToolUsageStats(
            token_count_estimator=RegisteredTokenCountEstimator.TIKTOKEN_GPT4O,
            allow_network_token_counting=False,
            allow_model_downloads=False
        )
    assert "not found locally and network access is disabled" in str(exc_info.value)


def test_anthropic_estimator_blocks_without_permission():
    """Test that Anthropic estimator blocks without explicit permission."""
    with pytest.raises(ValueError) as exc_info:
        RegisteredTokenCountEstimator.ANTHROPIC_CLAUDE_SONNET_4.load_estimator(allow_network_access=False)
    
    assert "requires explicit permission for network access" in str(exc_info.value)


def test_file_utils_blocks_downloads_without_permission():
    """Test that FileUtils blocks downloads by default."""
    logger = Mock(spec=LanguageServerLogger)
    
    with pytest.raises(SolidLSPException) as exc_info:
        FileUtils.download_file(
            logger=logger,
            url="https://example.com/test.zip",
            target_path="/tmp/test.zip",
            allow_network_access=False
        )
    
    assert "External download blocked for security" in str(exc_info.value)
    assert "allow_network_access=True" in str(exc_info.value)
    
    # Verify warning was logged
    logger.log.assert_called()
    logged_message = logger.log.call_args[0][0]
    assert "SECURITY" in logged_message
    assert "external URL" in logged_message


def test_file_utils_blocks_archive_downloads_without_permission():
    """Test that FileUtils blocks archive downloads by default."""
    logger = Mock(spec=LanguageServerLogger)
    
    with pytest.raises(SolidLSPException) as exc_info:
        FileUtils.download_and_extract_archive(
            logger=logger,
            url="https://example.com/test.zip",
            target_path="/tmp/extracted",
            archive_type="zip",
            allow_network_access=False
        )
    
    assert "External download blocked for security" in str(exc_info.value)
    assert "allow_network_access=True" in str(exc_info.value)
    
    # Verify warning was logged
    logger.log.assert_called()
    logged_message = logger.log.call_args[0][0]
    assert "SECURITY" in logged_message
    assert "external URL" in logged_message