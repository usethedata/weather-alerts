"""
Weather Alerts Test Suite
=========================

This package contains tests for the weather-alerts application.

Test Modules:
- test_evaluator.py: Tests for condition evaluation logic
- test_email.py: Tests for email sending and template substitution
- test_forecast.py: Tests for weather API integration and data normalization

Running Tests:
    # Run all tests
    python -m pytest tests/

    # Run with verbose output
    python -m pytest tests/ -v

    # Run a specific test file
    python -m pytest tests/test_evaluator.py

    # Run a specific test class
    python -m pytest tests/test_evaluator.py::TestThresholdCondition

    # Run a specific test
    python -m pytest tests/test_evaluator.py::TestThresholdCondition::test_threshold_triggered_first_day

    # Show print statements in output
    python -m pytest tests/ -v -s

    # Stop on first failure
    python -m pytest tests/ -x

    # Run tests matching a pattern
    python -m pytest tests/ -k "threshold"
"""
