# Basic Metrics & Observation Points for .url File Delivery Simulation

This document defines the initial, basic metrics for assessing the "success" of content delivery for `.url` files within the simulated channels designed in Task D.2.1. The focus is solely on the verifiable presence of the `.url` file on a simulated target system or within a target-accessible location.

## Core Success Metric: Verifiable Presence

The fundamental metric for success at this stage is the **verifiable presence** of the `.url` file at its intended destination within the simulation.

## Channel-Specific Metrics and Observation Points:

1.  **Email Attachment Delivery:**
    *   **Metric:** Successful receipt of the email containing the `.url` file as an attachment in the simulated recipient's mailbox or at a monitored email gateway.
    *   **Observation Point:**
        *   Simulated Mailbox: Check for the existence of the email with the correct subject and the `.url` file attachment.
        *   Email Gateway Log: If applicable, check logs for records of the email being processed and delivered, noting the presence of the attachment.
    *   **Success Criteria:** The `.url` file is present as an attachment in an email that has reached the target simulated inbox/gateway.

2.  **Shared Drive Placement:**
    *   **Metric:** Successful placement and confirmed existence of the `.url` file in the designated shared directory or collaboration space.
    *   **Observation Point:**
        *   Target Directory: Perform a directory listing or file check on the simulated shared drive/folder to confirm the `.url` file's presence.
        *   Timestamp Check: Note the creation or modification timestamp of the file to ensure it's the correct version from the simulation.
    *   **Success Criteria:** The `.url` file exists at the specified path within the shared location and is accessible (based on simulated permissions).

## Data to Record (for each test):

*   Timestamp of delivery attempt.
*   Target channel (Email/Shared Drive).
*   Intended recipient/path.
*   Status:
    *   Success (file present at observation point).
    *   Failure (file not present, with reason if determinable, e.g., email blocked, write error to share).
*   Name and hash (e.g., MD5, SHA256) of the delivered `.url` file to verify integrity.

## Exclusions:

These metrics specifically do *not* cover:
*   User interaction with the file (e.g., opens, clicks).
*   Execution of any payload within the `.url` file.
*   Downstream effects of the `.url` file's content.

The objective is strictly to confirm that the delivery mechanism under test has successfully transported the `.url` file to its immediate, intended destination.
