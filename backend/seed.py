"""
Seed script — populates the database with realistic pharmacy data.
Run from the backend/ directory:
    python seed.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from datetime import date, datetime, timedelta
import random

from app.core.database import SessionLocal, init_db
from app.models.medicine import Medicine
from app.models.batch import Batch
from app.models.sale import Sale
from app.models.stock_log import StockLog, ChangeType
from app.models.expiry_log import ExpiryLog, ExpiryAction

random.seed(42)

# ── Medicine catalogue ────────────────────────────────────────────────────────
MEDICINES = [
    # (name, generic_name, category, subcategory, unit, unit_size, manufacturer, supplier, selling_price, reorder_level, reorder_qty)
    ("Paracetamol 500mg", "Paracetamol", "Analgesic", "OTC", "Tablet", "500mg", "Accord Healthcare", "MedSupply Ltd", 0.05, 200, 1000),
    ("Amoxicillin 500mg", "Amoxicillin", "Antibiotic", "Prescription", "Capsule", "500mg", "Sandoz", "PharmaDirect", 0.30, 100, 500),
    ("Ibuprofen 400mg", "Ibuprofen", "Analgesic", "OTC", "Tablet", "400mg", "Reckitt", "MedSupply Ltd", 0.08, 150, 600),
    ("Metformin 500mg", "Metformin HCl", "Antidiabetic", "Prescription", "Tablet", "500mg", "Teva", "PharmaDirect", 0.12, 120, 500),
    ("Atorvastatin 20mg", "Atorvastatin", "Cardiovascular", "Prescription", "Tablet", "20mg", "Pfizer", "MedSupply Ltd", 0.45, 80, 300),
    ("Omeprazole 20mg", "Omeprazole", "Gastrointestinal", "OTC", "Capsule", "20mg", "AstraZeneca", "PharmaDirect", 0.25, 100, 400),
    ("Cetirizine 10mg", "Cetirizine HCl", "Antihistamine", "OTC", "Tablet", "10mg", "GSK", "MedSupply Ltd", 0.10, 150, 600),
    ("Salbutamol Inhaler", "Salbutamol", "Respiratory", "Prescription", "Inhaler", "100mcg/dose", "Allen & Hanburys", "PharmaDirect", 4.50, 30, 100),
    ("Lisinopril 10mg", "Lisinopril", "Cardiovascular", "Prescription", "Tablet", "10mg", "Teva", "MedSupply Ltd", 0.18, 80, 300),
    ("Fluoxetine 20mg", "Fluoxetine HCl", "Antidepressant", "Prescription", "Capsule", "20mg", "Eli Lilly", "PharmaDirect", 0.35, 60, 250),
    ("Amoxicillin 250mg/5ml Syrup", "Amoxicillin", "Antibiotic", "Prescription", "Bottle", "100ml", "Sandoz", "PharmaDirect", 3.20, 40, 150),
    ("Vitamin C 1000mg", "Ascorbic Acid", "Supplement", "OTC", "Tablet", "1000mg", "Bayer", "MedSupply Ltd", 0.15, 200, 800),
    ("Dextrose 5% IV", "Glucose", "IV Fluid", "Hospital", "Bottle", "500ml", "Baxter", "HospitalSupply", 1.80, 50, 200),
    ("Morphine 10mg/ml", "Morphine Sulphate", "Opioid Analgesic", "Controlled", "Vial", "1ml", "Macarthys", "ControlledMeds", 2.50, 20, 80),
    ("Metronidazole 400mg", "Metronidazole", "Antibiotic", "Prescription", "Tablet", "400mg", "Accord Healthcare", "MedSupply Ltd", 0.20, 100, 400),
    ("Aspirin 75mg", "Aspirin", "Cardiovascular", "OTC", "Tablet", "75mg", "Bayer", "MedSupply Ltd", 0.04, 200, 800),
    ("Lansoprazole 30mg", "Lansoprazole", "Gastrointestinal", "Prescription", "Capsule", "30mg", "Takeda", "PharmaDirect", 0.38, 80, 300),
    ("Amlodipine 5mg", "Amlodipine", "Cardiovascular", "Prescription", "Tablet", "5mg", "Pfizer", "MedSupply Ltd", 0.22, 80, 300),
    ("Prednisolone 5mg", "Prednisolone", "Corticosteroid", "Prescription", "Tablet", "5mg", "Actavis", "PharmaDirect", 0.15, 80, 350),
    ("Zinc Sulphate 20mg", "Zinc Sulphate", "Supplement", "OTC", "Tablet", "20mg", "Thornton & Ross", "MedSupply Ltd", 0.12, 120, 500),
]


def make_batch_number(med_name: str, idx: int) -> str:
    prefix = "".join(c for c in med_name if c.isalpha())[:4].upper()
    return f"{prefix}-{2024 + (idx % 2)}-{str(idx * 37 + 100).zfill(4)}"


def seed():
    init_db()
    db = SessionLocal()

    try:
        # Clear existing data
        for model in [Sale, StockLog, ExpiryLog, Batch, Medicine]:
            db.query(model).delete()
        db.commit()
        print("Cleared existing data.")

        today = date.today()
        medicines_db = []

        # ── Insert medicines ──────────────────────────────────────────────
        for row in MEDICINES:
            name, generic, cat, subcat, unit, unit_size, mfg, supplier, price, rl, rq = row
            m = Medicine(
                name=name,
                generic_name=generic,
                category=cat,
                subcategory=subcat,
                unit=unit,
                unit_size=unit_size,
                manufacturer=mfg,
                supplier=supplier,
                selling_price=price,
                reorder_level=rl,
                reorder_quantity=rq,
            )
            db.add(m)
            medicines_db.append(m)

        db.flush()
        print(f"Inserted {len(medicines_db)} medicines.")

        # ── Insert batches ────────────────────────────────────────────────
        batches_by_med = {}
        for i, m in enumerate(medicines_db):
            batches_by_med[m.id] = []
            # 2–3 batches per medicine with varying expiry dates
            for j in range(random.randint(2, 3)):
                purchase_offset = random.randint(30, 180)
                purchase_dt = today - timedelta(days=purchase_offset)

                # Mix of expiry scenarios for testing all alert tiers
                if j == 0 and i % 5 == 0:
                    expiry_dt = today - timedelta(days=random.randint(1, 10))   # expired
                elif j == 0 and i % 5 == 1:
                    expiry_dt = today + timedelta(days=random.randint(5, 28))   # critical
                elif j == 0 and i % 5 == 2:
                    expiry_dt = today + timedelta(days=random.randint(31, 58))  # warning
                elif j == 0 and i % 5 == 3:
                    expiry_dt = today + timedelta(days=random.randint(61, 88))  # watch
                else:
                    expiry_dt = today + timedelta(days=random.randint(180, 720))  # ok

                qty = random.randint(100, 600)
                qty_remaining = max(10, qty - random.randint(0, qty // 2))
                cost = round(m.selling_price * random.uniform(0.45, 0.70), 4) if m.selling_price else None

                b = Batch(
                    medicine_id=m.id,
                    batch_number=make_batch_number(m.name, i * 10 + j),
                    supplier_invoice=f"INV-{2024 + j}-{str(i * 10 + j).zfill(5)}",
                    supplier=m.supplier,
                    quantity_received=qty,
                    quantity_remaining=qty_remaining,
                    cost_price=cost,
                    purchase_date=purchase_dt,
                    manufacture_date=purchase_dt - timedelta(days=30),
                    expiry_date=expiry_dt,
                    is_active=True,
                )
                db.add(b)
                batches_by_med[m.id].append(b)

        db.flush()
        total_batches = sum(len(v) for v in batches_by_med.values())
        print(f"Inserted {total_batches} batches.")

        # ── Stock-in logs for all batches ─────────────────────────────────
        for med_id, blist in batches_by_med.items():
            running_stock = 0
            for b in blist:
                log = StockLog(
                    medicine_id=med_id,
                    batch_id=b.id,
                    change_type=ChangeType.STOCK_IN,
                    quantity=b.quantity_received,
                    stock_before=running_stock,
                    stock_after=running_stock + b.quantity_received,
                    reference=b.supplier_invoice,
                    log_date=datetime.combine(b.purchase_date, datetime.min.time()),
                    notes=f"Batch {b.batch_number} received",
                )
                running_stock += b.quantity_received
                db.add(log)

        db.flush()

        # ── Historical sales (180 days) ───────────────────────────────────
        sale_count = 0
        for m in medicines_db:
            med_batches = [b for b in batches_by_med[m.id] if b.expiry_date > today - timedelta(days=200)]
            if not med_batches:
                continue

            # Average daily demand: varies by medicine type
            base_demand = {
                "Analgesic": 15, "Antibiotic": 8, "Cardiovascular": 6,
                "Antidiabetic": 7, "Gastrointestinal": 10, "Antihistamine": 12,
                "Respiratory": 4, "Antidepressant": 3, "IV Fluid": 5,
                "Supplement": 20, "Corticosteroid": 5, "Opioid Analgesic": 1,
            }.get(m.category, 8)

            for day_offset in range(180, 0, -1):
                sale_date = today - timedelta(days=day_offset)

                # Seasonal variation: higher in winter months (Oct–Feb)
                month = sale_date.month
                seasonal = 1.4 if month in (10, 11, 12, 1, 2) else 1.0
                # Weekend dip
                dow_factor = 0.6 if sale_date.weekday() >= 5 else 1.0

                daily_qty = int(base_demand * seasonal * dow_factor * random.uniform(0.5, 1.8))
                if daily_qty <= 0:
                    continue

                # Pick a valid batch (simple round-robin, ignore FEFO for seed speed)
                b = random.choice(med_batches)

                sale = Sale(
                    medicine_id=m.id,
                    batch_id=b.id,
                    quantity=daily_qty,
                    unit_price=m.selling_price,
                    total_price=round((m.selling_price or 0) * daily_qty, 2),
                    is_prescription=m.subcategory == "Prescription",
                    served_by=random.choice(["Sarah M.", "John K.", "Aoife B.", "Cian D."]),
                    sale_date=datetime.combine(sale_date, datetime.min.time()).replace(
                        hour=random.randint(9, 18), minute=random.randint(0, 59)
                    ),
                )
                db.add(sale)
                sale_count += 1

        db.flush()
        print(f"Inserted {sale_count} historical sale records.")

        # ── Expiry log for already-expired batches ────────────────────────
        expiry_log_count = 0
        for med_id, blist in batches_by_med.items():
            for b in blist:
                if b.expiry_date < today and b.quantity_remaining > 0:
                    wasted = b.quantity_remaining
                    loss = round((b.cost_price or 0) * wasted, 2)
                    elog = ExpiryLog(
                        medicine_id=med_id,
                        batch_id=b.id,
                        expiry_date=b.expiry_date,
                        quantity_affected=wasted,
                        quantity_wasted=wasted,
                        estimated_loss=loss,
                        action=ExpiryAction.REMOVED,
                        action_date=today,
                        performed_by="System Seed",
                        notes="Auto-logged by seed script",
                    )
                    db.add(elog)
                    expiry_log_count += 1

        db.commit()
        print(f"Inserted {expiry_log_count} expiry log entries.")
        print("\n✓ Database seeded successfully.")

    except Exception as e:
        db.rollback()
        print(f"Error during seeding: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
