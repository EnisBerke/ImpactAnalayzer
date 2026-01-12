# Bulk Discounts and Shipping Surcharges (Complex)

## What this case changes
- `src/pricing.py`: introduces tiered bulk discounts (5/10/20+ units) and adds shipping surcharges for large orders while still honoring free-shipping promos.

## Modules indirectly affected (no direct edits)
- `src/tax.py`: tax base changes because discounts and surcharges alter taxable amounts.
- `src/fraud.py`: higher basket sizes can alter fraud scores due to larger order totals even with discounts.
- `src/loyalty.py`: points accrued shift with the new totals.

## Expected behaviors to validate
- Quantities 5-9 get a 7% bulk discount, 10-19 get 12%, and 20+ get 15% before coupons and category discounts.
- Shipping adds a $3 surcharge at 10-19 units and $6 at 20+ (unless a free-shipping promo is applied).
- Coupon and category discounts stack with the bulk discount.
- Fraud and loyalty calculations reflect the adjusted totals; tax uses the discounted subtotal plus surcharged shipping.
- Orders below 5 units behave exactly as before.

## How to replay this case
1. Start from a clean working tree.
2. Apply the patch:
   ```bash
   git apply tests/cases/complex_bulk_discount_case/complex_bulk_discount_case.patch
   ```
3. Run pricing calculations for quantities 1, 5, 10, and 20 to confirm each tier and shipping surcharge.
4. To undo:
   ```bash
   git apply -R tests/cases/complex_bulk_discount_case/complex_bulk_discount_case.patch
   ```

## Notes
- Consider edge checks with free-shipping coupons to verify surcharges are also waived.
