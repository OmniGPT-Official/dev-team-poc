# Technical Architecture

**Product/Feature:** Unnamed Product
**Created:** 2026-01-29 13:08:54
**Created By:** Lead Engineer

---

# Technical Architecture Document: Email Notification System

**Product:** JK Boat  
**Feature:** Email Notification System for Boat Tour Bookings  
**Date:** 2024  
**Status:** Technical Design - Draft  
**Author:** Lead Engineering Team

---

## 1. System Overview

The Email Notification System is an event-driven architecture that handles transactional email notifications for boat tour bookings. The system leverages asynchronous message processing to ensure reliable email delivery without blocking the main booking flow, providing a scalable and fault-tolerant solution. Core architectural decisions include: (1) event-driven architecture with message queues for decoupling, (2) template-based email rendering for maintainability, and (3) retry logic with dead-letter queues for reliability.

---

## 2. Components & Responsibilities

### 2.1 Booking Service
The primary application service that generates booking events (create, update, cancel) and publishes them to the message queue when customers interact with boat tour bookings.

### 2.2 Email Event Processor
A worker service that consumes booking events from the message queue, enriches event data with customer and booking details, and orchestrates the email sending workflow.

### 2.3 Email Template Engine
A component responsible for loading email templates (HTML/text), populating them with booking data using a templating system (e.g., Handlebars, Jinja), and generating the final email content.

### 2.4 Email Delivery Service
An abstraction layer that interfaces with third-party email providers (SendGrid, AWS SES, etc.), handles API authentication, manages rate limiting, and tracks delivery status.

### 2.5 Notification Audit Store
A persistent storage layer that records all email notification attempts, their status (sent, failed, pending), timestamps, and error details for debugging and compliance purposes.

---

## 3. Data Flow

```
┌─────────────────┐
│ Booking Service │
│  (API/Web App)  │
└────────┬────────┘
         │ 1. Publish Event
         ▼
┌─────────────────────┐
│   Message Queue     │
│  (RabbitMQ/SQS)     │
└────────┬────────────┘
         │ 2. Consume Event
         ▼
┌─────────────────────────┐
│ Email Event Processor   │◄─── 3. Fetch Details from DB
│   (Worker Service)      │
└────────┬────────────────┘
         │ 4. Request Rendered Email
         ▼
┌─────────────────────────┐
│  Email Template Engine  │
│  (Rendering Service)    │
└────────┬────────────────┘
         │ 5. Return HTML/Text
         ▼
┌─────────────────────────┐
│ Email Delivery Service  │
│  (SendGrid/SES Adapter) │
└────────┬────────────────┘
         │ 6. Send Email via Provider
         ▼
┌─────────────────────────┐
│   Email Provider API    │
│  (SendGrid/AWS SES)     │
└─────────────────────────┘
         │
         └──► 7. Log Status
              ┌────────────────────────┐
              │ Notification Audit     │
              │      Store (DB)        │
              └────────────────────────┘
```

**Key Interactions:**
1. Booking Service publishes events (booking.created, booking.updated, booking.cancelled) to message queue
2. Email Event Processor consumes events asynchronously
3. Processor fetches complete booking and customer data from database
4. Template Engine renders personalized email content
5. Delivery Service sends email via provider API
6. All attempts are logged to Audit Store for tracking and compliance
7. Failed messages are retried (3 attempts) then moved to Dead Letter Queue

---

## 4. Technology Stack

### 4.1 Languages & Frameworks
- **Backend:** Node.js (Express.js) or Python (FastAPI/Flask)
- **Worker Service:** Node.js with Bull/BullMQ or Python with Celery
- **Template Engine:** Handlebars (Node.js) or Jinja2 (Python)

### 4.2 Key Libraries & Services
- **Message Queue:** RabbitMQ (self-hosted) or AWS SQS (cloud-managed)
- **Email Provider:** SendGrid, AWS SES, or Mailgun (recommend SendGrid for rich API features)
- **Email Validation:** validator.js or email-validator
- **Retry Logic:** exponential-backoff library
- **Logging:** Winston (Node.js) or Python logging with structured JSON output

### 4.3 Infrastructure Requirements
- **Database:** PostgreSQL (booking data + audit logs) with appropriate indexes
- **Message Queue:** RabbitMQ cluster (3 nodes) or AWS SQS with DLQ configured
- **Worker Instances:** Minimum 2 instances for redundancy, autoscaling based on queue depth
- **Email Templates Storage:** S3/File System or embedded in codebase (recommend S3 for hot-reload)
- **Monitoring:** CloudWatch/Prometheus + Grafana for queue metrics and email delivery rates
- **Secret Management:** AWS Secrets Manager or HashiCorp Vault for API keys

---

## 5. API Design

### 5.1 Internal Event Schema (Message Queue)

**Event Type:** `booking.created`
```json
{
  "eventType": "booking.created",
  "eventId": "uuid-v4",
  "timestamp": "2024-01-15T10:30:00Z",
  "payload": {
    "bookingId": "BK123456",
    "customerId": "CUST789",
    "tourId": "TOUR001",
    "tourName": "Sunset Cruise",
    "tourDate": "2024-02-20",
    "tourTime": "18:00",
    "numberOfGuests": 4,
    "totalPrice": 240.00,
    "currency": "USD",
    "customerEmail": "customer@example.com",
    "customerName": "John Doe"
  }
}
```

**Event Type:** `booking.cancelled`
```json
{
  "eventType": "booking.cancelled",
  "eventId": "uuid-v4",
  "timestamp": "2024-01-16T14:20:00Z",
  "payload": {
    "bookingId": "BK123456",
    "customerId": "CUST789",
    "cancellationReason": "Customer request",
    "refundAmount": 240.00,
    "customerEmail": "customer@example.com",
    "customerName": "John Doe"
  }
}
```

### 5.2 Email Delivery Service API (Internal)

**Endpoint:** `POST /api/internal/email/send`

**Request:**
```json
{
  "to": "customer@example.com",
  "from": "bookings@jkboat.com",
  "subject": "Booking Confirmation - Sunset Cruise",
  "templateId": "booking-confirmation",
  "templateData": {
    "customerName": "John Doe",
    "bookingId": "BK123456",
    "tourName": "Sunset Cruise",
    "tourDate": "2024-02-20",
    "tourTime": "18:00",
    "numberOfGuests": 4,
    "totalPrice": "$240.00"
  },
  "metadata": {
    "bookingId": "BK123456",
    "eventId": "uuid-v4"
  }
}
```

**Response (Success):**
```json
{
  "success": true,
  "messageId": "provider-message-id-123",
  "status": "queued",
  "timestamp": "2024-01-15T10:30:05Z"
}
```

**Response (Error):**
```json
{
  "success": false,
  "error": "Invalid recipient email",
  "errorCode": "INVALID_EMAIL",
  "timestamp": "2024-01-15T10:30:05Z"
}
```

### 5.3 Audit Query API (for Admin Dashboard)

**Endpoint:** `GET /api/admin/notifications?bookingId={bookingId}`

**Response:**
```json
{
  "bookingId": "BK123456",
  "notifications": [
    {
      "id": "NOTIF001",
      "eventType": "booking.created",
      "emailType": "booking-confirmation",
      "recipient": "customer@example.com",
      "status": "sent",
      "attempts": 1,
      "sentAt": "2024-01-15T10:30:05Z",
      "providerId": "sendgrid-msg-123"
    }
  ]
}
```

---

## 6. Implementation Tasks

### Task 1: Setup Message Queue Infrastructure
Configure RabbitMQ/SQS with appropriate exchanges/queues, set up dead-letter queue for failed messages, configure TTL and retry policies, and establish connection pooling from application services.

### Task 2: Implement Event Publishing in Booking Service
Add event publishing logic to booking service at key lifecycle points (create, update, cancel), implement event schema validation, add error handling for queue unavailability, and include correlation IDs for tracing.

### Task 3: Build Email Event Processor Worker
Create worker service that consumes messages from queue, implement message acknowledgment logic, add data enrichment layer to fetch complete booking details, and implement exponential backoff retry mechanism (3 attempts with 1s, 5s, 15s delays).

### Task 4: Develop Email Template Engine
Design responsive HTML email templates for each notification type (confirmation, cancellation, reminder), implement template rendering with dynamic data injection, create plain-text fallback versions, and setup template versioning system.

### Task 5: Create Email Delivery Service Adapter
Build abstraction layer for email provider integration (SendGrid/SES), implement rate limiting and request throttling, add webhook handlers for delivery status updates (delivered, bounced, complained), and implement circuit breaker pattern for provider failures.

### Task 6: Implement Notification Audit Store
Design database schema for notification logs (notification_id, booking_id, event_type, status, attempts, timestamps), create indexes for efficient querying by bookingId and status, implement archival strategy for old logs (90+ days), and build query API for admin dashboard.

### Task 7: Add Monitoring and Alerting
Setup metrics collection for queue depth, processing rate, email delivery success/failure rates, configure alerts for queue backlog > 1000 messages or failure rate > 5%, implement distributed tracing with correlation IDs, and create Grafana dashboards for operational visibility.

### Task 8: Implement Testing Strategy
Write unit tests for template rendering and event processing logic (80%+ coverage), create integration tests for end-to-end email flow with mock provider, setup load testing to validate 10,000+ emails/hour capacity, and implement chaos testing for queue/provider failures.

---

## 7. Technical Risks & Mitigations

### Risk 1: Email Provider Outages
**Description:** Third-party email providers (SendGrid, SES) may experience downtime or rate limiting, preventing email delivery and impacting customer experience.

**Mitigation Strategies:**
- Implement multi-provider failover strategy (primary: SendGrid, fallback: AWS SES)
- Use message queue with persistent storage to buffer emails during outages (messages retained for 7 days)
- Configure exponential backoff with circuit breaker to avoid overwhelming recovering services
- Setup monitoring alerts for provider API errors and implement automated failover switching
- Maintain SLA documentation and test failover procedures quarterly

### Risk 2: Message Queue Bottlenecks
**Description:** High booking volumes (peak seasons, promotions) could overwhelm worker capacity, causing email delays and queue backlog leading to memory/disk issues.

**Mitigation Strategies:**
- Implement autoscaling for worker instances based on queue depth metrics (scale up when > 500 messages)
- Configure queue depth limits and priority queues (booking confirmations > reminders)
- Setup monitoring for processing lag time and alert when > 5 minutes
- Implement batch processing where appropriate (daily digest emails) to reduce peak load
- Conduct load testing simulating 5x normal traffic to validate capacity

### Risk 3: Data Consistency and Duplicate Emails
**Description:** Race conditions or retry logic failures could result in customers receiving duplicate notification emails or missing critical booking information.

**Mitigation Strategies:**
- Implement idempotency keys using eventId to prevent duplicate processing
- Use database transactions with appropriate isolation levels when logging notifications
- Add deduplication logic in Email Event Processor (check audit store before sending)
- Implement at-least-once delivery with consumer acknowledgment only after successful email send
- Create manual resend mechanism for support team to handle edge cases
- Add correlation IDs throughout the system for debugging and tracing duplicate scenarios

---

## 8. Additional Considerations

### 8.1 Security
- Encrypt sensitive customer data (PII) in audit logs at rest
- Use TLS for all external communications (email provider APIs)
- Implement API key rotation policy for email providers (quarterly)
- Add rate limiting on internal APIs to prevent abuse

### 8.2 Scalability
- Current design supports 10,000+ emails/hour
- Horizontal scaling of worker instances for growth
- Consider Redis cache for template caching at scale
- Plan for multi-region deployment if global expansion occurs

### 8.3 Compliance
- GDPR: Include unsubscribe links in marketing emails (not transactional)
- Retain audit logs for 7 years for financial compliance
- Implement data deletion API for customer right-to-erasure requests
- Add consent tracking if expanding beyond transactional emails

### 8.4 Future Enhancements
- SMS notifications via Twilio integration (similar architecture)
- Push notifications for mobile app
- Email preference center for customers
- A/B testing framework for email templates
- ML-based send-time optimization

---

## 9. Success Metrics

- **Email Delivery Rate:** > 99% successful delivery
- **Processing Latency:** < 30 seconds from booking to email sent
- **Queue Backlog:** < 100 messages during normal operation
- **Worker Uptime:** > 99.9% availability
- **Provider Failover Time:** < 2 minutes to switch providers

---

## 10. Open Questions for Product Team

1. What is the expected booking volume (daily/peak)? (Impacts infrastructure sizing)
2. Are there any specific email branding/design requirements? (Impacts template development)
3. Do we need to support multiple languages for international customers? (Impacts template architecture)
4. What is the desired customer experience for failed email scenarios? (Retry in app notification?)
5. Are there compliance requirements beyond standard transactional emails? (GDPR, CAN-SPAM)

---

**Next Steps:**
1. Review and approve technical architecture
2. Finalize technology stack choices (Node.js vs Python)
3. Select email provider and setup account
4. Provision infrastructure (message queue, workers)
5. Begin implementation with Task 1-2 in parallel

---

**Document Status:** Ready for Review  
**Approval Required From:** Engineering Manager, Product Manager, DevOps Lead

---

**PRD Reference:** /Users/anique/Desktop/Agent-Os/product_lead_prd_unnamed_product_20260129_130740.md
