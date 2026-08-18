# Requirements Document

## Introduction

This feature extends the pharmacy stock management system to support batch-level tracking of physical pack instances (rather than aggregate product quantities), enabling accurate partial-pack usage, FEFO (First-Expired-First-Out) dispensing, and a formal write-off process for damaged, expired, or lost stock. The system integrates alongside TouchStore Rx and feeds accurate on-hand quantities into the existing smart prediction and expiry tracking modules.

## Glossary

- **Pack_Instance**: A record representing one physical pack or box of a medicine, linked to a specific batch, with its own quantity remaining and lifecycle status.
- **PackStatus**: The lifecycle state of a Pack_Instance. Valid values are `sealed` (unopened), `open` (partially used), and `empty` (fully consumed).
- **FEFO**: First-Expired-First-Out — the dispensing strategy of consuming stock with the earliest expiry date first, prioritising already-opened packs before sealed packs.
- **Write_Off**: A formal transaction that removes stock from on-hand quantity due to damage, expiry, loss, or other non-sale reason, distinct from a dispense transaction.
- **Reason_Code**: A controlled vocabulary value categorising the cause of a write-off.
- **Controlled_Drug**: A medicine flagged in the system as subject to PSI/HPRA controlled drugs register requirements, requiring countersigned write-offs.
- **Countersign**: A second, distinct user's approval of a controlled drug write-off transaction before it is finalised.
- **Prediction_Module**: The existing smart prediction component that calculates expected future usage and reorder points for medicines.
- **Dispense_Transaction**: A transaction recording units drawn from Pack_Instances in response to a patient or prescription request.
- **Reconciliation_Adjustment**: An auditable correction transaction applied when the system's on-hand quantity disagrees with TouchStore Rx beyond a configurable tolerance.
- **TouchStore_Rx**: The external pharmacy dispensing system whose records are imported to trigger FEFO deduction logic.
- **Alert_Window**: A configurable number of days before expiry at which a Pack_Instance appears on the expiry alert list.
- **Unit_Cost**: The per-unit purchase price for a specific batch, sourced from the delivery invoice.

---

## Requirements

### Requirement 1: Pack Instance Tracking

**User Story:** As a pharmacy stock manager, I want each physical pack or box tracked as its own record, so that I know exactly how many units remain in opened packs and which batch and expiry each unit belongs to.

#### Acceptance Criteria

1. WHEN a new delivery of stock is received, THE Stock_Manager SHALL create one Pack_Instance record per physical pack, storing the product ID, batch/lot number, expiry date, and a received quantity of at least 1 unit.
2. IF a Pack_Instance is submitted with a missing product ID, missing batch/lot number, missing expiry date, or a received quantity less than 1, THEN THE System SHALL reject the record and return an error message indicating which fields are invalid, leaving no Pack_Instance record created.
3. WHEN a Pack_Instance is created, THE System SHALL set its status to `sealed`.
4. WHEN the first unit is removed from a `sealed` Pack_Instance and the quantity remaining after removal is greater than zero, THE System SHALL set its status to `open` and record the date on which the pack was opened.
5. WHEN one or more units are removed from a Pack_Instance and the quantity remaining reaches zero, THE System SHALL set its status to `empty`.
6. IF a unit removal is requested on a Pack_Instance with status `empty`, THEN THE System SHALL reject the request and return an error message indicating the pack is empty, leaving the Pack_Instance record unchanged.
7. WHEN a user requests the on-hand quantity for a product, THE System SHALL return the sum of quantity remaining across all Pack_Instances with status `sealed` or `open` for that product, excluding any Pack_Instance whose expiry date is earlier than the current date.
8. IF a product has multiple Pack_Instances with different expiry dates, THEN THE System SHALL display each Pack_Instance's expiry date separately rather than a single aggregate expiry date.

---

### Requirement 2: FEFO-Based Dispensing

**User Story:** As a pharmacy staff member dispensing medication, I want the system to automatically select which pack to draw from, so that opened packs are used up before new ones are opened and short-dated stock is used first.

#### Acceptance Criteria

1. WHEN a Dispense_Transaction is recorded for a product, THE System SHALL first draw from any Pack_Instance with status `open` for that product.
2. IF more than one Pack_Instance with status `open` exists for a product, THEN THE System SHALL draw from the Pack_Instance with the earliest expiry date; IF two or more `open` Pack_Instances share the same earliest expiry date, THEN THE System SHALL draw from the one with the lowest Pack_Instance ID.
3. IF no Pack_Instance with status `open` exists for a product, THEN THE System SHALL select the `sealed` Pack_Instance with the earliest expiry date and set its status to `open`.
4. WHEN the dispense quantity exceeds the quantity remaining in the currently selected Pack_Instance, THE System SHALL deduct the remainder from the next eligible Pack_Instance according to the same FEFO rule, repeating this cascade across as many Pack_Instances as necessary until the full dispense quantity is fulfilled.
5. WHEN a Dispense_Transaction completes, THE System SHALL update the quantity remaining on each affected Pack_Instance and log the transaction recording the Pack_Instance ID and the quantity deducted from each Pack_Instance used.
6. WHEN the quantity remaining on a Pack_Instance reaches zero as a result of a Dispense_Transaction, THE System SHALL set that Pack_Instance's status to `empty`.
7. IF the total quantity available across all `open` and `sealed` Pack_Instances for a product is less than the requested dispense quantity, THEN THE System SHALL reject the Dispense_Transaction and return an error indicating insufficient stock without modifying any Pack_Instance quantity or status.

---

### Requirement 3: Write-Off Recording

**User Story:** As a pharmacy stock manager, I want to record stock write-offs as a distinct transaction type, so that damaged, expired, or lost stock is removed from on-hand quantity without being misread as a sale by the prediction engine.

#### Acceptance Criteria

1. WHEN a user initiates a Write_Off, THE System SHALL require selection of a specific Pack_Instance, a quantity between 1 and the Pack_Instance's current quantity remaining (inclusive), and a Reason_Code before the transaction can be submitted.
2. THE System SHALL support the following Reason_Codes: `damaged`, `expired`, `spillage_contamination`, `short_dated_return_to_supplier`, `dispensing_error`, `theft_loss`, `recall`.
3. IF a Write_Off is submitted with a Reason_Code that is not in the supported list, THEN THE System SHALL reject the transaction and return an error identifying the invalid Reason_Code, leaving the Pack_Instance unchanged.
4. WHEN a Write_Off is submitted, THE System SHALL record the user ID, timestamp, Reason_Code, and optional free-text notes of no more than 500 characters alongside the transaction.
5. WHEN a Write_Off is submitted, THE System SHALL deduct the written-off quantity from the Pack_Instance's quantity remaining and update the Pack_Instance's status according to the rules in Requirement 1.
6. WHEN a Write_Off is recorded, THE System SHALL store it under a transaction type of `write_off`, such that a query filtered to `write_off` returns only write-off records and excludes Dispense_Transactions, and a query filtered to `dispense` returns only Dispense_Transactions and excludes write-off records.
7. IF a Write_Off quantity would reduce a Pack_Instance's quantity remaining below zero, THEN THE System SHALL reject the transaction, return an error indicating the quantity exceeds the available stock, and leave the Pack_Instance's quantity remaining unchanged.

---

### Requirement 4: Controlled Drug Write-Off Countersign

**User Story:** As a pharmacy superintendent, I want controlled drug write-offs to require a second sign-off, so that the system meets PSI/HPRA controlled drugs register requirements.

#### Acceptance Criteria

1. IF a Write_Off is initiated for a product flagged as a Controlled_Drug, THEN THE System SHALL require a Countersign from a second, distinct user who holds a Pharmacist or Superintendent role before the Write_Off is finalised.
2. WHILE a Controlled_Drug Write_Off is pending Countersign, THE System SHALL prevent the initiating user from providing the second approval.
3. WHEN a Controlled_Drug Write_Off is countersigned, THE System SHALL record the user ID and timestamp of both the initiating user and the countersigning user against the transaction.
4. IF a Controlled_Drug Write_Off has not been countersigned within a configurable time window, defaulting to 24 hours and configurable between 1 and 168 hours, THEN THE System SHALL include it on the outstanding-countersign review report.
5. WHEN a user with a Pharmacist or Superintendent role requests the outstanding-countersign review report, THE System SHALL display all Controlled_Drug Write_Offs that remain pending Countersign beyond their configured time window, including the initiating user ID, product name, quantity, and elapsed time since initiation.

---

### Requirement 5: Write-Off Cost Reporting

**User Story:** As a pharmacy manager, I want to see the monetary value of write-offs, so that I can report on stock loss to management.

#### Acceptance Criteria

1. WHEN a Pack_Instance is created, THE System SHALL store a Unit_Cost for that batch sourced from the delivery invoice where available.
2. WHEN a Write_Off transaction is recorded, THE System SHALL calculate the transaction value as the written-off quantity multiplied by the Pack_Instance's Unit_Cost and persist that calculated value on the Write_Off record.
3. WHEN a user requests a write-off report for a given date range, THE System SHALL return the total write-off value grouped by Reason_Code and by product for all Write_Offs whose timestamps fall within that range.
4. IF a Pack_Instance has no recorded Unit_Cost, THEN THE System SHALL record the Write_Off, set the transaction value field to null, and include a flag of `cost_unavailable` on that record in all report output rather than substituting zero.
5. WHEN a write-off report is requested, THE System SHALL include a summary row for each group showing the count of Write_Offs flagged `cost_unavailable` separately from those with a calculable value.

---

### Requirement 6: Prediction Engine Integration

**User Story:** As a pharmacy stock manager, I want write-offs excluded from demand forecasting, so that stock predictions reflect actual patient demand rather than losses.

#### Acceptance Criteria

1. WHEN the Prediction_Module calculates expected future usage, THE System SHALL include only Dispense_Transactions, not Write_Off transactions, as the demand signal; a query to the Prediction_Module SHALL return identical forecast values whether or not Write_Off records exist for the same product and period.
2. WHEN the Prediction_Module calculates on-hand quantity for reorder point checks, THE System SHALL use the sum of quantity remaining across `sealed` and `open` Pack_Instances per Requirement 1.7, reflecting all write-off deductions already applied to those quantities.
3. WHEN a Write_Off is recorded, THE System SHALL make the write-off volume available to the Prediction_Module as a separate `loss_signal` field on the product's data record, without including that volume in the demand forecast calculation; the Prediction_Module SHALL use this signal only for flagging products whose total write-off volume in a rolling 30-day window exceeds a configurable loss-rate threshold.

---

### Requirement 7: Expiry Tracking at Pack Level

**User Story:** As a pharmacy staff member, I want to be alerted about individual packs nearing expiry, so that I can prioritise their use or return them before they become a write-off.

#### Acceptance Criteria

1. WHEN a Pack_Instance's expiry date falls within the configurable Alert_Window, THE System SHALL include the Pack_Instance on the expiry alert list, displaying the Pack_Instance ID, product name, batch/lot number, expiry date, quantity remaining, and current status.
2. WHILE a Pack_Instance has status `open` and its expiry date falls within the Alert_Window, THE System SHALL rank it above `sealed` Pack_Instances of the same product with later expiry dates on the expiry alert list.
3. IF a Pack_Instance with a quantity remaining greater than zero has an expiry date equal to or earlier than the current date, THEN THE System SHALL display a prompt on the expiry alert list indicating that a Write_Off with Reason_Code `expired` is required for that Pack_Instance, and SHALL exclude that Pack_Instance from the on-hand quantity calculation per Requirement 1.7.

---

### Requirement 8: TouchStore Rx Integration

**User Story:** As a pharmacy IT administrator, I want this system to reconcile with TouchStore Rx dispensing records, so that stock levels stay consistent between both systems.

#### Acceptance Criteria

1. WHEN a dispense event is received or imported from TouchStore_Rx, THE System SHALL create a Dispense_Transaction record and trigger the FEFO deduction logic described in Requirement 2 using the product ID and quantity from the imported record.
2. IF the imported TouchStore_Rx record contains an unrecognised product ID, THEN THE System SHALL reject the import, log the unrecognised record with its raw content, and return an error without creating a Dispense_Transaction or modifying any Pack_Instance.
3. WHEN the System calculates on-hand quantity for a product per Requirement 1.7, IF the resulting quantity differs from the quantity reported by TouchStore_Rx for the same product by more than a configurable tolerance (defaulting to zero units and configurable from 0 to 99 units), THEN THE System SHALL flag the product for manual reconciliation.
4. WHEN a manual reconciliation adjustment is made, THE System SHALL require a free-text reason of at least 1 character, record the adjusting user ID, timestamp, and the before and after on-hand quantities, and store the record as a Reconciliation_Adjustment transaction that is distinct from both Dispense_Transactions and Write_Off transactions.
