sraget
======

Find peer-reviewed data in the NCBI SRA

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
