# Shipping/Pricing Case (Catalog + Shipping + Pricing cross-impact)

## What this case changes
- `src/catalog.py`: adds `is_hazardous` flag to products (alongside weight/fragile/category).
- `src/shipping.py`: shipping cost now depends on product weight, fragility, hazardous flag, and method; rejects unsupported methods.
- `src/pricing.py`: totals now use `ShippingService.quote`, so product attributes and promos affect shipping, tax base, and final totals.

## Modules indirectly affected (no direct edits)
- `src/order_service.py`: order total, fraud score, loyalty accrual/usage, audit events all shift because totals include new shipping logic.
- `src/returns.py`: refund amounts and tax base change via the updated pricing/shipping; bad shipping methods can now block returns.
- `src/fraud.py`: risk decisions change because `order_total` now reflects weight/fragile/hazardous shipping costs.
- `src/loyalty.py`: points earned/applied change with the new totals.
- `src/tax.py`: tax amounts change because taxable base includes the new shipping calculation.

## Expected behaviors to validate
- Heavy/fragile/hazardous products incur extra shipping; totals/tax increase accordingly.
- Free-shipping promos zero out shipping; tax and fraud risk drop; totals change.
- Unsupported shipping method raises an error and blocks order/return flows.
- Order flow: insufficient stock, loyalty failure, fraud block/review, payment failure, fulfilled with label and points — all using new totals.
- Return flow: invalid quantity rejected; refund uses updated pricing; shipping label issued; loyalty clawback applied.

## How to replay this case
1. Start from a clean working tree (e.g., `git status` shows no changes). This is your baseline “snapshot.”
2. Apply the patch:
   ```bash
   git apply tests/cases/shipping_pricing_case/shipping_pricing_case.patch
   ```
3. Inspect changes (`git diff`) and run the workflow script to generate LLM impact/tests.
4. To undo the case (restore baseline):
   ```bash
   git apply -R tests/cases/shipping_pricing_case/shipping_pricing_case.patch
   ```

## Notes
- Patch assumes the current HEAD versions of `src/catalog.py`, `src/shipping.py`, `src/pricing.py` as the baseline. If you change those files further, regenerate the patch.
- LLM prompt files already expect to surface cross-file impacts; no prompt edit required for this case.
