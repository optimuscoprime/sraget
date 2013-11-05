sraget
======

sraget - Find peer-reviewed data in the NCBI SRA
Copyright (C) 2013  Rupert Shuttleworth
optimuscoprime@gmail.com

Overview
--------

There is a lot of sequencing data available on the NCBI Sequence Read Archive, but only some of the data has a record of being published. This script finds data with explicit links to publications (in journals, etc.).

Output
------

The script outputs experiment accessions, run accessions and download URLs for data which matches the search query and also has a record of being published.

If you want to save just the accessions and URLs into a file, you could run the script like this:

<pre>
./sraget.py | tee results
</pre>

Usage
-----

<pre>
usage: sraget.py [-h] [--threads THREADS] [--hide-runs]

Find peer-reviewed data in the NCBI SRA

optional arguments:
  -h, --help         show this help message and exit
  --threads THREADS  number of threads (default: 8)
  --hide-runs        hide information about runs (default: False)
</pre>
