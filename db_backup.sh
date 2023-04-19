#! /bin/sh
# About
#   pg_dump:
#   - sed: Changes all instances of 'n3c' in the pg_dump file to $fname, but only where 'n3c' appears as a schema name. It does this by looking at any line that isn't a line of data (all lines of data start with a number).

dt=$(date +%Y%m%d)
fname=n3c_backup_$dt

cat <<-END
 

How to make a backup of n3c schema
----------------------------------

Step 1: Backup the DB
pg_dump -d \$psql_conn -n n3c | sed '/^[0-9][0-9]*\t/! s/[[:<:]]n3c[[:>:]]/$fname/' > $fname.dmp

Step 2: Upload
Immediately upload the backup schema to the database.
psql -d \$psql_conn < $fname.dmp

Step 3: Quality control checks
3.1. Make sure that the dump file is around 7.6G and that it appears in the database.
3.2. Run: `make counts-compare-schemas`. If there is a difference in row counts between 'n3c' and the new backup, this will require further analysis to determine why.

END

