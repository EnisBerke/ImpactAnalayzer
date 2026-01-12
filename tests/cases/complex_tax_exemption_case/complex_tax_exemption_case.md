# Tax-Exempt Product and Service Pricing (Complex)

## What this case changes
- `src/catalog.py`: adds a tax-exempt `support-plan` SKU and a `is_tax_exempt` flag on products.
- `src/tax.py`: tax calculator accepts `tax_exempt` to return zero tax and rate when applicable.
- `src/pricing.py`: passes the product tax-exempt flag into tax calculation so totals skip tax for exempt SKUs.

## Modules indirectly affected (no direct edits)
- `src/returns.py`: refunds inherit the zero-tax behavior for tax-exempt SKUs.
- `src/fraud.py`, `src/loyalty.py`: order totals change for exempt products, affecting risk scores and points accrual.
- `src/shipping.py`: shipping may still run for the service SKU, but totals/tax no longer include it.

## Expected behaviors to validate
- Orders for `support-plan` show zero tax with `TaxBreakdown.rate=0` and `amount=0`, regardless of region.
- Non-exempt products continue to tax normally using existing regional/category rates.
- Mixed scenarios: applying coupons or loyalty credits to exempt SKUs still produces zero tax; fraud scoring uses the lower total.
- Returns/refunds for tax-exempt products maintain zero tax in the refund breakdown.

## How to replay this case
1. Start from a clean working tree.
2. Apply the patch:
   ```bash
   git apply tests/cases/complex_tax_exemption_case/complex_tax_exemption_case.patch
   ```
3. Run pricing/return workflows against `support-plan` and a taxable SKU to compare behavior.
4. To undo:
   ```bash
   git apply -R tests/cases/complex_tax_exemption_case/complex_tax_exemption_case.patch
   ```

## Notes
- The service SKU ships with `weight_kg=0`; consider asserting that shipping labels are optional in your tests even though the patch leaves shipping unchanged.
