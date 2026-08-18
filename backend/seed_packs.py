"""
Seed script for pack instances — creates realistic pack-level data.
Run from the backend/ directory:
    python seed_packs.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from datetime import date, timedelta
import random

from app.core.database import SessionLocal, init_db
from app.models.medicine import Medicine
from app.models.pack_instance import PackInstance, PackStatus

random.seed(99)

init_db()
db = SessionLocal()

# Clear existing pack instances
db.query(PackInstance).delete()
db.commit()

today = date.today()
medicines = db.query(Medicine).all()

pack_count = 0
for med in medicines:
    # 3-5 packs per medicine with varied states
    num_packs = random.randint(3, 5)
    is_cd = med.category == "Opioid Analgesic"  # Morphine is controlled

    for j in range(num_packs):
        purchase_offset = random.randint(10, 120)
        purchase_dt = today - timedelta(days=purchase_offset)
        qty_received = random.choice([28, 50, 56, 100, 200, 500])

        # Create varied expiry scenarios
        if j == 0 and med.id % 4 == 0:
            # Expired pack (needs write-off)
            expiry = today - timedelta(days=random.randint(1, 15))
            qty_remaining = random.randint(5, qty_received // 2)
            status = PackStatus.OPEN
            date_opened = purchase_dt + timedelta(days=random.randint(1, 10))
        elif j == 0 and med.id % 4 == 1:
            # Critical expiry (< 30d)
            expiry = today + timedelta(days=random.randint(5, 28))
            qty_remaining = random.randint(10, qty_received // 2)
            status = PackStatus.OPEN
            date_opened = purchase_dt + timedelta(days=random.randint(1, 10))
        elif j == 1:
            # Open pack with good expiry
            expiry = today + timedelta(days=random.randint(90, 365))
            qty_remaining = random.randint(1, qty_received - 1)
            status = PackStatus.OPEN
            date_opened = today - timedelta(days=random.randint(1, 30))
        elif j == 2 and random.random() < 0.3:
            # Empty pack
            expiry = today + timedelta(days=random.randint(30, 200))
            qty_remaining = 0
            status = PackStatus.EMPTY
            date_opened = purchase_dt + timedelta(days=5)
        else:
            # Sealed pack
            expiry = today + timedelta(days=random.randint(120, 730))
            qty_remaining = qty_received
            status = PackStatus.SEALED
            date_opened = None

        # Cost: roughly 40-70% of selling price
        unit_cost = None
        if med.selling_price:
            unit_cost = round(med.selling_price * random.uniform(0.4, 0.7), 4)

        batch_num = f"PK-{med.name[:3].upper()}-{2024 + (j % 2)}-{str(med.id * 10 + j).zfill(4)}"

        pack = PackInstance(
            medicine_id=med.id,
            batch_number=batch_num,
            lot_number=f"LOT-{random.randint(1000, 9999)}",
            expiry_date=expiry,
            quantity_received=qty_received,
            quantity_remaining=qty_remaining,
            unit_cost=unit_cost,
            status=status,
            date_opened=date_opened,
            is_controlled_drug=is_cd,
            supplier_invoice=f"INV-PK-{2026}-{str(med.id * 10 + j).zfill(5)}",
        )
        db.add(pack)
        pack_count += 1

db.commit()
db.close()

print(f"Seeded {pack_count} pack instances across {len(medicines)} medicines.")
print("Includes: expired packs, critical-expiry packs, open/sealed/empty mix, controlled drugs.")
