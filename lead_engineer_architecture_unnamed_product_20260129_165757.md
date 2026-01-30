# Technical Architecture

**Product/Feature:** Unnamed Product
**Created:** 2026-01-29 16:57:57
**Created By:** Lead Engineer

---

# Technical Architecture Document: Shared Transfer Feature

## 1. System Overview

The shared transfer feature extends the existing private transfer service by introducing a ride-matching engine that groups passengers traveling similar routes within time windows, optimizing vehicle capacity while maintaining quality standards. The architecture leverages event-driven patterns for real-time availability updates and implements a sophisticated matching algorithm that balances cost savings (30-50% reduction) with service quality constraints including maximum detour time, vehicle capacity, and pickup time windows. The system is designed for horizontal scalability to handle peak booking periods and integrates seamlessly with existing booking, payment, and dispatch systems.

## 2. Components & Responsibilities

### 2.1 Booking Service (Enhanced)
Handles both private and shared transfer bookings, validates passenger requests, and orchestrates the booking flow including shared ride eligibility checks and price calculations.

### 2.2 Ride Matching Engine
Core component that implements geospatial and temporal matching algorithms to identify compatible rides, calculates optimal routes with multiple stops, and manages matching rules (capacity limits, detour constraints, time windows).

### 2.3 Pricing Calculator
Computes dynamic pricing for shared transfers based on route distance, number of passengers, demand patterns, and ensures 30-50% cost reduction while maintaining profitability thresholds.

### 2.4 Route Optimization Service
Determines optimal pickup/dropoff sequences for shared rides, calculates ETAs for all passengers, validates detour limits (e.g., max 20-30% additional travel time), and integrates with mapping services.

### 2.5 Notification & Coordination Service
Manages real-time updates to passengers about matched rides, booking confirmations, vehicle assignments, driver details, and pickup time adjustments.

### 2.6 Analytics & Reporting Module
Tracks key metrics including match rates, cost savings achieved, vehicle utilization improvements, passenger satisfaction scores, and operational efficiency.

## 3. Data Flow

### 3.1 Booking Flow
```
1. Passenger submits booking request (origin, destination, datetime, party size)
   ↓
2. Booking Service validates request and checks shared transfer eligibility
   ↓
3. Pricing Calculator computes both private and shared transfer prices
   ↓
4. Ride Matching Engine searches for compatible existing bookings (±30-60 min window)
   ↓
5. If matches found: Route Optimization Service validates feasibility
   ↓
6. Passenger presented with options (private vs shared with estimated savings)
   ↓
7. Upon selection, booking confirmed and stored
   ↓
8. Notification Service alerts all passengers in matched group
   ↓
9. Event published to dispatch system for vehicle assignment
```

### 3.2 Matching Process
```
- New shared booking triggers matching algorithm
- System queries bookings within temporal window (same day/time range)
- Geospatial filtering identifies routes within proximity threshold
- Compatibility checks: vehicle capacity, max detour limits, service level
- Route optimization validates combined route feasibility
- If valid match: update all bookings with shared ride reference
- Recalculate ETAs and notify affected passengers
- If no match: booking remains "pending match" until window expires or matched
```

### 3.3 Real-time Updates
```
- Dispatch system publishes vehicle assignment events
- Driver location updates flow to passengers via WebSocket/push notifications
- Booking modifications trigger re-matching evaluation
- Cancellations trigger ride group reconfiguration and passenger notifications
```

## 4. Technology Stack

### 4.1 Backend Services
- **Language:** Python 3.11+ (FastAPI/Django) or Node.js 18+ (Express/NestJS)
- **API Gateway:** Kong or AWS API Gateway for request routing and rate limiting
- **Message Queue:** Apache Kafka or AWS SQS for event-driven architecture
- **Cache:** Redis for matching candidates, session data, and rate limiting

### 4.2 Database Layer
- **Primary Database:** PostgreSQL 15+ with PostGIS extension for geospatial queries
- **Document Store:** MongoDB for flexible booking metadata and logs
- **Search Engine:** Elasticsearch for fast booking queries and analytics

### 4.3 Geospatial & Routing
- **Mapping Service:** Google Maps API or Mapbox for geocoding and route calculations
- **Geospatial Library:** Turf.js (Node) or Shapely (Python) for geometry operations
- **Distance Matrix:** Pre-computed caching for popular route combinations

### 4.4 Infrastructure
- **Cloud Provider:** AWS, GCP, or Azure
- **Compute:** Kubernetes (EKS/GKE/AKS) for container orchestration
- **Load Balancer:** Application Load Balancer with health checks
- **Monitoring:** Prometheus + Grafana for metrics, Datadog or New Relic for APM
- **Logging:** ELK Stack (Elasticsearch, Logstash, Kibana) or CloudWatch

### 4.5 Real-time Communication
- **WebSockets:** Socket.io or native WebSocket for live updates
- **Push Notifications:** Firebase Cloud Messaging or AWS SNS
- **Email/SMS:** SendGrid, Twilio for transactional communications

## 5. API Design

### 5.1 Booking Endpoints

#### POST /api/v1/bookings/quote
Request a price quote for private and shared transfer options.

**Request:**
```json
{
  "origin": {
    "lat": 40.7128,
    "lng": -74.0060,
    "address": "123 Main St, New York, NY"
  },
  "destination": {
    "lat": 40.7580,
    "lng": -73.9855,
    "address": "Times Square, New York, NY"
  },
  "pickup_datetime": "2024-02-15T14:30:00Z",
  "passengers": 2,
  "luggage_count": 2,
  "service_level": "standard"
}
```

**Response:**
```json
{
  "quote_id": "qt_abc123",
  "valid_until": "2024-02-15T14:45:00Z",
  "options": [
    {
      "type": "private",
      "price": 85.00,
      "currency": "USD",
      "vehicle_type": "sedan",
      "estimated_duration_minutes": 25
    },
    {
      "type": "shared",
      "price": 42.50,
      "currency": "USD",
      "savings_percentage": 50,
      "vehicle_type": "van",
      "estimated_duration_minutes": 35,
      "max_duration_minutes": 45,
      "max_passengers": 6,
      "matching_status": "immediate|pending"
    }
  ]
}
```

#### POST /api/v1/bookings
Create a new booking (private or shared).

**Request:**
```json
{
  "quote_id": "qt_abc123",
  "transfer_type": "shared",
  "passenger_details": {
    "name": "John Doe",
    "email": "john@example.com",
    "phone": "+1234567890",
    "count": 2
  },
  "special_requirements": ["child_seat", "wheelchair_accessible"],
  "payment_method_id": "pm_xyz789"
}
```

**Response:**
```json
{
  "booking_id": "bk_def456",
  "status": "confirmed",
  "transfer_type": "shared",
  "match_status": "pending",
  "price": 42.50,
  "currency": "USD",
  "pickup_window": {
    "earliest": "2024-02-15T14:20:00Z",
    "latest": "2024-02-15T14:40:00Z"
  },
  "estimated_dropoff": "2024-02-15T15:15:00Z",
  "confirmation_code": "ABC123XYZ",
  "qr_code_url": "https://cdn.example.com/qr/bk_def456.png"
}
```

### 5.2 Matching Endpoints

#### GET /api/v1/bookings/{booking_id}/match-status
Get current matching status for a shared booking.

**Response:**
```json
{
  "booking_id": "bk_def456",
  "match_status": "matched",
  "ride_group_id": "rg_ghi789",
  "passengers_count": 4,
  "vehicle_capacity": 6,
  "pickup_sequence": 2,
  "dropoff_sequence": 3,
  "updated_eta": {
    "pickup": "2024-02-15T14:32:00Z",
    "dropoff": "2024-02-15T15:12:00Z"
  },
  "other_passengers": [
    {
      "pickup_location": "124 Park Ave",
      "destination": "Grand Central Terminal",
      "relative_position": "before"
    }
  ]
}
```

### 5.3 Admin/Operations Endpoints

#### GET /api/v1/admin/ride-groups/{ride_group_id}
View details of a matched ride group for operational monitoring.

**Response:**
```json
{
  "ride_group_id": "rg_ghi789",
  "status": "assigned",
  "vehicle_id": "vh_123",
  "driver_id": "dr_456",
  "bookings": [
    {
      "booking_id": "bk_def456",
      "passenger_name": "John Doe",
      "pickup_sequence": 2,
      "pickup_time": "2024-02-15T14:32:00Z",
      "pickup_location": {...},
      "dropoff_sequence": 3,
      "dropoff_time": "2024-02-15T15:12:00Z",
      "dropoff_location": {...}
    }
  ],
  "optimized_route": {
    "total_distance_km": 18.5,
    "total_duration_minutes": 42,
    "waypoints": [...]
  },
  "utilization_percentage": 66
}
```

#### POST /api/v1/admin/matching/force-match
Manually match bookings for operational flexibility.

**Request:**
```json
{
  "booking_ids": ["bk_def456", "bk_jkl012"],
  "override_constraints": false
}
```

### 5.4 Real-time Event Stream

#### WebSocket: /ws/bookings/{booking_id}
Subscribe to real-time updates for a booking.

**Event Types:**
```json
{
  "event_type": "match_found|match_updated|vehicle_assigned|driver_approaching|pickup_completed|dropoff_completed",
  "timestamp": "2024-02-15T14:25:00Z",
  "data": {
    // Event-specific payload
  }
}
```

## 6. Implementation Tasks

### Task 1: Database Schema & Data Model Design
Design and implement database schema for shared bookings including ride groups table, matching rules configuration, and enhanced bookings table with shared transfer fields. Add PostGIS indexes for geospatial queries and create migration scripts for existing data.

### Task 2: Pricing Calculator Service
Build the dynamic pricing engine that calculates shared transfer prices ensuring 30-50% savings, implements tiered pricing based on demand/time, and handles edge cases (single passenger in shared ride, last-minute bookings). Include pricing rule configuration interface.

### Task 3: Core Matching Algorithm
Implement the ride matching engine with geospatial clustering (DBSCAN or similar), temporal window filtering, compatibility scoring system (route similarity, time windows, passenger count), and configurable constraint validation (max detour %, capacity limits).

### Task 4: Route Optimization Service
Develop route optimization logic using traveling salesman problem (TSP) algorithms or Google Maps Directions API with waypoints, validate all passenger detour limits, calculate accurate ETAs for each pickup/dropoff, and implement caching for common route patterns.

### Task 5: Booking Flow Enhancement
Extend existing booking service to support shared transfers including quote comparison UI, eligibility checks, payment processing for shared rides, confirmation workflow with match status, and integration with notification service.

### Task 6: Real-time Notification System
Build notification service using WebSockets for live updates, implement push notifications for match status changes, create email/SMS templates for booking confirmations and ride updates, and develop passenger communication for ride group changes.

### Task 7: Admin Dashboard & Monitoring
Create operational dashboard for viewing ride groups, monitoring match rates and utilization metrics, manual matching/override capabilities, passenger support tools, and alerts for failed matches or service issues.

### Task 8: Testing & Performance Optimization
Develop comprehensive test suite including unit tests for matching algorithm, integration tests for booking flows, load testing for concurrent booking scenarios (peak times), geospatial query performance tuning, and monitoring/alerting setup for production.

## 7. Technical Risks & Mitigations

### Risk 1: Poor Matching Rate Leading to Customer Dissatisfaction
**Risk:** In low-demand periods or less popular routes, shared bookings may not find matches within acceptable time windows, leading to extended wait times or forced upgrades to private transfers.

**Mitigation Strategies:**
- Implement intelligent matching windows that expand gradually (start with ±30 min, extend to ±60 min if no match)
- Offer "instant book" option with guaranteed match or automatic upgrade at shared price
- Pre-compute popular routes and times to set realistic expectations during booking
- Create "virtual pools" where passengers can opt-in to longer match windows for better prices
- Monitor match rates by route/time and adjust pricing dynamically to incentivize demand balancing
- Provide transparent communication about match probability before booking confirmation

### Risk 2: Complex Route Optimization at Scale
**Risk:** Real-time route optimization for multiple passengers with constraints (detour limits, time windows) becomes computationally expensive at scale, potentially causing API latency or timeout issues during peak booking periods.

**Mitigation Strategies:**
- Implement multi-tier matching strategy: exact match lookup (cached) → approximate matching (heuristics) → full optimization (async)
- Use geohashing or S2 geometry for rapid spatial indexing and candidate filtering before expensive route calculations
- Pre-compute and cache route combinations for popular origin-destination pairs
- Set hard timeout limits (e.g., 3 seconds) and fall back to simpler heuristic matching
- Process non-urgent matches asynchronously via background jobs for bookings >2 hours in future
- Implement circuit breakers for external routing APIs with fallback to distance-based approximations
- Consider dedicated matching service instances with horizontal autoscaling based on queue depth

### Risk 3: Data Consistency in Distributed Matching
**Risk:** Race conditions when multiple bookings simultaneously match to the same ride group, potentially causing overbooking, or inconsistent state when passengers cancel from partially matched groups.

**Mitigation Strategies:**
- Implement optimistic locking on ride group capacity using database version fields or Redis distributed locks
- Use event sourcing pattern for ride group state changes to maintain audit trail and enable replay
- Design idempotent matching operations with transaction boundaries around critical sections
- Implement compensating transactions for failed matches (e.g., refund, notify passengers)
- Add booking state machine with clear transitions (pending → matching → matched → assigned → completed)
- Use database constraints (CHECK constraints on capacity) to prevent invalid states
- Implement reconciliation jobs that detect and repair inconsistent ride groups
- Add circuit breaker pattern for matching service to prevent cascading failures

---

## Appendix: Architecture Decision Records

### ADR-001: Event-Driven Architecture for Matching
**Decision:** Use event-driven architecture with message queue (Kafka/SQS) for matching process rather than synchronous REST calls.

**Rationale:** Matching can be asynchronous for future bookings, improves system resilience, enables easier scaling, and allows multiple consumers to react to booking events.

### ADR-002: PostGIS for Geospatial Queries
**Decision:** Use PostgreSQL with PostGIS extension for primary storage and geospatial operations.

**Rationale:** Maintains ACID properties for bookings, provides powerful geospatial query capabilities, reduces operational complexity vs. dedicated geospatial database, and leverages existing PostgreSQL expertise.

### ADR-003: Hybrid Matching Strategy
**Decision:** Implement tiered matching approach (cached lookups → heuristics → full optimization) rather than always running complete optimization.

**Rationale:** Balances match quality with performance, handles peak load gracefully, provides predictable latency for majority of requests, and reserves expensive computation for edge cases.

---

**Document Version:** 1.0  
**Last Updated:** 2024-01-15  
**Author:** Lead Engineering Team  
**Status:** Ready for Review

---

**PRD Reference:** /Users/anique/Desktop/Agent-Os/product_lead_prd_unnamed_product_20260129_165631.md
