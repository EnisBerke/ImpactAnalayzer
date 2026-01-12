# Loyalty Clawback on Failed Orders (Negative Flow)

## What this case changes
- `src/loyalty.py`: adds `restore` to put points back after a failed redemption.
- `src/order_service.py`: tracks redeemed points and restores them when fraud blocks, manual reviews, or payment failures happen after redemption.

## Modules indirectly affected (no direct edits)
- `src/audit.py`: failure events now occur alongside balance restoration.
- `src/fraud.py`, `src/inventory.py`: fraud/payment branches now add a loyalty-side side effect without changing inventory behavior.

## Expected behaviors to validate
- Loyalty redemption succeeds, but if fraud blocks or flags the order, the redeemed points return to the account.
- Payment failures after redemption restore points and still log `payment_failed`.
- Successful orders accrue points as before; only failure paths invoke `restore`.
- Orders without loyalty redemption are untouched by the new logic.

## How to replay this case
1. Start from a clean working tree.
2. Apply the patch:
   ```bash
   git apply tests/cases/negative_loyalty_clawback_case/negative_loyalty_clawback_case.patch
   ```
3. Run your workflow or targeted tests that trigger fraud blocks, manual review, and payment failures.
4. To undo:
   ```bash
   git apply -R tests/cases/negative_loyalty_clawback_case/negative_loyalty_clawback_case.patch
   ```

## Notes
- Exercise both `blocked` and `manual_review` risk outcomes plus a simulated payment failure to verify points are restored in each path.
