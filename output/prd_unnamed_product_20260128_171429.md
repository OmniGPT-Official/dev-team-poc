# Product Requirements Document: JK Boats Booking System

## Overview
A seat-based boat booking platform for JK Boats that manages inventory across multiple boats, prevents overbooking, and captures customer information. The system handles boats with varying capacities, amenities (AC), pricing, departure times, and destinations to enable efficient seat reservations.

## Problem & Goals

**Problem Statement:**
JK Boats currently lacks a structured system to manage seat inventory across their fleet, leading to potential overbooking risks and inefficient booking operations.

**Goals:**
1. **Prevent Overbooking**: Ensure real-time seat availability tracking prevents capacity violations
2. **Streamline Booking Operations**: Enable efficient seat reservations with automated capacity management
3. **Capture Customer Data**: Systematically collect and store customer contact information (email, name, phone)
4. **Support Fleet Diversity**: Accommodate boats with different capacities, amenities, pricing, schedules, and destinations

## Target Users
- **Primary**: Customers booking boat seats (user type and booking channel unspecified - see Open Questions)
- **Secondary**: JK Boats staff managing bookings and fleet configuration (admin requirements undefined)

## Requirements

### Must Have (P0)

**1. Seat Inventory Management**
- System tracks available seats per boat per departure in real-time
- Available capacity automatically decrements when bookings are confirmed
- Booking requests exceeding available capacity are rejected/prevented

**2. Boat Configuration System**
- Each boat stores: maximum capacity (integer), air conditioning status (yes/no), price per seat, departure time, destination
- Boat attributes can be configured and updated
- System supports multiple boats with distinct configurations

**3. Customer Information Capture**
- Booking form collects: email (validated format), full name, phone number (validated format)
- Customer data is required to complete booking
- Customer records are stored and linked to bookings

**4. Booking Transaction Flow**
- User selects boat, views available seats, and submits booking request
- System validates availability before confirming booking
- Confirmed booking reserves seats and stores customer information

**5. Overbooking Prevention**
- Concurrent booking requests for same departure are handled safely (no race conditions)
- Total confirmed bookings never exceed boat capacity
- System provides clear feedback when capacity is reached

### Should Have (P1)

**1. Booking Confirmation**
- System generates booking confirmation with details: boat info, departure time, destination, customer name, seats booked
- Confirmation is displayed to user upon successful booking

**2. Availability Display**
- Users can view remaining seat availability before booking
- System displays boat attributes (AC status, departure time, destination, price) alongside availability

**3. Basic Booking History**
- System stores completed bookings with timestamp
- Bookings can be retrieved by customer email or phone number

### Nice to Have (P2)
- Multi-seat booking (group reservations)
- Booking modification/cancellation
- Email/SMS notifications
- Payment processing integration

## Success Metrics
1. **Zero Overbooking Incidents**: No capacity violations across all departures
2. **Booking Completion Rate**: % of started bookings that complete successfully
3. **Data Capture Quality**: % of bookings with valid, complete customer information
4. **System Uptime**: 99%+ availability during operating hours

## Out of Scope
- Payment processing (payment timing and method undefined)
- Return/round-trip bookings
- Multi-stop routes or complex itineraries
- Ticket fulfillment mechanism (digital/physical delivery)
- Customer accounts or authentication
- Refund/cancellation workflows
- Admin dashboard or reporting tools
- Mobile applications (platform type unspecified)

## Open Questions

**User & Access:**
- Who are the actual users? (tourists, locals, agents, walk-up customers)
- What platform(s)? (web app, mobile app, in-person counter system)
- Is user authentication needed, or are bookings anonymous?

**Business Operations:**
- When does payment occur? (at booking, at departure, deposit model)
- What is the cancellation/modification policy?
- Are return trips or round-trip bookings needed?
- How are tickets delivered to customers? (email, SMS, print at counter)
- What is the typical booking volume and peak demand?

**Operational Context:**
- How are boat schedules managed? (fixed daily, seasonal, dynamic)
- Are there multi-stop routes or only point-to-point?
- What admin capabilities are needed for fleet/schedule management?
- What reporting or analytics are required?

**Technical:**
- Are there existing systems to integrate with?
- What are performance/scale expectations?
- Is offline capability required?
- Are there regulatory/compliance requirements?

---

**Document Status:** Draft - Pending clarification on open questions  
**Next Steps:** Conduct user research and operational interviews to address open questions, then refine requirements and create technical specifications