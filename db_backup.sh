#! /bin/sh

dt=$(date +%Y%m%d)
fname=n3c_backup_$dt

cat <<-END
 

How to make a backup of n3c schema
----------------------------------

pg_dump -d \$psql_conn -n n3c | sed '/^[0-9][0-9]*\t/! s/[[:<:]]n3c[[:>:]]/$fname/' > $fname.dmp 

Then restore backup schema:

psql -d \$psql_conn < $fname.dmp

Make sure that the dump file is around 7.9G and that it restored appropriately.

END

