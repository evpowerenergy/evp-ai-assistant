"""
Date Extraction Utility
Extracts date ranges from natural language queries
"""
from datetime import date, datetime, timedelta
from typing import Optional, Tuple
import re

logger = None  # Will be initialized when needed


def extract_date_range(query: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Extract date range from natural language query
    
    Examples:
    - "เมื่อวาน" → (yesterday, yesterday)
    - "สัปดาห์นี้" → (start_of_week, today)
    - "เดือนนี้" → (start_of_month, today)
    - "วันที่ 15 มกราคม" → (2026-01-15, 2026-01-15)
    - "ระหว่าง 1-5 มกราคม" → (2026-01-01, 2026-01-05)
    
    Returns:
        (date_from, date_to) in YYYY-MM-DD format, or (None, None) if no date found
    """
    query_lower = query.lower()
    today = date.today()
    
    # Single date patterns
    if "เมื่อวาน" in query_lower or "yesterday" in query_lower:
        yesterday = today - timedelta(days=1)
        return (str(yesterday), str(yesterday))
    
    if "วันนี้" in query_lower or "today" in query_lower:
        return (str(today), str(today))
    
    if "พรุ่งนี้" in query_lower or "tomorrow" in query_lower:
        tomorrow = today + timedelta(days=1)
        return (str(tomorrow), str(tomorrow))
    
    # Week patterns
    if "สัปดาห์นี้" in query_lower or "this week" in query_lower or "week" in query_lower:
        # Start of week (Monday)
        days_since_monday = today.weekday()
        start_of_week = today - timedelta(days=days_since_monday)
        return (str(start_of_week), str(today))
    
    if "สัปดาห์ที่แล้ว" in query_lower or "last week" in query_lower:
        days_since_monday = today.weekday()
        start_of_last_week = today - timedelta(days=days_since_monday + 7)
        end_of_last_week = today - timedelta(days=days_since_monday + 1)
        return (str(start_of_last_week), str(end_of_last_week))
    
    # Month patterns
    if "เดือนนี้" in query_lower or "this month" in query_lower:
        start_of_month = date(today.year, today.month, 1)
        return (str(start_of_month), str(today))
    
    if "เดือนที่แล้ว" in query_lower or "last month" in query_lower:
        if today.month == 1:
            start_of_last_month = date(today.year - 1, 12, 1)
            end_of_last_month = date(today.year - 1, 12, 31)
        else:
            start_of_last_month = date(today.year, today.month - 1, 1)
            # Get last day of previous month
            if today.month == 1:
                end_of_last_month = date(today.year - 1, 12, 31)
            else:
                # Get last day of previous month
                first_day_of_current_month = date(today.year, today.month, 1)
                end_of_last_month = first_day_of_current_month - timedelta(days=1)
        return (str(start_of_last_month), str(end_of_last_month))
    
    # Year patterns
    if "ปีนี้" in query_lower or "this year" in query_lower:
        start_of_year = date(today.year, 1, 1)
        return (str(start_of_year), str(today))
    
    # Date range patterns (e.g., "ระหว่าง 1-5 มกราคม")
    # Thai month names
    thai_months = {
        'มกราคม': 1, 'กุมภาพันธ์': 2, 'มีนาคม': 3, 'เมษายน': 4,
        'พฤษภาคม': 5, 'มิถุนายน': 6, 'กรกฎาคม': 7, 'สิงหาคม': 8,
        'กันยายน': 9, 'ตุลาคม': 10, 'พฤศจิกายน': 11, 'ธันวาคม': 12
    }
    
    # Pattern: "ระหว่าง 1-5 มกราคม" or "1-5 มกราคม"
    range_pattern = r'(\d{1,2})\s*[-–]\s*(\d{1,2})\s*(มกราคม|กุมภาพันธ์|มีนาคม|เมษายน|พฤษภาคม|มิถุนายน|กรกฎาคม|สิงหาคม|กันยายน|ตุลาคม|พฤศจิกายน|ธันวาคม)'
    match = re.search(range_pattern, query_lower)
    if match:
        day_from = int(match.group(1))
        day_to = int(match.group(2))
        month_name = match.group(3)
        month = thai_months.get(month_name)
        if month:
            year = today.year
            # Assume current year, or next year if month has passed
            if month < today.month or (month == today.month and day_from < today.day):
                year = today.year
            date_from = date(year, month, day_from)
            date_to = date(year, month, day_to)
            return (str(date_from), str(date_to))
    
    # Pattern: "วันที่ 15 มกราคม" or "15 มกราคม"
    single_date_pattern = r'(\d{1,2})\s*(มกราคม|กุมภาพันธ์|มีนาคม|เมษายน|พฤษภาคม|มิถุนายน|กรกฎาคม|สิงหาคม|กันยายน|ตุลาคม|พฤศจิกายน|ธันวาคม)'
    match = re.search(single_date_pattern, query_lower)
    if match:
        day = int(match.group(1))
        month_name = match.group(2)
        month = thai_months.get(month_name)
        if month:
            year = today.year
            # Assume current year, or next year if month has passed
            if month < today.month or (month == today.month and day < today.day):
                year = today.year
            single_date = date(year, month, day)
            return (str(single_date), str(single_date))
    
    # YYYY-MM-DD pattern
    date_pattern = r'(\d{4})[-/](\d{1,2})[-/](\d{1,2})'
    matches = list(re.finditer(date_pattern, query))
    if len(matches) == 1:
        # Single date
        match = matches[0]
        year = int(match.group(1))
        month = int(match.group(2))
        day = int(match.group(3))
        try:
            single_date = date(year, month, day)
            return (str(single_date), str(single_date))
        except ValueError:
            pass
    elif len(matches) == 2:
        # Date range
        match1 = matches[0]
        match2 = matches[1]
        try:
            date1 = date(int(match1.group(1)), int(match1.group(2)), int(match1.group(3)))
            date2 = date(int(match2.group(1)), int(match2.group(2)), int(match2.group(3)))
            # Return in order (from, to)
            if date1 <= date2:
                return (str(date1), str(date2))
            else:
                return (str(date2), str(date1))
        except ValueError:
            pass
    
    # No date found
    return (None, None)


def extract_date_from_llm_params(tool_parameters: dict) -> Tuple[Optional[str], Optional[str]]:
    """
    Extract date_from and date_to from LLM tool parameters
    
    Parameters may contain:
    - date: single date (YYYY-MM-DD)
    - date_from: start date
    - date_to: end date
    - query: natural language query (will be parsed)
    """
    date_from = tool_parameters.get("date_from")
    date_to = tool_parameters.get("date_to")
    date_single = tool_parameters.get("date")
    query = tool_parameters.get("query", "")
    
    # If date_from and date_to are already provided, use them
    if date_from and date_to:
        return (date_from, date_to)
    
    # If single date is provided, use it for both
    if date_single:
        return (date_single, date_single)
    
    # Try to extract from query
    if query:
        return extract_date_range(query)
    
    return (None, None)
