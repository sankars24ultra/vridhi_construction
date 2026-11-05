
# Software Requirements Specification (SRS)

## Architecture Blueprint

### Project
Multi-Project Construction ERP and Job Costing Application

### Technology Stack
- **Frontend:** React, Vite, Tailwind CSS, and TanStack Query
- **Backend:** Python, FastAPI, Pydantic v2, and SQLAlchemy 2.0 Async
- **Database:** PostgreSQL

## 1. System Overview
This project is a project-centered ERP platform for construction businesses managing multiple job sites. Every purchase, invoice, and labor hour must be linked to a `project_id`.

## 2. PostgreSQL Database Schema
Save the following schema as `init_db.sql`. It defines the core tables, relationships, and data constraints.
```sql
-- Enable UUID extension for secure, non-sequential public identifiers if needed
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =========================================================================
-- MASTER DATA TABLES
-- =========================================================================

-- 1. Projects Table (The Core Anchor)
CREATE TABLE projects (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    location TEXT NOT NULL,
    allocated_budget NUMERIC(15, 2) NOT NULL CHECK (allocated_budget >= 0),
    start_date DATE NOT NULL,
    estimated_end_date DATE,
    status VARCHAR(50) DEFAULT 'Planning' CHECK (status IN ('Planning', 'Active', 'On Hold', 'Completed')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 2. Employees & Labor Roster
CREATE TABLE employees (
    id SERIAL PRIMARY KEY,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    role VARCHAR(100) NOT NULL, -- e.g., 'Foreman', 'Carpenter', 'Project Manager'
    default_hourly_rate NUMERIC(10, 2) NOT NULL CHECK (default_hourly_rate >= 0),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- =========================================================================
-- TRANSACTIONS & MODULE TABLES (All tied directly to a Project)
-- =========================================================================

-- 3. Module A: Procurement / Purchasing Ledger
CREATE TABLE purchase_orders (
    id SERIAL PRIMARY KEY,
    project_id INT NOT NULL REFERENCES projects(id) ON DELETE RESTRICT,
    vendor_name VARCHAR(255) NOT NULL,
    item_description TEXT NOT NULL,
    quantity NUMERIC(10, 2) NOT NULL CHECK (quantity > 0),
    unit_price NUMERIC(10, 2) NOT NULL CHECK (unit_price >= 0),
    total_amount NUMERIC(15, 2) GENERATED ALWAYS AS (quantity * unit_price) STORED,
    order_date DATE NOT NULL DEFAULT CURRENT_DATE,
    status VARCHAR(50) DEFAULT 'Pending' CHECK (status IN ('Pending', 'Approved', 'Shipped', 'Delivered', 'Cancelled')),
    delivery_photo_url TEXT
);

-- 4. Module B: Sales, Estimates, & Invoicing Ledger
CREATE TABLE sales_invoices (
    id SERIAL PRIMARY KEY,
    project_id INT NOT NULL REFERENCES projects(id) ON DELETE RESTRICT,
    client_name VARCHAR(255) NOT NULL,
    amount_billed NUMERIC(15, 2) NOT NULL CHECK (amount_billed >= 0),
    retention_percentage NUMERIC(4, 2) DEFAULT 10.00 CHECK (retention_percentage BETWEEN 0 AND 100),
    invoice_date DATE NOT NULL DEFAULT CURRENT_DATE,
    due_date DATE NOT NULL,
    status VARCHAR(50) DEFAULT 'Unpaid' CHECK (status IN ('Unpaid', 'Partially Paid', 'Paid', 'Overdue')),
    CHECK (due_date >= invoice_date)
);

-- 5. Module C: Labor Timecards & Job-Wise Payroll
CREATE TABLE labor_timecards (
    id SERIAL PRIMARY KEY,
    project_id INT NOT NULL REFERENCES projects(id) ON DELETE RESTRICT,
    employee_id INT NOT NULL REFERENCES employees(id) ON DELETE RESTRICT,
    cost_code VARCHAR(100) NOT NULL, -- e.g., 'Concrete Pouring', 'Drywall Framing'
    clock_in TIMESTAMP WITH TIME ZONE NOT NULL,
    clock_out TIMESTAMP WITH TIME ZONE NOT NULL,
    hourly_rate_at_time NUMERIC(10, 2) NOT NULL CHECK (hourly_rate_at_time >= 0), -- Captured historically
    hours_worked NUMERIC(5, 2) NOT NULL CHECK (hours_worked > 0),
    calculated_salary NUMERIC(12, 2) GENERATED ALWAYS AS (hours_worked * hourly_rate_at_time) STORED,
    gps_lat_in NUMERIC(9, 6),
    gps_lng_in NUMERIC(9, 6),
    CHECK (clock_out > clock_in)
);

-- =========================================================================
-- INDEXES FOR HIGH-SPEED AGGREGATION & REPORTING
-- =========================================================================
CREATE INDEX idx_po_project ON purchase_orders(project_id);
CREATE INDEX idx_sales_project ON sales_invoices(project_id);
CREATE INDEX idx_timecard_project ON labor_timecards(project_id);
```
---## 3. Backend FastAPI Implementation CodeThis script sets up a production-ready, asynchronous pattern to compute live project profitability. It defines the database connection, models, and a macro financial endpoint.
```python
# main.py
import os
from datetime import datetime, date
from typing import List, Optional
from decimal import Decimal
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy import text

# --- DATABASE SETUP ---
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://user:password@localhost:5432/construction_db")

engine = create_async_engine(DATABASE_URL, echo=True)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

# --- FASTAPI APP RECONCILIATION ---
app = FastAPI(title="Construction ERP Engine", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Tighten down to React App origin in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- PYDANTIC SCHEMAS ---
class ProjectBase(BaseModel):
    name: str = Field(..., example="Commercial Plaza A")
    location: str = Field(..., example="Dallas, TX")
    allocated_budget: Decimal = Field(..., example=500000.00)
    start_date: date
    estimated_end_date: Optional[date] = None

class ProjectCreate(ProjectBase):
    pass

class ProjectRead(ProjectBase):
    id: int

class ProjectFinancialSummary(BaseModel):
    project_id: int
    project_name: str
    allocated_budget: Decimal
    total_purchasing_costs: Decimal
    total_labor_costs: Decimal
    total_sales_billed: Decimal
    net_profit: Decimal
    budget_remaining: Decimal

# --- API ENDPOINTS ---

@app.post("/api/v1/projects", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
async def create_project(project: ProjectCreate, db: AsyncSession = Depends(get_db)):
    """Inserts a new project into the Master Directory."""
    query = text("""
        INSERT INTO projects (name, location, allocated_budget, start_date, estimated_end_date)
        VALUES (:name, :location, :allocated_budget, :start_date, :estimated_end_date)
        RETURNING id;
    """)
    try:
        result = await db.execute(query, project.model_dump())
        project_id = result.scalar_one()
        await db.commit()
        return ProjectRead(id=project_id, **project.model_dump())
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=f"Database execution failed: {str(e)}")

@app.get("/api/v1/projects/{project_id}/financial-snapshot", response_model=ProjectFinancialSummary)
async def get_project_financial_snapshot(project_id: int, db: AsyncSession = Depends(get_db)):
    """
    Computes real-time job costing data for a specific project.
    Aggregates across Procurement, Invoicing, and Payroll modules natively in Postgres.
    """
    # 1. Verify project exists
    proj_query = text("SELECT id, name, allocated_budget FROM projects WHERE id = :id")
    proj_res = await db.execute(proj_query, {"id": project_id})
    project = proj_res.fetchone()
    
    if not project:
        raise HTTPException(status_code=404, detail="Project context not found.")

    # 2. Execute unified aggregate metrics query
    financial_query = text("""
        SELECT 
            COALESCE((SELECT SUM(total_amount) FROM purchase_orders WHERE project_id = :id), 0) as total_po,
            COALESCE((SELECT SUM(amount_billed) FROM sales_invoices WHERE project_id = :id), 0) as total_sales,
            COALESCE((SELECT SUM(calculated_salary) FROM labor_timecards WHERE project_id = :id), 0) as total_labor
    """)
    
    fin_res = await db.execute(financial_query, {"id": project_id})
    totals = fin_res.fetchone()

    total_purchasing = Decimal(totals.total_po)
    total_sales = Decimal(totals.total_sales)
    total_labor = Decimal(totals.total_labor)
    allocated_budget = Decimal(project.allocated_budget)

    # Job Costing Core Math formulas
    net_profit = total_sales - (total_purchasing + total_labor)
    budget_remaining = allocated_budget - (total_purchasing + total_labor)

    return ProjectFinancialSummary(
        project_id=project.id,
        project_name=project.name,
        allocated_budget=allocated_budget,
        total_purchasing_costs=total_purchasing,
        total_labor_costs=total_labor,
        total_sales_billed=total_sales,
        net_profit=net_profit,
        budget_remaining=budget_remaining
    )
```
---## 4. Frontend React Core Interface Layout

This React baseline showcases how to orchestrate a global project-selection state context and leverage React Hooks to swap transactional data sets fluidly based on the selected project dropdown.
```jsx
// App.jsx
import { useState, createContext, useContext } from 'react';
import { useQuery, QueryClient, QueryClientProvider } from '@tanstack/react-query';
const ProjectContext = createContext(null);
const queryClient = new QueryClient();

function PurchasingModule() {
    const { selectedProjectId } = useContext(ProjectContext);
    return (
        <section>
            <h2>Material Procurement Log</h2>
            <p>Project ID: {selectedProjectId || 'None'}</p>
        </section>
    );
}

function DashboardHome() {
    const { selectedProjectId, setSelectedProjectId } = useContext(ProjectContext);
    const { data: snapshot, isLoading, error } = useQuery({
        queryKey: ['financialSnapshot', selectedProjectId],
        queryFn: async () => {
            const response = await fetch(`/api/v1/projects/${selectedProjectId}/financial-snapshot`);
            if (!response.ok) throw new Error('Failed to load project financials.');
            return response.json();
        },
        enabled: Boolean(selectedProjectId),
    });

    const formatMoney = (value) => Number(value ?? 0).toLocaleString(undefined, {
        style: 'currency',
        currency: 'USD',
    });

    return (
        <main>
            <h1>Construction Corporate ERP</h1>
            <label htmlFor="project-select">Project site</label>
            <select
                id="project-select"
                value={selectedProjectId}
                onChange={(event) => setSelectedProjectId(event.target.value)}
            >
                <option value="">Choose a project</option>
                <option value="1">Commercial Plaza Alpha</option>
                <option value="2">Highway Overpass Overhaul</option>
                <option value="3">Residential Hub Development</option>
            </select>

            {!selectedProjectId ? (
                <p>Select a project to view its financial summary.</p>
            ) : isLoading ? (
                <p>Loading financial summary...</p>
            ) : error ? (
                <p role="alert">{error.message}</p>
            ) : (
                <section aria-label="Project financial summary">
                    <p>Allocated budget: {formatMoney(snapshot.allocated_budget)}</p>
                    <p>Total billed: {formatMoney(snapshot.total_sales_billed)}</p>
                    <p>
                        Material and labor costs:{' '}
                        {formatMoney(Number(snapshot.total_purchasing_costs) + Number(snapshot.total_labor_costs))}
                    </p>
                    <p>Net profit: {formatMoney(snapshot.net_profit)}</p>
                </section>
            )}
            {selectedProjectId && <PurchasingModule />}
        </main>
    );
}

export default function App() {
    const [selectedProjectId, setSelectedProjectId] = useState('');
    return (
        <QueryClientProvider client={queryClient}>
            <ProjectContext.Provider value={{ selectedProjectId, setSelectedProjectId }}>
                <DashboardHome />
            </ProjectContext.Provider>
        </QueryClientProvider>
    );
}
```
------------------------------
## 5. Non-Functional, Security & Scale Guide for Developers
Developers must incorporate the following foundational security patterns when expanding this boilerplate document:

   1. Transactional Safety Protection (ACID): Financial transfers, material inventory shifts, or payroll approvals must execute using programmatic database transactions (BEGIN ... COMMIT). If an error is caught during processing, the mutation must execute a total ROLLBACK.
   2. Horizontal Token Boundaries (JWT Isolation): Do not solely pass user permissions via client states. When a site manager logs in, generate encrypted JSON Web Tokens embedding a security claim array identifying exactly which project_id scope parameters they are authenticated to inspect or mutate.
   3. Database Concurrency Connection Tuning: Because site workers may clock into cellular networks simultaneously at shifts' start, scale the FastAPI container deployment structure using multi-worker execution layers (e.g., Gunicorn running Uvicorn workers) integrated with database connection poolers (PgBouncer) to optimize incoming client execution pipelines.


<FollowUp>
When you are ready to expand on specific code implementation details, let me know:
* Do you want the **Pydantic schemas and database code** written out for the other modules (Sales and Labor/Timecards)?
* Do you need help setting up the **Docker configuration (`docker-compose`)** to spin up the local PostgreSQL database, FastAPI container, and React application automatically?
</FollowUp>


