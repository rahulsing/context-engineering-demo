#!/usr/bin/env python3
"""
Bootstrap script for retail/e-commerce customer analytics demo.
Seeds DuckDB with sample customer metrics data.

Run once to initialize: python bootstrap.py
"""

import duckdb
import os
from datetime import datetime, timedelta
import random

def bootstrap_customer_analytics():
    """Create and seed customer_metrics table with sample data."""

    db_path = "customer_analytics.duckdb"

    # Remove existing DB to start fresh
    if os.path.exists(db_path):
        os.remove(db_path)
        print(f"Removed existing database: {db_path}")

    # Connect to DuckDB
    conn = duckdb.connect(db_path)

    # Create customer_metrics table
    conn.execute("""
        CREATE TABLE customer_metrics (
            customer_id VARCHAR,
            region VARCHAR,
            customer_ltv DECIMAL(10, 2),
            churn_risk_score INTEGER,
            repeat_purchase_rate DECIMAL(5, 1),
            average_order_value DECIMAL(10, 2),
            purchase_frequency_12m DECIMAL(10, 1),
            days_since_last_purchase INTEGER,
            return_rate DECIMAL(5, 1),
            segment VARCHAR,
            updated_date DATE
        )
    """)

    print("✓ Created customer_metrics table")

    # Sample customer data
    regions = ["US", "EU", "APAC"]
    segments = ["high-value", "standard", "at-risk", "dormant"]

    customers_data = [
        # High-value customers (LTV > $5000)
        ("CUST_00001", "US", 8750.00, 15, 78.5, 156.25, 14.2, 3, 2.1, "high-value"),
        ("CUST_00002", "EU", 6290.50, 22, 65.3, 134.50, 11.8, 8, 3.2, "high-value"),
        ("CUST_00003", "APAC", 7145.75, 18, 72.1, 145.80, 12.5, 5, 2.8, "high-value"),

        # Standard customers (LTV $1000-$5000)
        ("CUST_00004", "US", 2847.00, 72, 45.2, 87.99, 8.5, 23, 12.3, "standard"),
        ("CUST_00005", "EU", 3421.50, 55, 52.0, 98.75, 9.2, 15, 8.5, "standard"),
        ("CUST_00006", "APAC", 1850.25, 68, 38.7, 72.50, 7.1, 31, 15.2, "standard"),
        ("CUST_00007", "US", 4100.00, 48, 60.0, 115.00, 10.5, 12, 6.5, "standard"),

        # At-risk customers (churn score > 70)
        ("CUST_00008", "EU", 1200.75, 82, 22.5, 55.25, 3.8, 67, 28.5, "at-risk"),
        ("CUST_00009", "US", 890.50, 89, 15.3, 42.10, 2.5, 89, 35.2, "at-risk"),
        ("CUST_00010", "APAC", 650.25, 86, 18.0, 38.50, 2.9, 74, 32.1, "at-risk"),

        # Dormant customers
        ("CUST_00011", "US", 125.00, 98, 2.5, 25.00, 0.5, 412, 50.0, "dormant"),
        ("CUST_00012", "EU", 89.50, 99, 1.0, 18.90, 0.3, 567, 60.0, "dormant"),
    ]

    # Insert sample data with calculated updated_date
    today = datetime.now().date()
    for cust_id, region, ltv, churn, repeat, aov, freq, days_since, ret_rate, seg in customers_data:
        conn.execute(
            """
            INSERT INTO customer_metrics VALUES
            (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                cust_id,
                region,
                ltv,
                churn,
                repeat,
                aov,
                freq,
                days_since,
                ret_rate,
                seg,
                today
            ]
        )

    conn.commit()

    # Verify data
    result = conn.execute("SELECT COUNT(*) as row_count FROM customer_metrics").fetchall()
    row_count = result[0][0]

    print(f"✓ Seeded customer_metrics: {row_count} rows → {db_path}")
    print()
    print("Sample data (first 5 customers):")
    print("-" * 100)

    sample = conn.execute("""
        SELECT
            customer_id,
            region,
            customer_ltv,
            churn_risk_score,
            segment,
            updated_date
        FROM customer_metrics
        LIMIT 5
    """).fetch_arrow_table().to_pandas()

    print(sample.to_string(index=False))
    print()
    print("✓ Bootstrap complete!")
    print()
    print("Next steps:")
    print("  1. Run: python agent.py (Anthropic API)")
    print("  2. Or:  python agent_ollama.py (Local Ollama)")

    conn.close()

if __name__ == "__main__":
    bootstrap_customer_analytics()
