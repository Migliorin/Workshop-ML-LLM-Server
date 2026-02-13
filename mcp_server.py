import os
import httpx
from datetime import date, datetime
from typing import Optional, List, Dict, Any
from fastmcp import FastMCP

def _normalize_hired_on(value: str) -> str:
    """
    Normaliza hired_on para ISO.
    - Se vier "YYYY-MM-DD" -> retorna "YYYY-MM-DD"
    - Se vier datetime ISO (com T) -> retorna só a data "YYYY-MM-DD"
    - Se vier vazio/ruim -> retorna o valor original (pra não estourar)
    """
    if not isinstance(value, str):
        return value  # type: ignore[return-value]

    s = value.strip()
    if not s:
        return value

    try:
        if "T" in s:
            dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
            return dt.date().isoformat()
        # valida e normaliza YYYY-MM-DD
        return date.fromisoformat(s).isoformat()
    except Exception:
        return value


# =========================
# Config
# =========================
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

mcp = FastMCP("admin-setor-mcp")


# =========================
# HTTP Client Helper
# =========================
# async def api_request(method: str, path: str, json: Optional[dict] = None, params: Optional[dict] = None):
#     url = f"{API_BASE_URL}{path}"
#     async with httpx.AsyncClient(timeout=20.0) as client:
#         response = await client.request(method, url, json=json, params=params)
#         print
#         response.raise_for_status()
#         return response.json()
async def api_request(method: str, path: str, **kwargs):
    url = f"{API_BASE_URL}{path}"
    async with httpx.AsyncClient(timeout=20.0) as client:
        r = await client.request(method, url, **kwargs)

        if r.status_code >= 400:
            try:
                body = r.json()
            except Exception:
                body = r.text
            return {"ok": False, "status": r.status_code, "body": body}

        return r.json()


# =========================
# TOOLS
# =========================

@mcp.tool()
async def list_departments(limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
    """Lista departamentos cadastrados."""
    return await api_request("GET", "/departments", params={"limit": limit, "offset": offset})


@mcp.tool()
async def create_department(name: str, cost_center: str) -> Dict[str, Any]:
    """Cria um novo departamento."""
    return await api_request("POST", "/departments", json={
        "name": name,
        "cost_center": cost_center
    })


@mcp.tool()
async def list_employees(limit: int = 50, offset: int = 0, department_id: Optional[int] = None) -> List[Dict[str, Any]]:
    """Lista funcionários."""
    params = {"limit": limit, "offset": offset}
    if department_id:
        params["department_id"] = department_id
    return await api_request("GET", "/employees", params=params)


@mcp.tool()
async def create_employee(
    department_id: int,
    full_name: str,
    email: str,
    role: str,
    salary_cents: int,
    hired_on: str,
    active: bool = True
) -> Dict[str, Any]:
    """Cria funcionário."""
    return await api_request("POST", "/employees", json={
        "department_id": department_id,
        "full_name": full_name,
        "email": email,
        "role": role,
        "salary_cents": salary_cents,
        "hired_on": _normalize_hired_on(hired_on),
        "active": active
    })


@mcp.tool()
async def list_suppliers(limit: int = 50, offset: int = 0):
    """Lista fornecedores."""
    return await api_request("GET", "/suppliers", params={"limit": limit, "offset": offset})


@mcp.tool()
async def create_supplier(name: str, tax_id: str, email: Optional[str] = None, phone: Optional[str] = None):
    """Cria fornecedor."""
    return await api_request("POST", "/suppliers", json={
        "name": name,
        "tax_id": tax_id,
        "email": email,
        "phone": phone
    })


@mcp.tool()
async def list_invoices(limit: int = 50, offset: int = 0, status: Optional[str] = None):
    """Lista faturas."""
    params = {"limit": limit, "offset": offset}
    if status:
        params["status"] = status
    return await api_request("GET", "/invoices", params=params)


@mcp.tool()
async def create_invoice(
    supplier_id: int,
    invoice_no: str,
    issued_on: str,
    due_on: str,
    amount_cents: int,
    status: str,
    po_id: Optional[int] = None
):
    """Cria fatura."""
    return await api_request("POST", "/invoices", json={
        "supplier_id": supplier_id,
        "po_id": po_id,
        "invoice_no": invoice_no,
        "issued_on": issued_on,
        "due_on": due_on,
        "amount_cents": amount_cents,
        "status": status
    })


@mcp.tool()
async def create_payment(
    invoice_id: int,
    paid_on: str,
    amount_cents: int,
    method: str,
    reference: Optional[str] = None
):
    """Registra pagamento."""
    return await api_request("POST", "/payments", json={
        "invoice_id": invoice_id,
        "paid_on": paid_on,
        "amount_cents": amount_cents,
        "method": method,
        "reference": reference
    })


# =========================
# Run Server
# =========================
if __name__ == "__main__":
    # Servidor remoto via Streamable HTTP (recomendado)
    mcp.run(
        transport="http",
        host="0.0.0.0",
        port=8001,
        path="/mcp",
    )

