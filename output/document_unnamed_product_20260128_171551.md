# Architecture & Implementation Document

**Product/Feature:** Unnamed Product
**Created:** 2026-01-28 17:15:51

---

# Technical Architecture Document: JK Boats Booking System

## System Overview

A **seat-based inventory management system** built on a traditional web application architecture with real-time seat tracking and transactional booking flow. The core technical challenge is **preventing overbooking through optimistic locking and atomic database operations**, ensuring data consistency under concurrent booking requests. Architecture follows a **layered monolithic approach** with clear separation between presentation, business logic, and data persistence layers to enable rapid development while maintaining flexibility for future scaling.

---

## Components & Responsibilities

### 1. **Web Application Layer (Frontend)**

Renders boat availability, booking forms, and confirmation screens; validates user input client-side before submission; provides responsive UI for boat selection and booking flow.

### 2. **API Service Layer (Backend)**

Exposes RESTful endpoints for boat listings, availability queries, and booking transactions; orchestrates business logic and enforces booking rules; handles request validation and error responses.

### 3. **Booking Engine (Core Business Logic)**

Manages seat inventory calculations, validates booking requests against capacity constraints, executes atomic booking transactions with optimistic locking to prevent race conditions.

### 4. **Database Layer (PostgreSQL)**

Stores boat configurations, seat inventory state, customer records, and booking transactions; provides ACID guarantees for concurrent write operations; maintains referential integrity across entities.

### 5. **Notification Service (Optional for P1+)**

Sends booking confirmations via email/SMS; operates asynchronously to avoid blocking booking flow; queues messages for retry on delivery failure.

---

## Data Flow

### Booking Transaction Flow:

```
1. USER REQUEST
   ↓
   Frontend → GET /api/boats?destination=X&date=Y
   ↓
2. AVAILABILITY CHECK
   API Service → Booking Engine → Query available_seats from Database
   ↓
3. DISPLAY OPTIONS
   Database → API Service → Frontend (renders boat list with capacity)
   ↓
4. BOOKING SUBMISSION
   Frontend → POST /api/bookings {boat_id, customer_info, seats_requested}
   ↓
5. TRANSACTION EXECUTION
   API Service → Booking Engine:
     a. BEGIN TRANSACTION
     b. SELECT available_seats FROM departures WHERE id=X FOR UPDATE (pessimistic lock)
     c. VALIDATE: available_seats >= seats_requested
     d. INSERT customer record
     e. INSERT booking record
     f. UPDATE departures SET available_seats = available_seats - seats_requested
     g. COMMIT TRANSACTION
   ↓
6. CONFIRMATION
   Booking Engine → API Service → Frontend (display confirmation)
   ↓
7. NOTIFICATION (async)
   API Service → Notification Service → Send email/SMS confirmation
```

### Concurrency Handling:

- **Pessimistic locking** via `SELECT ... FOR UPDATE` prevents double-booking during high traffic
- Database transaction isolation ensures atomicity of multi-step booking process
- Failed transactions rollback automatically, leaving inventory state unchanged

---

## Technology Stack

### Backend

- **Language**: Python 3.11+ (rapid development, rich ecosystem)
- **Framework**: FastAPI (async support, auto-generated API docs, built-in validation)
- **ORM**: SQLAlchemy 2.0+ (transaction management, relationship mapping)
- **Validation**: Pydantic (type-safe request/response models)

### Database

- **Primary DB**: PostgreSQL 15+ (ACID compliance, row-level locking, JSON support for flexible boat attributes)
- **Connection Pooling**: asyncpg (high-performance async PostgreSQL driver)

### Frontend

- **Framework**: React 18 with TypeScript (component reusability, type safety)
- **State Management**: React Query (server state caching, optimistic updates)
- **UI Library**: Tailwind CSS + Headless UI (rapid styling, accessible components)
- **Validation**: Zod (client-side form validation matching backend schemas)

### Infrastructure

- **Hosting**: Docker containers on AWS ECS/Fargate (or similar PaaS)
- **Database Hosting**: AWS RDS PostgreSQL (automated backups, read replicas for scaling)
- **CDN**: CloudFront (static asset delivery)
- **Email Service**: AWS SES or SendGrid (transactional emails)
- **SMS Service**: Twilio (optional for SMS confirmations)

### Supporting Tools

- **API Documentation**: OpenAPI/Swagger (auto-generated from FastAPI)
- **Logging**: Structured logging with Python `logging` + CloudWatch
- **Monitoring**: Application metrics (response times, booking success rate)

---

## API Design

### Core Endpoints

#### 1. **List Available Boats**

```http
GET /api/boats?destination={destination}&date={YYYY-MM-DD}
```

**Response:**

```json
{
  "boats": [
    {
      "id": "uuid",
      "name": "SeaExpress 1",
      "capacity": 50,
      "available_seats": 12,
      "has_ac": true,
      "price_per_seat": 25.0,
      "departure_time": "2024-03-15T09:00:00Z",
      "destination": "Island Paradise"
    }
  ]
}
```

---

#### 2. **Get Boat Details**

```http
GET /api/boats/{boat_id}/departures/{departure_id}
```

**Response:**

```json
{
  "departure_id": "uuid",
  "boat": {
    "id": "uuid",
    "name": "SeaExpress 1",
    "capacity": 50,
    "has_ac": true
  },
  "available_seats": 12,
  "price_per_seat": 25.0,
  "departure_time": "2024-03-15T09:00:00Z",
  "destination": "Island Paradise"
}
```

---

#### 3. **Create Booking**

```http
POST /api/bookings
Content-Type: application/json
```

**Request:**

```json
{
  "departure_id": "uuid",
  "seats_requested": 2,
  "customer": {
    "email": "john@example.com",
    "full_name": "John Doe",
    "phone": "+1234567890"
  }
}
```

**Response (Success):**

```json
{
  "booking_id": "uuid",
  "status": "confirmed",
  "confirmation_code": "JKB-ABC123",
  "departure": {
    "boat_name": "SeaExpress 1",
    "departure_time": "2024-03-15T09:00:00Z",
    "destination": "Island Paradise"
  },
  "seats_booked": 2,
  "total_price": 50.0,
  "customer": {
    "email": "john@example.com",
    "full_name": "John Doe"
  }
}
```

**Response (Failure - Insufficient Capacity):**

```json
{
  "error": "insufficient_capacity",
  "message": "Only 1 seat available, but 2 requested",
  "available_seats": 1
}
```

---

#### 4. **Retrieve Booking**

```http
GET /api/bookings?email={email}
  OR
GET /api/bookings?phone={phone}
```

**Response:**

```json
{
  "bookings": [
    {
      "booking_id": "uuid",
      "confirmation_code": "JKB-ABC123",
      "departure_time": "2024-03-15T09:00:00Z",
      "destination": "Island Paradise",
      "seats_booked": 2,
      "status": "confirmed",
      "created_at": "2024-03-10T14:30:00Z"
    }
  ]
}
```

---

## Data Model

### Core Entities

```sql
-- Boats (configuration)
CREATE TABLE boats (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    capacity INTEGER NOT NULL CHECK (capacity > 0),
    has_ac BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Departures (scheduled trips with dynamic inventory)
CREATE TABLE departures (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    boat_id UUID NOT NULL REFERENCES boats(id),
    departure_time TIMESTAMP NOT NULL,
    destination VARCHAR(200) NOT NULL,
    price_per_seat DECIMAL(10,2) NOT NULL CHECK (price_per_seat > 0),
    available_seats INTEGER NOT NULL CHECK (available_seats >= 0),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT unique_departure UNIQUE (boat_id, departure_time)
);

CREATE INDEX idx_departures_time_destination ON departures(departure_time, destination);

-- Customers
CREATE TABLE customers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) NOT NULL,
    full_name VARCHAR(200) NOT NULL,
    phone VARCHAR(20) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT unique_email UNIQUE (email)
);

CREATE INDEX idx_customers_email ON customers(email);
CREATE INDEX idx_customers_phone ON customers(phone);

-- Bookings
CREATE TABLE bookings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    confirmation_code VARCHAR(20) NOT NULL UNIQUE,
    departure_id UUID NOT NULL REFERENCES departures(id),
    customer_id UUID NOT NULL REFERENCES customers(id),
    seats_booked INTEGER NOT NULL CHECK (seats_booked > 0),
    total_price DECIMAL(10,2) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'confirmed',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_bookings_departure ON bookings(departure_id);
CREATE INDEX idx_bookings_customer ON bookings(customer_id);
CREATE INDEX idx_bookings_confirmation ON bookings(confirmation_code);
```

### Key Design Decisions:

1. **Separate `departures` from `boats`**: Allows same boat to have multiple scheduled trips with independent inventory
2. **`available_seats` on `departures`**: Denormalized for performance; updated atomically during booking
3. **`confirmation_code`**: Human-readable booking reference (e.g., "JKB-A1B2C3")
4. **Customer deduplication by email**: Prevents duplicate customer records while allowing quick lookup

---

## Implementation Risks & Mitigations

| Risk                                           | Mitigation                                                                                 |
| ---------------------------------------------- | ------------------------------------------------------------------------------------------ |
| **Race conditions during concurrent bookings** | Use pessimistic locking (`SELECT FOR UPDATE`) within database transactions                 |
| **Stale availability displayed to users**      | Implement short cache TTL (<30s) and verify availability at booking time                   |
| **Database connection pool exhaustion**        | Configure connection limits; implement timeout handling; monitor pool usage                |
| **Slow queries under load**                    | Add indexes on `departure_time`, `destination`; consider read replicas for listing queries |
| **Invalid customer data**                      | Enforce validation at API layer (Pydantic) and database layer (constraints)                |
| **Email/SMS delivery failures**                | Queue messages asynchronously; implement retry logic with exponential backoff              |

---

## Implementation Tasks

### Phase 1: Core Infrastructure (P0)

#### **Ticket 1: Database Schema & Setup**

- **Description**: Create PostgreSQL database with tables for boats, departures, customers, and bookings. Implement indexes, constraints, and initial seed data for 2-3 test boats with sample departures.
- **Acceptance Criteria**:
  - Schema matches data model specification
  - Foreign key constraints enforce referential integrity
  - Can insert sample boat configurations and query available seats

---

#### **Ticket 2: Backend API Framework & Boat Listing**

- **Description**: Set up FastAPI project structure with SQLAlchemy ORM. Implement `GET /api/boats` endpoint to list departures filtered by destination and date, showing available seats and boat attributes.
- **Acceptance Criteria**:
  - Endpoint returns JSON with boat details and availability
  - Query filters work correctly for destination and date ranges
  - API documentation auto-generated via Swagger UI

---

#### **Ticket 3: Booking Creation with Overbooking Prevention**

- **Description**: Implement `POST /api/bookings` endpoint with transactional booking logic. Use pessimistic locking to check availability, decrement `available_seats`, create customer record (or link existing), and insert booking record atomically.
- **Acceptance Criteria**:
  - Concurrent booking requests never result in overbooking
  - Returns 400 error when insufficient seats available
  - Generates unique confirmation code for each booking
  - Rolls back transaction on any validation failure

---

#### **Ticket 4: Customer Data Validation & Storage**

- **Description**: Implement Pydantic models for customer data validation (email format, phone format, required fields). Store customer records with deduplication by email. Link bookings to customer records via foreign key.
- **Acceptance Criteria**:
  - Invalid email/phone formats rejected with clear error messages
  - Existing customers reused when email matches
  - All required fields enforced at API and database layers

---

### Phase 2: User Experience Enhancements (P1)

#### **Ticket 5: Frontend Boat Listing & Selection**

- **Description**: Build React components to display available boats with filters for destination and date. Show boat details (capacity, AC status, price, remaining seats) in card layout. Implement responsive design with loading states.
- **Acceptance Criteria**:
  - Users can filter boats by destination and date
  - Remaining seats displayed prominently
  - Cards show all boat attributes from PRD
  - Mobile-responsive layout

---

#### **Ticket 6: Booking Form & Confirmation Flow**

- **Description**: Create multi-step booking form (customer info → review → confirmation). Implement client-side validation matching backend rules. Display success confirmation with booking details and confirmation code. Handle error states (capacity exceeded, validation errors).
- **Acceptance Criteria**:
  - Form validates email and phone format before submission
  - Shows clear error messages on booking failure
  - Confirmation screen displays all booking details
  - Confirmation code prominently displayed

---

#### **Ticket 7: Booking Lookup Feature**

- **Description**: Implement `GET /api/bookings` endpoint to retrieve bookings by email or phone. Create frontend page where customers can enter email/phone to view their booking history.
- **Acceptance Criteria**:
  - API returns all bookings for given email/phone
  - Frontend displays booking list with departure details
  - Shows "no bookings found" state appropriately

---

### Phase 3: Operational Features (P2)

#### **Ticket 8: Email Confirmation System**

- **Description**: Integrate email service (SendGrid/SES). Send transactional email after successful booking with confirmation code, departure details, and customer info. Implement async job queue to avoid blocking booking response.
- **Acceptance Criteria**:
  - Email sent within 60 seconds of booking confirmation
  - Email includes all booking details from PRD
  - Failed email sends logged but don't block booking completion
  - Retry logic for transient delivery failures

---

## Technical Debt & Future Considerations

### Immediate (within 3 months):

- **Connection pooling tuning**: Monitor and adjust database connection pool size based on actual load
- **API rate limiting**: Implement rate limiting to prevent abuse once traffic patterns are understood
- **Logging & monitoring**: Add structured logging for booking failures, slow queries, and capacity warnings

### Medium-term (3-6 months):

- **Read replicas**: If listing queries slow down under load, introduce read replicas for `GET` endpoints
- **Caching layer**: Add Redis for caching boat configurations and recent availability queries
- **Admin panel**: Build administrative interface for managing boats, departures, and viewing bookings

### Long-term (6+ months):

- **Microservices consideration**: If payment processing or complex inventory rules emerge, consider extracting booking engine into separate service
- **Mobile apps**: Native iOS/Android apps if customer research shows demand
- **Real-time updates**: WebSocket connections for live seat availability updates during high-demand departures

---

## Success Metrics & Monitoring

### Technical Metrics:

- **Booking Success Rate**: Target 95%+ (measure failed vs. successful booking attempts)
- **API Response Time**: P95 < 500ms for listing queries, P95 < 1s for booking creation
- **Database Lock Wait Time**: Monitor transaction lock duration; alert if >100ms average
- **Overbooking Incidents**: Zero tolerance; alert immediately on any capacity violation

### Operational Metrics:

- **Concurrent Booking Conflicts**: Track how often concurrent requests compete for last seats
- **Error Rate by Type**: Track validation errors vs. capacity errors vs. system errors
- **Email Delivery Rate**: Monitor bounce/failure rates for confirmation emails

---

## Open Questions Requiring Product Decisions

**Blockers for implementation:**

1. **Platform choice**: Web-only initially, or mobile-responsive web? (Affects frontend framework choice)
2. **Authentication**: Anonymous bookings or require user accounts? (Impacts customer table design and lookup security)
3. **Payment integration**: If needed in MVP, affects booking state machine (pending → confirmed workflow)

**Important for Phase 2+:** 4. **Boat schedule management**: Static seed data or admin interface needed? (Determines admin tool priority) 5. **Cancellation policy**: If modifications allowed, need to add booking state transitions and seat release logic 6. **Ticket delivery method**: Email-only, or integrate SMS/physical printing? (Affects notification service scope)

---

**Recommendation**: Start with web-responsive frontend, anonymous bookings (lookup by email/phone), and defer payment/admin tools to post-MVP based on operational feedback.

---

**Status:** Ready for Implementation
**PRD Reference:** /Users/anique/Desktop/Agent-Os/prd_unnamed_product_20260128_171429.md
