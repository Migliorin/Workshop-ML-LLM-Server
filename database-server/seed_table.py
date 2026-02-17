import os
import psycopg2
from psycopg2.extras import execute_values

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME", "admin_setor")
DB_USER = os.getenv("DB_USER", "admin")
DB_PASS = os.getenv("DB_PASS", "admin123")


DDL = """
BEGIN;

CREATE TABLE IF NOT EXISTS departments (
  id           SERIAL PRIMARY KEY,
  name         TEXT NOT NULL UNIQUE,
  cost_center  TEXT NOT NULL UNIQUE,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS employees (
  id             SERIAL PRIMARY KEY,
  department_id  INT NOT NULL REFERENCES departments(id) ON DELETE RESTRICT,
  full_name      TEXT NOT NULL,
  email          TEXT NOT NULL UNIQUE,
  role           TEXT NOT NULL,
  salary_cents   INT NOT NULL CHECK (salary_cents >= 0),
  hired_on       DATE NOT NULL,
  active         BOOLEAN NOT NULL DEFAULT TRUE,
  created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS suppliers (
  id           SERIAL PRIMARY KEY,
  name         TEXT NOT NULL UNIQUE,
  tax_id       TEXT NOT NULL UNIQUE,
  email        TEXT,
  phone        TEXT,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Pedido de compra (PO)
CREATE TABLE IF NOT EXISTS purchase_orders (
  id            SERIAL PRIMARY KEY,
  supplier_id   INT NOT NULL REFERENCES suppliers(id) ON DELETE RESTRICT,
  requested_by  INT NOT NULL REFERENCES employees(id) ON DELETE RESTRICT,
  department_id INT NOT NULL REFERENCES departments(id) ON DELETE RESTRICT,
  status        TEXT NOT NULL CHECK (status IN ('DRAFT','APPROVED','SENT','RECEIVED','CANCELLED')),
  total_cents   INT NOT NULL CHECK (total_cents >= 0),
  created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Nota/Fatura (pode apontar para um PO)
CREATE TABLE IF NOT EXISTS invoices (
  id            SERIAL PRIMARY KEY,
  supplier_id   INT NOT NULL REFERENCES suppliers(id) ON DELETE RESTRICT,
  po_id         INT REFERENCES purchase_orders(id) ON DELETE SET NULL,
  invoice_no    TEXT NOT NULL,
  issued_on     DATE NOT NULL,
  due_on        DATE NOT NULL,
  amount_cents  INT NOT NULL CHECK (amount_cents >= 0),
  status        TEXT NOT NULL CHECK (status IN ('OPEN','PAID','CANCELLED','OVERDUE')),
  created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (supplier_id, invoice_no)
);

CREATE TABLE IF NOT EXISTS payments (
  id            SERIAL PRIMARY KEY,
  invoice_id    INT NOT NULL REFERENCES invoices(id) ON DELETE CASCADE,
  paid_on       DATE NOT NULL,
  amount_cents  INT NOT NULL CHECK (amount_cents > 0),
  method        TEXT NOT NULL CHECK (method IN ('PIX','TED','BOLETO','CREDIT_CARD','CASH')),
  reference     TEXT,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMIT;
"""


def get_conn():
  return psycopg2.connect(
    host=DB_HOST,
    port=DB_PORT,
    dbname=DB_NAME,
    user=DB_USER,
    password=DB_PASS,
  )


def upsert_base_data(cur):
  # Departments
  departments = [
    ("Financeiro", "CC-100"),
    ("RH", "CC-200"),
    ("Compras", "CC-300"),
    ("Administrativo", "CC-400"),
  ]
  execute_values(
    cur,
    """
    INSERT INTO departments (name, cost_center)
    VALUES %s
    ON CONFLICT (name) DO UPDATE SET cost_center = EXCLUDED.cost_center
    RETURNING id, name;
    """,
    departments,
  )
  dept_rows = cur.fetchall()
  dept_id = {name: _id for (_id, name) in dept_rows}

  # Employees
  employees = [
    (dept_id["Financeiro"], "Ana Souza", "ana.souza@empresa.com", "Analista Financeiro", 550000, "2023-02-10", True),
    (dept_id["RH"], "Bruno Lima", "bruno.lima@empresa.com", "Analista de RH", 480000, "2022-08-01", True),
    (dept_id["Compras"], "Carla Mendes", "carla.mendes@empresa.com", "Comprador", 520000, "2021-05-12", True),
    (dept_id["Administrativo"], "Diego Pereira", "diego.pereira@empresa.com", "Assistente Administrativo", 320000, "2024-01-15", True),
  ]
  execute_values(
    cur,
    """
    INSERT INTO employees (department_id, full_name, email, role, salary_cents, hired_on, active)
    VALUES %s
    ON CONFLICT (email) DO UPDATE SET
      department_id = EXCLUDED.department_id,
      full_name = EXCLUDED.full_name,
      role = EXCLUDED.role,
      salary_cents = EXCLUDED.salary_cents,
      hired_on = EXCLUDED.hired_on,
      active = EXCLUDED.active
    RETURNING id, email;
    """,
    employees,
  )
  emp_rows = cur.fetchall()
  emp_id = {email: _id for (_id, email) in emp_rows}

  # Suppliers
  suppliers = [
    ("Papelaria Norte", "12.345.678/0001-00", "contato@papelarianorte.com", "+55 92 99999-0000"),
    ("TechOffice LTDA", "98.765.432/0001-11", "financeiro@techoffice.com", "+55 11 98888-1111"),
  ]
  execute_values(
    cur,
    """
    INSERT INTO suppliers (name, tax_id, email, phone)
    VALUES %s
    ON CONFLICT (tax_id) DO UPDATE SET
      name = EXCLUDED.name,
      email = EXCLUDED.email,
      phone = EXCLUDED.phone
    RETURNING id, tax_id;
    """,
    suppliers,
  )
  sup_rows = cur.fetchall()
  sup_id = {tax_id: _id for (_id, tax_id) in sup_rows}

  # Purchase Orders
  # (vamos inserir de forma idempotente usando uma chave lógica simples: supplier_id + total_cents + created_at::date não é perfeita,
  # mas serve para seed exemplo. Em produção, crie um campo "po_number" UNIQUE.)
  pos = [
    (sup_id["12.345.678/0001-00"], emp_id["carla.mendes@empresa.com"], dept_id["Compras"], "APPROVED", 125900),
    (sup_id["98.765.432/0001-11"], emp_id["diego.pereira@empresa.com"], dept_id["Administrativo"], "SENT", 349900),
  ]
  execute_values(
    cur,
    """
    INSERT INTO purchase_orders (supplier_id, requested_by, department_id, status, total_cents)
    VALUES %s
    RETURNING id;
    """,
    pos,
  )
  po_ids = [r[0] for r in cur.fetchall()]

  # Invoices
  invoices = [
    (sup_id["12.345.678/0001-00"], po_ids[0], "NF-0001", "2026-02-01", "2026-02-20", 125900, "OPEN"),
    (sup_id["98.765.432/0001-11"], po_ids[1], "NF-0100", "2026-02-05", "2026-02-15", 349900, "PAID"),
  ]
  execute_values(
    cur,
    """
    INSERT INTO invoices (supplier_id, po_id, invoice_no, issued_on, due_on, amount_cents, status)
    VALUES %s
    ON CONFLICT (supplier_id, invoice_no) DO UPDATE SET
      po_id = EXCLUDED.po_id,
      issued_on = EXCLUDED.issued_on,
      due_on = EXCLUDED.due_on,
      amount_cents = EXCLUDED.amount_cents,
      status = EXCLUDED.status
    RETURNING id, invoice_no;
    """,
    invoices,
  )
  inv_rows = cur.fetchall()
  inv_id = {invoice_no: _id for (_id, invoice_no) in inv_rows}

  # Payments (apenas para a fatura paga)
  payments = [
    (inv_id["NF-0100"], "2026-02-06", 349900, "PIX", "PIX-REF-20260206-0001"),
  ]
  execute_values(
    cur,
    """
    INSERT INTO payments (invoice_id, paid_on, amount_cents, method, reference)
    VALUES %s
    ON CONFLICT DO NOTHING;
    """,
    payments,
  )


def main():
  conn = get_conn()
  conn.autocommit = False
  try:
    with conn.cursor() as cur:
      cur.execute(DDL)
      upsert_base_data(cur)
    conn.commit()
    print("✅ Tabelas criadas e dados inseridos com sucesso.")
  except Exception as e:
    conn.rollback()
    print("❌ Erro:", e)
    raise
  finally:
    conn.close()


if __name__ == "__main__":
  main()
