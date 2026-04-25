# Data Dictionary

## leads table

- `lead_id` (`TEXT`): UUID4 primary key for lead. Allowed values: non-null unique UUID string. Derivation: generated in seeding/ingestion.
- `company_name` (`TEXT`): company/account name. Allowed values: non-null text. Derivation: Faker company generator.
- `icp_tier` (`TEXT`): ICP segment. Allowed values: `Tier 1`, `Tier 2`, `Tier 3`. Derivation: weighted random by configured tier weights.
- `persona` (`TEXT`): buyer/contact persona. Allowed values: configured persona list. Derivation: random selection.
- `source` (`TEXT`): lead source channel. Allowed values: `Outbound`, `Inbound`, `Referral`, `Event`. Derivation: weighted random by source weights.
- `industry` (`TEXT`): company industry. Allowed values: configured industry list. Derivation: random selection or provided API input.
- `employee_count` (`INTEGER`): company employee count. Allowed values: positive integer in tier range. Derivation: random in configured range by tier or provided API input.
- `annual_revenue` (`INTEGER`): company annual revenue (USD). Allowed values: non-negative integer in tier range. Derivation: random in configured range by tier or provided API input.
- `region` (`TEXT`): sales region. Allowed values: configured region list. Derivation: random selection or provided API input.
- `owner_name` (`TEXT`): account owner. Allowed values: non-null text. Derivation: random selection from owner pool or provided API input.
- `created_at` (`DATE`): lead creation date. Allowed values: non-null ISO date, up to today. Derivation: generated with 90-day lookback or provided API input.

## sequences table

- `sequence_id` (`TEXT`): UUID4 primary key for sequence record. Allowed values: non-null unique UUID string. Derivation: generated in seeding/ingestion.
- `lead_id` (`TEXT`): FK to leads table. Allowed values: existing `leads.lead_id`. Derivation: copied from parent lead record.
- `sequence_name` (`TEXT`): outreach/playbook name. Allowed values: source-mapped sequence names. Derivation: random choice from `SOURCE_TO_SEQUENCES[source]`.
- `step_count` (`INTEGER`): number of sequence steps. Allowed values: integer from 1 to 8. Derivation: random integer.
- `replied` (`INTEGER`): reply flag. Allowed values: `0` or `1`. Derivation: Bernoulli trial with tier-specific reply rate.
- `converted_to_opp` (`INTEGER`): opportunity conversion flag. Allowed values: `0` or `1`. Derivation: conditional Bernoulli trial if replied.
- `deal_value` (`INTEGER`): opportunity value in USD. Allowed values: `0` for non-converted; positive integer for converted. Derivation: tier range with optional outlier multiplier.
- `status` (`TEXT`): pipeline status. Allowed values: `Open`, `Closed Won`, `Closed Lost`, `No Reply`, `Replied - No Opp`. Derivation: deterministic from reply/convert flags plus weighted status logic.
- `started_at` (`DATE`): sequence start date. Allowed values: non-null ISO date, not in future. Derivation: `created_at + 0..3 days` (capped to maintain chronology).
- `last_touch_at` (`DATE`): final touchpoint date. Allowed values: non-null ISO date, not in future. Derivation: `started_at + step_count*(2..4) days` (capped to maintain chronology).
- `opportunity_created_at` (`DATE`): opportunity creation date. Allowed values: null if not converted, otherwise ISO date not in future. Derivation: `last_touch_at + 1..7 days` for converted.
- `closed_at` (`DATE`): close date. Allowed values: null for `Open`, `No Reply`, `Replied - No Opp`; otherwise ISO date not in future. Derivation: `opportunity_created_at + 14..90 days` for closed statuses.
