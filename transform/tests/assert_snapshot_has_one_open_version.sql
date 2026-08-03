-- A snapshot must hold exactly one *open* version per key. Nothing in dbt
-- enforces that: a customer deleted and later re-signed under the same id
-- leaves two rows with dbt_valid_to IS NULL, because the deletion is stamped
-- with dbt's clock and the revival with the source's, and the two cannot be
-- ordered. Part 3 finds that failure; this test is what turns it from silent
-- into loud. Returning zero rows is a pass.
select
    customer_id,
    count(*) as open_versions
from {{ ref('customers_snapshot') }}
where dbt_valid_to is null
group by customer_id
having count(*) > 1
