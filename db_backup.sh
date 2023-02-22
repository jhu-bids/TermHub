#! /bin/sh

dt=$(date +%Y%m%d)
cat <<-END
How to make a backup of n3c schema
----------------------------------
In psql alter name of n3c to desired name of backup schema:

  alter SCHEMA n3c RENAME TO n3c_backup_$dt;

Then create backup file \(from cmd line\):

  pg_dump -d \$psql_conn -n n3c_backup_$dt -f n3c_backup_$dt.dmp

Then rename back to n3c:

  alter SCHEMA n3c_backup_$dt RENAME TO n3c;

Then restore backup schema:

  psql -d \$psql_conn < n3c_backup_$dt.dmp

END

