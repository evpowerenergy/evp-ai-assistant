"""
Prompt E2E Test API
CRUD test cases, run tests, view results
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List

from app.core.auth import get_current_user, require_role
from app.services.supabase import get_supabase_client
from app.orchestrator.graph import process_message
from app.orchestrator.state import AIAssistantState
from app.services.embedding_similarity import compute_similarity
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()


class TestCaseCreate(BaseModel):
    user_message: str
    expected_intent: Optional[str] = None
    expected_tool: Optional[str] = None
    expected_message: Optional[str] = None
    similarity_threshold: float = 0.70
    notes: Optional[str] = None


class TestCaseUpdate(BaseModel):
    user_message: Optional[str] = None
    expected_intent: Optional[str] = None
    expected_tool: Optional[str] = None
    expected_message: Optional[str] = None
    similarity_threshold: Optional[float] = None
    notes: Optional[str] = None


class RunTestsRequest(BaseModel):
    test_case_ids: Optional[List[str]] = None  # None = run all


class RunStartRequest(BaseModel):
    test_case_ids: Optional[List[str]] = None  # None = all cases


class RunOneRequest(BaseModel):
    run_id: str
    test_case_id: str


def _primary_tool_from_state(state: dict) -> Optional[str]:
    """Extract primary tool name from state tool_calls"""
    tool_calls = state.get("tool_calls") or []
    if tool_calls:
        first = tool_calls[0]
        return first.get("tool") if isinstance(first, dict) else None
    return None


@router.get("/prompt-tests/cases")
async def list_test_cases(
    current_user: dict = Depends(require_role(["admin", "manager", "super_admin"]))
):
    """List all test cases"""
    try:
        supabase = get_supabase_client()
        r = supabase.table("prompt_test_cases").select("*").order("created_at", desc=True).execute()
        return {"success": True, "data": r.data or []}
    except Exception as e:
        logger.error(f"List test cases error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/prompt-tests/cases")
async def create_test_case(
    body: TestCaseCreate,
    current_user: dict = Depends(require_role(["admin", "manager", "super_admin"]))
):
    """Create a new test case"""
    try:
        supabase = get_supabase_client()
        row = {
            "user_message": body.user_message,
            "expected_intent": body.expected_intent,
            "expected_tool": body.expected_tool,
            "expected_message": body.expected_message,
            "similarity_threshold": float(body.similarity_threshold),
            "notes": body.notes,
        }
        r = supabase.table("prompt_test_cases").insert(row).execute()
        if r.data:
            return {"success": True, "data": r.data[0]}
        raise HTTPException(status_code=500, detail="Insert failed")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Create test case error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/prompt-tests/cases/{case_id}")
async def get_test_case(
    case_id: str,
    current_user: dict = Depends(require_role(["admin", "manager", "super_admin"]))
):
    """Get a test case by id"""
    try:
        supabase = get_supabase_client()
        r = supabase.table("prompt_test_cases").select("*").eq("id", case_id).execute()
        if not r.data:
            raise HTTPException(status_code=404, detail="Test case not found")
        return {"success": True, "data": r.data[0]}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get test case error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/prompt-tests/cases/{case_id}")
async def update_test_case(
    case_id: str,
    body: TestCaseUpdate,
    current_user: dict = Depends(require_role(["admin", "manager", "super_admin"]))
):
    """Update a test case"""
    try:
        supabase = get_supabase_client()
        row = {k: v for k, v in body.model_dump(exclude_unset=True).items()}
        if not row:
            raise HTTPException(status_code=400, detail="No fields to update")
        if "similarity_threshold" in row:
            row["similarity_threshold"] = float(row["similarity_threshold"])
        r = supabase.table("prompt_test_cases").update(row).eq("id", case_id).execute()
        if r.data:
            return {"success": True, "data": r.data[0]}
        raise HTTPException(status_code=404, detail="Test case not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update test case error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/prompt-tests/cases/{case_id}")
async def delete_test_case(
    case_id: str,
    current_user: dict = Depends(require_role(["admin", "manager", "super_admin"]))
):
    """Delete a test case"""
    try:
        supabase = get_supabase_client()
        supabase.table("prompt_test_cases").delete().eq("id", case_id).execute()
        return {"success": True}
    except Exception as e:
        logger.error(f"Delete test case error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/prompt-tests/run/start")
async def run_tests_start(
    body: RunStartRequest,
    current_user: dict = Depends(require_role(["admin", "manager", "super_admin"]))
):
    """สร้าง run record แล้วค่อยรันทีละเคสผ่าน run/one — คืน run_id"""
    try:
        supabase = get_supabase_client()
        user_id = current_user.get("id", "")
        q = supabase.table("prompt_test_cases").select("id")
        if body.test_case_ids:
            q = q.in_("id", body.test_case_ids)
        r = q.execute()
        cases = r.data or []
        if not cases:
            raise HTTPException(status_code=400, detail="No test cases to run")
        run_row = {"total": len(cases), "passed": 0, "failed": 0, "run_by": user_id}
        run_r = supabase.table("prompt_test_runs").insert(run_row).execute()
        run_id = run_r.data[0]["id"] if run_r.data else None
        if not run_id:
            raise HTTPException(status_code=500, detail="Failed to create run record")
        return {"success": True, "run_id": run_id, "total": len(cases)}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Run start error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def _run_single_case(
    supabase,
    run_id: str,
    tc: dict,
    user_id: str,
    user_role: str,
) -> tuple[dict, str, int, int]:
    """รันหนึ่ง test case; คืน (result_dict, pass_fail, new_passed, new_failed)."""
    tc_id = tc["id"]
    user_message = tc.get("user_message", "")
    expected_intent = tc.get("expected_intent")
    expected_tool = tc.get("expected_tool")
    expected_message = tc.get("expected_message", "")
    actual_intent = None
    actual_tool = None
    ai_message = ""
    similarity_score = None
    pass_fail = "fail"
    error_message = None
    try:
        initial_state: AIAssistantState = {
            "user_message": user_message,
            "user_id": user_id,
            "user_role": user_role,
            "session_id": "",
            "chat_history": [],
            "history_context": "",
            "intent": None,
            "confidence": 0.0,
            "tool_calls": [],
            "tool_results": [],
            "rag_results": [],
            "citations": [],
            "retry_count": 0,
            "max_retries": 0,
            "previous_attempts": [],
            "data_quality": None,
            "quality_reason": None,
            "suggested_retry_params": None,
            "alternative_queries": [],
            "response": None,
            "error": None,
        }
        result_state = await process_message(initial_state)
        ai_message = result_state.get("response") or ""
        actual_intent = result_state.get("intent")
        actual_tool = _primary_tool_from_state(result_state)
        has_error = bool(result_state.get("error"))
        intent_ok = (
            not expected_intent
            or (str(actual_intent or "").lower() == str(expected_intent or "").lower())
        )
        tool_ok = (
            not expected_tool
            or (str(actual_tool or "").lower() == str(expected_tool or "").lower())
        )
        pass_fail = "pass" if (not has_error and intent_ok and tool_ok) else "fail"
        if expected_message and ai_message:
            similarity_score = await compute_similarity(ai_message, expected_message)
            similarity_score = round(float(similarity_score), 4)
    except Exception as e:
        error_message = str(e)
        pass_fail = "fail"
    supabase.table("prompt_test_results").insert({
        "run_id": run_id,
        "test_case_id": tc_id,
        "actual_intent": actual_intent,
        "actual_tool": actual_tool,
        "ai_message": ai_message,
        "similarity_score": float(similarity_score) if similarity_score is not None else None,
        "pass_fail": pass_fail,
        "error_message": error_message,
    }).execute()
    run_r = supabase.table("prompt_test_runs").select("passed, failed").eq("id", run_id).execute()
    prev_passed = run_r.data[0]["passed"] if run_r.data else 0
    prev_failed = run_r.data[0]["failed"] if run_r.data else 0
    if pass_fail == "pass":
        new_passed, new_failed = prev_passed + 1, prev_failed
    else:
        new_passed, new_failed = prev_passed, prev_failed + 1
    supabase.table("prompt_test_runs").update({"passed": new_passed, "failed": new_failed}).eq("id", run_id).execute()
    result = {
        "test_case_id": tc_id,
        "user_message": user_message,
        "expected_intent": expected_intent,
        "expected_tool": expected_tool,
        "actual_intent": actual_intent,
        "actual_tool": actual_tool,
        "ai_message": ai_message[:500] if ai_message else "",
        "expected_message": expected_message[:500] if expected_message else "",
        "similarity_score": similarity_score,
        "pass_fail": pass_fail,
    }
    return result, pass_fail, new_passed, new_failed


@router.post("/prompt-tests/run/one")
async def run_one_test(
    body: RunOneRequest,
    current_user: dict = Depends(require_role(["admin", "manager", "super_admin"]))
):
    """รันหนึ่ง test case แล้วคืนผล — ใช้ร่วมกับ run/start เพื่อให้ผลออกทีละ row"""
    try:
        supabase = get_supabase_client()
        user_id = current_user.get("id", "")
        user_role = current_user.get("role", "staff")
        run_r = supabase.table("prompt_test_runs").select("id").eq("id", body.run_id).execute()
        if not run_r.data:
            raise HTTPException(status_code=404, detail="Run not found")
        tc_r = supabase.table("prompt_test_cases").select("*").eq("id", body.test_case_id).execute()
        if not tc_r.data:
            raise HTTPException(status_code=404, detail="Test case not found")
        tc = tc_r.data[0]
        result, _pf, passed, failed = await _run_single_case(
            supabase, body.run_id, tc, user_id, user_role
        )
        return {
            "success": True,
            "result": result,
            "passed": passed,
            "failed": failed,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Run one error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/prompt-tests/run")
async def run_tests(
    body: RunTestsRequest,
    current_user: dict = Depends(require_role(["admin", "manager", "super_admin"]))
):
    """
    Run E2E tests: send each test case through the chat pipeline,
    compute similarity vs expected_message, store results.
    """
    try:
        supabase = get_supabase_client()
        user_id = current_user.get("id", "")
        user_role = current_user.get("role", "staff")

        # Load test cases
        q = supabase.table("prompt_test_cases").select("*")
        if body.test_case_ids:
            q = q.in_("id", body.test_case_ids)
        r = q.execute()
        cases = r.data or []
        if not cases:
            raise HTTPException(status_code=400, detail="No test cases to run")

        # Create run record
        run_row = {"total": len(cases), "passed": 0, "failed": 0, "run_by": user_id}
        run_r = supabase.table("prompt_test_runs").insert(run_row).execute()
        run_id = run_r.data[0]["id"] if run_r.data else None
        if not run_id:
            raise HTTPException(status_code=500, detail="Failed to create run record")

        passed = 0
        failed = 0
        results = []

        for tc in cases:
            tc_id = tc["id"]
            user_message = tc.get("user_message", "")
            expected_intent = tc.get("expected_intent")
            expected_tool = tc.get("expected_tool")
            expected_message = tc.get("expected_message", "")

            actual_intent = None
            actual_tool = None
            ai_message = ""
            similarity_score = None
            pass_fail = "fail"
            error_message = None

            try:
                # Run through pipeline (no history, no save)
                initial_state: AIAssistantState = {
                    "user_message": user_message,
                    "user_id": user_id,
                    "user_role": user_role,
                    "session_id": "",
                    "chat_history": [],
                    "history_context": "",
                    "intent": None,
                    "confidence": 0.0,
                    "tool_calls": [],
                    "tool_results": [],
                    "rag_results": [],
                    "citations": [],
                    "retry_count": 0,
                    "max_retries": 0,
                    "previous_attempts": [],
                    "data_quality": None,
                    "quality_reason": None,
                    "suggested_retry_params": None,
                    "alternative_queries": [],
                    "response": None,
                    "error": None,
                }
                result_state = await process_message(initial_state)
                ai_message = result_state.get("response") or ""
                actual_intent = result_state.get("intent")
                actual_tool = _primary_tool_from_state(result_state)

                # Dynamic pass/fail: ไม่ error + intent ตรง (ถ้าระบุ) + tool ตรง (ถ้าระบุ)
                # Expected message ใช้เก็บ/แสดง similarity เป็นข้อมูลเท่านั้น ไม่ใช้ตัด pass/fail
                has_error = bool(result_state.get("error"))
                intent_ok = (
                    not expected_intent
                    or (str(actual_intent or "").lower() == str(expected_intent or "").lower())
                )
                tool_ok = (
                    not expected_tool
                    or (str(actual_tool or "").lower() == str(expected_tool or "").lower())
                )
                pass_fail = "pass" if (not has_error and intent_ok and tool_ok) else "fail"

                # Similarity vs expected_message — สำหรับแสดงใน UI เท่านั้น (reference)
                if expected_message and ai_message:
                    similarity_score = await compute_similarity(ai_message, expected_message)
                    similarity_score = round(float(similarity_score), 4)
                else:
                    similarity_score = None

                if pass_fail == "pass":
                    passed += 1
                else:
                    failed += 1

            except Exception as e:
                error_message = str(e)
                failed += 1
                pass_fail = "fail"

            # Insert result
            supabase.table("prompt_test_results").insert({
                "run_id": run_id,
                "test_case_id": tc_id,
                "actual_intent": actual_intent,
                "actual_tool": actual_tool,
                "ai_message": ai_message,
                "similarity_score": float(similarity_score) if similarity_score is not None else None,
                "pass_fail": pass_fail,
                "error_message": error_message,
            }).execute()

            results.append({
                "test_case_id": tc_id,
                "user_message": user_message,
                "expected_intent": expected_intent,
                "expected_tool": expected_tool,
                "actual_intent": actual_intent,
                "actual_tool": actual_tool,
                "ai_message": ai_message[:500] if ai_message else "",
                "expected_message": expected_message[:500] if expected_message else "",
                "similarity_score": similarity_score,
                "pass_fail": pass_fail,
            })

        # Update run counts
        supabase.table("prompt_test_runs").update(
            {"passed": passed, "failed": failed}
        ).eq("id", run_id).execute()

        return {
            "success": True,
            "run_id": run_id,
            "total": len(cases),
            "passed": passed,
            "failed": failed,
            "results": results,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Run tests error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/prompt-tests/runs")
async def list_runs(
    limit: int = 20,
    current_user: dict = Depends(require_role(["admin", "manager", "super_admin"]))
):
    """List recent test runs"""
    try:
        supabase = get_supabase_client()
        r = supabase.table("prompt_test_runs").select("*").order("run_at", desc=True).limit(limit).execute()
        return {"success": True, "data": r.data or []}
    except Exception as e:
        logger.error(f"List runs error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/prompt-tests/runs/{run_id}")
async def get_run_results(
    run_id: str,
    current_user: dict = Depends(require_role(["admin", "manager", "super_admin"]))
):
    """Get results for a specific run"""
    try:
        supabase = get_supabase_client()
        run_r = supabase.table("prompt_test_runs").select("*").eq("id", run_id).execute()
        if not run_r.data:
            raise HTTPException(status_code=404, detail="Run not found")
        run_row = run_r.data[0]

        results_r = supabase.table("prompt_test_results").select("*").eq("run_id", run_id).execute()
        result_rows = results_r.data or []

        # Enrich with test case details
        case_ids = [r["test_case_id"] for r in result_rows]
        cases_r = supabase.table("prompt_test_cases").select("id, user_message, expected_intent, expected_tool, expected_message").in_("id", case_ids).execute()
        cases_by_id = {c["id"]: c for c in (cases_r.data or [])}

        results = []
        for row in result_rows:
            tc = cases_by_id.get(row["test_case_id"]) or {}
            results.append({
                **row,
                "user_message": tc.get("user_message"),
                "expected_intent": tc.get("expected_intent"),
                "expected_tool": tc.get("expected_tool"),
                "expected_message": tc.get("expected_message"),
            })

        return {
            "success": True,
            "run": run_row,
            "results": results,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get run results error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
