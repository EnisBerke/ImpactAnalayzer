# System Architecture - Module Dependencies & Logical Connections

## Module Inventory

### Orchestration Layer
- `order_service.py` - Order placement workflow coordinator
- `returns.py` - Return/refund workflow coordinator

### Domain Services
- `pricing.py` - Price calculation engine
- `inventory.py` - Stock management
- `fraud.py` - Risk assessment
- `loyalty.py` - Customer points management
- `shipping.py` - Label generation
- `tax.py` - Tax calculation
- `promotions.py` - Discount logic
- `catalog.py` - Product information

### Infrastructure
- `audit.py` - Event logging
- `email_notifications.py` - Customer communications

---

## Direct Code Dependencies

### order_service.py
**Imports and uses:**
- `inventory.InventoryRepository` - calls `has_enough()`, `reserve_with_buffer()`
- `pricing.PricingService` - calls `calculate()`
- `shipping.ShippingService` - calls `create_label()`
- `fraud.FraudService` - calls `score()`
- `loyalty.LoyaltyService` - calls `redeem()`, `accrue_points()`
- `audit.AuditLogger` - calls `log()`
- `PaymentGateway` (Protocol) - calls `charge()`

**Data types used:**
- `Order` (dataclass from order_service)
- `PricingBreakdown` (from pricing)
- `ShippingLabel` (from shipping)
- `FraudAssessment` (from fraud)

### returns.py
**Imports and uses:**
- `inventory.InventoryRepository` - calls `add_item()`
- `pricing.PricingService` - calls `calculate_refund()`
- `shipping.ShippingService` - calls `create_label()`
- `loyalty.LoyaltyService` - calls `clawback()`
- `audit.AuditLogger` - calls `log()`
- `RefundGateway` (Protocol) - calls `refund()`

**Data types used:**
- `ReturnRequest` (dataclass from returns)
- `PricingBreakdown` (from pricing)
- `ShippingLabel` (from shipping)

### pricing.py
**Imports and uses:**
- `catalog.CatalogService` - calls `get()`
- `promotions.PromotionService` - calls `apply_coupon()`
- `tax.TaxService` - calls `calculate()`

**Data types used:**
- `Product` (from catalog)
- `PromotionResult` (from promotions)
- `TaxBreakdown` (from tax)
- `PricingBreakdown` (dataclass from pricing)

### promotions.py
**Imports and uses:**
- `catalog.CatalogService` - calls `get()`

**Data types used:**
- `Product` (from catalog)
- `PromotionResult` (dataclass from promotions)

### inventory.py
**No imports from other modules**
- Self-contained with internal dictionary state

### shipping.py
**No imports from other modules**
- Self-contained with dataclasses `Address`, `ShippingLabel`

### fraud.py
**No imports from other modules**
- Self-contained with dataclass `FraudAssessment`

### loyalty.py
**No imports from other modules**
- Self-contained with internal dictionary state

### tax.py
**No imports from other modules**
- Self-contained with dataclass `TaxBreakdown`

### catalog.py
**No imports from other modules**
- Self-contained with dataclass `Product`

### audit.py
**No imports from other modules**
- Self-contained with dataclass `AuditEntry`

### email_notifications.py
**No imports from other modules**
- Utility functions only

---

## Logical Dependencies (Business Logic Connections)

### Order Flow Logical Chain
```
order_service.place_order()
  → Must check inventory before pricing (business rule: don't price unavailable items)
  → Must price before fraud check (business rule: fraud scoring uses total amount)
  → Must fraud check before payment (business rule: don't charge blocked orders)
  → Must payment before inventory reservation (business rule: don't hold stock for unpaid orders)
  → Must reserve inventory before shipping (business rule: don't ship unavailable items)
  → Must ship before loyalty points (business rule: points only for fulfilled orders)
```

### Return Flow Logical Chain
```
returns.process()
  → Must calculate refund amount (based on original pricing logic)
  → Must process refund before inventory restore (business rule: don't restock until paid)
  → Must inventory restore before loyalty clawback (business rule: clawback for actual returns)
  → Must generate return shipping label (business rule: customer needs label to ship back)
```

### Pricing Calculation Logical Chain
```
pricing.calculate()
  → Must get product price from catalog (base price)
  → Must apply promotions to subtotal (discount calculation order matters)
  → Must add shipping cost before tax (tax applies to shipping in some regions)
  → Must calculate tax on adjusted total (tax = f(subtotal - discount + shipping))
  → Must apply loyalty credit last (post-tax deduction)
```

### Inventory Safety Stock Logic
```
inventory.reserve_with_buffer()
  → Logical constraint: physical_stock >= requested_quantity + safety_buffer
  → Business rule: Never allow stock to drop below safety threshold
  → Impacts: order_service must handle "insufficient stock" even if physical stock exists
```

### Fraud Scoring Logic
```
fraud.score()
  → Uses pricing.total (calculated before fraud check)
  → Uses order.region (from order data)
  → Impacts: order_service decisions (approve/block/review)
  → No code dependency but logically requires pricing to run first
```

### Loyalty Points Logic
```
loyalty.accrue_points()
  → Logical dependency: Must know final order total (from pricing)
  → Business rule: Points = floor(total_amount) 
  → Timing constraint: Must happen AFTER payment success
  → Not in code imports but requires pricing.total value

loyalty.redeem()
  → Logical dependency: Affects pricing calculation
  → Business rule: Reduces final total by points/100
  → Timing constraint: Must happen BEFORE payment
  → pricing.calculate() accepts loyalty_credit parameter (data coupling)
```

### Tax Calculation Logic
```
tax.calculate()
  → Logically depends on: subtotal, discount, shipping (all from pricing context)
  → Business rule: Tax applies to (subtotal - discount + shipping)
  → Special case: Hardware category has different rate
  → No direct code import but requires catalog.category information
```

### Promotion Application Logic
```
promotions.apply_coupon()
  → Logical dependency: Needs product.category (from catalog)
  → Business rule: Some coupons (BOGO) require quantity >= 2
  → Logical constraint: Free shipping promotions affect shipping.cost
  → No direct code dependency on shipping but logically coupled
```

### Shipping Cost Logic
```
shipping.create_label()
  → Logical dependency: Shipping method affects pricing.shipping_cost
  → Business rule: Express = $12, Standard = $5
  → No code import between shipping and pricing but data coupling via method parameter
```

### Audit Logging Logic
```
audit.log()
  → Logical dependency: Must capture state AFTER operations complete
  → Business rule: Log order_fulfilled only after ALL steps succeed
  → No code dependency but temporal coupling with all operations
```

---

## Data Flow Connections (Shared Data Structures)

### Order Object
```
Created by: order_service
Contains: items (SKU + quantity), account_id, region, shipping_method
Used by:
  - inventory (reads SKU, quantity)
  - pricing (reads items, region, shipping_method)
  - fraud (reads region, total)
  - shipping (reads items, shipping_method)
  - loyalty (reads account_id, total)
  - audit (reads all fields for logging)
```

### PricingBreakdown Object
```
Created by: pricing.calculate()
Contains: subtotal, discount, tax, shipping, total
Used by:
  - order_service (reads total for payment)
  - fraud (reads total for scoring)
  - loyalty (reads total for points)
  - audit (reads all for logging)
```

### Product Object
```
Created by: catalog.get()
Contains: sku, name, price, weight_kg, category, is_fragile
Used by:
  - pricing (reads price, category)
  - promotions (reads category for discounts)
  - shipping (reads weight_kg, is_fragile for label)
```

### FraudAssessment Object
```
Created by: fraud.score()
Contains: score, status (approved/blocked/review), reason
Used by:
  - order_service (reads status to decide if continue or abort)
  - audit (reads all for fraud logging)
```

### ShippingLabel Object
```
Created by: shipping.create_label()
Contains: order_id, tracking_number, carrier, address, method
Used by:
  - order_service (stores reference)
  - returns (uses for return label generation)
```

### TaxBreakdown Object
```
Created by: tax.calculate()
Contains: rate, amount, region
Used by:
  - pricing (reads amount to add to total)
```

### PromotionResult Object
```
Created by: promotions.apply_coupon()
Contains: discount_amount, free_shipping, applied_coupon
Used by:
  - pricing (reads discount_amount, free_shipping)
```

---

## Implicit Logical Dependencies

### inventory ↔ pricing
- **No direct code import**
- **Logical connection:** Pricing needs to know if items are in stock (but doesn't call inventory)
- **Coupling point:** order_service coordinates both
- **Impact:** Changing inventory availability logic affects which orders get priced

### fraud ↔ inventory
- **No direct code import**
- **Logical connection:** High fraud risk should prevent inventory reservation
- **Coupling point:** order_service checks fraud before inventory
- **Impact:** Changing fraud thresholds affects inventory turnover

### loyalty ↔ pricing
- **No direct code import**
- **Logical connection:** Loyalty credit affects final price
- **Coupling point:** pricing.calculate() accepts loyalty_credit parameter
- **Impact:** Changing loyalty redemption rate affects pricing totals

### promotions ↔ shipping
- **No direct code import**
- **Logical connection:** FREESHIP coupon affects shipping cost
- **Coupling point:** pricing.calculate() reads PromotionResult.free_shipping
- **Impact:** Changing shipping costs affects promotion value

### tax ↔ catalog
- **No direct code import**
- **Logical connection:** Hardware category has special tax rate
- **Coupling point:** tax.calculate() uses category from pricing context
- **Impact:** Adding new categories may require tax rule updates

### audit ↔ all modules
- **Code import:** All orchestrators import audit
- **Logical connection:** Audit must log after operations complete
- **Coupling point:** Temporal dependency (log AFTER success/failure)
- **Impact:** Changing audit schema affects all calling modules

### shipping ↔ inventory
- **No direct code import**
- **Logical connection:** Can't ship what's not in stock
- **Coupling point:** order_service ensures inventory before shipping
- **Impact:** Changing inventory reservation affects shipping label generation timing

---

## Change Impact Propagation Map

### If catalog.py changes (e.g., add new field to Product):
```
catalog.py
  ↓ (direct import)
pricing.py → May need to read new field
  ↓ (direct import)
promotions.py → May need new field for discount rules
  ↓ (logical)
order_service.py → May need to pass new field through
returns.py → May need new field for refund calculation
```

### If pricing.py changes (e.g., modify total calculation formula):
```
pricing.py
  ↓ (direct import)
order_service.py → Reads PricingBreakdown.total
  ↓ (logical dependency)
fraud.py → Scoring uses total amount
loyalty.py → Points based on total
audit.py → Logs total amount
  ↓ (business logic)
returns.py → Refund calculation must match original pricing
```

### If inventory.py changes (e.g., modify safety_buffer logic):
```
inventory.py
  ↓ (direct import)
order_service.py → Calls reserve_with_buffer()
  ↓ (logical impact)
pricing.py → More/fewer orders will be priced
fraud.py → More/fewer orders will be fraud-checked
shipping.py → More/fewer labels generated
  ↓ (business impact)
returns.py → More/fewer items available for return
```

### If fraud.py changes (e.g., adjust scoring threshold):
```
fraud.py
  ↓ (direct import)
order_service.py → Reads FraudAssessment.status
  ↓ (logical impact)
inventory.py → More/fewer reservations
pricing.py → More/fewer completed transactions
loyalty.py → More/fewer points awarded
audit.py → More/fewer "blocked" vs "fulfilled" events
```

### If loyalty.py changes (e.g., change points conversion rate):
```
loyalty.py
  ↓ (direct import)
order_service.py → Calls redeem() and accrue_points()
  ↓ (data flow)
pricing.py → Loyalty credit affects total
  ↓ (logical impact)
fraud.py → Different totals affect fraud scoring
tax.py → Different totals affect tax amount
  ↓ (business impact)
returns.py → Clawback amount changes
```

### If shipping.py changes (e.g., modify shipping costs):
```
shipping.py
  ↓ (direct import)
order_service.py → Calls create_label()
returns.py → Calls create_label()
  ↓ (data coupling)
pricing.py → Reads shipping_method to determine cost
  ↓ (logical impact)
promotions.py → FREESHIP value changes
tax.py → Tax on shipping changes
fraud.py → Order total changes (affects scoring)
```

### If tax.py changes (e.g., add new region or rate):
```
tax.py
  ↓ (direct import)
pricing.py → Calls calculate()
  ↓ (data flow)
order_service.py → Reads PricingBreakdown.tax
returns.py → Refund includes tax reversal
  ↓ (logical impact)
fraud.py → Total amount changes (affects scoring)
loyalty.py → Final total changes (affects points)
```

### If promotions.py changes (e.g., add new coupon type):
```
promotions.py
  ↓ (direct import)
pricing.py → Calls apply_coupon()
  ↓ (data flow)
order_service.py → Reads PricingBreakdown.discount
  ↓ (logical impact)
tax.py → Taxable amount changes
fraud.py → Total amount changes
loyalty.py → Points calculation changes
  ↓ (business impact)
returns.py → Refund calculation must handle promotion
```

### If audit.py changes (e.g., modify log format):
```
audit.py
  ↓ (direct import by ALL orchestrators)
order_service.py → Calls log()
returns.py → Calls log()
  ↓ (no logical impact on business logic)
  ↓ (potential impact on downstream systems)
Analytics systems reading logs
Compliance reporting tools
Monitoring dashboards
```

---

## Module Interaction Patterns

### Orchestrator Pattern
```
order_service and returns act as orchestrators
  → Call multiple domain services in sequence
  → Coordinate data flow between services
  → Handle transaction boundaries
  → Manage error recovery
```

### Calculator Pattern
```
pricing, tax, fraud act as calculators
  → Receive input parameters
  → Perform calculations
  → Return result objects
  → No side effects (stateless)
```

### Repository Pattern
```
inventory, loyalty, catalog act as repositories
  → Manage internal state
  → Provide query methods
  → Provide mutation methods
  → Encapsulate storage logic
```

### Gateway Pattern
```
PaymentGateway, RefundGateway are protocol interfaces
  → Abstract external systems
  → Define contracts
  → Enable dependency injection
  → Facilitate testing with mocks
```

### Logger Pattern
```
audit acts as event logger
  → Receives events from all modules
  → Stores chronological history
  → No business logic
  → Non-blocking operations
```

---

## Cross-Module Data Contracts

### Order Placement Contract
```
Input: Order object
Process:
  1. inventory validates stock
  2. pricing calculates total
  3. fraud assesses risk
  4. payment charges amount
  5. inventory reserves stock
  6. shipping creates label
  7. loyalty awards points
  8. audit logs event
Output: OrderResult object
```

### Return Processing Contract
```
Input: ReturnRequest object
Process:
  1. pricing calculates refund
  2. refund gateway processes payment
  3. inventory restores stock
  4. loyalty claws back points
  5. shipping creates return label
  6. audit logs event
Output: ReturnResult object
```

### Pricing Calculation Contract
```
Input: items, region, shipping_method, coupon_code, loyalty_credit
Process:
  1. catalog provides product prices
  2. promotions applies discounts
  3. shipping determines cost
  4. tax calculates amount
  5. loyalty credit subtracted
Output: PricingBreakdown object
```

---

## Temporal Dependencies

### Order Flow Sequencing
```
Must happen in order:
1. inventory.has_enough() BEFORE pricing.calculate()
   Reason: Don't price unavailable orders

2. pricing.calculate() BEFORE fraud.score()
   Reason: Fraud scoring needs total amount

3. fraud.score() BEFORE payment_gateway.charge()
   Reason: Don't charge blocked orders

4. payment_gateway.charge() BEFORE inventory.reserve_with_buffer()
   Reason: Don't hold stock for unpaid orders

5. inventory.reserve_with_buffer() BEFORE shipping.create_label()
   Reason: Don't ship unreserved items

6. shipping.create_label() BEFORE loyalty.accrue_points()
   Reason: Points only for fulfilled orders

7. ALL operations BEFORE audit.log()
   Reason: Log final state
```

### Return Flow Sequencing
```
Must happen in order:
1. pricing.calculate_refund() BEFORE refund_gateway.refund()
   Reason: Need amount before processing refund

2. refund_gateway.refund() BEFORE inventory.add_item()
   Reason: Don't restock until paid

3. inventory.add_item() BEFORE loyalty.clawback()
   Reason: Clawback for confirmed returns

4. ALL operations BEFORE audit.log()
   Reason: Log final state
```

---

## State Management Dependencies

### inventory._stock
```
Modified by:
  - order_service.place_order() → reserve_with_buffer() (decreases)
  - returns.process() → add_item() (increases)

Read by:
  - order_service.place_order() → has_enough() (queries)

Impacts:
  - Future orders (availability)
  - Return processing (stock restoration)
```

### loyalty._balances
```
Modified by:
  - order_service.place_order() → accrue_points() (increases)
  - order_service.place_order() → redeem() (decreases)
  - returns.process() → clawback() (decreases)

Read by:
  - order_service.place_order() → redeem() (queries)

Impacts:
  - Customer point balance
  - Future redemptions
  - Pricing calculations (when redeemed)
```

### audit._logs
```
Modified by:
  - order_service.place_order() → log() (appends)
  - returns.process() → log() (appends)

Read by:
  - External systems (compliance, analytics)

Impacts:
  - Audit trail completeness
  - Compliance reporting
  - Analytics accuracy
```

### shipping._labels
```
Modified by:
  - shipping.create_label() (adds)

Read by:
  - order_service.place_order() (stores reference)
  - returns.process() (generates return label)

Impacts:
  - Label retrieval
  - Tracking number validity
```

---

## Business Rule Coupling

### Rule: Safety Stock Buffer
```
Defined in: inventory.reserve_with_buffer()
Affects:
  - order_service (may reject orders despite physical stock)
  - pricing (fewer orders get priced)
  - fraud (fewer orders get scored)
  - loyalty (fewer points awarded)
```

### Rule: Fraud Blocking Thresholds
```
Defined in: fraud.score()
Affects:
  - order_service (blocks high-risk orders)
  - payment_gateway (fewer charges processed)
  - inventory (fewer reservations)
  - loyalty (fewer points awarded)
```

### Rule: Loyalty Points Conversion
```
Defined in: loyalty.redeem(), loyalty.accrue_points()
Affects:
  - pricing (loyalty credit changes total)
  - fraud (different totals affect scoring)
  - tax (different totals affect tax)
```

### Rule: Promotion Application Order
```
Defined in: pricing.calculate()
Affects:
  - Discount amount (subtotal first, then promotion)
  - Tax calculation (applied after discount)
  - Final total (all factors combined)
```

### Rule: Tax Calculation Basis
```
Defined in: tax.calculate()
Based on: (subtotal - discount) + shipping
Affects:
  - pricing.total (adds tax amount)
  - fraud.score() (higher total = higher risk)
  - loyalty.accrue_points() (points based on total)
```

---

## Summary

This architecture has 12 modules with:
- **6 direct dependency chains** (code imports)
- **15+ logical dependency connections** (business rules)
- **8 shared data structures** (coupling via objects)
- **Multiple temporal dependencies** (operation sequencing)
- **4 state repositories** (inventory, loyalty, audit, shipping)

Changes to any module propagate through:
1. Direct code dependencies (imports)
2. Logical business rule connections
3. Shared data structure contracts
4. Temporal sequencing requirements
5. State management side effects