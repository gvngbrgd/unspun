from unittest.mock import patch

from conftest import load_main_module

main = load_main_module()


def test_extract_article_returns_clean_text():
    mock_response = {
        "data": {
            "main_content": (
                "Short line.\n"
                "This is a valid paragraph that is definitely longer than sixty characters but has no links at all, so it should be kept.\n"
                "This paragraph contains a single http://example.com link but is also longer than sixty characters so should be kept as well.\n"
                "This paragraph has two links http://a.com and http://b.com and is long enough to be removed because http count is not <2."
            )
        }
    }

    with patch.object(main.fc_app, "extract", return_value=mock_response):
        result = main.extract_article("http://example.com")

    expected = (
        "This is a valid paragraph that is definitely longer than sixty characters but has no links at all, so it should be kept.\n\n"
        "This paragraph contains a single http://example.com link but is also longer than sixty characters so should be kept as well."
    )
    assert result == expected


def test_extract_article_returns_none_when_missing_content():
    with patch.object(main.fc_app, "extract", return_value={"data": {}}):
        result = main.extract_article("http://example.com")
    assert result is None
