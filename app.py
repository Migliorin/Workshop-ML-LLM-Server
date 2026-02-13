import os
from datetime import date, datetime
from typing import Optional, List

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import (
    create_engine, String, Text, Integer, Boolean, Date, DateTime, ForeignKey,
    CheckConstraint, UniqueConstraint, func
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker

# =========================
# Config (usa .env)
# =========================
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "admin_setor")
DB_USER = os.getenv("DB_USER", "admin")
DB_PASS = os.getenv("DB_PASS", "admin123")

DATABASE_URL = f"postgresql+psycopg2://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


# =========================
# Models (SQLAlchemy)
# =========================
class Department(Base):
    __tablename__ = "departments"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    cost_center: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    employees: Mapped[List["Employee"]] = relationship(back_populates="department")


class Employee(Base):
    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(primary_key=True)
    department_id: Mapped[int] = mapped_column(ForeignKey("departments.id", ondelete="RESTRICT"), nullable=False)
    full_name: Mapped[str] = mapped_column(Text, nullable=False)
    email: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    role: Mapped[str] = mapped_column(Text, nullable=False)
    salary_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    hired_on: Mapped[date] = mapped_column(Date, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    department: Mapped["Department"] = relationship(back_populates="employees")


class Supplier(Base):
    __tablename__ = "suppliers"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    tax_id: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    email: Mapped[Optional[str]] = mapped_column(Text)
    phone: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    supplier_id: Mapped[int] = mapped_column(ForeignKey("suppliers.id", ondelete="RESTRICT"), nullable=False)
    requested_by: Mapped[int] = mapped_column(ForeignKey("employees.id", ondelete="RESTRICT"), nullable=False)
    department_id: Mapped[int] = mapped_column(ForeignKey("departments.id", ondelete="RESTRICT"), nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    total_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint("status IN ('DRAFT','APPROVED','SENT','RECEIVED','CANCELLED')", name="po_status_check"),
        CheckConstraint("total_cents >= 0", name="po_total_check"),
    )


class Invoice(Base):
    __tablename__ = "invoices"

    id: Mapped[int] = mapped_column(primary_key=True)
    supplier_id: Mapped[int] = mapped_column(ForeignKey("suppliers.id", ondelete="RESTRICT"), nullable=False)
    po_id: Mapped[Optional[int]] = mapped_column(ForeignKey("purchase_orders.id", ondelete="SET NULL"))
    invoice_no: Mapped[str] = mapped_column(Text, nullable=False)
    issued_on: Mapped[date] = mapped_column(Date, nullable=False)
    due_on: Mapped[date] = mapped_column(Date, nullable=False)
    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("supplier_id", "invoice_no", name="uq_supplier_invoice"),
        CheckConstraint("status IN ('OPEN','PAID','CANCELLED','OVERDUE')", name="inv_status_check"),
        CheckConstraint("amount_cents >= 0", name="inv_amount_check"),
    )


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True)
    invoice_id: Mapped[int] = mapped_column(ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False)
    paid_on: Mapped[date] = mapped_column(Date, nullable=False)
    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    method: Mapped[str] = mapped_column(Text, nullable=False)
    reference: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint("method IN ('PIX','TED','BOLETO','CREDIT_CARD','CASH')", name="pay_method_check"),
        CheckConstraint("amount_cents > 0", name="pay_amount_check"),
    )


# =========================
# Schemas (Pydantic)
# =========================
class DepartmentCreate(BaseModel):
    name: str = Field(min_length=2)
    cost_center: str = Field(min_length=2)

class DepartmentOut(BaseModel):
    id: int
    name: str
    cost_center: str
    created_at: datetime
    class Config:
        from_attributes = True


class EmployeeCreate(BaseModel):
    department_id: int
    full_name: str
    email: EmailStr
    role: str
    salary_cents: int = Field(ge=0)
    hired_on: date
    active: bool = True

class EmployeeOut(BaseModel):
    id: int
    department_id: int
    full_name: str
    email: str
    role: str
    salary_cents: int
    hired_on: date
    active: bool
    created_at: datetime
    class Config:
        from_attributes = True


class SupplierCreate(BaseModel):
    name: str
    tax_id: str
    email: Optional[str] = None
    phone: Optional[str] = None

class SupplierOut(BaseModel):
    id: int
    name: str
    tax_id: str
    email: Optional[str]
    phone: Optional[str]
    created_at: datetime
    class Config:
        from_attributes = True


class POCreate(BaseModel):
    supplier_id: int
    requested_by: int
    department_id: int
    status: str = Field(pattern="^(DRAFT|APPROVED|SENT|RECEIVED|CANCELLED)$")
    total_cents: int = Field(ge=0)

class POOut(BaseModel):
    id: int
    supplier_id: int
    requested_by: int
    department_id: int
    status: str
    total_cents: int
    created_at: datetime
    class Config:
        from_attributes = True


class InvoiceCreate(BaseModel):
    supplier_id: int
    po_id: Optional[int] = None
    invoice_no: str
    issued_on: date
    due_on: date
    amount_cents: int = Field(ge=0)
    status: str = Field(pattern="^(OPEN|PAID|CANCELLED|OVERDUE)$")

class InvoiceOut(BaseModel):
    id: int
    supplier_id: int
    po_id: Optional[int]
    invoice_no: str
    issued_on: date
    due_on: date
    amount_cents: int
    status: str
    created_at: datetime
    class Config:
        from_attributes = True


class PaymentCreate(BaseModel):
    invoice_id: int
    paid_on: date
    amount_cents: int = Field(gt=0)
    method: str = Field(pattern="^(PIX|TED|BOLETO|CREDIT_CARD|CASH)$")
    reference: Optional[str] = None

class PaymentOut(BaseModel):
    id: int
    invoice_id: int
    paid_on: date
    amount_cents: int
    method: str
    reference: Optional[str]
    created_at: datetime
    class Config:
        from_attributes = True


# =========================
# App + helpers
# =========================
app = FastAPI(title="Admin Setor API", version="1.0")


def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.on_event("startup")
def startup():
    # Cria tabelas se não existirem
    Base.metadata.create_all(bind=engine)


# =========================
# CRUD - Departments
# =========================
@app.post("/departments", response_model=DepartmentOut, status_code=201)
def create_department(payload: DepartmentCreate):
    with SessionLocal() as db:
        obj = Department(name=payload.name, cost_center=payload.cost_center)
        db.add(obj)
        try:
            db.commit()
        except Exception as e:
            db.rollback()
            raise HTTPException(400, detail="Departamento já existe ou dados inválidos.")
        db.refresh(obj)
        return obj


@app.get("/departments", response_model=list[DepartmentOut])
def list_departments(limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0)):
    with SessionLocal() as db:
        return db.query(Department).order_by(Department.id).offset(offset).limit(limit).all()


@app.get("/departments/{dept_id}", response_model=DepartmentOut)
def get_department(dept_id: int):
    with SessionLocal() as db:
        obj = db.get(Department, dept_id)
        if not obj:
            raise HTTPException(404, detail="Departamento não encontrado.")
        return obj


@app.delete("/departments/{dept_id}", status_code=204)
def delete_department(dept_id: int):
    with SessionLocal() as db:
        obj = db.get(Department, dept_id)
        if not obj:
            raise HTTPException(404, detail="Departamento não encontrado.")
        db.delete(obj)
        db.commit()
        return None


# =========================
# CRUD - Employees
# =========================
@app.post("/employees", response_model=EmployeeOut, status_code=201)
def create_employee(payload: EmployeeCreate):
    with SessionLocal() as db:
        if not db.get(Department, payload.department_id):
            raise HTTPException(400, detail="department_id inválido.")
        obj = Employee(**payload.model_dump())
        db.add(obj)
        try:
            db.commit()
        except Exception:
            db.rollback()
            raise HTTPException(400, detail="Email já existe ou dados inválidos.")
        db.refresh(obj)
        return obj


@app.get("/employees", response_model=list[EmployeeOut])
def list_employees(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    department_id: Optional[int] = None,
    active: Optional[bool] = None,
):
    with SessionLocal() as db:
        q = db.query(Employee)
        if department_id is not None:
            q = q.filter(Employee.department_id == department_id)
        if active is not None:
            q = q.filter(Employee.active == active)
        return q.order_by(Employee.id).offset(offset).limit(limit).all()


@app.get("/employees/{emp_id}", response_model=EmployeeOut)
def get_employee(emp_id: int):
    with SessionLocal() as db:
        obj = db.get(Employee, emp_id)
        if not obj:
            raise HTTPException(404, detail="Funcionário não encontrado.")
        return obj


@app.delete("/employees/{emp_id}", status_code=204)
def delete_employee(emp_id: int):
    with SessionLocal() as db:
        obj = db.get(Employee, emp_id)
        if not obj:
            raise HTTPException(404, detail="Funcionário não encontrado.")
        db.delete(obj)
        db.commit()
        return None


# =========================
# CRUD - Suppliers
# =========================
@app.post("/suppliers", response_model=SupplierOut, status_code=201)
def create_supplier(payload: SupplierCreate):
    with SessionLocal() as db:
        obj = Supplier(**payload.model_dump())
        db.add(obj)
        try:
            db.commit()
        except Exception:
            db.rollback()
            raise HTTPException(400, detail="Fornecedor já existe (tax_id) ou dados inválidos.")
        db.refresh(obj)
        return obj


@app.get("/suppliers", response_model=list[SupplierOut])
def list_suppliers(limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0)):
    with SessionLocal() as db:
        return db.query(Supplier).order_by(Supplier.id).offset(offset).limit(limit).all()


@app.get("/suppliers/{supplier_id}", response_model=SupplierOut)
def get_supplier(supplier_id: int):
    with SessionLocal() as db:
        obj = db.get(Supplier, supplier_id)
        if not obj:
            raise HTTPException(404, detail="Fornecedor não encontrado.")
        return obj


@app.delete("/suppliers/{supplier_id}", status_code=204)
def delete_supplier(supplier_id: int):
    with SessionLocal() as db:
        obj = db.get(Supplier, supplier_id)
        if not obj:
            raise HTTPException(404, detail="Fornecedor não encontrado.")
        db.delete(obj)
        db.commit()
        return None


# =========================
# CRUD - Purchase Orders
# =========================
@app.post("/purchase-orders", response_model=POOut, status_code=201)
def create_po(payload: POCreate):
    with SessionLocal() as db:
        if not db.get(Supplier, payload.supplier_id):
            raise HTTPException(400, detail="supplier_id inválido.")
        if not db.get(Employee, payload.requested_by):
            raise HTTPException(400, detail="requested_by inválido.")
        if not db.get(Department, payload.department_id):
            raise HTTPException(400, detail="department_id inválido.")
        obj = PurchaseOrder(**payload.model_dump())
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj


@app.get("/purchase-orders", response_model=list[POOut])
def list_pos(limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0), status: Optional[str] = None):
    with SessionLocal() as db:
        q = db.query(PurchaseOrder)
        if status:
            q = q.filter(PurchaseOrder.status == status)
        return q.order_by(PurchaseOrder.id).offset(offset).limit(limit).all()


@app.get("/purchase-orders/{po_id}", response_model=POOut)
def get_po(po_id: int):
    with SessionLocal() as db:
        obj = db.get(PurchaseOrder, po_id)
        if not obj:
            raise HTTPException(404, detail="PO não encontrado.")
        return obj


@app.delete("/purchase-orders/{po_id}", status_code=204)
def delete_po(po_id: int):
    with SessionLocal() as db:
        obj = db.get(PurchaseOrder, po_id)
        if not obj:
            raise HTTPException(404, detail="PO não encontrado.")
        db.delete(obj)
        db.commit()
        return None


# =========================
# CRUD - Invoices
# =========================
@app.post("/invoices", response_model=InvoiceOut, status_code=201)
def create_invoice(payload: InvoiceCreate):
    with SessionLocal() as db:
        if not db.get(Supplier, payload.supplier_id):
            raise HTTPException(400, detail="supplier_id inválido.")
        if payload.po_id is not None and not db.get(PurchaseOrder, payload.po_id):
            raise HTTPException(400, detail="po_id inválido.")
        obj = Invoice(**payload.model_dump())
        db.add(obj)
        try:
            db.commit()
        except Exception:
            db.rollback()
            raise HTTPException(400, detail="invoice_no duplicada para esse fornecedor ou dados inválidos.")
        db.refresh(obj)
        return obj


@app.get("/invoices", response_model=list[InvoiceOut])
def list_invoices(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    status: Optional[str] = None,
    supplier_id: Optional[int] = None,
):
    with SessionLocal() as db:
        q = db.query(Invoice)
        if status:
            q = q.filter(Invoice.status == status)
        if supplier_id is not None:
            q = q.filter(Invoice.supplier_id == supplier_id)
        return q.order_by(Invoice.id).offset(offset).limit(limit).all()


@app.get("/invoices/{invoice_id}", response_model=InvoiceOut)
def get_invoice(invoice_id: int):
    with SessionLocal() as db:
        obj = db.get(Invoice, invoice_id)
        if not obj:
            raise HTTPException(404, detail="Fatura não encontrada.")
        return obj


@app.delete("/invoices/{invoice_id}", status_code=204)
def delete_invoice(invoice_id: int):
    with SessionLocal() as db:
        obj = db.get(Invoice, invoice_id)
        if not obj:
            raise HTTPException(404, detail="Fatura não encontrada.")
        db.delete(obj)
        db.commit()
        return None


# =========================
# CRUD - Payments
# =========================
@app.post("/payments", response_model=PaymentOut, status_code=201)
def create_payment(payload: PaymentCreate):
    with SessionLocal() as db:
        inv = db.get(Invoice, payload.invoice_id)
        if not inv:
            raise HTTPException(400, detail="invoice_id inválido.")
        obj = Payment(**payload.model_dump())
        db.add(obj)
        db.commit()
        db.refresh(obj)

        # Opcional: se pagou tudo, marcar invoice como PAID.
        total_paid = db.query(func.coalesce(func.sum(Payment.amount_cents), 0)).filter(Payment.invoice_id == inv.id).scalar()
        if total_paid >= inv.amount_cents and inv.status != "PAID":
            inv.status = "PAID"
            db.commit()

        return obj


@app.get("/payments", response_model=list[PaymentOut])
def list_payments(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    invoice_id: Optional[int] = None,
):
    with SessionLocal() as db:
        q = db.query(Payment)
        if invoice_id is not None:
            q = q.filter(Payment.invoice_id == invoice_id)
        return q.order_by(Payment.id).offset(offset).limit(limit).all()


@app.get("/payments/{payment_id}", response_model=PaymentOut)
def get_payment(payment_id: int):
    with SessionLocal() as db:
        obj = db.get(Payment, payment_id)
        if not obj:
            raise HTTPException(404, detail="Pagamento não encontrado.")
        return obj


@app.delete("/payments/{payment_id}", status_code=204)
def delete_payment(payment_id: int):
    with SessionLocal() as db:
        obj = db.get(Payment, payment_id)
        if not obj:
            raise HTTPException(404, detail="Pagamento não encontrado.")
        db.delete(obj)
        db.commit()
        return None

