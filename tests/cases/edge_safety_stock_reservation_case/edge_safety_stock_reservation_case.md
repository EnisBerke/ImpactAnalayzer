# Safety Stock Reservation Edge Case

## What this case changes
- `src/order_service.py`: uses `reserve_with_buffer` when `safety_stock` is set, returns a distinct reason when the buffer cannot be preserved, and rolls reservations back on fraud or payment failure.

## Modules indirectly affected (no direct edits)
- `src/inventory.py`: reservations/rollbacks now change stock counts earlier in the flow.
- `src/audit.py`, `src/fraud.py`, `src/loyalty.py`: order outcomes and audit entries shift because fraud/payment outcomes now restore or retain inventory differently.

## Expected behaviors to validate
- Orders created with `safety_stock > 0` reserve inventory up front; insufficient stock with buffer returns `insufficient_stock` and reason `not_enough_inventory_with_buffer`.
- Fraud blocks/manual reviews restore the reserved quantity so available stock is unchanged.
- Payment failures restore the reserved quantity and keep the failure audit entry.
- Successful orders that used the buffer do **not** remove inventory a second time.
- Orders with `safety_stock=0` still behave as before.

## How to replay this case
1. Start from a clean working tree.
2. Apply the patch:
   ```bash
   git apply tests/cases/edge_safety_stock_reservation_case/edge_safety_stock_reservation_case.patch
   ```
3. Inspect the diff and run your workflow as needed.
4. To undo:
   ```bash
   git apply -R tests/cases/edge_safety_stock_reservation_case/edge_safety_stock_reservation_case.patch
   ```

## Notes
- Exercise both paths by instantiating `OrderService` with `safety_stock` set and unset. Reservations only engage when `safety_stock` is positive.
