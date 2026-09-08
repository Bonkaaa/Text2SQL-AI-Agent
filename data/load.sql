COPY customer FROM 'tpch_parquet/customer.parquet' (FORMAT 'parquet');
COPY lineitem FROM 'tpch_parquet/lineitem.parquet' (FORMAT 'parquet');
COPY nation FROM 'tpch_parquet/nation.parquet' (FORMAT 'parquet');
COPY orders FROM 'tpch_parquet/orders.parquet' (FORMAT 'parquet');
COPY part FROM 'tpch_parquet/part.parquet' (FORMAT 'parquet');
COPY partsupp FROM 'tpch_parquet/partsupp.parquet' (FORMAT 'parquet');
COPY region FROM 'tpch_parquet/region.parquet' (FORMAT 'parquet');
COPY supplier FROM 'tpch_parquet/supplier.parquet' (FORMAT 'parquet');
