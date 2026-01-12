# Address Validation Failure (Negative Flow)

## What this case changes
- `src/shipping.py`: validates every address field before creating a label and raises a `Missing address field` error when any field is blank.

## Modules indirectly affected (no direct edits)
- `src/order_service.py`, `src/returns.py`: shipping label creation can now fail earlier, changing order/return outcomes and audit timing.
- `src/audit.py`: may record fewer fulfillments because invalid addresses are rejected before label issuance.

## Expected behaviors to validate
- Orders/returns with empty `name`, `line1`, `city`, `region`, `postal_code`, or `country` fail with a clear `Missing address field: <field>` error.
- Valid addresses still produce labels and track in `_issued`.
- Unsupported shipping methods are still rejected after address validation.
- Existing labels remain queryable via `get_label`.

## How to replay this case
1. Start from a clean working tree.
2. Apply the patch:
   ```bash
   git apply tests/cases/negative_address_validation_case/negative_address_validation_case.patch
   ```
3. Run the workflow or targeted tests that create labels with missing fields to trigger failures.
4. To undo:
   ```bash
   git apply -R tests/cases/negative_address_validation_case/negative_address_validation_case.patch
   ```

## Notes
- Exercise both order fulfillment and returns flows with intentionally incomplete addresses to confirm the new guard rails.
