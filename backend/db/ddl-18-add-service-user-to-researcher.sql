-- A lot of code sets are created_by the service user, who does not appear in the
-- researcher table. Easiest way to deal with this is to add it

INSERT INTO {{schema}}researcher ("multipassId", "emailAddress", institution, name)
SELECT '6387db50-9f12-48d2-b7dc-e8e88fdf51e3', 'termhub-support@jh.edu', 'Johns Hopkins University BIDS', 'UNITEConceptSetBulkImportUser'
WHERE NOT EXISTS (
    SELECT 1 FROM researcher WHERE "multipassId" = '6387db50-9f12-48d2-b7dc-e8e88fdf51e3'
);

CREATE INDEX ON {{schema}}researcher("multipassId");