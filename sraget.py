#!/usr/bin/env python

# sraget - Find peer-reviewed data in the NCBI SRA
# Copyright (C) 2013  Rupert Shuttleworth
# optimuscoprime@gmail.com

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

import sys
import pdb
import os
import urllib
import urllib2
import cookielib
import re
import argparse
import threading
import Queue

ENTREZ_PAGE_SIZE = 100

DEFAULT_ENTREZ_PARAMETERS = {
    "EntrezSystem2.PEntrez.Sra.Sra_PageController.PreviousPageName": "results",
    "EntrezSystem2.PEntrez.Sra.Sra_Facets.FacetsUrlFrag": "filters=",
    "EntrezSystem2.PEntrez.Sra.Sra_Facets.FacetSubmitted": "false",
    "EntrezSystem2.PEntrez.Sra.Sra_Facets.BMFacets": "",
    "EntrezSystem2.PEntrez.Sra.Sra_ResultsPanel.Sra_DisplayBar.sPresentation": "DocSum",
    "EntrezSystem2.PEntrez.Sra.Sra_ResultsPanel.Sra_DisplayBar.sPageSize": ENTREZ_PAGE_SIZE,
    "EntrezSystem2.PEntrez.Sra.Sra_ResultsPanel.Sra_DisplayBar.FFormat": "docsumcsv",
    "EntrezSystem2.PEntrez.Sra.Sra_ResultsPanel.Sra_DisplayBar.FileFormat": "docsum",
    "EntrezSystem2.PEntrez.Sra.Sra_ResultsPanel.Sra_DisplayBar.LastPresentation": "docsum",
    "EntrezSystem2.PEntrez.Sra.Sra_ResultsPanel.Sra_DisplayBar.Presentation": "docsum",
    "EntrezSystem2.PEntrez.Sra.Sra_ResultsPanel.Sra_DisplayBar.PageSize": ENTREZ_PAGE_SIZE,
    "EntrezSystem2.PEntrez.Sra.Sra_ResultsPanel.Sra_DisplayBar.LastPageSize": ENTREZ_PAGE_SIZE,
    "EntrezSystem2.PEntrez.Sra.Sra_ResultsPanel.Sra_DisplayBar.Format": "",
    "EntrezSystem2.PEntrez.Sra.Sra_ResultsPanel.Sra_DisplayBar.LastFormat": "",
    "EntrezSystem2.PEntrez.Sra.Sra_ResultsPanel.Sra_ResultsController.RunLastQuery": "",
    "EntrezSystem2.PEntrez.Sra.Sra_ResultsPanel.Sra_DisplayBar.sPresentation2": "DocSum",
    "EntrezSystem2.PEntrez.Sra.Sra_ResultsPanel.Sra_DisplayBar.sPageSize2": ENTREZ_PAGE_SIZE,
    "EntrezSystem2.PEntrez.Sra.Sra_ResultsPanel.Sra_DisplayBar.FFormat2": "docsumcsv",
    "EntrezSystem2.PEntrez.Sra.Sra_ResultsPanel.Sra_MultiItemSupl.RelatedDataLinks.rdDatabase": "rddbto",
    "EntrezSystem2.PEntrez.Sra.Sra_ResultsPanel.Sra_MultiItemSupl.RelatedDataLinks.DbName": "sra",
    "EntrezSystem2.PEntrez.Sra.Sra_ResultsPanel.HistoryDisplay.Cmd": "PageChanged",
    "EntrezSystem2.PEntrez.DbConnector.Db": "sra",
    "EntrezSystem2.PEntrez.DbConnector.LastDb": "sra",
    "EntrezSystem2.PEntrez.DbConnector.LastTabCmd": "",
    "EntrezSystem2.PEntrez.DbConnector.LastQueryKey": 1,
    "EntrezSystem2.PEntrez.DbConnector.IdsFromResult": "",
    "EntrezSystem2.PEntrez.DbConnector.LastIdsFromResult": "",
    "EntrezSystem2.PEntrez.DbConnector.LinkName": "",
    "EntrezSystem2.PEntrez.DbConnector.LinkReadableName": "",
    "EntrezSystem2.PEntrez.DbConnector.LinkSrcDb": "",
    "EntrezSystem2.PEntrez.DbConnector.Cmd": "PageChanged",
    "EntrezSystem2.PEntrez.DbConnector.TabCmd": "",
    "EntrezSystem2.PEntrez.DbConnector.QueryKey": "",
    "p$a": "EntrezSystem2.PEntrez.Sra.Sra_ResultsPanel.Entrez_Pager.Page",
    "p$l": "EntrezSystem2",
    "p$st": "sra",
}

ENTREZ_HEADERS = {
    'Content-Type': 'application/x-www-form-urlencoded',
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.8; rv:21.0) Gecko/20100101 Firefox/21.0',
    'Referer': 'http://www.ncbi.nlm.nih.gov/sra',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
}

RE_ACCESSION = re.compile(r'<dl class="rprtid"><dt>Accession:\s*</dt>\s*<dd>([^<]*)</dd></dl>', re.M)
RE_ACCESSION_BIOPROJECT = re.compile(r'href="(/[^"]+LinkName=sra_bioproject[^"]+)"', re.M)
RE_ACCESSION_PUBMED = re.compile(r'href="/pubmed\?LinkName=sra_pubmed', re.M)
RE_PUBLICATIONS = re.compile(r'<div class="SecTitle">Publications:</div>', re.M)
RE_RESULT_COUNT = re.compile(r'result_count', re.M)
RE_MULTIPLE_BIOPROJECT = re.compile(r'<a href="(/bioproject/\d+)" ref="', re.M)

# TODO does this table ever show up even with 0 publications?
RE_PUBLICATIONS_TABLE = re.compile(r'<class="DataGrp">Publications', re.M)

RE_RUN_ACCESSION = re.compile(r'href="(ftp://ftp-trace.ncbi.nlm.nih.gov/sra/sra-instant/reads/ByRun/sra/.RR/.RR[0-9][0-9][0-9]/(.RR[0-9]+))', re.M)

# global variables needed for threading
page_potential_experiment_accessions = None
page_valid_experiments = None
semaphore = threading.Semaphore()

# disable buffering so that prints go straight to the screen
sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 0)
sys.stderr = os.fdopen(sys.stderr.fileno(), 'w', 0)

def main():    
    args = parse_arguments()
    num_threads = args.threads
    show_runs = not args.hide_runs
    
    # query strings can be too long for arguments
    # so we take the query on stdin instead
    log("NCBI SRA search query: ", stderr=True, newline=False)
    term = raw_input()
    log("", stderr=True)

    params = DEFAULT_ENTREZ_PARAMETERS.copy()
    params.update({
        "term": term,
        "EntrezSystem2.PEntrez.DbConnector.Term": term,
        "EntrezSystem2.PEntrez.Sra.Sra_ResultsPanel.Discovery_SearchDetails.SearchDetailsTerm": term,
    })

    filtered_experiments = {}
    page_number = 1

    has_more_pages = True
    while has_more_pages:
        log("Processing Page %d..." % (page_number), stderr=True)

        # for handling entrez cookies for this page
        urllib2.install_opener(urllib2.build_opener(
            urllib2.HTTPCookieProcessor(cookielib.LWPCookieJar())
        ))

        url = "http://www.ncbi.nlm.nih.gov/sra?term=%s" % (urllib.quote_plus(term))

        log("Asking for a cookie... ", stderr=True, newline=False)
        retry_request(urllib2.Request(
            url=url,
            headers=ENTREZ_HEADERS
        ))
        log("Done.", stderr=True)

        log("Asking for results for page %d... " % (page_number), stderr=True, newline=False)
        page = retry_request(urllib2.Request(
            url=url,
            data=urllib.urlencode(params),
            headers=ENTREZ_HEADERS
        ))
        log("Done.", stderr=True)

        has_more_pages = process_search_results_page(
            filtered_experiments,
            page,
            page_number,
            num_threads=num_threads
        )

        if has_more_pages:
            page_number = page_number + 1
            params.update({
                "EntrezSystem2.PEntrez.Sra.Sra_ResultsPanel.Entrez_Pager.CurrPage": page_number,
                "EntrezSystem2.PEntrez.Sra.Sra_ResultsPanel.Entrez_Pager.cPage": page_number,
            })

    if len(filtered_experiments) > 0:
        log("", stderr=True)
        log("Results:", stderr=True)
        log("", stderr=True)
        total_runs = 0
        for experiment_accession in sorted(filtered_experiments.iterkeys()):
            experiment = filtered_experiments[experiment_accession]
            if show_runs:
                for run in sorted(experiment["runs"], key=lambda x: x["accession"]):
                    log("%s\t%s\t%s" % (experiment_accession, run["accession"], run["url"]))
                    total_runs += 1
            else:
                log("%s" % (experiment_accession))
        log("", stderr=True)
        if show_runs:
            log("Total: %d experiments, %d runs." % (len(filtered_experiments), total_runs), stderr=True)
        else:
            log("Total: %d experiments." % (len(filtered_experiments)), stderr=True)
    else:
        log("No results.", stderr=True)

def process_search_results_page(filtered_experiments, page, page_number, num_threads):
    global page_potential_experiment_accessions
    global page_valid_experiments

    page_potential_experiment_accessions = Queue.Queue()
    page_valid_experiments = Queue.Queue()

    experiment_accession_matches = RE_ACCESSION.findall(page)
    num_experiment_accession_matches = len(experiment_accession_matches)    

    if num_experiment_accession_matches > 0:
        for experiment_accession in experiment_accession_matches:
            page_potential_experiment_accessions.put(experiment_accession)

        log("Creating threads to process page %d" % (page_number), stderr=True)
    
        for i in xrange(num_threads):
            thread = threading.Thread(target=process_experiment_worker)
            thread.setDaemon(True)
            thread.start()

        # wait for processing to complete
        page_potential_experiment_accessions.join()

        num_page_valid_experiments = page_valid_experiments.qsize()

        # consume global queue
        while not page_valid_experiments.empty():
            valid_experiment = page_valid_experiments.get()
            filtered_experiments[valid_experiment["accession"]] = valid_experiment

        log("Found %d/%d valid experiments on page %d (%d total valid experiments so far)." % (
            num_page_valid_experiments, num_experiment_accession_matches, page_number, len(filtered_experiments)
        ), stderr=True)
    else:
        log("No potential experiments found on page %d (%d total valid experiments so far)." % (
            page_number, len(filtered_experiments)
        ), stderr=True)

    if num_experiment_accession_matches < ENTREZ_PAGE_SIZE:
        has_more_pages = False
    else:
        has_more_pages = True
    
    return has_more_pages

# thread template for processing experiment accessions
def process_experiment_worker():
    global page_potential_experiment_accessions

    while True:
        if page_potential_experiment_accessions.empty():
            sys.exit(-1)
        try:
            experiment_accession = page_potential_experiment_accessions.get()
            process_experiment(experiment_accession)
            page_potential_experiment_accessions.task_done()
        except Exception as e:
            log("Failed to process experiment %s" % (e), stderr=True)
            sys.exit(-1)

def process_experiment(experiment_accession):
    global page_valid_experiments

    valid_experiment = False
    status = "UNPUBLISHED"

    experiment_page=retry_request(urllib2.Request(
        url="http://www.ncbi.nlm.nih.gov/sra/?term=%s&report=Full" % (experiment_accession),
        headers=ENTREZ_HEADERS
    ))

    # first check if there is a pubmed link
    pubmed_matches = RE_ACCESSION_PUBMED.findall(experiment_page)

    if len(pubmed_matches) == 1:
        valid_experiment = True
        status = "OK PUBMED-LINK"
    else:        
        # otherwise, check if there is a bioproject
        bioproject_matches = RE_ACCESSION_BIOPROJECT.findall(experiment_page)
        if len(bioproject_matches) == 0:
            status = "UNPUBLISHED NO-BIOPROJECT"
        else:
            assert len(bioproject_matches) == 1
            bioproject = bioproject_matches[0]

            bioproject_page = retry_request(urllib2.Request(
                url="http://www.ncbi.nlm.nih.gov" + bioproject,
                headers=ENTREZ_HEADERS
            ))

            bioprojects = set() 

            # check if there are several bioprojects
            result_count_matches = RE_RESULT_COUNT.findall(bioproject_page)

            if len(result_count_matches) == 0:
                # we are already on the right page
                # save it
                bioprojects.add(bioproject)
            else:
                # we have multiple bioproject results
                # save each one
                multiple_bioproject_matches = RE_MULTIPLE_BIOPROJECT.findall(bioproject_page)
                assert len(multiple_bioproject_matches) > 1
                for bioproject in multiple_bioproject_matches:
                    bioprojects.add(bioproject)

            for bioproject in bioprojects:
                bioproject_page = retry_request(urllib2.Request(
                    url="http://www.ncbi.nlm.nih.gov" + bioproject,
                    headers=ENTREZ_HEADERS
                ))

                # look for project publications
                bioproject_publications_matches = RE_PUBLICATIONS.findall(bioproject_page)

                if len(bioproject_publications_matches) == 1:
                    valid_experiment = True
                    status = "OK BIOPROJECT-LINK"
                    break
                else:
                    # look for project publications in another form
                    bioproject_publications_table_matches = RE_PUBLICATIONS_TABLE.findall(bioproject_page)

                    if len(bioproject_publications_table_matches) == 1:
                        valid_experiment = True
                        status = "OK BIOPROJECT-TABLE"
                        break
                    else:
                        status = "UNPUBLISHED NO-BIOPROJECT-LINK-OR-TABLE"
            
    if valid_experiment:
        runs_matches = RE_RUN_ACCESSION.findall(experiment_page)
        if len(runs_matches) > 0:
            runs = []
            # TODO are we guaranteed the runs will be unique?
            for run_match in runs_matches:
                runs.append({
                    "accession": run_match[1],
                    "url": "%s/%s.sra" % (run_match[0], run_match[1])
                })
        else:
            status = "NO RUNS"
            valid_experiment = False

        if valid_experiment:
            experiment = {
                "accession": experiment_accession,
                "runs": runs
            }
            page_valid_experiments.put(experiment)

    log("%s\t%s" % (experiment_accession, status), stderr=True)

# prevents bad interleavings of printed characters
def log(str, stderr=False, newline=True):
    semaphore.acquire()
    if stderr:
        if newline:
            sys.stderr.write("%s\n" % str)
        else:
            sys.stderr.write(str)
    else:
        if newline:
            print str
        else:
            print str,
    semaphore.release()

# Keep retrying a failed HTTP request
def retry_request(request, max_retries=10):
    got_page = False
    page = None
    num_retries = 0
    while not got_page and num_retries < max_retries:
        try:
            page = urllib2.urlopen(request).read()
            got_page = True
        except:
            num_retries += 1
    return page

def parse_arguments():
    description = 'Find peer-reviewed data in the NCBI SRA'
    parser = argparse.ArgumentParser(
        description=description,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    parser.add_argument('--threads',
        help="number of threads",
        default=8,
        type=int,
        required=False
    )   

    parser.add_argument('--hide-runs',
        help='hide information about runs',
        action='store_const',
        const=True,
        default=False,
        required=False
    )

    args = parser.parse_args()

    return args

if __name__ == "__main__":
    main()
