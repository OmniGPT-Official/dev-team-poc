# Requirements Document: JK Boats - Shared Transfers

## Overview
JK Boats currently offers private boat transfers between islands. We're expanding our service model to include shared boat transfers, enabling customers to choose between private and shared transfer options when booking inter-island transportation.

## Problem & Goals

**Problem:**  
Customers currently only have access to private boat transfers, which may not suit all budget preferences or travel needs when moving between islands.

**Goals:**
1. Launch shared transfer booking capability alongside existing private transfers within [timeframe TBD]
2. Enable customers to compare and choose between private and shared transfer options
3. Achieve [X%] adoption rate of shared transfers within first [Y] months
4. Maintain or improve current booking conversion rates

## Target Audience
**Primary Users:** Island travelers seeking transportation between destinations  
**Core Use Case:** Booking boat transfers between islands with option to choose between private or shared service

## Requirements

### Must Have (P0)

**1. Dual Transfer Type Selection**
- Customers can view both private and shared transfer options in booking flow
- Clear differentiation between transfer types (pricing, capacity, schedule)
- Single checkout flow accommodates both transfer types
- *Acceptance Criteria:*
  - [ ] Both transfer types displayed on search results
  - [ ] Customer can select one transfer type before checkout

**2. Shared Transfer Scheduling System**
- Shared transfers operate on fixed schedules between islands
- System displays available shared transfer times/dates
- *Acceptance Criteria:*
  - [ ] Fixed schedule defined and displayed for each island route
  - [ ] Available seats shown for each scheduled departure

**3. Capacity Management**
- System tracks available seats on shared transfers
- Prevents overbooking beyond vessel capacity
- *Acceptance Criteria:*
  - [ ] Maximum capacity defined per shared transfer
  - [ ] Bookings blocked when capacity reached

**4. Pricing Display**
- Shared transfers priced per person
- Private transfers priced per boat
- Transparent pricing comparison visible to customers
- *Acceptance Criteria:*
  - [ ] Price per person shown for shared transfers
  - [ ] Price per boat shown for private transfers

**5. Booking Confirmation**
- Customers receive confirmation with transfer type, time, and pickup details
- *Acceptance Criteria:*
  - [ ] Confirmation email includes all booking details
  - [ ] Transfer type clearly stated in confirmation

### Should Have (P1)

**1. Multi-passenger Booking for Shared Transfers**
- Single customer can book multiple seats on one shared transfer
- *Acceptance Criteria:*
  - [ ] Passenger count selector for shared transfers
  - [ ] Total price updates based on passenger count

**2. Route Availability Management**
- Admin ability to set which routes offer shared vs. private only
- *Acceptance Criteria:*
  - [ ] Backend control to enable/disable shared transfers per route

**3. Cancellation Policy Differentiation**
- Different cancellation terms for shared vs. private transfers
- *Acceptance Criteria:*
  - [ ] Cancellation policy displayed per transfer type
  - [ ] Policy enforced in cancellation flow

### Nice to Have (P2)
- None identified at this time

## Success Metrics
1. **Booking Mix:** [X%] of total bookings use shared transfers within 3 months
2. **Conversion Rate:** Maintain or exceed current [Y%] booking conversion rate
3. **Revenue per Route:** Increase total revenue on routes offering shared transfers by [Z%]
4. **Customer Satisfaction:** Achieve [rating] or higher for shared transfer experience

## Out of Scope
- Real-time GPS tracking of shared transfers
- Dynamic pricing based on demand
- Loyalty/rewards program integration
- Multi-stop or custom route requests
- Integration with third-party booking platforms (Phase 1)

## Open Questions

**Critical:**
1. What is the target launch date/timeline?
2. Which island routes will offer shared transfers initially?
3. What are the shared transfer vessel capacities per route?
4. What are the fixed schedules for shared transfers?
5. What is the pricing strategy for shared transfers (absolute prices, discount % vs private)?
6. Who is the target audience specifically? (Budget travelers, solo travelers, groups?)
7. What are the cancellation policies for each transfer type?
8. Are there minimum passenger requirements for shared transfers to operate?

**Important:**
9. Do shared transfers have different pickup/drop-off locations than private?
10. How will customers be notified if a shared transfer is cancelled due to low bookings?
11. What payment methods will be supported?
12. Are there age restrictions or special accommodations needed for shared transfers?

---

**Document Version:** 1.0  
**Last Updated:** [Date]  
**Owner:** Product Lead