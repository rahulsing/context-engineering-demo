# Retention Policy — Section 3.1: Customer Retention Trigger Rules

**Owner:** Retail Analytics Team
**Effective:** 2026-05-01
**Status:** Approved

## Purpose

This section defines which retention actions apply to a customer, based on
lifetime value, churn risk, and purchase recency signals already computed
in the `customer_metrics` table. It is the authoritative source for this
rule — any system that decides which retention action to trigger for a
customer must trace back to this document, not to a hardcoded threshold in
application code.

## Defined terms

Customers are assigned to one of the following segments:

| Code | Meaning |
|------|---------|
| `high-value` | Customer lifetime value (LTV) above $5,000 |
| `standard`   | LTV between $1,000 and $5,000 |
| `at-risk`    | Churn risk score above 70 |
| `dormant`    | No purchase in over 365 days and churn risk score above 90 |

## Retention trigger rules

| Rule | Condition (SQL expression) | Action | Timeline | Channel |
|------|-----------------------------|--------|----------|---------|
| `VIPRetention` | `customer_ltv > 5000 AND churn_risk_score > 50` | `Assign a dedicated account manager and initiate personal retention outreach` | `immediate` | `dedicated_account_manager` |
| `RetentionOffer24h` | `churn_risk_score > 85` | `Send a personalized discount offer` | `within 24 hours` | `email, sms, in-app` |
| `WinBackCampaign` | `days_since_last_purchase > 365 AND churn_risk_score > 90` | `Send a win-back campaign with a comeback discount` | `within 7 days` | `email, direct_mail, paid_social` |

A customer may match more than one rule — every matching action triggers
independently. This document does not impose a priority order between
them.

## Out of scope

Customers who match none of the rules above (low or medium churn risk, no
LTV or recency trigger) are covered by routine marketing calendars, not by
this policy.

## Revision history

| Version | Date | Change |
|---------|------|--------|
| 1.0 | 2026-05-01 | Initial publication of the three retention trigger rules |
