#! /bin/sh

dt=$(date +%Y%m%d)
fname=n3c_backup_$dt

cat <<-END
 

How to make a backup of n3c schema
----------------------------------

# sed: Changes all instances of 'n3c' in the pg_dump file to $fname, but only where 'n3c' appears as a schema name. It does this by looking at any line that isn't a line of data (all lines of data start with a number).
pg_dump -d \$psql_conn -n n3c | sed '/^[0-9][0-9]*\t/! s/[[:<:]]n3c[[:>:]]/$fname/' > $fname.dmp 

Then, immediately upload the backup schema to the database:

psql -d \$psql_conn < $fname.dmp

Make sure that the dump file is around 7.9G and that it restored appropriately.

END

