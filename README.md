sraget
======

Overview
--------

As of November 2013, the NCBI Sequence Read Archive (SRA) contains over three million gigabytes of DNA and RNA sequencing files.

Each file has a publication date, which appears to be the date that the file was made available on the SRA. However, we were interested in whether any data had actually been used to write a paper which had been published in a journal. In particular, we thought this might be a proxy for “good quality” data. So we developed a program to automatically check various webpages and identify the SRA data which had corresponding journal publications.

License
-------

<pre>
sraget - Find peer-reviewed data in the NCBI SRA
Copyright (C) 2013  Rupert Shuttleworth
optimuscoprime@gmail.com

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License along
with this program; if not, write to the Free Software Foundation, Inc.,
51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
</pre>

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
