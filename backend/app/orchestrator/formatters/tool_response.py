"""
Format tool results as natural language for LLM context.
Includes helpers for sales closed report (category, platform, per-month summary).
"""
from typing import Dict, Any, List, Optional

# Category values for sales closed (match frontend /reports/sales-closed and LeadSummary)
CATEGORY_PACKAGE = "Package"
CATEGORY_WHOLESALES_ALIASES = ("Wholesale", "Wholesales")

# Thai month labels for period_start YYYY-MM-DD
_MONTH_LABELS = {
    "01": "มกราคม", "02": "กุมภาพันธ์", "03": "มีนาคม", "04": "เมษายน", "05": "พฤษภาคม", "06": "มิถุนายน",
    "07": "กรกฎาคม", "08": "สิงหาคม", "09": "กันยายน", "10": "ตุลาคม", "11": "พฤศจิกายน", "12": "ธันวาคม",
}


def _normalize_category_for_sales_closed(category: Any) -> str:
    """Normalize lead category for sales closed report. Wholesale/Wholesales → Wholesales."""
    if not category:
        return "ไม่ระบุ"
    c = (category or "").strip()
    if c == CATEGORY_PACKAGE:
        return CATEGORY_PACKAGE
    if c in CATEGORY_WHOLESALES_ALIASES:
        return "Wholesales"
    return c or "ไม่ระบุ"


def _compute_sales_closed_category_summary(sales_leads: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """
    Compute Package vs Wholesales summary from salesLeads (same logic as /reports/sales-closed).
    Returns e.g. {"Package": {"salesCount": 15, "totalSalesValue": 3321854.85}, "Wholesales": {...}}
    """
    summary: Dict[str, Dict[str, Any]] = {}
    for lead in sales_leads or []:
        cat = _normalize_category_for_sales_closed(lead.get("category"))
        if cat not in summary:
            summary[cat] = {"salesCount": 0, "totalSalesValue": 0.0}
        qt_count = int(lead.get("totalQuotationCount") or 0)
        amount = float(lead.get("totalQuotationAmount") or 0)
        summary[cat]["salesCount"] += qt_count
        summary[cat]["totalSalesValue"] += amount
    return summary


def _compute_sales_closed_platform_summary(sales_leads: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """
    Compute summary per platform from salesLeads.
    Returns e.g. {"Huawei": {"salesCount": 10, "totalSalesValue": 500000}, ...}.
    """
    summary: Dict[str, Dict[str, Any]] = {}
    for lead in sales_leads or []:
        platform = (lead.get("platform") or "").strip() or "ไม่ระบุ"
        if platform not in summary:
            summary[platform] = {"salesCount": 0, "totalSalesValue": 0.0}
        qt_count = int(lead.get("totalQuotationCount") or 0)
        amount = float(lead.get("totalQuotationAmount") or 0)
        summary[platform]["salesCount"] += qt_count
        summary[platform]["totalSalesValue"] += amount
    return summary


def _compute_sales_closed_per_month_summary(sales_leads: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    When salesLeads have period_start/period_end (from multi-month merge), compute category summary
    per period. Returns list of { period_start, period_end, month_label, Package, Wholesales }.
    """
    periods: Dict[str, List[Dict[str, Any]]] = {}
    for lead in sales_leads or []:
        if not isinstance(lead, dict):
            continue
        start = lead.get("period_start")
        if not start:
            continue
        key = str(start)
        if key not in periods:
            periods[key] = []
        periods[key].append(lead)
    result = []
    for start in sorted(periods.keys()):
        rows = periods[start]
        end = rows[0].get("period_end", start[:8] + "31") if rows else start
        summary = _compute_sales_closed_category_summary(rows)
        y, m = start[:4], start[5:7]
        month_label = f"{_MONTH_LABELS.get(m, m)} {y}"
        result.append({
            "period_start": start,
            "period_end": end,
            "month_label": month_label,
            "Package": summary.get("Package", {"salesCount": 0, "totalSalesValue": 0.0}),
            "Wholesales": summary.get("Wholesales", {"salesCount": 0, "totalSalesValue": 0.0}),
        })
    return result


def _map_sales_logs_to_leads(sales_logs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Map RPC salesLogs[] to salesLeads format for category summary."""
    leads: List[Dict[str, Any]] = []
    for log in sales_logs or []:
        if not isinstance(log, dict):
            continue
        lead = log.get("lead") if isinstance(log.get("lead"), dict) else log
        if not isinstance(lead, dict):
            continue
        row = dict(lead)
        if "totalQuotationCount" not in row and "total_quotation_count" in row:
            row["totalQuotationCount"] = row["total_quotation_count"]
        if "totalQuotationAmount" not in row and "total_quotation_amount" in row:
            row["totalQuotationAmount"] = row["total_quotation_amount"]
        if "category" not in row and "lead_category" in row:
            row["category"] = row["lead_category"]
        if row.get("totalQuotationCount") is None:
            row["totalQuotationCount"] = 1
        if row.get("totalQuotationAmount") is None:
            row["totalQuotationAmount"] = 0
        leads.append(row)
    return leads


def format_tool_response(
    tool_results: list, user_message: str, debug_out: Optional[Dict[str, Any]] = None
) -> str:
    """Format tool results as natural language response"""
    responses = []

    for result in tool_results:
        tool_name = result.get("tool", "")
        output = result.get("output", {})
        inp = result.get("input", {})

        if tool_name == "search_leads":
            if output.get("success") and output.get("data"):
                sales_leads = output.get("data", {}).get("salesLeads", [])
                if sales_leads and len(sales_leads) > 0:
                    # Sales closed data (from ai_get_sales_closed)
                    total_sales_value = output.get("data", {}).get("totalSalesValue", 0)
                    sales_count = output.get("data", {}).get("salesCount", 0)

                    sales_list = []
                    for i, lead in enumerate(sales_leads, 1):
                        name = lead.get("displayName") or lead.get("fullName", "N/A")
                        category = lead.get("category", "")
                        platform = lead.get("platform", "")
                        qt_amount = lead.get("totalQuotationAmount", 0)
                        qt_count = lead.get("totalQuotationCount", 0)
                        qt_numbers = lead.get("quotationNumbers", [])

                        sales_info = f"{i}. {name}"
                        if category:
                            sales_info += f" ({category})"
                        if platform:
                            sales_info += f" - Platform: {platform}"
                        if qt_count > 0:
                            sales_info += f" - QT: {qt_count} รายการ"
                            if qt_numbers and len(qt_numbers) > 0:
                                sales_info += f" ({', '.join(qt_numbers[:3])}"
                                if len(qt_numbers) > 3:
                                    sales_info += f" และอีก {len(qt_numbers) - 3} รายการ"
                                sales_info += ")"
                        if qt_amount > 0:
                            sales_info += f" - ยอดรวม: ฿{qt_amount:,.0f}"

                        sales_list.append(sales_info)

                    result_text = "\n".join(sales_list)
                    summary = f"พบยอดขายที่ปิดการขายสำเร็จ {sales_count} รายการ (QT) มูลค่ารวม ฿{total_sales_value:,.0f}"
                    responses.append(f"{summary}\n\nรายละเอียด:\n{result_text}")
                else:
                    # Regular leads data (from ai_get_leads)
                    leads = output.get("data", {}).get("leads", [])
                    stats = output.get("data", {}).get("stats", {})

                    if leads and len(leads) > 0:
                        lead_list = []
                        for i, lead in enumerate(leads, 1):
                            name = lead.get("display_name") or lead.get("full_name", "N/A")
                            tel = lead.get("tel")
                            status = lead.get("status", "N/A")
                            region = lead.get("region", "")

                            lead_info = f"{i}. {name}"
                            if region:
                                lead_info += f" ({region})"
                            if status:
                                lead_info += f" - สถานะ: {status}"
                            if tel:
                                lead_info += f" - โทร: {tel}"

                            lead_list.append(lead_info)

                        total = stats.get("returned", len(leads))
                        result_text = "\n".join(lead_list)

                        summary_parts = [f"พบ {total} leads"]
                        df, dt = inp.get("date_from"), inp.get("date_to")
                        if df and dt:
                            summary_parts.append(f"ช่วงข้อมูลที่ขอ: {df} - {dt}")
                        responses.append(f"{' | '.join(summary_parts)}\n{result_text}")
                    else:
                        responses.append("ไม่พบ lead สำหรับคำค้นหานี้")
            elif output.get("error"):
                responses.append(f"เกิดข้อผิดพลาด: {output.get('error')}")
            else:
                responses.append("ไม่พบข้อมูล lead")

        elif tool_name == "get_sales_closed":
            if output.get("success") and output.get("data"):
                data = output.get("data", {})
                sales_leads = data.get("salesLeads", [])
                if not sales_leads and data.get("salesLogs"):
                    sales_leads = _map_sales_logs_to_leads(data.get("salesLogs"))
                total_sales_value = data.get("totalSalesValue", 0)
                sales_count = data.get("salesCount", 0)
                request_date_from = data.get("request_date_from")
                request_date_to = data.get("request_date_to")

                if sales_leads and len(sales_leads) > 0:
                    user_msg = (user_message or "").lower()

                    wants_category_breakdown = any(
                        kw in user_msg
                        for kw in [
                            "package", "wholesales", "wholesale", "แพ็กเกจ", "โฮลเซล",
                            "แยกตาม", "แยก package", "แยก wholesales", "ปิดได้กี่ลีด", "ปิดได้กี่ qt",
                            "กี่ลีด", "กี่ qt", "ยอดขายกี่บาท", "กี่บาท", "แยกรายการ",
                            "category", "แยกตาม category", "แยก category"
                        ]
                    )

                    category_summary = _compute_sales_closed_category_summary(sales_leads)
                    package_stats = category_summary.get("Package", {"salesCount": 0, "totalSalesValue": 0.0})
                    wholesale_stats = category_summary.get("Wholesales", {"salesCount": 0, "totalSalesValue": 0.0})
                    category_summary_text = (
                        f"สรุปตามหน้า /reports/sales-closed (แยกตาม category): "
                        f"Package: {package_stats['salesCount']} QT, ฿{package_stats['totalSalesValue']:,.2f} บาท; "
                        f"Wholesales: {wholesale_stats['salesCount']} QT, ฿{wholesale_stats['totalSalesValue']:,.2f} บาท; "
                        f"รวม {package_stats['salesCount'] + wholesale_stats['salesCount']} QT, "
                        f"฿{package_stats['totalSalesValue'] + wholesale_stats['totalSalesValue']:,.2f} บาท. "
                        f"(จำนวน QT = sum(totalQuotationCount) ต่อ category ไม่ใช่นับจำนวนแถว)"
                    )
                    if request_date_from and request_date_to:
                        category_summary_text = (
                            f"ช่วงข้อมูลที่ขอ: {request_date_from} ถึง {request_date_to} — ให้ระบุช่วงตามนี้ในคำตอบ (ไม่สรุปจากวันที่ใน raw). "
                            + category_summary_text
                        )

                    per_month_summary_text = ""
                    if sales_leads and isinstance(sales_leads[0], dict) and sales_leads[0].get("period_start"):
                        per_month = _compute_sales_closed_per_month_summary(sales_leads)
                        if per_month:
                            lines_pm = []
                            for pm in per_month:
                                pkg = pm.get("Package", {})
                                whs = pm.get("Wholesales", {})
                                sc_p = pkg.get("salesCount", 0)
                                sc_w = whs.get("salesCount", 0)
                                amt_p = pkg.get("totalSalesValue", 0)
                                amt_w = whs.get("totalSalesValue", 0)
                                lines_pm.append(
                                    f"{pm.get('month_label', pm.get('period_start', ''))} ({pm.get('period_start')} ถึง {pm.get('period_end')}): "
                                    f"Package {sc_p} QT, ฿{amt_p:,.2f}; Wholesales {sc_w} QT, ฿{amt_w:,.2f}; รวม {sc_p + sc_w} QT, ฿{amt_p + amt_w:,.2f}"
                                )
                            per_month_summary_text = (
                                "สรุปแยกตามเดือน (จาก period ที่ดึงแต่ละเดือน):\n"
                                + "\n".join(lines_pm)
                            )

                    wants_platform_breakdown = any(
                        kw in user_msg
                        for kw in [
                            "แพลตฟอร์ม", "platform", "แยกตามแพลตฟอร์ม", "ยอดตามแพลตฟอร์ม", "ยอดขายตามแพลตฟอร์ม",
                            "ตามแพลตฟอร์ม"
                        ]
                    )
                    platform_summary_text = ""
                    platform_summary = _compute_sales_closed_platform_summary(sales_leads)
                    keys_with_platform = [k for k in platform_summary.keys() if k != "ไม่ระบุ"]
                    if not keys_with_platform and platform_summary:
                        platform_summary_text = (
                            "ข้อมูลชุดนี้ไม่มี field platform ในแต่ละรายการ — ไม่สามารถรายงานยอดแยกตามแพลตฟอร์มได้อย่างถูกต้อง. "
                            "ที่ยืนยันได้มีแค่: ยอดรวมทั้งเดือน และแยกตาม category (Package/Wholesales) ด้านบน."
                        )
                    elif platform_summary:
                        lines_plat = []
                        for plat_name in sorted(platform_summary.keys(), key=lambda x: (x == "ไม่ระบุ", x)):
                            st = platform_summary[plat_name]
                            lines_plat.append(f"{plat_name}: {st['salesCount']} QT, ฿{st['totalSalesValue']:,.2f} บาท")
                        platform_summary_text = (
                            "สรุปแยกตามแพลตฟอร์ม: " + "; ".join(lines_plat) + ". "
                            "ให้ใช้ตัวเลขนี้เป็นหลัก — ห้ามคำนวณใหม่จาก raw."
                        )

                    if debug_out is not None:
                        debug_out["get_sales_closed"] = {
                            "category_summary": category_summary_text,
                            "platform_summary": platform_summary_text or "",
                            "per_month_summary": per_month_summary_text or "",
                        }

                    wants_per_customer = any(
                        kw in user_msg
                        for kw in ["แต่ละคน", "รายบุคคล", "แยกตามคน", "ชื่อลูกค้า", "รายชื่อลูกค้า"]
                    )

                    wants_qt_details = any(
                        kw in user_msg
                        for kw in ["แยกรายการ qt", "รายละเอียด qt", "qt ของแต่ละคน", "รายการ qt", "qt แต่ละคน", "qt แต่ละรายการ"]
                    )

                    if wants_per_customer:
                        customer_data: Dict[str, Dict[str, Any]] = {}
                        for lead in sales_leads:
                            name = lead.get("displayName") or lead.get("fullName") or "N/A"
                            lead_id = lead.get("leadId")
                            key = f"{lead_id}:{name}" if lead_id is not None else name
                            amt = float(lead.get("totalQuotationAmount") or 0)
                            qt_count = int(lead.get("totalQuotationCount") or 0)
                            quotation_docs = lead.get("quotationDocuments", [])

                            if key not in customer_data:
                                customer_data[key] = {
                                    "name": name,
                                    "amount": 0.0,
                                    "qt_count": 0,
                                    "quotations": []
                                }

                            customer_data[key]["amount"] += amt
                            customer_data[key]["qt_count"] += qt_count

                            if isinstance(quotation_docs, list):
                                for qt in quotation_docs:
                                    if isinstance(qt, dict):
                                        customer_data[key]["quotations"].append({
                                            "document_number": qt.get("document_number", "N/A"),
                                            "amount": float(qt.get("amount") or 0),
                                            "created_at": qt.get("created_at_thai", "")
                                        })

                        sorted_customers = sorted(customer_data.values(), key=lambda x: x["amount"], reverse=True)

                        lines = []
                        for i, c in enumerate(sorted_customers, 1):
                            customer_line = f"{i}. {c['name']} - ฿{c['amount']:,.0f} ({c['qt_count']} QT)"

                            if wants_qt_details and c["quotations"]:
                                customer_line += "\n   รายการ QT:"
                                for qt in c["quotations"]:
                                    qt_num = qt.get("document_number", "N/A")
                                    qt_amt = qt.get("amount", 0)
                                    customer_line += f"\n   - QT {qt_num}: ฿{qt_amt:,.0f}"

                            lines.append(customer_line)

                        summary = (
                            f"สรุปยอดปิดการขาย (แยกรายบุคคล)\n"
                            f"- QT ที่ปิดทั้งหมด: {sales_count} รายการ\n"
                            f"- มูลค่ารวม: ฿{total_sales_value:,.0f}\n"
                            f"- ตัวเลขยึดตามหน้า /reports/sales-closed\n\n"
                        )

                        if wants_qt_details:
                            summary += "รายชื่อลูกค้าที่ปิดการขาย พร้อมรายละเอียด QT:\n\n"
                        else:
                            summary += "รายชื่อลูกค้าที่ปิดการขาย:\n\n"

                        if wants_category_breakdown or wants_platform_breakdown:
                            extra = category_summary_text
                            if per_month_summary_text:
                                extra += "\n\n" + per_month_summary_text
                            if platform_summary_text:
                                extra += "\n\n" + platform_summary_text
                            responses.append(summary + "\n".join(lines) + "\n\n" + extra)
                        else:
                            responses.append(summary + "\n".join(lines))
                    else:
                        has_breakdown = bool(category_summary_text or platform_summary_text or per_month_summary_text)
                        if has_breakdown:
                            summary_block = category_summary_text
                            if per_month_summary_text:
                                summary_block += "\n\n" + per_month_summary_text
                            if platform_summary_text:
                                summary_block += "\n\n" + platform_summary_text
                            responses.append(
                                f"พบยอดขายที่ปิดการขายสำเร็จ {sales_count} รายการ (QT) มูลค่ารวม ฿{total_sales_value:,.0f} "
                                f"(ตัวเลขยึดตามหน้า /reports/sales-closed).\n\n{summary_block}"
                            )
                        else:
                            responses.append(
                                f"พบยอดขายที่ปิดการขายสำเร็จ {sales_count} รายการ (QT) "
                                f"มูลค่ารวม ฿{total_sales_value:,.0f} (ตัวเลขยึดตามหน้า /reports/sales-closed)"
                            )
                else:
                    responses.append("ไม่พบข้อมูลยอดขายที่ปิดการขายสำเร็จในช่วงเวลาที่ระบุ")
            elif output.get("error"):
                responses.append(f"เกิดข้อผิดพลาด: {output.get('error')}")
            else:
                responses.append("ไม่พบข้อมูลยอดขายที่ปิดการขายสำเร็จ")

        elif tool_name == "get_sales_unsuccessful":
            if output.get("success") and output.get("data"):
                data = output.get("data", {})
                leads = data.get("unsuccessfulLeads", [])
                count = data.get("unsuccessfulCount", 0)
                total_val = data.get("totalQuotationValue", 0)
                df = data.get("request_date_from")
                dt = data.get("request_date_to")

                if count > 0 or leads:
                    summary = f"พบ {count} รายการที่ปิดการขายไม่สำเร็จ"
                    if total_val and float(total_val) > 0:
                        summary += f" มูลค่า QT รวม ฿{float(total_val):,.0f}"
                    if df and dt:
                        summary += f"\nช่วงข้อมูล: {df} ถึง {dt}"
                    summary += "\nตัวเลขตรงกับหน้า /reports/sales-unsuccessful"

                    user_msg = (user_message or "").lower()
                    wants_details = any(kw in user_msg for kw in ["รายชื่อ", "รายละเอียด", "แยกรายการ", "ใครบ้าง", "มีใคร", "แยกรายการ"])

                    if wants_details and leads:
                        lead_lines = []
                        for i, lead in enumerate(leads, 1):
                            name = lead.get("displayName") or lead.get("fullName", "N/A")
                            platform = lead.get("platform", "")
                            category = lead.get("category", "")
                            line = f"{i}. {name}"
                            if platform:
                                line += f" ({platform})"
                            if category:
                                line += f" [{category}]"
                            lead_lines.append(line)
                        responses.append(summary + "\n\nรายละเอียด:\n" + "\n".join(lead_lines))
                    else:
                        responses.append(summary)
                else:
                    responses.append("ไม่พบรายการปิดการขายไม่สำเร็จในช่วงเวลาที่ระบุ")
            elif output.get("error"):
                responses.append(f"เกิดข้อผิดพลาด: {output.get('error')}")
            else:
                responses.append("ไม่พบข้อมูลปิดการขายไม่สำเร็จ")

        elif tool_name == "get_customer_info":
            if output.get("found"):
                responses.append(
                    f"พบข้อมูลลูกค้า: {output.get('customer_name', 'N/A')}\n"
                    f"ประเภทบริการ: {output.get('service_type', 'N/A')}\n"
                    f"สถานะ: {output.get('status', 'N/A')}"
                )
            else:
                responses.append("ไม่พบข้อมูลลูกค้า")

        elif tool_name == "get_team_kpi":
            if not output.get("error"):
                responses.append(
                    f"KPI ทีม:\n"
                    f"- Total Leads: {output.get('total_leads', 0)}\n"
                    f"- Active Leads: {output.get('active_leads', 0)}"
                )
            else:
                responses.append(output.get("message", "ไม่สามารถดึงข้อมูล KPI ได้"))

        elif tool_name == "get_sales_team_list":
            if output.get("success") and output.get("data"):
                sales_team = output.get("data", {}).get("salesTeam", [])

                if sales_team and len(sales_team) > 0:
                    team_list = []
                    for i, member in enumerate(sales_team, 1):
                        name = member.get("name", "N/A")
                        email = member.get("email", "")
                        phone = member.get("phone", "")
                        status = member.get("status", "")
                        position = member.get("position", "")
                        department = member.get("department", "")

                        member_info = f"{i}. {name}"
                        if position:
                            member_info += f" - {position}"
                        if department:
                            member_info += f" ({department})"
                        if status:
                            member_info += f" - สถานะ: {status}"
                        if email:
                            member_info += f" - Email: {email}"
                        if phone:
                            member_info += f" - โทร: {phone}"

                        team_list.append(member_info)

                    total = len(sales_team)
                    result_text = "\n".join(team_list)
                    responses.append(f"พบ {total} รายชื่อเซลล์ (Sales Team):\n{result_text}")
                else:
                    responses.append("ไม่พบรายชื่อเซลล์")
            elif output.get("error"):
                responses.append(f"เกิดข้อผิดพลาด: {output.get('error')}")
            else:
                responses.append("ไม่พบข้อมูลรายชื่อเซลล์")

        elif tool_name == "get_sales_team":
            if output.get("success") and output.get("data"):
                sales_team = output.get("data", {}).get("salesTeam", [])

                if sales_team and len(sales_team) > 0:
                    team_list = []
                    for i, member in enumerate(sales_team, 1):
                        name = member.get("name", "N/A")
                        current_leads = member.get("currentLeads", 0)
                        total_leads = member.get("totalLeads", 0)
                        closed_leads = member.get("closedLeads", 0)
                        conversion_rate = member.get("conversionRate", 0)

                        member_info = f"{i}. {name}"
                        member_info += f" - ลีดปัจจุบัน: {current_leads}"
                        member_info += f" - ลีดทั้งหมด: {total_leads}"
                        member_info += f" - ปิดการขาย: {closed_leads}"
                        if conversion_rate:
                            member_info += f" - อัตราแปลง: {conversion_rate:.2f}%"

                        team_list.append(member_info)

                    total = len(sales_team)
                    result_text = "\n".join(team_list)
                    responses.append(f"พบ {total} รายชื่อทีมขายพร้อม metrics:\n{result_text}")
                else:
                    responses.append("ไม่พบรายชื่อทีมขาย")
            elif output.get("error"):
                responses.append(f"เกิดข้อผิดพลาด: {output.get('error')}")
            else:
                responses.append("ไม่พบข้อมูลทีมขาย")

        elif tool_name == "get_lead_detail":
            if output.get("success") and output.get("data"):
                lead = output.get("data", {}).get("lead", {})
                logs = output.get("data", {}).get("productivity_logs", [])

                if lead:
                    name = lead.get("display_name") or lead.get("full_name", "N/A")
                    tel = lead.get("tel", "")
                    status = lead.get("status", "N/A")
                    category = lead.get("category", "")

                    detail_parts = [f"รายละเอียดลีด: {name}"]
                    if category:
                        detail_parts.append(f"หมวดหมู่: {category}")
                    if status:
                        detail_parts.append(f"สถานะ: {status}")
                    if tel:
                        detail_parts.append(f"โทร: {tel}")

                    if logs and len(logs) > 0:
                        detail_parts.append(f"\nมี {len(logs)} productivity logs")

                    responses.append("\n".join(detail_parts))
                else:
                    responses.append("ไม่พบรายละเอียดลีด")
            elif output.get("error"):
                responses.append(f"เกิดข้อผิดพลาด: {output.get('error')}")
            else:
                responses.append("ไม่พบข้อมูลรายละเอียดลีด")

        elif tool_name == "get_appointments":
            if output.get("success") and output.get("data"):
                follow_up = output.get("data", {}).get("followUp", [])
                engineer = output.get("data", {}).get("engineer", [])
                payment = output.get("data", {}).get("payment", [])

                appointment_parts = []
                if follow_up and len(follow_up) > 0:
                    appointment_parts.append(f"นัดติดตาม: {len(follow_up)} รายการ")
                if engineer and len(engineer) > 0:
                    appointment_parts.append(f"นัดช่าง: {len(engineer)} รายการ")
                if payment and len(payment) > 0:
                    appointment_parts.append(f"นัดชำระเงิน: {len(payment)} รายการ")

                if appointment_parts:
                    responses.append("พบนัดหมาย:\n" + "\n".join(appointment_parts))
                else:
                    responses.append("ไม่พบนัดหมาย")
            elif output.get("error"):
                responses.append(f"เกิดข้อผิดพลาด: {output.get('error')}")
            else:
                responses.append("ไม่พบข้อมูลนัดหมาย")

        elif tool_name in ["get_sales_team_overview", "get_sales_team_data", "get_team_kpi", "get_sales_team", "get_sales_performance"]:
            if output.get("success") and output.get("data"):
                data = output.get("data", {})
                sales_team = data.get("salesTeam", [])

                # Single-member mode payload (from get_sales_performance)
                if (not sales_team) and isinstance(data, dict) and any(k in data for k in ["deals_closed", "pipeline_value", "conversion_rate", "total_leads"]):
                    name = data.get("name", "N/A")
                    total_leads = data.get("total_leads", 0)
                    deals_closed = data.get("deals_closed", 0)
                    pipeline_value = data.get("pipeline_value", 0)
                    conversion_rate = data.get("conversion_rate", 0)
                    try:
                        pipeline_value_num = float(pipeline_value or 0)
                    except (TypeError, ValueError):
                        pipeline_value_num = 0.0
                    try:
                        conversion_rate_num = float(conversion_rate or 0)
                    except (TypeError, ValueError):
                        conversion_rate_num = 0.0
                    responses.append(
                        "สรุปผลงานรายเซล\n"
                        f"- ชื่อ: {name}\n"
                        f"- ลีดทั้งหมด: {int(total_leads or 0)}\n"
                        f"- ปิดการขาย: {int(deals_closed or 0)} ดีล\n"
                        f"- ยอดขาย: {pipeline_value_num:,.2f} บาท\n"
                        f"- Conversion Rate: {conversion_rate_num:.2f}%"
                    )
                    continue

                if sales_team and len(sales_team) > 0:
                    date_from = inp.get("date_from")
                    date_to = inp.get("date_to")
                    team_list = []
                    total_amount = 0.0
                    for i, member in enumerate(sales_team, 1):
                        name = member.get("name", "N/A")
                        # Support both snake_case and camelCase in case RPC payload changes.
                        deals_closed = (
                            member.get("deals_closed")
                            if member.get("deals_closed") is not None
                            else member.get("dealsClosed", 0)
                        )
                        pipeline_value = (
                            member.get("pipeline_value")
                            if member.get("pipeline_value") is not None
                            else member.get("pipelineValue", 0)
                        )
                        conversion_rate = (
                            member.get("conversion_rate")
                            if member.get("conversion_rate") is not None
                            else member.get("conversionRate", 0)
                        )

                        try:
                            pipeline_value_num = float(pipeline_value or 0)
                        except (TypeError, ValueError):
                            pipeline_value_num = 0.0
                        total_amount += pipeline_value_num

                        member_info = f"{i}. {name}"
                        member_info += f" - ปิดการขาย {int(deals_closed or 0)} ดีล"
                        member_info += f" - ยอดขาย {pipeline_value_num:,.2f} บาท"
                        if conversion_rate:
                            try:
                                member_info += f" - Conversion Rate: {float(conversion_rate):.2f}%"
                            except (TypeError, ValueError):
                                pass

                        team_list.append(member_info)

                    total = len(sales_team)
                    result_text = "\n".join(team_list)
                    header = f"สรุปยอดขายรายเซล: {total} คน"
                    if date_from and date_to:
                        header += f" (ช่วง {date_from} ถึง {date_to})"
                    header += f"\nยอดขายรวมทั้งทีม: {total_amount:,.2f} บาท"
                    responses.append(f"{header}\n\n{result_text}")
                else:
                    responses.append("ไม่พบรายชื่อทีมขาย")
            elif output.get("error"):
                responses.append(f"เกิดข้อผิดพลาด: {output.get('error')}")
            else:
                responses.append("ไม่พบข้อมูลทีมขาย")

        elif tool_name == "get_service_appointments":
            if output.get("success") and output.get("data"):
                appointments = output.get("data", {}).get("appointments", [])

                if appointments and len(appointments) > 0:
                    responses.append(f"พบนัดหมายบริการ: {len(appointments)} รายการ")
                else:
                    responses.append("ไม่พบนัดหมายบริการ")
            elif output.get("error"):
                responses.append(f"เกิดข้อผิดพลาด: {output.get('error')}")
            else:
                responses.append("ไม่พบข้อมูลนัดหมายบริการ")

        elif tool_name == "get_sales_performance":
            if output.get("success") and output.get("data"):
                performance = output.get("data", {})

                total_leads = performance.get("total_leads", 0)
                deals_closed = performance.get("deals_closed", 0)
                pipeline_value = performance.get("pipeline_value", 0)
                conversion_rate = performance.get("conversion_rate", 0)

                perf_parts = ["ประสิทธิภาพการขาย:"]
                perf_parts.append(f"- Total Leads: {total_leads}")
                perf_parts.append(f"- Deals Closed: {deals_closed}")
                perf_parts.append(f"- Pipeline Value: {pipeline_value:,.0f}")
                if conversion_rate:
                    perf_parts.append(f"- Conversion Rate: {conversion_rate:.2f}%")

                responses.append("\n".join(perf_parts))
            elif output.get("error"):
                responses.append(f"เกิดข้อผิดพลาด: {output.get('error')}")
            else:
                responses.append("ไม่พบข้อมูลประสิทธิภาพการขาย")

        elif tool_name in ["get_sales_docs", "get_permit_requests"]:
            if output.get("success"):
                data = output.get("data", {})
                if tool_name == "get_sales_docs" and isinstance(data, dict):
                    docs = data.get("sales_docs", []) if isinstance(data.get("sales_docs", []), list) else []
                    if docs:
                        lines = []
                        for i, d in enumerate(docs[:10], 1):
                            doc_no = d.get("doc_number", "N/A")
                            doc_type = d.get("doc_type", "N/A")
                            amount = float(d.get("total_amount") or 0)
                            doc_date = d.get("doc_date", "")
                            customer_name = d.get("customer_name")
                            sale_name = d.get("sale_name")
                            lead_status = d.get("lead_status")
                            line = f"{i}. {doc_no} ({doc_type}) - ฿{amount:,.2f}"
                            if doc_date:
                                line += f" - วันที่ {doc_date}"
                            if customer_name:
                                line += f"\n   ลูกค้า: {customer_name}"
                            if sale_name:
                                line += f"\n   เซลล์ผู้รับผิดชอบ: {sale_name}"
                            if lead_status:
                                line += f"\n   สถานะลูกค้าปัจจุบัน: {lead_status}"
                            lines.append(line)
                        more = f"\nและอีก {len(docs) - 10} รายการ" if len(docs) > 10 else ""
                        responses.append(f"พบเอกสารการขาย {len(docs)} รายการ\n" + "\n".join(lines) + more)
                    else:
                        responses.append("ไม่พบเอกสารการขายที่ตรงเงื่อนไข")
                elif isinstance(data, list) and len(data) > 0:
                    responses.append(f"พบข้อมูล: {len(data)} รายการ")
                elif isinstance(data, dict) and data:
                    responses.append("พบข้อมูล")
                else:
                    responses.append("ไม่พบข้อมูล")
            elif output.get("error"):
                responses.append(f"เกิดข้อผิดพลาด: {output.get('error')}")
            else:
                responses.append("ไม่พบข้อมูล")

    return "\n\n".join(responses) if responses else "ไม่พบข้อมูลที่เกี่ยวข้อง"
